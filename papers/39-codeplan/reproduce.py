"""
CodePlan reproduction: multi-file edit propagation.

This script reproduces the core claim of CodePlan (Bairi et al. 2023, Microsoft
Research): when a function signature, class field, or default value changes,
the LLM-driven edit must propagate to all callers/uses. CodePlan uses a
dependency graph + plan graph to drive this propagation; the baseline just
asks the LLM to "fix the issue" in one shot.

We compare:
  - Baseline: single LLM call with all files + seed edit description
  - CodePlan: AST-based dependency analysis + sequential LLM edits per affected
              file (mimicking the paper's plan graph execution)

Benchmark: 6 synthetic multi-file Python tasks where one definition change
must propagate to 2-3 caller files. Each task has an oracle with the
correct edits; we compare line-level diff accuracy.

Metrics:
  - file_pass_rate: fraction of files that exactly match oracle
  - full_pass: all files exactly match oracle
  - line_F1: per-line precision/recall vs oracle
"""
import os
import re
import json
import ast
import difflib
import subprocess
import sys
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

# ---- LLM call ----
def llm_chat(messages, max_tokens=2000, temperature=0.0):
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

# ---- Extract code block ----
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

# ---- Build baseline prompt (all files at once) ----
SYSTEM_BASELINE = (
    "You are an expert Python programmer. You will be given a multi-file Python "
    "codebase and a task instruction. Apply the required change to ALL relevant "
    "files (caller sites, subclasses, etc.) so the codebase stays consistent.\n\n"
    "Output format: For each file that needs changes, output a single "
    "```python code block tagged with the filename as a comment on the first line "
    "like: # FILE: <filename>\\n<code>. Output ALL files in the proper format. "
    "If a file does not need any changes, skip it."
)

def make_baseline_prompt(task):
    files_text = "\n\n".join(
        f"# FILE: {fname}\n```python\n{content}\n```"
        for fname, content in sorted(task["initial_files"].items())
    )
    return (
        f"{files_text}\n\n"
        f"# TASK\n{task['description']}\n\n"
        f"Apply the change to all files. Output each modified file in a "
        f"```python``` block starting with `# FILE: <filename>`."
    )

# ---- Dependency graph (lightweight AST-based) ----
def find_callers_and_uses(files, target_name):
    """Find all files that import/call/contain target_name."""
    callers = []
    for fname, content in files.items():
        try:
            tree = ast.parse(content)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            # imports
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name == target_name or alias.asname == target_name:
                        callers.append((fname, "import"))
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == target_name or (alias.asname == target_name):
                        callers.append((fname, "import"))
            # function/class definitions (the target itself)
            if isinstance(node, ast.FunctionDef) and node.name == target_name:
                callers.append((fname, "definition"))
            if isinstance(node, ast.ClassDef) and node.name == target_name:
                callers.append((fname, "definition"))
            # method calls
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == target_name:
                    callers.append((fname, "call"))
                if isinstance(func, ast.Attribute) and func.attr == target_name:
                    callers.append((fname, "call"))
            # class instantiation
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == target_name:
                    callers.append((fname, "instantiate"))
            # field/method use
            if isinstance(node, ast.Attribute) and node.attr == target_name:
                callers.append((fname, "attribute"))
    return callers

def build_dependency_plan(task, seed_edit):
    """Build a CodePlan-style plan: which files must be edited, in what order."""
    target = None
    # Pattern 1: module.func( in seed_edit (e.g., "math_ops.add(a, b)")
    m = re.search(r"(\w+)\.(\w+)\(", seed_edit)
    if m:
        target = m.group(2)
    # Pattern 2: function in parens (e.g., "http.get default timeout")
    if not target:
        m = re.search(r"(\w+)\.(\w+)", seed_edit)
        if m:
            target = m.group(2)
    # Pattern 3: any function-like name from description
    if not target:
        m = re.search(r"\b(\w+)\s*\(", task["description"])
        if m:
            target = m.group(1)
    # Pattern 4: class name (e.g., "'internal_id' field from User class")
    if not target:
        m = re.search(r"(\w+)\s+class", seed_edit)
        if m:
            target = m.group(1)
    # Last fallback
    if not target:
        m = re.search(r"(\w+)", seed_edit)
        target = m.group(1) if m else None

    plan = []
    visited = set()

    if target:
        callers = find_callers_and_uses(task["initial_files"], target)
        # If single result (just definition), also search for class field uses
        if len(callers) < 2:
            # Look for any field/method use of related names
            # For task_3: User class + created_at field
            # For task_5: User class + internal_id field
            m2 = re.search(r"['\"](\w+)['\"]", seed_edit)
            if m2:
                field_name = m2.group(1)
                field_callers = find_callers_and_uses(task["initial_files"], field_name)
                callers.extend(field_callers)
            # Also try instantiation
            for fname, content in task["initial_files"].items():
                if f" {target}(" in content and fname not in [c[0] for c in callers]:
                    callers.append((fname, "instantiate"))

        # Group by file, preserving order: file with definition first
        files_in_order = []
        seen = set()
        # First: file with the definition
        for fname, kind in callers:
            if kind == "definition" and fname not in seen:
                files_in_order.append(fname)
                seen.add(fname)
                break
        # Then: files with imports, calls, instantiates
        for fname, kind in callers:
            if fname not in seen:
                files_in_order.append(fname)
                seen.add(fname)

        for fname in files_in_order:
            kinds = [k for f, k in callers if f == fname]
            plan.append((fname, ",".join(kinds)))

    return plan

# ---- CodePlan per-file edit ----
SYSTEM_CODEPLAN = (
    "You are an expert Python programmer doing repository-level code editing. "
    "You will be given:\n"
    "  - The overall task description\n"
    "  - The full set of files in the repository\n"
    "  - A specific FILE that needs to be edited (with its current content)\n"
    "  - Reason for the edit (what change was made and why this file is affected)\n\n"
    "Edit ONLY the specified file, applying the required change consistently. "
    "Output the COMPLETE updated file in a single ```python``` code block."
)

def make_codeplan_prompt(task, fname, content, edit_reason):
    files_text = "\n\n".join(
        f"# FILE: {f}\n```python\n{c}\n```"
        for f, c in sorted(task["initial_files"].items())
        if f != fname
    )
    return (
        f"# TASK\n{task['description']}\n\n"
        f"# OTHER FILES (context only — do not modify)\n{files_text}\n\n"
        f"# FILE TO EDIT: {fname}\n"
        f"Edit reason: {edit_reason}\n\n"
        f"Current content of {fname}:\n```python\n{content}\n```\n\n"
        f"Output the complete updated file in a single ```python``` block."
    )

# ---- Test final state ----
def test_files(final_files, task):
    """Run test_app.py (or equivalent) and check if it imports + runs cleanly.

    Also check if final_files exactly match oracle.
    """
    # Write all files to a temp dir and try to import
    test_dir = SANDBOX / f"test_{task['task_id']}"
    test_dir.mkdir(parents=True, exist_ok=True)
    for fname, content in final_files.items():
        (test_dir / fname).write_text(content)

    # Try to find a test file or main file
    test_candidates = [f for f in final_files if "test" in f or "main" in f]
    if not test_candidates:
        # Just try to import every file
        for fname in final_files:
            try:
                proc = subprocess.run(
                    [sys.executable, "-c", f"import sys; sys.path.insert(0, '{test_dir}'); "
                     f"import importlib.util as u; "
                     f"spec = u.spec_from_file_location('m', '{test_dir}/{fname}'); "
                     f"m = u.module_from_spec(spec); spec.loader.exec_module(m)"],
                    capture_output=True, text=True, timeout=10,
                )
                if proc.returncode != 0:
                    return False, f"import error in {fname}: {proc.stderr[:200]}"
            except subprocess.TimeoutExpired:
                return False, f"timeout importing {fname}"
            except Exception as e:
                return False, f"exec error in {fname}: {e}"
        return True, "all files import OK"

    # Run test file(s)
    for tf in test_candidates:
        try:
            proc = subprocess.run(
                [sys.executable, str(test_dir / tf)],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode != 0:
                return False, f"test {tf} failed: {(proc.stderr or proc.stdout)[:200]}"
        except subprocess.TimeoutExpired:
            return False, f"timeout running {tf}"
        except Exception as e:
            return False, f"exec error in {tf}: {e}"

    return True, "all tests pass"

# ---- Compare to oracle ----
def file_diff(pred, gold):
    """Line-level diff metrics."""
    pred_lines = pred.splitlines()
    gold_lines = gold.splitlines()
    sm = difflib.SequenceMatcher(None, pred_lines, gold_lines)
    matches = sum(triple.size for triple in sm.get_matching_blocks())
    precision = matches / max(len(pred_lines), 1)
    recall = matches / max(len(gold_lines), 1)
    f1 = 2 * precision * recall / max(precision + recall, 1e-9)
    return precision, recall, f1

# ---- Baseline: single LLM call ----
def run_baseline(task):
    prompt = make_baseline_prompt(task)
    raw, in_tok, out_tok = llm_chat(
        [{"role": "system", "content": SYSTEM_BASELINE},
         {"role": "user", "content": prompt}],
        max_tokens=3000,
    )

    # Parse output: extract each # FILE: ... ```python ... ``` block
    final_files = dict(task["initial_files"])
    # Split by # FILE: markers
    blocks = re.split(r"# FILE:\s*(\S+)", raw)
    # blocks is like: [preamble, fname1, content1, fname2, content2, ...]
    i = 1
    while i < len(blocks) - 1:
        fname = blocks[i]
        content = blocks[i + 1]
        # Extract code block
        m = re.search(r"```python\s*\n(.*?)```", content, re.DOTALL)
        if m:
            final_files[fname] = m.group(1).strip()
        i += 2

    return final_files, in_tok, out_tok, raw

# ---- CodePlan: dependency-graph-driven per-file LLM calls ----
def run_codeplan(task):
    plan = build_dependency_plan(task, task["seed_edit"])
    final_files = dict(task["initial_files"])
    in_tok_total = 0
    out_tok_total = 0
    all_runs = []

    for fname, reason in plan:
        content = final_files[fname]
        # Build edit reason
        if "definition" in reason:
            edit_reason = f"You are editing the DEFINITION of the function. Apply the change described in the task."
        elif "import" in reason:
            edit_reason = f"This file imports the function. Update the import line if the function was renamed."
        elif "call" in reason or "instantiate" in reason:
            edit_reason = f"This file CALLS the function. Update the call site to match the new signature/name."
        elif "attribute" in reason:
            edit_reason = f"This file uses the function as a method/attribute. Update the access site."
        else:
            edit_reason = f"Edit this file as needed for the task."

        prompt = make_codeplan_prompt(task, fname, content, edit_reason)
        raw, in_tok, out_tok = llm_chat(
            [{"role": "system", "content": SYSTEM_CODEPLAN},
             {"role": "user", "content": prompt}],
            max_tokens=2000,
        )
        in_tok_total += in_tok
        out_tok_total += out_tok
        new_content = extract_code(raw)
        if new_content:
            final_files[fname] = new_content
        all_runs.append({"file": fname, "reason": reason, "raw_len": len(raw), "in_tok": in_tok, "out_tok": out_tok})

    return final_files, in_tok_total, out_tok_total, plan, all_runs

# ---- Main ----
def main():
    with (DATA / "tasks.json").open() as f:
        tasks = json.load(f)

    SANDBOX.mkdir(parents=True, exist_ok=True)
    log = LOG.open("w")
    results = []

    for i, t in enumerate(tasks, 1):
        print(f"\n[{i}/{len(tasks)}] {t['task_id']} ({t['category']})", flush=True)

        # --- Baseline ---
        bl_files, bl_in, bl_out, bl_raw = run_baseline(t)
        # Compute per-file diff vs oracle
        bl_file_metrics = {}
        bl_files_correct = 0
        for fname, gold in t["oracle_files"].items():
            pred = bl_files.get(fname, "")
            p, r, f1 = file_diff(pred, gold)
            bl_file_metrics[fname] = {"p": p, "r": r, "f1": f1, "exact": pred.strip() == gold.strip()}
            if pred.strip() == gold.strip():
                bl_files_correct += 1
        bl_test_pass, bl_test_msg = test_files(bl_files, t)
        bl_full_match = bl_files_correct == len(t["oracle_files"])

        # --- CodePlan ---
        cp_files, cp_in, cp_out, cp_plan, cp_runs = run_codeplan(t)
        cp_file_metrics = {}
        cp_files_correct = 0
        for fname, gold in t["oracle_files"].items():
            pred = cp_files.get(fname, "")
            p, r, f1 = file_diff(pred, gold)
            cp_file_metrics[fname] = {"p": p, "r": r, "f1": f1, "exact": pred.strip() == gold.strip()}
            if pred.strip() == gold.strip():
                cp_files_correct += 1
        cp_test_pass, cp_test_msg = test_files(cp_files, t)
        cp_full_match = cp_files_correct == len(t["oracle_files"])

        entry = {
            "task_id": t["task_id"],
            "category": t["category"],
            "n_files": len(t["oracle_files"]),
            "baseline": {
                "files_correct": bl_files_correct,
                "full_match": bl_full_match,
                "test_pass": bl_test_pass,
                "test_msg": bl_test_msg,
                "file_metrics": bl_file_metrics,
                "in_tok": bl_in, "out_tok": bl_out,
            },
            "codeplan": {
                "files_correct": cp_files_correct,
                "full_match": cp_full_match,
                "test_pass": cp_test_pass,
                "test_msg": cp_test_msg,
                "file_metrics": cp_file_metrics,
                "plan": cp_plan,
                "n_llm_calls": len(cp_runs),
                "in_tok": cp_in, "out_tok": cp_out,
            },
        }
        results.append(entry)

        sym_bl = "✓" if bl_full_match else "✗"
        sym_cp = "✓" if cp_full_match else "✗"
        print(
            f"  Baseline: {bl_files_correct}/{len(t['oracle_files'])} files, full={sym_bl} "
            f"({bl_in+bl_out} tok)",
            flush=True,
        )
        print(
            f"  CodePlan: {cp_files_correct}/{len(t['oracle_files'])} files, full={sym_cp} "
            f"({cp_in+cp_out} tok, {len(cp_runs)} LLM calls)",
            flush=True,
        )
        log.write(f"=== {t['task_id']} ({t['category']}) ===\n")
        log.write(f"Plan: {cp_plan}\n")
        log.write(f"Baseline: {bl_files_correct}/{len(t['oracle_files'])} files correct, full_match={bl_full_match}, test_pass={bl_test_pass}\n")
        if not bl_test_pass:
            log.write(f"  test msg: {bl_test_msg}\n")
        log.write(f"CodePlan: {cp_files_correct}/{len(t['oracle_files'])} files correct, full_match={cp_full_match}, test_pass={cp_test_pass}\n")
        if not cp_test_pass:
            log.write(f"  test msg: {cp_test_msg}\n")
        log.write("\n")

    # Summary
    n = len(results)
    n_files = sum(r["n_files"] for r in results)
    bl_full = sum(1 for r in results if r["baseline"]["full_match"])
    cp_full = sum(1 for r in results if r["codeplan"]["full_match"])
    bl_files_correct = sum(r["baseline"]["files_correct"] for r in results)
    cp_files_correct = sum(r["codeplan"]["files_correct"] for r in results)
    bl_test_pass = sum(1 for r in results if r["baseline"]["test_pass"])
    cp_test_pass = sum(1 for r in results if r["codeplan"]["test_pass"])

    # F1 average
    bl_f1s = [m["f1"] for r in results for m in r["baseline"]["file_metrics"].values()]
    cp_f1s = [m["f1"] for r in results for m in r["codeplan"]["file_metrics"].values()]
    bl_avg_f1 = sum(bl_f1s) / len(bl_f1s) if bl_f1s else 0
    cp_avg_f1 = sum(cp_f1s) / len(cp_f1s) if cp_f1s else 0

    summary = {
        "n_tasks": n,
        "n_files_total": n_files,
        "baseline": {
            "full_match_tasks": bl_full,
            "files_correct": bl_files_correct,
            "files_correct_rate": bl_files_correct / n_files,
            "test_pass_tasks": bl_test_pass,
            "avg_line_f1": bl_avg_f1,
        },
        "codeplan": {
            "full_match_tasks": cp_full,
            "files_correct": cp_files_correct,
            "files_correct_rate": cp_files_correct / n_files,
            "test_pass_tasks": cp_test_pass,
            "avg_line_f1": cp_avg_f1,
            "avg_llm_calls_per_task": sum(r["codeplan"]["n_llm_calls"] for r in results) / n,
        },
    }

    print(f"\n=== Summary (n={n} tasks, {n_files} files total) ===", flush=True)
    print(f"  {'Metric':<25s} {'Baseline':>10s} {'CodePlan':>10s}", flush=True)
    print(f"  {'─'*47}", flush=True)
    print(f"  {'Full match (all files)':<25s} {bl_full:>4d}/{n:<5d} {cp_full:>4d}/{n:<5d}", flush=True)
    print(f"  {'Test pass':<25s} {bl_test_pass:>4d}/{n:<5d} {cp_test_pass:>4d}/{n:<5d}", flush=True)
    print(f"  {'Files correct':<25s} {bl_files_correct:>4d}/{n_files:<5d} {cp_files_correct:>4d}/{n_files:<5d}", flush=True)
    print(f"  {'Avg line F1':<25s} {bl_avg_f1:>10.3f} {cp_avg_f1:>10.3f}", flush=True)
    print(f"  CodePlan avg LLM calls: {summary['codeplan']['avg_llm_calls_per_task']:.1f}", flush=True)

    OUT.write_text(json.dumps({"summary": summary, "results": results}, indent=2))
    log.close()
    print(f"\nResults: {OUT}", flush=True)


if __name__ == "__main__":
    main()
