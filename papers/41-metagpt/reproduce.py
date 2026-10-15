"""
MetaGPT reproduction: multi-agent SOP + executable feedback ablation.

This script reproduces the core claims of MetaGPT (Hong et al. ICLR 2024,
arXiv:2308.00352) on 6 mini HumanEval-style tasks:

  1. Pass@1 of multi-agent SOP > single-agent baseline
  2. Executable feedback adds pass@1 (+4.2% HumanEval / +5.4% MBPP in paper)
  3. More roles → higher executability (1.0 → 4.0 in paper Table 3)
  4. Structured output reduces "human revision cost" (Table 1)

We compare 4 settings on the same 6 tasks:
  - Baseline:   1 LLM call, no role, no structure
  - 1-agent:    Engineer only, structured system prompt
  - 3-agent:    Product + Architect + Engineer, structured chain
  - 3-agent+FB: 3-agent + executable feedback loop (max 3 retries)

For each task and setting we measure:
  - pass@1 (test execution passes)
  - # LLM calls (proxy for token cost)
  - total token cost (in + out)
  - code structure score (0-3: docstring, type hints, edge case handling)
"""
import os
import re
import json
import sys
import subprocess
import ast
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
SANDBOX = HERE / "_sandbox"
OUT = HERE / "_reproduction_results.json"
LOG = HERE / "_reproduction_log.txt"
MODEL = "openai/MiniMax-M3.1-Flash-Preview"

# ---- LLM ----
def llm_chat(messages, max_tokens=1500, temperature=0.0):
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


def extract_code(raw):
    if not raw:
        return ""
    m = re.search(r"```python\s*\n(.*?)```", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r"```\s*\n(.*?)```", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
    return raw.strip()


def extract_func_name(sig):
    m = re.search(r"def\s+(\w+)\s*\(", sig)
    return m.group(1) if m else "func"


# ---- Test runner ----
def run_test(code, task, func_name, sandbox_dir):
    f = sandbox_dir / "candidate.py"
    f.write_text(code)
    test_text = "\n".join(task["test_cases"])
    runner = sandbox_dir / "run_test.py"
    runner.write_text(
        f"import sys\nsys.path.insert(0, '{sandbox_dir}')\n"
        f"from candidate import {func_name}\n"
        f"{test_text}\n"
        f"print('ALL_TESTS_PASS')\n"
    )
    try:
        proc = subprocess.run(
            [sys.executable, str(runner)],
            capture_output=True, text=True, timeout=8,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        if "ALL_TESTS_PASS" in out and proc.returncode == 0:
            return True, "PASS"
        return False, out[:300]
    except subprocess.TimeoutExpired:
        return False, "timeout"
    except Exception as e:
        return False, str(e)[:200]


# ---- Code structure score ----
def code_structure_score(code):
    """Heuristic: 0-3 score. +1 docstring, +1 type hints, +1 edge case handling."""
    score = 0
    if re.search(r'""".*?"""', code, re.DOTALL) or re.search(r"'''.*?'''", code, re.DOTALL):
        score += 1
    if re.search(r"def\s+\w+\([^)]*:\s*[^=]*->", code):
        score += 1
    if any(kw in code for kw in ["if not", "if len", "raise ", "edge case", "empty", "None"]):
        score += 1
    return score


# ---- 4 Settings ----
def setting_baseline(task):
    """Setting 1: 1 LLM call, no role, no structure."""
    prompt = (
        f"# Task\n{task['description']}\n\n"
        f"# Function signature\n{task['function_signature']}\n\n"
        f"# Test cases\n```python\n{chr(10).join(task['test_cases'])}\n```\n\n"
        f"Implement the function in a single ```python``` code block."
    )
    raw, in_tok, out_tok = llm_chat(
        [{"role": "user", "content": prompt}],
        max_tokens=600,
    )
    return extract_code(raw), 1, in_tok + out_tok


def setting_1agent(task):
    """Setting 2: Engineer only, structured system prompt."""
    system = (
        "You are a Python engineer at a software company. Your goal is to write "
        "elegant, readable, extensible, efficient code. Follow PEP 8. The code you "
        "write should conform to code standards, be modular, be easy to read and "
        "maintain. Output the function in a single ```python``` code block."
    )
    user = (
        f"# Task\n{task['description']}\n\n"
        f"# Function signature\n{task['function_signature']}\n\n"
        f"# Test cases (your function MUST pass these)\n```python\n{chr(10).join(task['test_cases'])}\n```"
    )
    raw, in_tok, out_tok = llm_chat(
        [{"role": "system", "content": system},
         {"role": "user", "content": user}],
        max_tokens=600,
    )
    return extract_code(raw), 1, in_tok + out_tok


PRODUCT_SYSTEM = (
    "You are a Product Manager. Given a task, produce a structured PRD with:\n"
    "  ## Goal (1 sentence)\n"
    "  ## User Stories (2-3 bullet points)\n"
    "  ## Acceptance Criteria (specific testable conditions)\n"
    "  ## Edge Cases to handle\n"
    "Output in markdown format."
)

ARCHITECT_SYSTEM = (
    "You are a Software Architect. Given a Product Requirements Document, produce a "
    "structured design with:\n"
    "  ## Function Signature (exact signature with types)\n"
    "  ## Approach (1-2 sentences describing algorithm)\n"
    "  ## Data Flow (input → processing → output)\n"
    "  ## Error Handling Strategy\n"
    "Output in markdown format."
)

ENGINEER_SYSTEM = (
    "You are a Python Engineer. Given a PRD and design, implement the function. "
    "Follow PEP 8, include docstring, type hints, and handle edge cases. Output "
    "the COMPLETE function in a single ```python``` code block."
)

ENGINEER_FEEDBACK_SYSTEM = (
    "You are a Python Engineer with a debugging memory. You will be given a task, "
    "your previous code attempt, and the test failure output. Analyze the failure, "
    "fix the code, and output the COMPLETE updated function in a single ```python``` "
    "code block. Be specific about what went wrong."
)


def setting_3agent(task):
    """Setting 3: Product + Architect + Engineer, structured chain."""
    # Step 1: Product Manager
    prd_prompt = f"# Task\n{task['description']}\n\nWrite a structured PRD."
    prd_raw, in1, out1 = llm_chat(
        [{"role": "system", "content": PRODUCT_SYSTEM},
         {"role": "user", "content": prd_prompt}],
        max_tokens=400,
    )
    # Step 2: Architect
    arch_prompt = (
        f"# Task\n{task['description']}\n\n"
        f"# PRD\n{prd_raw}\n\n"
        f"Given this PRD, produce a structured design."
    )
    arch_raw, in2, out2 = llm_chat(
        [{"role": "system", "content": ARCHITECT_SYSTEM},
         {"role": "user", "content": arch_prompt}],
        max_tokens=400,
    )
    # Step 3: Engineer
    eng_prompt = (
        f"# Task\n{task['description']}\n\n"
        f"# Function signature\n{task['function_signature']}\n\n"
        f"# PRD\n{prd_raw}\n\n"
        f"# Design\n{arch_raw}\n\n"
        f"# Test cases (your function MUST pass these)\n```python\n{chr(10).join(task['test_cases'])}\n```\n\n"
        f"Implement the function. Output the COMPLETE code in a single ```python``` block."
    )
    eng_raw, in3, out3 = llm_chat(
        [{"role": "system", "content": ENGINEER_SYSTEM},
         {"role": "user", "content": eng_prompt}],
        max_tokens=800,
    )
    return extract_code(eng_raw), 3, (in1 + out1) + (in2 + out2) + (in3 + out3)


def setting_3agent_feedback(task, sandbox_dir, func_name, max_retries=3):
    """Setting 4: 3-agent + executable feedback loop."""
    code, n_calls, base_tok = setting_3agent(task)
    total_tok = base_tok
    feedback_tok = 0

    for retry in range(max_retries):
        passed, msg = run_test(code, task, func_name, sandbox_dir)
        if passed:
            break
        # Failure: give error to engineer
        feedback_prompt = (
            f"# Task\n{task['description']}\n\n"
            f"# Function signature\n{task['function_signature']}\n\n"
            f"# Test cases\n```python\n{chr(10).join(task['test_cases'])}\n```\n\n"
            f"# Your previous code\n```python\n{code}\n```\n\n"
            f"# Test failure output\n{msg}\n\n"
            f"Analyze the failure and output the COMPLETE fixed function in a ```python``` block."
        )
        raw, in_tok, out_tok = llm_chat(
            [{"role": "system", "content": ENGINEER_FEEDBACK_SYSTEM},
             {"role": "user", "content": feedback_prompt}],
            max_tokens=800,
        )
        new_code = extract_code(raw)
        feedback_tok += in_tok + out_tok
        n_calls += 1
        if new_code:
            code = new_code
    return code, n_calls, total_tok + feedback_tok


# ---- Main ----
def main():
    with (DATA / "tasks.json").open() as f:
        tasks = json.load(f)

    SANDBOX.mkdir(parents=True, exist_ok=True)
    log = LOG.open("w")
    results = []
    settings = [
        ("baseline", setting_baseline),
        ("1agent", setting_1agent),
        ("3agent", setting_3agent),
    ]

    for i, t in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] {t['task_id']} ({t['category']})", flush=True)
        func_name = extract_func_name(t["function_signature"])
        sandbox_dir = SANDBOX / t["task_id"]
        sandbox_dir.mkdir(parents=True, exist_ok=True)

        entry = {
            "task_id": t["task_id"],
            "category": t["category"],
            "func_name": func_name,
            "settings": {},
        }

        for setting_name, setting_fn in settings:
            code, n_calls, tok = setting_fn(t)
            passed, msg = run_test(code, t, func_name, sandbox_dir) if code else (False, "no code")
            score = code_structure_score(code) if code else 0
            entry["settings"][setting_name] = {
                "pass": passed,
                "n_calls": n_calls,
                "tokens": tok,
                "code_len": len(code),
                "structure_score": score,
                "msg": msg[:150],
            }
            sym = "✓" if passed else "✗"
            print(f"  {setting_name:<10s}: pass={sym} calls={n_calls} tok={tok} struct={score}", flush=True)

        # Setting 4: 3-agent + feedback (uses 3-agent code as starting point)
        # Re-run 3-agent to be independent of caching
        code3, n3, tok3 = setting_3agent(t)
        code_fb, n_fb, tok_fb = setting_3agent_feedback(t, sandbox_dir, func_name, max_retries=3)
        passed_fb, msg_fb = run_test(code_fb, t, func_name, sandbox_dir) if code_fb else (False, "no code")
        score_fb = code_structure_score(code_fb) if code_fb else 0
        entry["settings"]["3agent+FB"] = {
            "pass": passed_fb,
            "n_calls": n_fb,
            "tokens": tok_fb,
            "code_len": len(code_fb),
            "structure_score": score_fb,
            "msg": msg_fb[:150],
        }
        sym = "✓" if passed_fb else "✗"
        print(f"  3agent+FB  : pass={sym} calls={n_fb} tok={tok_fb} struct={score_fb}", flush=True)

        results.append(entry)
        log.write(f"=== {t['task_id']} ({t['category']}) ===\n")
        for s, d in entry["settings"].items():
            log.write(f"  {s}: pass={d['pass']} calls={d['n_calls']} tok={d['tokens']} struct={d['structure_score']}\n")
            if not d["pass"]:
                log.write(f"    msg: {d['msg']}\n")
        log.write("\n")

    # ---- Summary ----
    n = len(tasks)
    summary = {}
    for s in ["baseline", "1agent", "3agent", "3agent+FB"]:
        passing = sum(1 for r in results if r["settings"][s]["pass"])
        avg_calls = sum(r["settings"][s]["n_calls"] for r in results) / n
        avg_tok = sum(r["settings"][s]["tokens"] for r in results) / n
        avg_struct = sum(r["settings"][s]["structure_score"] for r in results) / n
        summary[s] = {
            "pass_count": passing,
            "pass_rate": passing / n,
            "avg_calls": avg_calls,
            "avg_tokens": avg_tok,
            "avg_structure": avg_struct,
        }

    print(f"\n=== Summary (n={n} tasks) ===", flush=True)
    print(f"  {'Setting':<14s} {'Pass':>8s} {'AvgCalls':>10s} {'AvgTok':>10s} {'Struct':>8s}", flush=True)
    print(f"  {'─'*54}", flush=True)
    for s, d in summary.items():
        sym = f"{d['pass_count']}/{n}"
        print(f"  {s:<14s} {sym:>8s} {d['avg_calls']:>10.1f} {d['avg_tokens']:>10.0f} {d['avg_structure']:>8.2f}", flush=True)
    print(f"", flush=True)
    print(f"  Pass@1 improvement (paper claim: +4.2% HumanEval / +5.4% MBPP from feedback)", flush=True)
    if summary["3agent"]["pass_rate"] > 0:
        delta_fb = summary["3agent+FB"]["pass_rate"] - summary["3agent"]["pass_rate"]
        print(f"  Ours: 3-agent {summary['3agent']['pass_rate']:.0%} → 3-agent+FB {summary['3agent+FB']['pass_rate']:.0%} (Δ={delta_fb:+.0%})", flush=True)
    if summary["baseline"]["pass_rate"] > 0:
        delta_sop = summary["3agent"]["pass_rate"] - summary["baseline"]["pass_rate"]
        print(f"  Ours: baseline {summary['baseline']['pass_rate']:.0%} → 3-agent {summary['3agent']['pass_rate']:.0%} (Δ={delta_sop:+.0%})", flush=True)

    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    log.close()
    print(f"\nResults: {OUT}", flush=True)


if __name__ == "__main__":
    main()
