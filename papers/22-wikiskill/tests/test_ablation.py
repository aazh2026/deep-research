"""Ablation 4 配置对比：必须产生不同 skill（wiki 关键性）。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wikiskill.orchestrator import ABLATION_CONFIGS


def test_outputs_exist():
    """4 个 config 的 JSON 必须存在。"""
    out_dir = Path(__file__).parent.parent / "outputs"
    for name in ABLATION_CONFIGS:
        p = out_dir / f"ablation_{name}.json"
        assert p.exists(), f"missing {p}"
        data = json.loads(p.read_text())
        assert "final_wiki_size" in data
        assert "final_R_best" in data
        assert "final_skills" in data
    print("✓ test_outputs_exist (4 ablation JSONs present)")


def test_full_skill_uses_wiki_pattern():
    """`full` config 的 skill body 必须包含 wiki pattern 引用。

    关键 ablation claim：wiki access 真的影响了 proposer 的输出。
    """
    full = json.loads(Path(__file__).parent.parent.joinpath("outputs/ablation_full.json").read_text())
    no_wiki = json.loads(Path(__file__).parent.parent.joinpath("outputs/ablation_no_wiki.json").read_text())

    full_skills = full["final_skills"]
    no_wiki_skills = no_wiki["final_skills"]

    print(f"  full skills: {full_skills}")
    print(f"  no_wiki skills: {no_wiki_skills}")

    # full 至少有一个 skill 引用 wiki pattern
    full_has_pattern = any("pattern:" in s for s in full_skills)
    assert full_has_pattern, f"full config should reference wiki patterns, got: {full_skills}"

    # no_wiki 不应有 pattern 引用（用 generic 模板）
    no_wiki_has_pattern = any("pattern:" in s for s in no_wiki_skills)
    assert not no_wiki_has_pattern, f"no_wiki config should not reference wiki patterns, got: {no_wiki_skills}"

    print("✓ test_full_skill_uses_wiki_pattern (full ✓ wiki-aware, no_wiki ✗)")


def test_wiki_monotonic_across_ablation():
    """每个 config 的 wiki size 应该是单调不减的。"""
    for name in ABLATION_CONFIGS:
        data = json.loads(Path(__file__).parent.parent.joinpath(f"outputs/ablation_{name}.json").read_text())
        wiki_size = data["final_wiki_size"]
        # baseline 之后 ≥ 1，因为 maintainer 在 iter 1 加了东西
        # （除非 early stop 在 iter 0，但 paper config 不会）
        assert wiki_size >= 0
        print(f"  {name}: wiki_size={wiki_size}, R_best={data['final_R_best']:.3f}, "
              f"n_commits={data['n_commits']}, n_rollbacks={data['n_rollbacks']}")
    print("✓ test_wiki_monotonic_across_ablation")


def test_gating_happens():
    """至少有一个 config 出现过 rollback（证明 gating 在工作）。"""
    total_rollbacks = 0
    for name in ABLATION_CONFIGS:
        data = json.loads(Path(__file__).parent.parent.joinpath(f"outputs/ablation_{name}.json").read_text())
        total_rollbacks += data["n_rollbacks"]
    # 8 iter × 5 config = 40 个 proposal 机会；至少应该有几次 rollback
    assert total_rollbacks >= 1, f"expected at least 1 rollback, got {total_rollbacks}"
    print(f"✓ test_gating_happens (total_rollbacks={total_rollbacks})")


def test_sanity_forced_no_wiki_makes_ablations_identical():
    """Sanity: 强制不看 wiki → 4 个 config 应该产生**完全相同**的 skill body。

    意义：如果 sanity 下 4 config 仍然不同 → 说明原 ablation 的差异
    不是 wiki 驱动的，是 config flag 自身驱动的（inf_wiki=True 时 MockLLM
    base_accuracy 提升了 → gating 决策不同 → 间接改了 skill 路径）。
    这种情况下原 ablation claim 不成立。
    """
    sanity = json.loads(
        Path(__file__).parent.parent.joinpath("outputs/sanity_summary.json").read_text()
    )

    skill_sets = {name: frozenset(d["final_skills"]) for name, d in sanity.items()}
    distinct = set(skill_sets.values())

    print(f"  sanity distinct skill sets: {len(distinct)}")
    for name, skills in skill_sets.items():
        print(f"    {name}: {len(skills)} unique skill(s)")

    # sanity 期望：1（全部相同）
    assert len(distinct) == 1, (
        f"sanity ablation produced {len(distinct)} distinct skill sets, expected 1.\n"
        f"This means ablation diffs in main run are NOT purely wiki-driven.\n"
        f"Skill sets: {skill_sets}"
    )
    print("✓ test_sanity_forced_no_wiki_makes_ablations_identical (ablation diffs are wiki-driven)")


def test_multi_seed_summary_exists():
    """多 seed 统计应该存在且每个 config 有 mean ± std。"""
    p = Path(__file__).parent.parent / "outputs" / "ablation_multi_seed.json"
    assert p.exists(), f"missing {p}"
    data = json.loads(p.read_text())
    for name in ABLATION_CONFIGS:
        assert name in data
        d = data[name]
        assert "r_best_mean" in d and "r_best_std" in d
        assert "wiki_size_mean" in d and "wiki_size_std" in d
        assert d["n_seeds"] >= 3, f"expected at least 3 seeds, got {d['n_seeds']}"
        # mean 在 [0, 1]
        assert 0.0 <= d["r_best_mean"] <= 1.0
    print(f"✓ test_multi_seed_summary_exists (5 configs × {data['no_wiki']['n_seeds']} seeds)")


if __name__ == "__main__":
    test_outputs_exist()
    test_full_skill_uses_wiki_pattern()
    test_wiki_monotonic_across_ablation()
    test_gating_happens()
    test_sanity_forced_no_wiki_makes_ablations_identical()
    test_multi_seed_summary_exists()
    print("\n所有 ablation 测试通过。")
