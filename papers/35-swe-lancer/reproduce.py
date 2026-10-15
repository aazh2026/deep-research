"""
SWE-Lancer reproduction: SWE Manager-style task — pick best of N proposals.

This script reproduces the SWE Manager subset of the SWE-Lancer benchmark
(Miserendino et al. ICML 2025, OpenAI). SWE Manager tasks give the LLM:
  - a real engineering issue
  - the codebase snippet
  - N candidate proposals (A, B, C, ...)
and ask the LLM to pick the best one. Paper reports:
  - Claude 3.5 Sonnet: 44.9% pass@1 on Diamond SWE Manager
  - o1: 41.3%
  - GPT-4o: 38.7%
  - Random baseline (4-pick-1): 25%

We use 8 synthetic mini-tasks (real Upwork task format preserved, but with
synthetic proposals) to test whether M3.1 achieves a similar pass rate when
asked to pick the best of 3 proposals.
"""
import os
import re
import json
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
DATA = HERE / "data"
OUT = HERE / "_reproduction_results.json"
LOG = HERE / "_reproduction_log.txt"
MODEL = "openai/MiniMax-M3.1-Flash-Preview"
N_RUNS = 3  # paper averages over multiple runs for stability

# ---- LLM call ----
def llm_chat(messages, max_tokens=200, temperature=0.0):
    try:
        resp = litellm.completion(
            model=MODEL,
            messages=messages,
            api_base=os.environ["OPENAI_API_BASE_URL"],
            api_key=os.environ["OPENAI_KEY"],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        msg = resp.choices[0].message
        content = (msg.content or "").strip()
        if not content and hasattr(msg, "reasoning_content") and msg.reasoning_content:
            rc = msg.reasoning_content
            content = rc[rc.rfind("\n", 0, max(0, len(rc) - 2000)) + 1:].strip()
        return content, resp.usage.prompt_tokens, resp.usage.completion_tokens
    except Exception as e:
        return f"[ERROR: {e}]", 0, 0

# ---- Build SWE Manager prompt ----
SYSTEM = (
    "You are a software engineering manager reviewing multiple proposals "
    "submitted by freelance engineers for an Upwork issue. "
    "You will receive:\n"
    "  - The original issue (with payout amount)\n"
    "  - A snippet of the current codebase\n"
    "  - Several candidate proposals (A, B, C, ...)\n\n"
    "Your job: pick the SINGLE best proposal that correctly and completely "
    "solves the issue. Consider correctness, completeness, security implications, "
    "and adherence to the codebase's existing style.\n\n"
    "Output format: respond with EXACTLY one letter (A, B, C, ...) on the first line, "
    "then a 1-2 sentence justification. Do NOT include any other text."
)

def make_manager_prompt(task):
    proposals_text = "\n".join(
        f"Proposal {letter}: {proposal}"
        for letter, proposal in task["proposals"].items()
    )
    return (
        f"# Issue (Payout: ${task['payout_usd']:,})\n"
        f"{task['issue']}\n\n"
        f"# Current codebase snippet\n"
        f"```python\n{task['codebase_snippet']}\n```\n\n"
        f"# Candidate proposals\n{proposals_text}\n\n"
        f"Which proposal is best? Respond with the letter (A, B, C, ...) on the first line."
    )

# ---- Parse LLM response ----
def parse_choice(raw):
    """Extract the chosen letter from the LLM response."""
    if not raw:
        return None
    # First non-empty line
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        # Match: "A", "A.", "A:", "A - reason", "Proposal A", "The answer is A"
        m = re.match(r"^(?:Proposal\s+|The\s+answer\s+is\s+|I\s+choose\s+|Answer:\s*)?([A-Z])(?:\.|:|\s|$|-)", line, re.IGNORECASE)
        if m:
            return m.group(1).upper()
        # First letter as fallback
        if line[0].isalpha() and line[0].upper() in "ABCDEFGH":
            return line[0].upper()
    return None

# ---- Main ----
def main():
    with (DATA / "tasks.json").open() as f:
        tasks = json.load(f)

    log = LOG.open("w")
    results = []

    for i, t in enumerate(tasks, 1):
        prompt = make_manager_prompt(t)
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ]

        run_results = []
        all_picks = []
        all_in_tok = 0
        all_out_tok = 0
        for run in range(N_RUNS):
            raw, in_tok, out_tok = llm_chat(messages, max_tokens=200)
            all_in_tok += in_tok
            all_out_tok += out_tok
            pick = parse_choice(raw)
            all_picks.append(pick)
            passed = pick == t["correct_proposal"]
            run_results.append({
                "raw": raw,
                "pick": pick,
                "passed": passed,
                "in_tok": in_tok,
                "out_tok": out_tok,
            })

        # Compute pass@1 = mean over runs (paper's approach)
        n_pass = sum(1 for r in run_results if r["passed"])
        pass_at_1 = n_pass / N_RUNS

        # Most common pick (majority vote)
        from collections import Counter
        most_common = Counter(all_picks).most_common(1)
        majority_pick = most_common[0][0] if most_common else None
        majority_pass = majority_pick == t["correct_proposal"]

        # pass@k = "did any run get it right" (n=3 here)
        pass_at_k = int(any(r["passed"] for r in run_results))

        entry = {
            "task_id": t["task_id"],
            "category": t["category"],
            "payout_usd": t["payout_usd"],
            "correct": t["correct_proposal"],
            "all_picks": all_picks,
            "n_pass": n_pass,
            "pass_at_1": pass_at_1,
            "pass_at_k": pass_at_k,
            "majority_pick": majority_pick,
            "majority_pass": majority_pass,
            "run_results": run_results,
            "in_tok": all_in_tok,
            "out_tok": all_out_tok,
        }
        results.append(entry)

        sym_pass = "✓" if pass_at_k else "✗"
        picks_str = " ".join(p or "?" for p in all_picks)
        print(
            f"  [{i}] {t['task_id']:30s} payout=${t['payout_usd']:>5d} "
            f"correct={t['correct_proposal']} picks=[{picks_str}] {sym_pass} "
            f"majority={majority_pick}",
            flush=True,
        )
        log.write(f"=== {t['task_id']} (payout ${t['payout_usd']}) ===\n")
        log.write(f"Correct: {t['correct_proposal']}\n")
        for ridx, rrun in enumerate(run_results, 1):
            log.write(f"  Run {ridx}: pick={rrun['pick']}, pass={rrun['passed']}\n")
            log.write(f"    raw: {rrun['raw'][:300]}\n")
        log.write(f"  pass@1={pass_at_1:.2f}, pass@k={pass_at_k}, majority={majority_pick} ({'pass' if majority_pass else 'fail'})\n\n")

    # Summary
    n = len(results)
    # pass@1 averaged across tasks and runs
    total_passes = sum(r["n_pass"] for r in results)
    total_runs = n * N_RUNS
    pass_at_1_overall = total_passes / total_runs
    pass_at_k_overall = sum(r["pass_at_k"] for r in results) / n
    majority_pass = sum(1 for r in results if r["majority_pass"]) / n

    # Earn rate: only count pass@k task payouts
    earned = sum(r["payout_usd"] for r in results if r["pass_at_k"])
    possible = sum(r["payout_usd"] for r in results)
    earn_rate = earned / possible if possible else 0

    # By category
    by_cat = {}
    for r in results:
        c = r["category"]
        by_cat.setdefault(c, []).append(r["pass_at_k"])
    cat_summary = {c: sum(v) / len(v) for c, v in by_cat.items()}

    # By payout tier
    by_tier = {"<$1K": [], "$1K-$2K": [], ">$2K": []}
    for r in results:
        p = r["payout_usd"]
        if p < 1000:
            by_tier["<$1K"].append(r["pass_at_k"])
        elif p <= 2000:
            by_tier["$1K-$2K"].append(r["pass_at_k"])
        else:
            by_tier[">$2K"].append(r["pass_at_k"])
    tier_summary = {t: sum(v) / len(v) if v else 0 for t, v in by_tier.items()}

    summary = {
        "n": n,
        "n_runs_per_task": N_RUNS,
        "total_llm_calls": total_runs,
        "pass_at_1_overall": pass_at_1_overall,
        "pass_at_k_overall": pass_at_k_overall,
        "majority_vote_pass_rate": majority_pass,
        "by_category": cat_summary,
        "by_payout_tier": tier_summary,
        "earned_usd": earned,
        "possible_usd": possible,
        "earn_rate": earn_rate,
        "total_in_tokens": sum(r["in_tok"] for r in results),
        "total_out_tokens": sum(r["out_tok"] for r in results),
    }

    print(f"\n=== Summary (n={n} tasks × {N_RUNS} runs = {total_runs} LLM calls) ===", flush=True)
    print(f"  pass@1 (avg over runs):      {pass_at_1_overall*100:.1f}%", flush=True)
    print(f"  pass@k (any of {N_RUNS} runs):    {pass_at_k_overall*100:.1f}%", flush=True)
    print(f"  Majority-vote pass rate:     {majority_pass*100:.1f}%", flush=True)
    print(f"  Random baseline (3-pick-1):  33.3%", flush=True)
    print(f"\n  Earn rate: ${earned:,} / ${possible:,} = {earn_rate*100:.1f}%", flush=True)
    print(f"\n  By category:", flush=True)
    for c, v in cat_summary.items():
        print(f"    {c:15s} {v*100:.1f}%", flush=True)
    print(f"\n  By payout tier:", flush=True)
    for t, v in tier_summary.items():
        print(f"    {t:10s} {v*100:.1f}%", flush=True)
    print(f"\n  Tokens: {sum(r['in_tok'] for r in results):,} in / {sum(r['out_tok'] for r in results):,} out", flush=True)

    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    log.close()
    print(f"\nResults: {OUT}", flush=True)


if __name__ == "__main__":
    main()
