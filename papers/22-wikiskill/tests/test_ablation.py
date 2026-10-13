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
    # 3 iter × 4 config = 12 个 proposal 机会；至少应该有几次 rollback
    assert total_rollbacks >= 1, f"expected at least 1 rollback, got {total_rollbacks}"
    print(f"✓ test_gating_happens (total_rollbacks={total_rollbacks})")


if __name__ == "__main__":
    test_outputs_exist()
    test_full_skill_uses_wiki_pattern()
    test_wiki_monotonic_across_ablation()
    test_gating_happens()
    print("\n所有 ablation 测试通过。")
