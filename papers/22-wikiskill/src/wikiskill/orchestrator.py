"""Algorithm 1 主体：WikiSkill evolution loop。

直接对应 paper §A.1 Algorithm 1（page 19）。
"""

from __future__ import annotations

import time
from typing import Any, Callable

from .agents import InferenceAgent, WikiMaintainer, SkillProposer
from .skills import SkillPatch, SkillsStore
from .workspace import WikiWorkspace


# ---------------------------------------------------------------------------
# 4 个 ablation 配置（Table 3, Gemini-3.5-Flash, default WikiSkill）
# ---------------------------------------------------------------------------
ABLATION_CONFIGS: dict[str, dict[str, bool]] = {
    # Table 3 第一行：NoSkill（baseline）—— Inf 和 Prop 都不读 wiki
    "no_wiki": dict(inf_wiki=False, prop_wiki=False),
    # Table 3 第二行：Inf 读 wiki 但 Prop 不读
    "inf_wiki_only": dict(inf_wiki=True, prop_wiki=False),
    # Table 3 第三行：Prop 读 wiki 但 Inf 不读（去除 Maintainer）
    "prop_wiki_only": dict(inf_wiki=False, prop_wiki=True),
    # Table 3 第四行：default WikiSkill，Inf 和 Prop 都读 wiki
    "full": dict(inf_wiki=True, prop_wiki=True),
}


def _evaluate(
    inference: InferenceAgent,
    val: list[dict],
    skills: list[str],
    wiki_entries: list[str],
) -> float:
    """在 val split 上跑 inference，返回平均 accuracy。"""
    if not val:
        return 0.0
    n_correct = 0
    for task in val:
        tr = inference.rollout(task, skills, wiki_entries)
        if tr["is_correct"]:
            n_correct += 1
    return n_correct / len(val)


def algorithm_one_loop(
    workspace: WikiWorkspace,
    skills: SkillsStore,
    inference: InferenceAgent,
    maintainer: WikiMaintainer,
    proposer: SkillProposer,
    train: list[dict],
    val: list[dict],
    n_iters: int = 3,
    early_stop: bool = True,
) -> dict[str, Any]:
    """Algorithm 1: WikiSkill evolution loop.

    Args:
        workspace: WikiWorkspace（3 层）
        skills: SkillsStore（gating + rollback）
        inference: InferenceAgent
        maintainer: WikiMaintainer
        proposer: SkillProposer
        train: 训练 task 列表
        val: 验证 task 列表
        n_iters: 最大迭代数 K
        early_stop: 达到 R_best=1.0 是否提前终止

    Returns:
        dict: 含 val_per_iter, test_acc (optional), final_wiki, final_skills, log
    """
    val_per_iter: list[dict] = []
    log: list[dict] = []
    t0 = time.time()

    # --- line 2: Baseline validation ---
    wiki_for_inf = workspace.read_wiki() if inference.wiki_aware else []
    R_best = _evaluate(inference, val, skills.current(), wiki_for_inf)
    val_per_iter.append({"iter": 0, "R": R_best, "phase": "baseline"})
    log.append({"event": "baseline", "iter": 0, "R": R_best})

    # --- line 3: for k = 1, ..., K ---
    for k in range(1, n_iters + 1):
        # lines 4-6: early stop
        if early_stop and R_best >= 1.0:
            log.append({"event": "early_stop", "iter": k - 1, "R_best": R_best})
            break

        # --- line 7: Inference on training ---
        train_traces = []
        for task in train:
            tr = inference.rollout(task, skills.current(), wiki_for_inf)
            train_traces.append(tr)
            # raw layer: write-only
            workspace.write_raw({
                "iter": k,
                "split": "train",
                **tr,
            })

        # --- line 9: Wiki Maintainer ---
        new_patterns = maintainer.consolidate(train_traces)
        workspace.update_wiki(new_patterns, source="maintainer")

        # --- line 10: Skill Proposer ---
        proposal: SkillPatch = proposer.propose(
            traces=train_traces,
            wiki_entries=workspace.read_wiki() if proposer.wiki_aware else [],
            current_skills=skills.current(),
            iter_k=k,
        )

        # --- line 11: Apply (stage) ---
        skills.stage(proposal)

        # --- line 12: Validate ---
        wiki_for_inf = workspace.read_wiki() if inference.wiki_aware else []
        R_new = _evaluate(inference, val, skills.staged_text(), wiki_for_inf)

        # --- lines 13-17: gate / commit or rollback ---
        accepted = R_new > R_best
        if accepted:
            skills.commit()
            R_best = R_new
        else:
            skills.rollback()
            # 关键：wiki 永远不动
        a_k = "Accepted" if accepted else "Rejected"

        # --- line 18: Update Wiki Log ---
        workspace.log_iteration(k, proposal.to_dict(), R_new, accepted=accepted)

        val_per_iter.append({
            "iter": k, "R": R_new, "R_best": R_best, "accepted": accepted,
        })
        log.append({
            "event": "iteration",
            "iter": k,
            "proposal": proposal.to_dict(),
            "R_new": R_new,
            "R_best": R_best,
            "accepted": accepted,
        })

    # --- line 20: return S_K, W_K ---
    return {
        "val_per_iter": val_per_iter,
        "final_R_best": R_best,
        "final_wiki": workspace.read_wiki(),
        "final_wiki_size": workspace.wiki_size(),
        "final_skills": skills.current(),
        "n_skills": skills.n_skills(),
        "n_commits": skills.n_commits,
        "n_rollbacks": skills.n_rollbacks,
        "log": log,
        "elapsed_sec": time.time() - t0,
    }
