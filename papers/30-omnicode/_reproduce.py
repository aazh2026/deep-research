"""
OmniCode reproduction: Bug-Fixing task on 10 Python instances.

We approximate the SWE-bench evaluation without Docker by computing
textual overlap between the LLM-generated patch and the gold patch:
  - exact_match:        generated patch is byte-identical to gold
  - file_overlap:       generated patch touches the same files as gold
  - line_overlap:       generated +/- lines overlap with gold
  - no_empty:           generated patch is non-empty
  - looks_like_diff:    starts with '---' or 'diff --git'

This is a coarse signal but it lets us measure whether the LLM endpoint
can do this task without paying for hours of Docker evaluation.
"""
import os
import re
import sys
import json
import time
import difflib
from pathlib import Path

# Load env
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ[k] = v

import litellm

DATA = Path(__file__).parent / "repo" / "data"
SAMPLE = DATA / "_sample_10.json"
OUT = Path(__file__).parent / "_reproduction_results.json"
LOG = Path(__file__).parent / "_reproduction_log.txt"

# ---- prompt ----
SYSTEM = (
    "You are an expert software engineer. You will be given a GitHub issue "
    "and must produce a unified-diff patch that fixes it. Output ONLY the "
    "diff (starting with 'diff --git' or '--- a/...'), no commentary, no "
    "Markdown fences. The diff must apply cleanly to the repository at HEAD."
)

def make_user_prompt(instance):
    return (
        f"Repository: {instance['repo']}\n"
        f"Commit: {instance['base_commit'][:8]}\n\n"
        f"Issue:\n{instance['problem_statement']}\n\n"
        "Output the unified diff patch now:"
    )

# ---- diff parsing ----
def parse_files(patch_text):
    """Extract set of file paths touched by a diff."""
    files = set()
    for line in patch_text.splitlines():
        m = re.match(r"^\+\+\+ b/(.+)$", line)
        if m:
            files.add(m.group(1))
        m = re.match(r"^--- a/(.+)$", line)
        if m:
            files.add(m.group(1))
    return files

def parse_changed_lines(patch_text):
    """Extract set of +/- content lines (with prefix)."""
    plus, minus = set(), set()
    for line in patch_text.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            plus.add(line[1:])
        elif line.startswith("-"):
            minus.add(line[1:])
    return plus, minus

# ---- evaluation ----
def evaluate(predicted, gold):
    if not predicted or not predicted.strip():
        return {"valid_diff": False, "exact_match": False, "file_overlap": 0.0,
                "line_overlap_plus": 0.0, "line_overlap_minus": 0.0,
                "no_empty": False, "looks_like_diff": False}
    valid = predicted.lstrip().startswith(("diff --git", "--- a/"))
    gold_files = parse_files(gold)
    pred_files = parse_files(predicted)
    file_overlap = len(gold_files & pred_files) / max(len(gold_files), 1)
    g_plus, g_minus = parse_changed_lines(gold)
    p_plus, p_minus = parse_changed_lines(predicted)
    plus_overlap = len(g_plus & p_plus) / max(len(g_plus), 1)
    minus_overlap = len(g_minus & p_minus) / max(len(g_minus), 1)
    return {
        "valid_diff": valid,
        "exact_match": predicted.strip() == gold.strip(),
        "file_overlap": round(file_overlap, 3),
        "line_overlap_plus": round(plus_overlap, 3),
        "line_overlap_minus": round(minus_overlap, 3),
        "no_empty": True,
        "looks_like_diff": valid,
    }

# ---- main ----
def main():
    api_base = os.environ["OPENAI_API_BASE_URL"]
    api_key = os.environ["OPENAI_KEY"]
    model = "openai/MiniMax-M3.1-Flash-Preview"

    with SAMPLE.open() as f:
        instances = json.load(f)
    print(f"Loaded {len(instances)} sample instances\n", flush=True)

    results = []
    with LOG.open("w") as logf:
        for i, inst in enumerate(instances, 1):
            t0 = time.time()
            pred = ""
            in_tok = out_tok = 0
            try:
                resp = litellm.completion(
                    model=model,
                    messages=[
                        {"role": "system", "content": SYSTEM},
                        {"role": "user", "content": make_user_prompt(inst)},
                    ],
                    api_base=api_base,
                    api_key=api_key,
                    max_tokens=16000,
                    temperature=0.0,
                )
                msg = resp.choices[0].message
                pred = (msg.content or "").strip() if msg.content else ""
                # Some responses hide output in reasoning_content when content is None
                if not pred and hasattr(msg, "reasoning_content") and msg.reasoning_content:
                    # Try to extract a diff from reasoning_content
                    rc = msg.reasoning_content
                    if "diff --git" in rc:
                        pred = rc[rc.index("diff --git"):]
                in_tok = resp.usage.prompt_tokens
                out_tok = resp.usage.completion_tokens
            except Exception as e:
                print(f"  [{i}] ERROR: {type(e).__name__}: {e}", flush=True)
            elapsed = time.time() - t0
            metrics = evaluate(pred, inst["patch"])
            entry = {
                "instance_id": inst["instance_id"],
                "repo": inst["repo"],
                "elapsed_s": round(elapsed, 1),
                "in_tokens": in_tok,
                "out_tokens": out_tok,
                "pred_len": len(pred),
                "gold_len": len(inst["patch"]),
                **metrics,
            }
            results.append(entry)
            status = "✓" if metrics["looks_like_diff"] and metrics["file_overlap"] > 0 else "✗"
            print(
                f"  [{i}] {status} {inst['instance_id']:35s} "
                f"file_overlap={metrics['file_overlap']:.2f} "
                f"plus={metrics['line_overlap_plus']:.2f} "
                f"minus={metrics['line_overlap_minus']:.2f} "
                f"({elapsed:.1f}s, {in_tok}→{out_tok} tok)",
                flush=True,
            )
            logf.write(f"=== {inst['instance_id']} ({inst['repo']}) ===\n")
            logf.write(f"Time: {elapsed:.1f}s, tokens {in_tok}→{out_tok}\n")
            logf.write(f"Predicted ({len(pred)} chars):\n{pred[:600]}\n")
            if len(pred) > 600:
                logf.write(f"... [truncated, total {len(pred)} chars]\n")
            logf.write(f"\nGold ({len(inst['patch'])} chars):\n{inst['patch'][:600]}\n")
            if len(inst['patch']) > 600:
                logf.write(f"... [truncated]\n")
            logf.write("\n\n")

        # Aggregate
        n = len(results)
        n_looks_diff = sum(r["looks_like_diff"] for r in results)
        n_nonempty = sum(r["no_empty"] for r in results)
        avg_file = sum(r["file_overlap"] for r in results) / n
        avg_plus = sum(r["line_overlap_plus"] for r in results) / n
        avg_minus = sum(r["line_overlap_minus"] for r in results) / n
        n_exact = sum(r["exact_match"] for r in results)
        total_in = sum(r["in_tokens"] for r in results)
        total_out = sum(r["out_tokens"] for r in results)
        total_time = sum(r["elapsed_s"] for r in results)

        summary = {
            "n_instances": n,
            "n_looks_like_diff": n_looks_diff,
            "n_non_empty": n_nonempty,
            "n_exact_match": n_exact,
            "avg_file_overlap": round(avg_file, 3),
            "avg_line_overlap_plus": round(avg_plus, 3),
            "avg_line_overlap_minus": round(avg_minus, 3),
            "total_in_tokens": total_in,
            "total_out_tokens": total_out,
            "total_time_s": round(total_time, 1),
            "model": model,
        }
        print("\n=== Summary ===", flush=True)
        for k, v in summary.items():
            print(f"  {k}: {v}", flush=True)

    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    print(f"\nResults saved to {OUT}", flush=True)


if __name__ == "__main__":
    main()
