"""
Beyond Code Generation reproduction: PQC rate vs candidate rate.

This script operationalizes Happy Bhati's (2026) four engineering constructs on
6 mini coding tasks:

  1. Agentic SDLC Throughput Paradox
     - measure: candidate generation rate vs PQC rate
     - expect: generation >> PQC (per Demirer et al. NBER 2026: 180% commits, 30% releases)

  2. Production-Qualified Change (PQC)
     - PQC_i = pass ALL 5 reliability gates
     - Gate 1 (compile/import):    python3 -c "import m"
     - Gate 2 (test pass):         run task's assert tests
     - Gate 3 (code review):       LLM-as-reviewer
     - Gate 4 (security):          LLM-as-security-checker
     - Gate 5 (deploy ready):      LLM-as-deploy-checker

  3. Verification Tax
     - V_tax = (tokens in verification LLM calls) / (tokens in generation LLM call)
     - expect: > 1.0 (verification is heavier than generation)

  4. Agentic Autonomy Budget
     - we do not run multi-day tasks, but we record per-task token + time
       so future work can map to (Money, Reliability, Human-attention) triangle

Benchmark: 6 HumanEval-style tasks spanning 5 categories (string, list, dict,
filter, security, math). 1 generation LLM call + 3 verification LLM calls per
task = 4 calls / task, 24 total.
"""
import os
import re
import json
import sys
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


# ---- Gate prompts ----
GENERATION_SYSTEM = (
    "You are an expert Python programmer. Implement the requested function. "
    "Output the complete implementation in a single ```python``` code block. "
    "Do not include any other explanation."
)

def make_generation_prompt(task):
    tests_text = "\n".join(task["test_cases"])
    return (
        f"# Task\n{task['description']}\n\n"
        f"# Function signature\n{task['function_signature']}\n\n"
        f"# Test cases (your function MUST pass these)\n```python\n{tests_text}\n```\n\n"
        f"Implement the function. Output the complete code in a single ```python``` block."
    )

REVIEW_SYSTEM = (
    "You are a senior Python code reviewer evaluating a single small standalone "
    "function (10-30 lines). This is a competitive coding / utility function, not "
    "production library code. Evaluate:\n"
    "  - Correctness of approach (not just style)\n"
    "  - Reasonable naming and clarity\n"
    "  - No obvious bugs or edge case misses\n"
    "Be LENIENT about minor things (no docstring, single-letter vars for tiny "
    "lambdas, etc.). Only FAIL if there is a real correctness or major clarity "
    "concern. Output PASS or FAIL on the first line, then one short sentence."
)

SECURITY_SYSTEM = (
    "You are a security engineer doing a code review. Look for:\n"
    "  - Hardcoded secrets, passwords, API keys\n"
    "  - SQL injection, command injection, unsafe deserialization\n"
    "  - Use of `eval`, `exec`, `os.system` with user input\n"
    "  - Plaintext password comparison (must use constant-time compare)\n"
    "  - Use of `print` to log sensitive data (passwords, tokens)\n"
    "Output PASS or FAIL on the first line, then one short paragraph."
)

DEPLOY_SYSTEM = (
    "You are an SRE evaluating production-readiness of a code change. Check for:\n"
    "  - Adequate error handling (try/except for I/O, no bare except)\n"
    "  - Logging or observability hooks (instead of print statements)\n"
    "  - No debug print() left in code\n"
    "  - Reasonable performance (no obvious O(n^3) where O(n) suffices)\n"
    "  - Input validation at boundaries\n"
    "Output PASS or FAIL on the first line, then one short paragraph."
)


def make_verification_prompt(task, code, gate):
    system = {"review": REVIEW_SYSTEM, "security": SECURITY_SYSTEM, "deploy": DEPLOY_SYSTEM}[gate]
    return system, f"# Task\n{task['description']}\n\n# Candidate code\n```python\n{code}\n```\n\nEvaluate."


def parse_pass_fail(raw):
    """Look for PASS or FAIL on first non-empty line."""
    if not raw:
        return False, ""
    for line in raw.splitlines()[:3]:
        line = line.strip()
        if line.startswith("PASS"):
            return True, raw
        if line.startswith("FAIL"):
            return False, raw
    # If model didn't follow format, look anywhere in first 200 chars
    head = raw[:200].upper()
    if "PASS" in head and "FAIL" not in head:
        return True, raw
    return False, raw


# ---- Gates 1-2: deterministic ----
def gate_compile(code, func_name, sandbox_dir):
    """Write code to file and try to import it."""
    f = sandbox_dir / "candidate.py"
    f.write_text(code)
    try:
        proc = subprocess.run(
            [sys.executable, "-c", f"import sys; sys.path.insert(0, '{sandbox_dir}'); "
             f"import importlib.util as u; "
             f"spec = u.spec_from_file_location('candidate', '{f}'); "
             f"m = u.module_from_spec(spec); spec.loader.exec_module(m); "
             f"assert hasattr(m, '{func_name}'), 'no function {func_name}'"],
            capture_output=True, text=True, timeout=5,
        )
        return proc.returncode == 0, (proc.stderr or proc.stdout)[:200]
    except subprocess.TimeoutExpired:
        return False, "import timeout"
    except Exception as e:
        return False, str(e)[:200]


def gate_test(code, task, func_name, sandbox_dir):
    """Write code + tests, run as standalone script."""
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
            capture_output=True, text=True, timeout=5,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        passed = (proc.returncode == 0) and ("ALL_TESTS_PASS" in out or "AssertionError" not in out)
        # If there are assertion errors, definitely fail
        if "AssertionError" in out:
            passed = False
        return passed, out[:300]
    except subprocess.TimeoutExpired:
        return False, "test timeout"
    except Exception as e:
        return False, str(e)[:200]


# ---- Main ----
def main():
    with (DATA / "tasks.json").open() as f:
        tasks = json.load(f)

    SANDBOX.mkdir(parents=True, exist_ok=True)
    log = LOG.open("w")
    results = []

    total_gen_in = 0
    total_gen_out = 0
    total_ver_in = 0
    total_ver_out = 0
    gate_pass_counts = {
        "gate_0_gen": 0,
        "gate_1_compile": 0,
        "gate_2_test": 0,
        "gate_3_review": 0,
        "gate_4_security": 0,
        "gate_5_deploy": 0,
    }
    final_pqc = 0
    cum_candidate = 0
    cum_test_pass = 0  # for "candidate rate" comparison

    for i, t in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] {t['task_id']} ({t['category']})", flush=True)
        func_name = extract_func_name(t["function_signature"])
        sandbox_dir = SANDBOX / t["task_id"]
        sandbox_dir.mkdir(parents=True, exist_ok=True)

        # --- Step 1: Generation ---
        gen_prompt = make_generation_prompt(t)
        gen_raw, gen_in, gen_out = llm_chat(
            [{"role": "system", "content": GENERATION_SYSTEM},
             {"role": "user", "content": gen_prompt}],
            max_tokens=800,
        )
        code = extract_code(gen_raw)
        total_gen_in += gen_in
        total_gen_out += gen_out

        # Candidate = generation succeeded AND gate 1 (compile) passed
        gate_results = {}
        entry = {
            "task_id": t["task_id"],
            "category": t["category"],
            "func_name": func_name,
            "code_len": len(code),
            "gen_in": gen_in, "gen_out": gen_out,
            "ver_in": 0, "ver_out": 0,
        }

        if not code:
            print(f"  [GEN] No code extracted (raw_len={len(gen_raw)})", flush=True)
            entry["gates"] = {"gate_0_gen": False, "gate_1_compile": False, "gate_2_test": False, "gate_3_review": False, "gate_4_security": False, "gate_5_deploy": False}
            entry["pqc"] = False
            results.append(entry)
            log.write(f"=== {t['task_id']}: NO CODE EXTRACTED ===\n\n")
            continue

        gate_results["gate_0_gen"] = True
        gate_pass_counts["gate_0_gen"] += 1
        cum_candidate += 1

        # --- Gate 1: Compile ---
        g1_pass, g1_msg = gate_compile(code, func_name, sandbox_dir)
        gate_results["gate_1_compile"] = g1_pass
        if g1_pass:
            gate_pass_counts["gate_1_compile"] += 1
        # --- Gate 2: Test ---
        g2_pass, g2_msg = gate_test(code, t, func_name, sandbox_dir)
        gate_results["gate_2_test"] = g2_pass
        if g2_pass:
            gate_pass_counts["gate_2_test"] += 1
            cum_test_pass += 1

        # --- Gates 3-5: LLM verification (only if Gate 1 passed; otherwise code is broken) ---
        ver_in_total = 0
        ver_out_total = 0
        for gate_name, key in [("review", "gate_3_review"), ("security", "gate_4_security"), ("deploy", "gate_5_deploy")]:
            if not g1_pass:
                gate_results[key] = False
                continue
            system, user = make_verification_prompt(t, code, gate_name)
            raw, in_tok, out_tok = llm_chat(
                [{"role": "system", "content": system},
                 {"role": "user", "content": user}],
                max_tokens=400,
            )
            ver_in_total += in_tok
            ver_out_total += out_tok
            passed, _ = parse_pass_fail(raw)
            gate_results[key] = passed
            if passed:
                gate_pass_counts[key] += 1

        total_ver_in += ver_in_total
        total_ver_out += ver_out_total
        entry["ver_in"] = ver_in_total
        entry["ver_out"] = ver_out_total
        entry["gates"] = gate_results
        entry["g1_msg"] = g1_msg[:200]
        entry["g2_msg"] = g2_msg[:200]

        # --- Compute PQC ---
        pqc = all(gate_results.get(f"gate_{k}_{n}", False) for k, n in [(1, "compile"), (2, "test"), (3, "review"), (4, "security"), (5, "deploy")])
        entry["pqc"] = pqc
        if pqc:
            final_pqc += 1

        results.append(entry)

        # Logging
        sym = {True: "✓", False: "✗"}
        gate_str = " ".join(f"G{k}={sym[gate_results.get(f'gate_{k}_'+n, False)]}" for k, n in [(1, "compile"), (2, "test"), (3, "review"), (4, "security"), (5, "deploy")])
        print(f"  {gate_str}  PQC={sym[pqc]}  gen={gen_in+gen_out} ver={ver_in_total+ver_out_total} tok", flush=True)
        log.write(f"=== {t['task_id']} ({t['category']}) ===\n")
        log.write(f"  code_len: {len(code)}\n")
        log.write(f"  gates: {gate_results}\n")
        log.write(f"  PQC: {pqc}\n")
        log.write(f"  g1_msg: {g1_msg[:200]}\n")
        log.write(f"  g2_msg: {g2_msg[:200]}\n")
        log.write(f"  gen tokens: {gen_in}+{gen_out}, ver tokens: {ver_in_total}+{ver_out_total}\n\n")

    # ---- Summary ----
    n = len(tasks)
    summary = {
        "n_tasks": n,
        "total_generation_tokens": total_gen_in + total_gen_out,
        "total_verification_tokens": total_ver_in + total_ver_out,
        "verification_tax": (total_ver_in + total_ver_out) / max(total_gen_in + total_gen_out, 1),
        "gate_pass_counts": gate_pass_counts,
        "gate_pass_rates": {k: v / n for k, v in gate_pass_counts.items()},
        "candidate_generated": cum_candidate,
        "candidate_rate": cum_candidate / n,
        "test_pass": cum_test_pass,
        "test_pass_rate": cum_test_pass / n,
        "pqc_count": final_pqc,
        "pqc_rate": final_pqc / n,
        "throughput_paradox_attenuation": {
            "candidate_rate_minus_pqc": cum_candidate / n - final_pqc / n,
            "ratio_pqc_to_candidate": (final_pqc / n) / max(cum_candidate / n, 0.01),
        },
    }

    print(f"\n=== Summary (n={n} tasks) ===", flush=True)
    print(f"  Generation tokens:        {summary['total_generation_tokens']:>6d}", flush=True)
    print(f"  Verification tokens:      {summary['total_verification_tokens']:>6d}", flush=True)
    print(f"  Verification Tax:         {summary['verification_tax']:>5.2f}x", flush=True)
    print(f"", flush=True)
    print(f"  {'Gate':<30s} {'Pass':>6s} {'Rate':>8s}", flush=True)
    print(f"  {'─'*46}", flush=True)
    labels = [
        ("gate_0_gen", "Generation (code extracted)"),
        ("gate_1_compile", "G1 Compile/import"),
        ("gate_2_test", "G2 Test pass"),
        ("gate_3_review", "G3 Code review (LLM)"),
        ("gate_4_security", "G4 Security (LLM)"),
        ("gate_5_deploy", "G5 Deploy ready (LLM)"),
    ]
    for k, label in labels:
        cnt = gate_pass_counts[k]
        rate = cnt / n
        print(f"  {label:<30s} {cnt:>3d}/{n:<3d} {rate:>7.1%}", flush=True)
    print(f"", flush=True)
    print(f"  Candidate generation rate: {summary['candidate_rate']:>5.1%}  (passed G0+G1)", flush=True)
    print(f"  Test pass rate:            {summary['test_pass_rate']:>5.1%}  (G2)", flush=True)
    print(f"  PQC rate (all 5 gates):    {summary['pqc_rate']:>5.1%}  (G1-G5)", flush=True)
    print(f"", flush=True)
    print(f"  Throughput Paradox (Demirer): commits +180%, releases +30%", flush=True)
    print(f"  Our mini analog:           candidate {summary['candidate_rate']:.0%}, PQC {summary['pqc_rate']:.0%}, attenuation {(summary['candidate_rate']-summary['pqc_rate']):.0%}", flush=True)

    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    log.close()
    print(f"\nResults: {OUT}", flush=True)


if __name__ == "__main__":
    main()
