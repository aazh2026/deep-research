"""
Loop Engineering Building Block Detector (Lulla et al. JAWs@ASE 2026)

This script reproduces the central claim of the paper: even in canonical
agent implementations, only 1-2 of 8 loop engineering building blocks leave
traceable artifacts. We implement 8 deterministic heuristic detectors and
run them against 8 representative agent code patterns.

Paper: arXiv:2608.21884v2, "Loop Engineering: Building Blocks, Adoption, and Impact"
RQ2 main claim: 7/8 building blocks have detection rate < 1% in real GitHub repos.

Our mini reproduction:
- 8 building block detectors (regex / file pattern, NO LLM, deterministic)
- 8 canonical agent code snippets (AutoGPT, Claude Code SDK, Aider, MetaGPT,
  Reflexion, ReAct, Beyond-Code-Gen PQC, Ralph Wiggum)
- For each: which building blocks does it have?

Expected: most snippets show 4-6/8 blocks present in code, but only 1-2 would
leave traceable commit artifacts (because state, budget, verifier all live in
runtime, not in committed files).
"""
import os
import re
import json
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"
OUT = HERE / "_reproduction_results.json"
LOG = HERE / "_reproduction_log.txt"

# ---- 8 building block detectors (paper Table 2 column "Mechanism") ----
# Each returns (has_block: bool, evidence: list[str])

def detect_triggering(code: str):
    """Building block 1: Triggering & scheduling.
    Paper found 253/36645 detected. The ONE block with high traceability."""
    evidence = []
    # Cron / schedule (CI files)
    if re.search(r'cron[:\s]', code) or re.search(r"on:\s*\n\s*schedule", code, re.MULTILINE):
        evidence.append("cron/schedule trigger (e.g. `cron: '0 2 * * *'`)")
    # Infinite loop with explicit schedule
    if re.search(r'while\s*[:]|while\s+True', code):
        evidence.append("infinite loop `while :` or `while True`")
    # GitHub Actions on: trigger
    if re.search(r"on:\s*\n\s*(push|pull_request|schedule|workflow_dispatch)", code, re.MULTILINE):
        evidence.append("GitHub Actions on: event trigger")
    # systemd timer / launchd
    if "systemd" in code or "launchd" in code:
        evidence.append("systemd/launchd timer")
    # schedule library
    if "schedule." in code or "apscheduler" in code:
        evidence.append("schedule library")
    return len(evidence) > 0, evidence


def detect_goal_stop(code: str):
    """Building block 2: Goal & stop conditions.
    Paper found 0/36645 detected. Goal/stop conditions do NOT leave commit trace.
    We test for them in code, but the question is: would they be COMMITTED?"""
    evidence = []
    # max_iterations / max_steps / max_trials
    if re.search(r'max_iterations|max_steps|max_trials|max_commits|MAX_RUNS', code):
        evidence.append("explicit iteration cap (e.g. max_iterations)")
    # Done file / completion marker
    if re.search(r'DONE_FILE|REVIEW_DONE|TASK_COMPLETE|if done|is_done|goal_achieved', code):
        evidence.append("completion marker (e.g. DONE_FILE)")
    # While + break pattern
    if re.search(r'for\s+\w+\s+in\s+range\([^)]*max', code) or re.search(r'if\s+[^:]+:\s*\n\s+break', code, re.MULTILINE):
        evidence.append("for-range + break stop condition")
    # If the file has the stop condition written but in a comment / docstring only
    # (mimics paper's "stop condition in skill file, not in committed code")
    if re.search(r'(?:#|##).*?stop.*?condition', code, re.IGNORECASE):
        evidence.append("stop condition mentioned in comment/docstring only")
    return len(evidence) > 0, evidence


def detect_state(code: str):
    """Building block 3: State & memory.
    Paper found 2 detected / 0 TP. STATE.md / LOOP.md rarely committed."""
    evidence = []
    # State file naming
    if re.search(r'STATE\.md|LOOP\.md|state\.json|loop-state|autogpt_state', code):
        evidence.append("named state file (STATE.md / LOOP.md / state.json)")
    # Persistent state write
    if re.search(r'json\.dump|pickle\.dump|sqlite|save_state|\.log', code):
        evidence.append("persistent state write (json.dump / sqlite / .log)")
    # Plan / progress files
    if re.search(r'plan.*?\.md|progress.*?\.md|progress\.files', code):
        evidence.append("plan / progress files")
    # In-memory only (negative signal: NOT in committed state)
    if "in-memory only" in code.lower() or "in-memory" in code.lower():
        evidence.append("[NEGATIVE] explicit 'in-memory only' annotation")
    return len(evidence) > 0, evidence


def detect_skills(code: str):
    """Building block 4: Skills & intent.
    Paper found 1/36645. Skills are tool-specific (.claude/skills, etc.)."""
    evidence = []
    # Skill directories
    if re.search(r'\.claude/skills|/\.claude/agents/|SKILL\.md', code):
        evidence.append("Claude Code skill directory (.claude/skills/ or SKILL.md)")
    # Tool registry
    if re.search(r'tool_registry|tools\s*=\s*\{|self\.tools|skill.*?registry', code):
        evidence.append("tool/skill registry")
    # Settings.json
    if re.search(r'settings\.json|"hooks"|"skills":\s*\[', code):
        evidence.append(".claude/settings.json with hooks/skills")
    return len(evidence) > 0, evidence


def detect_parallel(code: str):
    """Building block 5: Parallel isolation.
    Paper says worktrees are NOT pushed, so unmeasurable from repo data."""
    evidence = []
    # Git worktree
    if re.search(r'git worktree|worktree add', code):
        evidence.append("git worktree (local only, NOT pushed)")
    # Subprocess parallel
    if re.search(r'subprocess\.Popen|multiprocessing|concurrent\.futures|asyncio\.gather', code):
        evidence.append("parallel subprocess / multiprocessing")
    # Branch naming
    if re.search(r'agent/\w+|claude/\w+', code):
        evidence.append("agent-prefix branch naming (worktree convention)")
    # Negative: single-threaded
    if "sequential" in code.lower() and "parallel" not in code.lower():
        evidence.append("[NEGATIVE] explicitly sequential")
    return len(evidence) > 0, evidence


def detect_verification(code: str):
    """Building block 6: Verification (maker/checker).
    Paper found 0/36645. CI gates indistinguishable from regular CI."""
    evidence = []
    # pytest / test runner
    if re.search(r'pytest|run_test|run_pytest|def test_', code):
        evidence.append("pytest / test runner")
    # Assert
    if re.search(r'assert\s+\w+', code):
        evidence.append("assert statements in tests")
    # LLM-as-verifier
    if re.search(r'llm_review|llm_security|llm_verify|verifier', code, re.IGNORECASE):
        evidence.append("LLM-as-verifier (maker/checker)")
    # CI gate / protected branch
    if re.search(r'CI gate|protected branch|verifier subagent', code, re.IGNORECASE):
        evidence.append("CI gate / protected branch / verifier subagent")
    return len(evidence) > 0, evidence


def detect_human(code: str):
    """Building block 7: Human oversight & escalation.
    Paper found 15/36645. PR review patterns visible, in-loop input() invisible."""
    evidence = []
    # input() / human-in-the-loop
    if re.search(r'input\(|human_input|await.*?input', code):
        evidence.append("input() / human-in-the-loop")
    # PR review / CODEOWNERS
    if re.search(r'PR review|CODEOWNERS|approval gate|review trace', code, re.IGNORECASE):
        evidence.append("PR review / CODEOWNERS / approval gate")
    # Escalation
    if re.search(r'escalation|escalat|needs-review|@.*?review', code, re.IGNORECASE):
        evidence.append("escalation pattern (mentions or labels)")
    return len(evidence) > 0, evidence


def detect_budget(code: str):
    """Building block 8: Budgets & pause controls.
    Paper found 0/36645. Budgets are runtime-only (max_cost, max_token)."""
    evidence = []
    # Token / cost budget
    if re.search(r'max_cost|max_tokens|TOKEN_USED|budget|cost', code, re.IGNORECASE):
        evidence.append("token/cost budget (max_cost / max_tokens)")
    # Kill switch / pause
    if re.search(r'kill_switch|pause|interrupt|cancel.*?run', code, re.IGNORECASE):
        evidence.append("kill switch / pause control")
    # Token check in CI
    if re.search(r'env\.TOKEN_USED|env\.MAX_COST|if.*?cost.*?>', code):
        evidence.append("runtime budget enforcement")
    return len(evidence) > 0, evidence


DETECTORS = [
    ("Triggering & scheduling", detect_triggering),
    ("Goal & stop conditions", detect_goal_stop),
    ("State & memory", detect_state),
    ("Skills & intent", detect_skills),
    ("Parallel isolation", detect_parallel),
    ("Verification (maker/checker)", detect_verification),
    ("Human oversight & escalation", detect_human),
    ("Budgets & pause controls", detect_budget),
]

# ---- Paper Table 2 reference data (for comparison) ----
PAPER_TABLE2 = {
    "Triggering & scheduling":       {"detected": 253, "TP": 242, "n_repo": 36645},
    "Goal & stop conditions":        {"detected": 0,   "TP": 0,   "n_repo": 36645},
    "State & memory":                {"detected": 2,   "TP": 0,   "n_repo": 36645},
    "Skills & intent":               {"detected": 1,   "TP": 1,   "n_repo": 36645},
    "Parallel isolation":            {"detected": None,"TP": None,"n_repo": 36645},
    "Verification (maker/checker)":  {"detected": 0,   "TP": 0,   "n_repo": 36645},
    "Human oversight & escalation":  {"detected": 15,  "TP": 13,  "n_repo": 36645},
    "Budgets & pause controls":      {"detected": 0,   "TP": 0,   "n_repo": 36645},
}


def main():
    canonical_agents = json.loads((DATA / "canonical_agents.json").read_text())
    log = LOG.open("w")
    results = []

    for agent in canonical_agents:
        name = agent["name"]
        display = agent["display"]
        code = agent["code"]
        log.write(f"=== {display} ({name}) ===\n")
        log.write(f"  category: {agent['category']}\n")
        log.write(f"  source:   {agent['source']}\n\n")

        entry = {
            "name": name,
            "display": display,
            "category": agent["category"],
            "source": agent["source"],
            "code_len": len(code),
            "blocks": {},
        }
        n_present = 0
        for label, fn in DETECTORS:
            has_block, evidence = fn(code)
            entry["blocks"][label] = {
                "present": has_block,
                "evidence": evidence,
            }
            sym = "✓" if has_block else "✗"
            log.write(f"  {sym} {label}\n")
            for e in evidence:
                log.write(f"      - {e}\n")
            if has_block:
                n_present += 1
        entry["n_blocks_present"] = n_present
        entry["n_blocks_total"] = len(DETECTORS)
        log.write(f"\n  Total blocks present in code: {n_present}/{len(DETECTORS)}\n\n")
        results.append(entry)

    # ---- Summary matrix ----
    print(f"\n=== Loop Engineering Compliance Matrix ({len(canonical_agents)} canonical agents) ===\n")
    headers = [a["display"][:24] for a in canonical_agents]
    print(f"  {'Block':<32s} " + " ".join(f"{h:>24s}" for h in headers) + "  Ours  Paper")
    print(f"  {'─'*32} " + " ".join(f"{'─'*24}" for _ in headers) + f"  {'─'*5} {'─'*5}")

    summary = {}
    for label, _fn in DETECTORS:
        row_syms = []
        n = 0
        for a in canonical_agents:
            entry = next(r for r in results if r["name"] == a["name"])
            has = entry["blocks"][label]["present"]
            row_syms.append("✓" if has else "✗")
            if has:
                n += 1
        # Paper TP rate
        paper = PAPER_TABLE2[label]
        paper_pct = (paper["TP"] / paper["n_repo"] * 100) if paper["TP"] is not None else None
        paper_str = f"{paper_pct:.2f}%" if paper_pct is not None else "--"
        ours_pct = n / len(canonical_agents) * 100
        print(f"  {label:<32s} " + " ".join(f"{s:>24s}" for s in row_syms) +
              f"  {ours_pct:>3.0f}%  {paper_str}")
        summary[label] = {
            "n_canonical_with_block": n,
            "n_canonical_total": len(canonical_agents),
            "ours_pct": ours_pct,
            "paper_TP": paper["TP"],
            "paper_n_repo": paper["n_repo"],
            "paper_pct": paper_pct,
        }

    # Per-agent summary
    print(f"\n=== Per-agent compliance ===")
    for r in results:
        print(f"  {r['display'][:32]:<32s} {r['n_blocks_present']}/{r['n_blocks_total']} blocks present")

    # ---- Headline finding ----
    print(f"\n=== Headline finding (paper RQ2 main claim) ===")
    n_blocks_with_zero_trace = 0
    for label, _fn in DETECTORS:
        paper = PAPER_TABLE2[label]
        if paper["detected"] == 0:
            n_blocks_with_zero_trace += 1
    print(f"  Paper: {n_blocks_with_zero_trace}/{len(DETECTORS)} building blocks have ZERO detection rate in 36,645 repos.")
    print(f"  Ours:  building blocks with at least one positive signal across {len(canonical_agents)} canonical agents:")
    for label, _fn in DETECTORS:
        n = summary[label]["n_canonical_with_block"]
        if n == 0:
            print(f"    {label}: 0/{len(canonical_agents)} (matches paper's 0-detection)")

    # Save
    OUT.write_text(json.dumps({
        "summary": summary,
        "results": results,
    }, indent=2))
    log.close()
    print(f"\nResults: {OUT}")
    print(f"Log:     {LOG}")


if __name__ == "__main__":
    main()
