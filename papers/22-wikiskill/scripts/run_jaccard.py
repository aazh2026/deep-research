"""计算 5 个 ablation config 之间的 wiki + skill Jaccard 矩阵。

目的：量化 ablation 4 config 在 wiki 内容和 skill 内容上的真实差异。
v1 弱点：4 config wiki 完全相同（Jaccard=1.0），因为 Maintainer 不看 skills。
v2 改进：Maintainer skill-aware → wiki 内容随 config 分歧。
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


def _jaccard(a: set, b: set) -> float:
    """Jaccard 相似度 = |A∩B| / |A∪B|。两个空集 → 1.0（vacuously similar）。"""
    if not a and not b:
        return 1.0
    return len(a & b) / len(a | b)


def _wiki_set(full_wiki: list[str], mode: str = "all") -> set[str]:
    """把 wiki entry 列表转成 set。mode 控制是否按 prefix 过滤。"""
    if mode == "pattern":
        return {w for w in full_wiki if w.startswith("pattern:")}
    if mode == "skill_use":
        return {w for w in full_wiki if w.startswith("skill_use:")}
    return set(full_wiki)


def run_one(config_name: str, train, val, n_iters: int, seed: int) -> dict:
    cfg = ABLATION_CONFIGS[config_name]
    llm = MockLLM(seed=seed, wiki_aware=True)
    workspace = WikiWorkspace()
    skills = SkillsStore()
    inf = InferenceAgent(llm, wiki_aware=cfg["inf_wiki"])
    mnt = WikiMaintainer(llm)
    prop = SkillProposer(llm, wiki_aware=cfg["prop_wiki"])

    res = algorithm_one_loop(
        workspace=workspace,
        skills=skills,
        inference=inf,
        maintainer=mnt,
        proposer=prop,
        train=[task_to_dict(t) for t in train],
        val=[task_to_dict(t) for t in val],
        n_iters=n_iters,
        early_stop=True,
        no_maintainer=cfg.get("no_maintainer", False),
    )
    return res


def compute_jaccard_matrices(per_config: dict[str, dict]) -> dict:
    """对所有 config 两两算 Jaccard：wiki_all / wiki_pattern / wiki_skill_use / skill_body。"""
    names = list(per_config.keys())

    # 4 个矩阵
    matrices = {
        "wiki_all": [[0.0] * len(names) for _ in names],
        "wiki_pattern": [[0.0] * len(names) for _ in names],
        "wiki_skill_use": [[0.0] * len(names) for _ in names],
        "skill_body": [[0.0] * len(names) for _ in names],
    }

    for i, na in enumerate(names):
        for j, nb in enumerate(names):
            w_a = _wiki_set(per_config[na]["final_wiki"], "all")
            w_b = _wiki_set(per_config[nb]["final_wiki"], "all")
            matrices["wiki_all"][i][j] = round(_jaccard(w_a, w_b), 3)

            wp_a = _wiki_set(per_config[na]["final_wiki"], "pattern")
            wp_b = _wiki_set(per_config[nb]["final_wiki"], "pattern")
            matrices["wiki_pattern"][i][j] = round(_jaccard(wp_a, wp_b), 3)

            ws_a = _wiki_set(per_config[na]["final_wiki"], "skill_use")
            ws_b = _wiki_set(per_config[nb]["final_wiki"], "skill_use")
            matrices["wiki_skill_use"][i][j] = round(_jaccard(ws_a, ws_b), 3)

            s_a = set(per_config[na]["final_skills"])
            s_b = set(per_config[nb]["final_skills"])
            matrices["skill_body"][i][j] = round(_jaccard(s_a, s_b), 3)

    return {"names": names, "matrices": matrices}


def main():
    n_iters = 8
    seeds = [42, 123, 7, 256, 999]
    out_dir = Path(__file__).parent.parent / "outputs"
    out_dir.mkdir(exist_ok=True)

    print("[jaccard] loading LiveMath 50 题子集 ...")
    splits = load_livemath_subset(n_total=50, seed=42, cache_dir="./cache")
    train, val = splits["train"], splits["val"]

    # 每 config 5 seeds 跑一次（取每 seed 的 final_wiki + final_skills）
    print(f"[jaccard] running {len(ABLATION_CONFIGS)} configs × {len(seeds)} seeds × {n_iters} iters ...")
    per_config_runs: dict[str, list[dict]] = {n: [] for n in ABLATION_CONFIGS}
    for seed in seeds:
        for name in ABLATION_CONFIGS:
            res = run_one(name, train, val, n_iters=n_iters, seed=seed)
            per_config_runs[name].append({
                "seed": seed,
                "final_wiki": res["final_wiki"],
                "final_skills": res["final_skills"],
            })
        print(f"  seed={seed} done")

    # 取每个 config 在所有 seed 下 union 的 wiki + intersection 的 wiki
    # 用于"最坏/最好情况"的 Jaccard 估计
    per_config_union: dict[str, dict] = {}
    per_config_intersection: dict[str, dict] = {}
    per_config_first_seed: dict[str, dict] = {}
    for name, runs in per_config_runs.items():
        all_wikis = [set(r["final_wiki"]) for r in runs]
        all_skills = [set(r["final_skills"]) for r in runs]
        per_config_union[name] = {
            "final_wiki": list(set().union(*all_wikis)),
            "final_skills": list(set().union(*all_skills)),
        }
        per_config_intersection[name] = {
            "final_wiki": list(set().intersection(*all_wikis)) if all_wikis else [],
            "final_skills": list(set().intersection(*all_skills)) if all_skills else [],
        }
        per_config_first_seed[name] = {
            "final_wiki": runs[0]["final_wiki"],
            "final_skills": runs[0]["final_skills"],
        }

    # 算 3 个版本的 Jaccard：union / intersection / first_seed
    jaccard_union = compute_jaccard_matrices(per_config_union)
    jaccard_intersection = compute_jaccard_matrices(per_config_intersection)
    jaccard_first = compute_jaccard_matrices(per_config_first_seed)

    summary = {
        "n_seeds": len(seeds),
        "n_iters": n_iters,
        "config_names": list(ABLATION_CONFIGS.keys()),
        "jaccard_first_seed": jaccard_first,
        "jaccard_union_across_seeds": jaccard_union,
        "jaccard_intersection_across_seeds": jaccard_intersection,
    }

    out_path = out_dir / "jaccard_matrix.json"
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\n[jaccard] wrote {out_path}")

    # 打印 first-seed wiki_all 矩阵
    print("\n[jaccard] first-seed wiki_all Jaccard matrix:")
    names = jaccard_first["names"]
    print("            " + "  ".join(f"{n[:10]:>10s}" for n in names))
    for i, na in enumerate(names):
        row = jaccard_first["matrices"]["wiki_all"][i]
        print(f"  {na[:10]:10s} " + "  ".join(f"{v:>10.3f}" for v in row))

    print("\n[jaccard] first-seed skill_body Jaccard matrix:")
    print("            " + "  ".join(f"{n[:10]:>10s}" for n in names))
    for i, na in enumerate(names):
        row = jaccard_first["matrices"]["skill_body"][i]
        print(f"  {na[:10]:10s} " + "  ".join(f"{v:>10.3f}" for v in row))

    # 计算关键 metric：no_wiki vs full 的 Jaccard
    j_full = jaccard_first["matrices"]
    i_no = names.index("no_wiki")
    i_full = names.index("full")
    print(f"\n[jaccard] no_wiki vs full:")
    print(f"  wiki_all:     {j_full['wiki_all'][i_no][i_full]:.3f}")
    print(f"  wiki_pattern: {j_full['wiki_pattern'][i_no][i_full]:.3f}")
    print(f"  wiki_skill_use: {j_full['wiki_skill_use'][i_no][i_full]:.3f}")
    print(f"  skill_body:   {j_full['skill_body'][i_no][i_full]:.3f}")


if __name__ == "__main__":
    main()
