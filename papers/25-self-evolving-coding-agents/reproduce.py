"""
Self-evolving coding agents reproduction: Reflexion algorithm on mini HumanEval.

This script reproduces the core claim of Reflexion (Shinn et al. 2023), which is
the most cited method in the survey "Self-Evolving Coding Agents" (Zhou et al.
arXiv:2608.03392v4, 2026, §4.1).

Reflexion algorithm:
  1. attempt 1: agent writes code, runs tests
  2. if pass: success, exit
  3. if fail: ask LLM to verbalize WHY it failed (reflection)
  4. attempt 2: include reflection in prompt, write code again
  5. repeat up to MAX_ATTEMPTS times

We compare:
  - Base agent: 1 attempt, no memory
  - Reflexion agent: up to 3 attempts, with verbal reflection memory

Benchmark: 8 mini-HumanEval-style tasks, each with hidden unit tests.

The "self-evolution" angle: after each failure, the agent's prompt grows with a
verbal reflection (the "memory"), matching the survey's claim that failed
trajectories (T) + diagnostic evidence (D) can be turned into reusable memory
asset updates.
"""
import os
import re
import json
import sys
import traceback
import subprocess
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
MAX_ATTEMPTS = 3  # Reflexion: at most 3 retries

# ---- LLM call ----
def llm_chat(messages, max_tokens=600, temperature=0.0):
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

# ---- Code extraction ----
def extract_code(raw):
    """Extract a python code block from LLM response.

    Strict mode: require a fenced ```python``` block. If absent, look for any
    fenced block. If still nothing, return the whole raw text — the test
    executor will catch it as a SyntaxError and trigger reflection.
    """
    if not raw:
        return ""
    # 1) fenced ```python ... ``` — most reliable
    m = re.search(r"```python\s*\n(.*?)```", raw, re.DOTALL)
    if m:
        return m.group(1).strip()
    # 2) fenced ``` ... ``` with no language tag
    m = re.search(r"```\s*\n(.*?)```", raw, re.DOTALL)
    if m:
        return m.group(2).strip() if False else m.group(1).strip()
    # 3) any ``` block (single line or multi)
    m = re.search(r"```([^\n]*)\n(.*?)```", raw, re.DOTALL)
    if m:
        return m.group(2).strip()
    # 4) Last resort: find first `def ` line and take everything from there
    lines = raw.splitlines()
    start = None
    for i, ln in enumerate(lines):
        if re.match(r"^def\s+\w+\s*\(", ln):
            start = i
            break
    if start is not None:
        return "\n".join(lines[start:]).strip()
    return raw.strip()

# ---- Prompts ----
SYSTEM = (
    "You are an expert Python programmer. When given a problem, "
    "write a complete, runnable Python function inside a ```python``` code block. "
    "Do NOT include any explanation outside the code block. "
    "Just code. The function signature is provided in the problem."
)

def make_codegen_prompt(task, reflection=None):
    parts = [
        f"# Problem\n{task['prompt']}\n",
        f"\n# Function signature\n{task['signature']}\n",
    ]
    if reflection:
        parts.append(f"\n# Previous attempt(s) failed. Reflection from the failure:\n{reflection}\n")
        parts.append("\nPlease fix the issues identified in the reflection. Write the complete corrected function.\n")
    else:
        parts.append("\nPlease implement the function. Write the complete function definition in a ```python``` block.\n")
    return "".join(parts)

REFLECTION_SYSTEM = (
    "You are a debugging assistant. You will see: (1) a problem, "
    "(2) a function signature, (3) a previous implementation that failed one or more tests, "
    "(4) the error output. Produce a short, concrete reflection explaining "
    "what went wrong and how to fix it. Be specific: name the bug, name the fix. "
    "Do not write code. Just write 2-4 sentences of natural language reflection."
)

def make_reflection_prompt(task, code, error):
    return (
        f"# Problem\n{task['prompt']}\n\n"
        f"# Function signature\n{task['signature']}\n\n"
        f"# Failed implementation\n```python\n{code}\n```\n\n"
        f"# Error or assertion failure\n{error}\n\n"
        f"Reflect on what went wrong and what to change in the next attempt. Be specific."
    )

# ---- Test execution in subprocess ----
def run_tests(code, tests, timeout=10):
    """Run the candidate code + tests in a fresh Python subprocess."""
    full = code + "\n\n" + "\n".join(tests) + "\n"
    try:
        proc = subprocess.run(
            [sys.executable, "-c", full],
            capture_output=True, text=True, timeout=timeout,
        )
        if proc.returncode == 0:
            return True, ""
        return False, (proc.stderr or proc.stdout).strip().splitlines()[-5:] and "\n".join((proc.stderr or proc.stdout).strip().splitlines()[-5:]) or "test failed"
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT (>10s)"
    except Exception as e:
        return False, f"EXEC ERROR: {e}"

# ---- Reflexion agent ----
def run_reflexion(task, max_attempts=MAX_ATTEMPTS):
    """Run base attempt + reflective retries."""
    reflections = []  # accumulated memory
    attempts = []
    final_code = None
    final_pass = False

    for n in range(1, max_attempts + 1):
        reflection = "\n\n".join(reflections) if reflections else None
        prompt = make_codegen_prompt(task, reflection)
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": prompt},
        ]
        raw, in_tok, out_tok = llm_chat(messages, max_tokens=600)
        code = extract_code(raw)

        # Execute tests
        passed, err = run_tests(code, task["tests"])

        attempts.append({
            "n": n,
            "raw_len": len(raw),
            "code": code,
            "passed": passed,
            "err": err,
            "in_tok": in_tok,
            "out_tok": out_tok,
        })

        if passed:
            final_code = code
            final_pass = True
            break

        # If this is the last attempt, do not generate reflection
        if n == max_attempts:
            final_code = code
            break

        # Generate reflection for next attempt
        ref_messages = [
            {"role": "system", "content": REFLECTION_SYSTEM},
            {"role": "user", "content": make_reflection_prompt(task, code, err)},
        ]
        ref_text, rt_in, rt_out = llm_chat(ref_messages, max_tokens=200)
        reflections.append(f"Attempt {n} reflection: {ref_text.strip()}")
        attempts[-1]["reflection"] = ref_text.strip()
        attempts[-1]["ref_in_tok"] = rt_in
        attempts[-1]["ref_out_tok"] = rt_out

    return {
        "final_code": final_code,
        "passed": final_pass,
        "attempts": attempts,
        "n_attempts": len(attempts),
    }

# ---- Base agent (no memory) ----
def run_base(task):
    """Single attempt, no reflection memory."""
    prompt = make_codegen_prompt(task, reflection=None)
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": prompt},
    ]
    raw, in_tok, out_tok = llm_chat(messages, max_tokens=600)
    code = extract_code(raw)
    passed, err = run_tests(code, task["tests"])
    return {
        "final_code": code,
        "passed": passed,
        "attempts": [{
            "n": 1,
            "raw_len": len(raw),
            "code": code,
            "passed": passed,
            "err": err,
            "in_tok": in_tok,
            "out_tok": out_tok,
        }],
        "n_attempts": 1,
    }

# ---- main ----
def main():
    with (DATA / "tasks.json").open() as f:
        tasks = json.load(f)

    log = LOG.open("w")
    results = []

    for i, t in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] {t['task_id']}", flush=True)

        # Base agent
        base = run_base(t)
        # Reflexion agent
        refl = run_reflexion(t, max_attempts=MAX_ATTEMPTS)

        entry = {
            "task_id": t["task_id"],
            "category": t["category"],
            "base_passed": base["passed"],
            "reflexion_passed": refl["passed"],
            "reflexion_n_attempts": refl["n_attempts"],
            "base_n_attempts": base["n_attempts"],
            "base_first_err": base["attempts"][0]["err"][:200],
            "reflexion_attempts": refl["attempts"],
        }
        results.append(entry)

        sym_base = "✓" if base["passed"] else "✗"
        sym_refl = "✓" if refl["passed"] else "✗"
        print(
            f"  Base: {sym_base} (1 attempt) | "
            f"Reflexion: {sym_refl} ({refl['n_attempts']} attempts)",
            flush=True,
        )
        log.write(f"=== {t['task_id']} ===\n")
        log.write(f"Base pass={base['passed']}, err={base['attempts'][0]['err'][:200]}\n")
        for a in refl["attempts"]:
            log.write(f"  Reflexion attempt {a['n']}: pass={a['passed']}, err={a.get('err','')[:150]}\n")
            if "reflection" in a:
                log.write(f"    reflection: {a['reflection']}\n")
        log.write("\n")

    # Summary
    n = len(results)
    base_pass = sum(1 for r in results if r["base_passed"])
    refl_pass = sum(1 for r in results if r["reflexion_passed"])
    # Per-attempt pass counts
    per_attempt = {}
    for r in results:
        for a in r["reflexion_attempts"]:
            per_attempt.setdefault(a["n"], 0)
            if a["passed"]:
                per_attempt[a["n"]] += 1

    summary = {
        "n": n,
        "max_attempts": MAX_ATTEMPTS,
        "base_pass@1": base_pass,
        "reflexion_pass_within_K": refl_pass,
        "per_attempt_pass": per_attempt,
        "reflexion_improvement": refl_pass - base_pass,
    }
    print(f"\n=== Summary (n={n} tasks) ===", flush=True)
    print(f"  Base agent (1 attempt):    {base_pass}/{n} pass ({base_pass/n*100:.1f}%)", flush=True)
    print(f"  Reflexion agent (≤{MAX_ATTEMPTS} attempts):  {refl_pass}/{n} pass ({refl_pass/n*100:.1f}%)", flush=True)
    for k, v in sorted(per_attempt.items()):
        print(f"    attempt {k}: {v}/{n} pass ({v/n*100:.1f}%)", flush=True)
    print(f"  Δ (Reflexion - Base):      +{refl_pass - base_pass} pass", flush=True)

    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    log.close()
    print(f"\nResults: {OUT}", flush=True)


if __name__ == "__main__":
    main()
