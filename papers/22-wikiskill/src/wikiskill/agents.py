"""三个 Agent：Inference / WikiMaintainer / SkillProposer。

paper §3.2.1-3.2.3。

每个 agent 都被一个 MockLLM 驱动（避免真 LLM 调用）。
"wiki access" 由构造时的 `wiki_aware` 决定。
"""

from __future__ import annotations

from typing import Any

from .llm import MockLLM
from .skills import SkillPatch


class InferenceAgent:
    """执行 task 给出预测。"""

    def __init__(self, llm: MockLLM, wiki_aware: bool = True):
        # 重要：inference 的 wiki_aware 与 proposer 独立
        # 但本实现里两者共享同一个 llm 对象的 wiki_aware
        # 实际 ablation 用两个 MockLLM 实例分别配置
        self.llm = llm
        self.wiki_aware = wiki_aware

    def rollout(self, task: dict, skills: list[str], wiki_entries: list[str]) -> dict:
        """执行一道题，返回一条 trace。"""
        wiki_for_infer = wiki_entries if self.wiki_aware else []
        pred = self.llm.infer(task, skills, wiki_for_infer)
        return {
            "query": task.get("question", ""),
            "prediction": pred,
            "gold": task.get("answer", []),
            "is_correct": self._is_correct(pred, task.get("answer", [])),
        }

    @staticmethod
    def _is_correct(pred: str, gold: list[str]) -> bool:
        if not pred or not gold:
            return False
        # 用最简单的 set membership 模拟"答对"
        return pred in gold


class WikiMaintainer:
    """从 traces 抽 pattern 写入 wiki。"""

    def __init__(self, llm: MockLLM):
        self.llm = llm

    def consolidate(self, traces: list[dict]) -> list[str]:
        return self.llm.maintain(traces, current_wiki=[])


class SkillProposer:
    """基于 wiki + traces 提议 skill 改动。"""

    def __init__(self, llm: MockLLM, wiki_aware: bool = True):
        self.llm = llm
        self.wiki_aware = wiki_aware

    def propose(
        self,
        traces: list[dict],
        wiki_entries: list[str],
        current_skills: list[str],
        iter_k: int,
    ) -> SkillPatch:
        wiki_for_prop = wiki_entries if self.wiki_aware else []
        raw = self.llm.propose(
            traces=traces,
            wiki_entries=wiki_for_prop,
            current_skills=current_skills,
            baseline_acc=0.0,
        )
        raw["iter"] = iter_k
        return SkillPatch(
            skill_name=raw["skill_name"],
            skill_body=raw["skill_body"],
            uses_wiki=raw.get("uses_wiki", False),
            iter=iter_k,
        )
