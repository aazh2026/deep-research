"""Sanity ablation: 用 `forced_no_wiki=True` 的 MockLLM 跑 4 个 config。

目的：验证 ablation 的差异**真的来自 wiki**，而不是 config flag 本身。
如果 forced_no_wiki 下 4 个 config 都产生一样的 generic skill（因为没人用 wiki），
就证明原 ablation 的差异是 wiki-driven，不是 config-flag-driven。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wikiskill.agents import InferenceAgent, WikiMaintainer, SkillProposer
from wikiskill.datasets import load_livemath_subset, task_to_dict
from wikiskill.llm import MockLLM
from wikiskill.orchestrator import algorithm_one_loop, ABLATION_CONFIGS
from wikiskill.skills import SkillsStore
from wikiskill.workspace import WikiWorkspace


def run_sanity_config(config_name: str, train, val, n_iters: int = 8, seed: int = 42) -> dict:
    """跑一个 config，但 MockLLM 强制不看 wiki。"""
    cfg = ABLATION_CONFIGS[config_name]
    # 关键：forced_no_wiki=True 覆盖一切 wiki_aware 开关
    llm = MockLLM(seed=seed, wiki_aware=True, forced_no_wiki=True)
    workspace = WikiWorkspace()
    skills = SkillsStore()
    inf = InferenceAgent(llm, wiki_aware=cfg["inf_wiki"])
    mnt = WikiMaintainer(llm)
    prop = SkillProposer(llm, wiki_aware=cfg["prop_wiki"])

    train_dicts = [task_to_dict(t) for t in train]
    val_dicts = [task_to_dict(t) for t in val]

    res = algorithm_one_loop(
        workspace=workspace,
        skills=skills,
        inference=inf,
        maintainer=mnt,
        proposer=prop,
        train=train_dicts,
        val=val_dicts,
        n_iters=n_iters,
        early_stop=True,
        no_maintainer=cfg.get("no_maintainer", False),
    )
    return res


def main():
    out_dir = Path(__file__).parent.parent / "outputs"
    out_dir.mkdir(exist_ok=True)

    print("[sanity] loading LiveMath 50 题子集 ...")
    splits = load_livemath_subset(n_total=50, seed=42, cache_dir="./cache")
    train, val = splits["train"], splits["val"]

    print("[sanity] MockLLM.forced_no_wiki=True → 4 configs should be IDENTICAL")
    print("[sanity] (any diff is config-flag-driven, NOT wiki-driven)")

    summary: dict[str, dict] = {}
    for name in ABLATION_CONFIGS:
        res = run_sanity_config(name, train, val, n_iters=8, seed=42)
        summary[name] = {
            "config": ABLATION_CONFIGS[name],
            "final_R_best": res["final_R_best"],
            "final_wiki_size": res["final_wiki_size"],
            "final_skills": res["final_skills"],
            "n_commits": res["n_commits"],
            "n_rollbacks": res["n_rollbacks"],
        }
        print(f"  {name:20s} R={res['final_R_best']:.3f} "
              f"wiki={res['final_wiki_size']:3d} "
              f"skills={res['final_skills'][:1] if res['final_skills'] else '(none)'}")

    out_path = out_dir / "sanity_summary.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    print(f"\n[sanity] wrote {out_path}")

    # 验证：4 config 的 skill bodies 应该全一样（因为 forced_no_wiki）
    skill_sets = {name: frozenset(d["final_skills"]) for name, d in summary.items()}
    distinct = set(skill_sets.values())
    print(f"\n[sanity] distinct skill sets across 4 configs: {len(distinct)}")
    print(f"[sanity] expected: 1 (all configs should produce identical generic skills)")

    if len(distinct) == 1:
        print("✓ PASSED: 4 configs produced IDENTICAL skill bodies")
        print("  → ablation difference in main run is wiki-driven (not config-flag)")
        return 0
    else:
        print("✗ FAILED: 4 configs produced DIFFERENT skill bodies")
        for name, skills in skill_sets.items():
            print(f"  {name}: {skills}")
        print("  → ablation difference in main run may be config-flag-driven")
        return 1


if __name__ == "__main__":
    sys.exit(main())
