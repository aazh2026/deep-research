"""
RepoCoder reproduction: 5 line-completion tasks with 3 methods.

Methods compared:
  1. In-File      — only in-file context, no retrieval
  2. RepoCoder-1  — vanilla RAG (1 retrieval iteration)
  3. RepoCoder-2  — iterative RAG (use iter-1's output to query iter-2)

We use a sparse bag-of-words retriever (Jaccard similarity) over a
synthetic mini-repo with cross-file dependencies (utils.py + stats.py +
app.py), testing whether the agent can complete `add(a, b)`, `divide(a, b)`,
`median(values)`, `variance(values)` etc.

LLM is the same one used in previous rounds (MiniMax-M3.1-Flash-Preview).
"""
import os
import re
import json
import time
from pathlib import Path

# env
ENV = Path(__file__).parent / ".env"
if ENV.exists():
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k] = v

import litellm

HERE = Path(__file__).parent
SANDBOX = HERE / "_sandbox"
DATA = HERE / "data"
OUT = HERE / "_reproduction_results.json"
LOG = HERE / "_reproduction_log.txt"
MODEL = "openai/MiniMax-M3.1-Flash-Preview"

# ---- retriever: Jaccard on tokenized code ----
def jaccard(s1, s2):
    t1 = set(re.findall(r"\w+", s1.lower()))
    t2 = set(re.findall(r"\w+", s2.lower()))
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / len(t1 | t2)

def retrieve(query, code_files, k=5):
    """Return top-k code chunks by Jaccard similarity."""
    scored = []
    for path, content in code_files.items():
        # chunk by function (or by ~30 lines for non-function code)
        chunks = split_into_chunks(content)
        for ch in chunks:
            s = jaccard(query, ch)
            if s > 0:
                scored.append((s, path, ch))
    scored.sort(key=lambda x: -x[0])
    return scored[:k]

def split_into_chunks(content):
    """Split code into chunks (one per function, fallback: 30-line windows)."""
    chunks = []
    lines = content.splitlines()
    # Try function-based chunking
    current = []
    for ln in lines:
        if re.match(r"^(def |class )", ln) and current:
            chunks.append("\n".join(current))
            current = [ln]
        else:
            current.append(ln)
    if current:
        chunks.append("\n".join(current))
    # Filter very small chunks
    chunks = [c for c in chunks if len(c) > 20]
    return chunks

# ---- LLM call ----
def llm_complete(system, user, max_tokens=200):
    try:
        resp = litellm.completion(
            model=MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            api_base=os.environ["OPENAI_API_BASE_URL"],
            api_key=os.environ["OPENAI_KEY"],
            max_tokens=max_tokens,
            temperature=0.0,
        )
        msg = resp.choices[0].message
        content = (msg.content or "").strip()
        if not content and hasattr(msg, "reasoning_content") and msg.reasoning_content:
            rc = msg.reasoning_content
            content = rc[rc.rfind("\n", 0, max(0, len(rc) - 2000)) + 1:].strip()
        # Post-process: try to extract a code-completion-like line
        content = extract_completion(content)
        return content, resp.usage.prompt_tokens, resp.usage.completion_tokens
    except Exception as e:
        return f"[ERROR: {e}]", 0, 0

def extract_completion(raw):
    """Try to extract a single-line code completion from a possibly chatty response."""
    if not raw:
        return ""
    raw = raw.strip()
    # Find a backtick-wrapped code segment first
    m = re.search(r"`([^`\n]{1,80})`", raw)
    if m:
        return m.group(1).strip()
    # Otherwise: find the first line that looks like a function call (contains "()" )
    for line in raw.splitlines():
        line = line.strip()
        if re.match(r"^[a-zA-Z_][\w.]*\(.*\)[,;]?$", line):
            return line
    # Otherwise: return first non-empty line trimmed
    for line in raw.splitlines():
        line = line.strip()
        if line and not line.startswith(("We ", "Let ", "The ", "I ", "Need ", "Looking ", "Given ", "Context ", "Current ", "Output", "Completion")):
            # If line ends with ``` or has code-fence chars, strip
            line = re.sub(r"```.*$", "", line).strip()
            if line:
                return line
    return raw.split("\n")[0].strip()

# ---- prompts ----
SYSTEM = (
    "You are a Python code completion assistant. "
    "Output ONLY the completion text (typically a function call like `add(a, b),`). "
    "ABSOLUTELY NO commentary, NO explanation, NO markdown, NO code fences. "
    "Output the SHORTEST valid completion. "
    "Start your reply with the completion directly — never with words like 'We', 'The', 'I', 'Need'."
)

def make_in_file_prompt(in_file_context, file_path):
    return f"File: {file_path}\n\n{in_file_context}"

def make_rag_prompt(retrieved, in_file_context, file_path):
    """retrieved: list of (score, path, chunk)"""
    parts = [f"# Repository context\n"]
    for score, path, chunk in retrieved:
        parts.append(f"## {path} (relevance={score:.2f})\n```python\n{chunk}\n```\n")
    parts.append(f"\n# Current file: {file_path}\n```python\n{in_file_context}\n```\n")
    parts.append("\n# Complete the unfinished line. Output ONLY the completion text:")
    return "\n".join(parts)

# ---- evaluation ----
def normalize(s):
    s = s.strip()
    # remove leading/trailing quotes, backticks, code fences
    s = re.sub(r"^```python\s*", "", s)
    s = re.sub(r"^```", "", s)
    s = re.sub(r"```\s*$", "", s)
    s = s.strip()
    # first line only
    if "\n" in s:
        s = s.split("\n")[0]
    return s.strip().rstrip(".,;")

def exact_match(pred, gold):
    return normalize(pred) == normalize(gold)

def edit_similarity(pred, gold):
    # Levenshtein-based ES = 1 - lev / max(|pred|, |gold|)
    p, g = normalize(pred), normalize(gold)
    if not p and not g:
        return 1.0
    if not p or not g:
        return 0.0
    lev = levenshtein(p, g)
    return 1.0 - lev / max(len(p), len(g))

def levenshtein(a, b):
    if len(a) < len(b):
        return levenshtein(b, a)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        cur = [i + 1]
        for j, cb in enumerate(b):
            cost = 0 if ca == cb else 1
            cur.append(min(cur[-1] + 1, prev[j + 1] + 1, prev[j] + cost))
        prev = cur
    return prev[-1]

# ---- main ----
def main():
    # Load sandbox files (retrieval corpus)
    code_files = {}
    for f in SANDBOX.glob("*.py"):
        if f.name in ("app.py",):  # exclude target file from corpus
            continue
        code_files[f.name] = f.read_text()
    print(f"Retrieval corpus: {list(code_files.keys())}", flush=True)

    # Load tasks
    with (DATA / "tasks.json").open() as f:
        tasks = json.load(f)

    results = []
    log = LOG.open("w")
    # Run each method N_RUNS times to average LLM variance
    N_RUNS = 2

    for i, t in enumerate(tasks, 1):
        in_file_context = t["in_file_context"]
        file_path = t["file"]
        gold = t["ground_truth"]

        # === Method 1: In-File (N_RUNS averaged) ===
        prompt_if = make_in_file_prompt(in_file_context, file_path)
        if_preds, if_ems, if_ess, if_in_tok, if_out_tok = [], [], [], 0, 0
        for _ in range(N_RUNS):
            o, i_t, o_t = llm_complete(SYSTEM, prompt_if, max_tokens=80)
            if_preds.append(o)
            if_ems.append(int(exact_match(o, gold)))
            if_ess.append(edit_similarity(o, gold))
            if_in_tok += i_t
            if_out_tok += o_t
        out_if = if_preds[0]  # canonical: first run
        em_if = sum(if_ems) / N_RUNS
        es_if = sum(if_ess) / N_RUNS

        # === Method 2: RepoCoder-1 (single iteration) ===
        query = "\n".join(in_file_context.splitlines()[-5:])
        retrieved1 = retrieve(query, code_files, k=3)
        prompt_r1 = make_rag_prompt(retrieved1, in_file_context, file_path)
        r1_preds, r1_ems, r1_ess, r1_in_tok, r1_out_tok = [], [], [], 0, 0
        for _ in range(N_RUNS):
            o, i_t, o_t = llm_complete(SYSTEM, prompt_r1, max_tokens=80)
            r1_preds.append(o)
            r1_ems.append(int(exact_match(o, gold)))
            r1_ess.append(edit_similarity(o, gold))
            r1_in_tok += i_t
            r1_out_tok += o_t
        out_r1 = r1_preds[0]
        em_r1 = sum(r1_ems) / N_RUNS
        es_r1 = sum(r1_ess) / N_RUNS

        # === Method 3: RepoCoder-2 (iterative) ===
        query2 = query + "\n" + (out_r1 or "")
        retrieved2 = retrieve(query2, code_files, k=3)
        prompt_r2 = make_rag_prompt(retrieved2, in_file_context, file_path)
        r2_preds, r2_ems, r2_ess, r2_in_tok, r2_out_tok = [], [], [], 0, 0
        for _ in range(N_RUNS):
            o, i_t, o_t = llm_complete(SYSTEM, prompt_r2, max_tokens=80)
            r2_preds.append(o)
            r2_ems.append(int(exact_match(o, gold)))
            r2_ess.append(edit_similarity(o, gold))
            r2_in_tok += i_t
            r2_out_tok += o_t
        out_r2 = r2_preds[0]
        em_r2 = sum(r2_ems) / N_RUNS
        es_r2 = sum(r2_ess) / N_RUNS

        entry = {
            "task_id": t["task_id"],
            "category": t["category"],
            "gold": gold,
            "n_runs": N_RUNS,
            "in_file": {"pred": out_if, "em": round(em_if, 3), "es": round(es_if, 3),
                        "all_preds": if_preds, "all_ems": if_ems,
                        "in_tok": if_in_tok, "out_tok": if_out_tok},
            "repocoder_1": {"pred": out_r1, "em": round(em_r1, 3), "es": round(es_r1, 3),
                            "all_preds": r1_preds, "all_ems": r1_ems,
                            "in_tok": r1_in_tok, "out_tok": r1_out_tok,
                            "top1_path": retrieved1[0][1] if retrieved1 else None},
            "repocoder_2": {"pred": out_r2, "em": round(em_r2, 3), "es": round(es_r2, 3),
                            "all_preds": r2_preds, "all_ems": r2_ems,
                            "in_tok": r2_in_tok, "out_tok": r2_out_tok,
                            "top1_path": retrieved2[0][1] if retrieved2 else None},
        }
        results.append(entry)
        sym_if = "✓" if em_if >= 0.5 else "✗"
        sym_r1 = "✓" if em_r1 >= 0.5 else "✗"
        sym_r2 = "✓" if em_r2 >= 0.5 else "✗"
        print(
            f"  [{i}] {t['task_id']:18s} In-File={sym_if}(em={em_if:.2f}, es={es_if:.2f}) "
            f"R1={sym_r1}(em={em_r1:.2f}, es={es_r1:.2f}, top={entry['repocoder_1']['top1_path']}) "
            f"R2={sym_r2}(em={em_r2:.2f}, es={es_r2:.2f}, top={entry['repocoder_2']['top1_path']})",
            flush=True,
        )
        log.write(f"=== {t['task_id']} ===\n")
        log.write(f"Gold: {gold!r}\n")
        log.write(f"In-File:  pred={out_if!r}, em={em_if}, es={es_if:.3f}\n")
        log.write(f"  prompt: {prompt_if[:200]}\n")
        log.write(f"R1: pred={out_r1!r}, em={em_r1}, es={es_r1:.3f}\n")
        log.write(f"  top-3: {[(p, round(s, 2)) for s, p, _ in retrieved1]}\n")
        log.write(f"R2: pred={out_r2!r}, em={em_r2}, es={es_r2:.3f}\n")
        log.write(f"  top-3: {[(p, round(s, 2)) for s, p, _ in retrieved2]}\n\n")

    # Summary
    n = len(results)
    summary = {
        "n": n,
        "n_runs_per_method": N_RUNS,
        "in_file": {
            "em_mean": sum(r["in_file"]["em"] for r in results) / n,
            "es_mean": sum(r["in_file"]["es"] for r in results) / n,
        },
        "repocoder_1": {
            "em_mean": sum(r["repocoder_1"]["em"] for r in results) / n,
            "es_mean": sum(r["repocoder_1"]["es"] for r in results) / n,
        },
        "repocoder_2": {
            "em_mean": sum(r["repocoder_2"]["em"] for r in results) / n,
            "es_mean": sum(r["repocoder_2"]["es"] for r in results) / n,
        },
        "total_in_tokens": sum(r["in_file"]["in_tok"] + r["repocoder_1"]["in_tok"] + r["repocoder_2"]["in_tok"] for r in results),
        "total_out_tokens": sum(r["in_file"]["out_tok"] + r["repocoder_1"]["out_tok"] + r["repocoder_2"]["out_tok"] for r in results),
    }
    print(f"\n=== Summary (n={n} tasks × {N_RUNS} runs/method) ===", flush=True)
    for m in ["in_file", "repocoder_1", "repocoder_2"]:
        s = summary[m]
        print(f"  {m:14s}: EM_mean={s['em_mean']*100:5.1f}%  ES_mean={s['es_mean']:.3f}", flush=True)
    print(f"  Total tokens: {summary['total_in_tokens']} in / {summary['total_out_tokens']} out", flush=True)

    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    log.close()
    print(f"\nResults: {OUT}", flush=True)


if __name__ == "__main__":
    main()
