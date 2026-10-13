"""Algorithm 1 端到端测试（不依赖真数据集）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from wikiskill.agents import InferenceAgent, WikiMaintainer, SkillProposer
from wikiskill.llm import MockLLM
from wikiskill.orchestrator import algorithm_one_loop, ABLATION_CONFIGS
from wikiskill.skills import SkillsStore
from wikiskill.workspace import WikiWorkspace


def make_tasks(n: int) -> list[dict]:
    out = []
    for i in range(n):
        out.append({
            "uid": f"t-{i}",
            "question": f"Question {i}?",
            "options": [f"a-{i}", f"b-{i}", f"c-{i}"],
            "answer": [f"a-{i}"],
        })
    return out


def test_full_loop_runs():
    """Algorithm 1 跑 3 迭代不报错，返回结构化结果。"""
    cfg = ABLATION_CONFIGS["full"]
    llm = MockLLM(seed=42)
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
        train=make_tasks(10),
        val=make_tasks(3),
        n_iters=3,
        early_stop=False,
    )

    # 结构断言
    assert "val_per_iter" in res
    assert len(res["val_per_iter"]) >= 1
    assert "final_wiki" in res
    assert "final_skills" in res
    assert "log" in res
    assert res["elapsed_sec"] >= 0
    print(f"✓ test_full_loop_runs: iters={len(res['val_per_iter'])}, "
          f"wiki_size={res['final_wiki_size']}, "
          f"n_commits={res['n_commits']}, n_rollbacks={res['n_rollbacks']}")


def test_early_stop_at_perfect():
    """如果 baseline R_best=1.0，应该立即 early stop。"""
    llm = MockLLM(seed=42, base_accuracy=1.0, wiki_aware=True)  # 100% 正确
    workspace = WikiWorkspace()
    skills = SkillsStore()
    inf = InferenceAgent(llm, wiki_aware=True)
    mnt = WikiMaintainer(llm)
    prop = SkillProposer(llm, wiki_aware=True)

    res = algorithm_one_loop(
        workspace=workspace,
        skills=skills,
        inference=inf,
        maintainer=mnt,
        proposer=prop,
        train=make_tasks(3),
        val=make_tasks(2),
        n_iters=5,
        early_stop=True,
    )
    # baseline 后 R_best=1.0 应该 early stop，wiki 还没开始增
    assert res["final_R_best"] == 1.0
    assert res["final_wiki_size"] == 0, "wiki should not grow when early-stopped at iter 0"
    print(f"✓ test_early_stop_at_perfect: wiki_size={res['final_wiki_size']}")


if __name__ == "__main__":
    test_full_loop_runs()
    test_early_stop_at_perfect()
    print("\n所有 orchestrator 测试通过。")
