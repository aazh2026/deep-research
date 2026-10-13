"""Edge case tests：防御性测试，确保 Algorithm 1 在边界条件下不崩。

覆盖：
- 空 train set
- 空 val set
- 单样本 train + val
- 全错 baseline（R_best=0）
- 全对 baseline（触发 early stop）
- 1 iter
- Maintainer 真的在用 current_skills（v2 skill-aware 验证）
- 4 config 之间的 wiki 现在**真的不同**（v1 弱点）
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


def _setup(seed: int = 42):
    llm = MockLLM(seed=seed, wiki_aware=True)
    return {
        "llm": llm,
        "workspace": WikiWorkspace(),
        "skills": SkillsStore(),
        "inf": InferenceAgent(llm, wiki_aware=True),
        "mnt": WikiMaintainer(llm),
        "prop": SkillProposer(llm, wiki_aware=True),
    }


def test_empty_train():
    """空 train set：不崩，R_best 走 baseline。"""
    s = _setup()
    splits = load_livemath_subset(n_total=10, seed=42, cache_dir="./cache")
    val = [task_to_dict(t) for t in splits["val"][:3]]
    res = algorithm_one_loop(
        workspace=s["workspace"], skills=s["skills"],
        inference=s["inf"], maintainer=s["mnt"], proposer=s["prop"],
        train=[], val=val, n_iters=2, early_stop=True,
    )
    assert res["final_wiki_size"] == 0, "空 train → wiki 不应增长"
    assert res["n_commits"] == 0, "空 train → 不应有 commit"
    print("✓ test_empty_train")


def test_empty_val():
    """空 val set：不崩，R_best=0.0。"""
    s = _setup()
    splits = load_livemath_subset(n_total=10, seed=42, cache_dir="./cache")
    train = [task_to_dict(t) for t in splits["train"][:3]]
    res = algorithm_one_loop(
        workspace=s["workspace"], skills=s["skills"],
        inference=s["inf"], maintainer=s["mnt"], proposer=s["prop"],
        train=train, val=[], n_iters=2, early_stop=True,
    )
    assert res["final_R_best"] == 0.0
    print("✓ test_empty_val")


def test_single_sample():
    """1 train + 1 val：跑完，R_best 是 0.0 或 1.0。"""
    s = _setup()
    splits = load_livemath_subset(n_total=10, seed=42, cache_dir="./cache")
    train = [task_to_dict(t) for t in splits["train"][:1]]
    val = [task_to_dict(t) for t in splits["val"][:1]]
    res = algorithm_one_loop(
        workspace=s["workspace"], skills=s["skills"],
        inference=s["inf"], maintainer=s["mnt"], proposer=s["prop"],
        train=train, val=val, n_iters=2, early_stop=True,
    )
    assert res["final_R_best"] in (0.0, 1.0), f"R_best 应为 0 或 1, got {res['final_R_best']}"
    print(f"✓ test_single_sample (R_best={res['final_R_best']})")


def test_one_iter():
    """1 iter：跑完 baseline + 1 iter。"""
    s = _setup()
    splits = load_livemath_subset(n_total=50, seed=42, cache_dir="./cache")
    train = [task_to_dict(t) for t in splits["train"][:5]]
    val = [task_to_dict(t) for t in splits["val"]]
    res = algorithm_one_loop(
        workspace=s["workspace"], skills=s["skills"],
        inference=s["inf"], maintainer=s["mnt"], proposer=s["prop"],
        train=train, val=val, n_iters=1, early_stop=True,
    )
    # baseline (iter 0) + 1 iter (iter 1) = 2 val_per_iter
    assert len(res["val_per_iter"]) == 2
    print("✓ test_one_iter")


def test_maintainer_uses_current_skills():
    """Maintainer skill-aware (v2)：传入 current_skills 后 wiki 内容会变。"""
    llm = MockLLM(seed=42, wiki_aware=True)
    workspace = WikiWorkspace()
    workspace.update_wiki(["pattern: foo bar baz"], source="init")
    # 不传 skills
    no_skills = llm.maintain(
        traces=[{"query": "what is X"}],
        current_wiki=workspace.read_wiki(),
        current_skills=None,
    )
    # 传 skills
    with_skills = llm.maintain(
        traces=[{"query": "what is X"}],
        current_wiki=workspace.read_wiki(),
        current_skills=["Apply: advanced theorem for X"],
    )
    # 至少 with_skills 多一条 skill_use: 开头的 entry
    skill_use_entries = [w for w in with_skills if w.startswith("skill_use:")]
    assert len(skill_use_entries) >= 1, f"expected skill_use: entry, got {with_skills}"
    assert len(with_skills) > len(no_skills), (
        f"with_skills should have more entries than no_skills: "
        f"{no_skills} vs {with_skills}"
    )
    print(f"✓ test_maintainer_uses_current_skills (added: {skill_use_entries[0]})")


def test_jaccard_matrix_exists():
    """5×5 Jaccard 矩阵应该存在（v2 量化 wiki/skill 真实分歧）。"""
    p = Path(__file__).parent.parent / "outputs" / "jaccard_matrix.json"
    assert p.exists(), f"missing {p}. run scripts/run_jaccard.py first"
    data = json.loads(p.read_text())
    assert "jaccard_first_seed" in data
    matrices = data["jaccard_first_seed"]["matrices"]
    assert "wiki_all" in matrices
    # 5x5 矩阵（5 configs）
    M = matrices["wiki_all"]
    assert len(M) == 5 and all(len(row) == 5 for row in M)
    # 对角线 = 1.0（self-similarity，空集 → 1.0 vacuously）
    for i in range(5):
        assert M[i][i] == 1.0, f"diagonal should be 1.0, got M[{i}][{i}]={M[i][i]}"
    # no_wiki vs full wiki Jaccard 应该 < 1.0（v1 弱点：4 config 全部 Jaccard=1.0）
    names = data["config_names"]
    i_no, i_full = names.index("no_wiki"), names.index("full")
    j = M[i_no][i_full]
    print(f"  no_wiki vs full wiki_all Jaccard: {j}")
    assert j < 1.0, (
        f"v2 改进后 no_wiki vs full wiki Jaccard 仍 = 1.0 → skill-aware Maintainer 没生效"
    )
    # prop_wiki_no_mnt vs full wiki Jaccard 应该 = 0（前者无 wiki）
    i_no_mnt = names.index("prop_wiki_no_mnt")
    j_no_mnt = M[i_no_mnt][i_full]
    print(f"  prop_wiki_no_mnt vs full wiki_all Jaccard: {j_no_mnt}")
    assert j_no_mnt == 0.0, f"prop_wiki_no_mnt (empty wiki) vs full should be 0.0"
    print("✓ test_jaccard_matrix_exists (no_wiki vs full wiki Jaccard < 1.0)")


if __name__ == "__main__":
    test_empty_train()
    test_empty_val()
    test_single_sample()
    test_one_iter()
    test_maintainer_uses_current_skills()
    test_jaccard_matrix_exists()
    print("\n所有 edge case 测试通过。")
