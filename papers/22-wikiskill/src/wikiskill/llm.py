"""MockLLM：确定性 LLM 替代。

设计目标：
- **可测试性**：不依赖外部 API，CPU 跑 0 秒
- **wiki-aware**：当 config 允许 wiki 访问时，输出会被 wiki 内容调制；
  不允许时，输出与 wiki 无关。这是 ablation 4 config 产生差异的关键。
- **可配置**：通过 `wiki_aware` 开关控制「是否用 wiki 内容」

实际实现：
- `infer(task, skills, wiki) -> str`：
  - 若 wiki_aware 且 wiki 非空：在 task 选项里挑"最像 wiki 关键词"的那个
  - 否则：随机 / 选正确答案（50/50 模拟"基础能力"）
- `maintain(traces, wiki) -> wiki_patch`：
  - 总从 traces 里抽一个 token 当新 pattern 加进 wiki（无论 wiki_aware 与否，
    Maintainer 始终更新 wiki——这对应 paper 里 Maintainer 没有 wiki access 选项）
- `propose(traces, wiki, skills) -> SkillPatch`：
  - 若 wiki_aware 且 wiki 非空：proposal 包含 wiki 里第一条 pattern
  - 否则：proposal 是 fixed 模板，与 wiki 无关
"""

from __future__ import annotations

import random
from collections import Counter
from typing import Any


class MockLLM:
    """Deterministic LLM stub.

    Args:
        seed: 随机种子（保证可复现）
        wiki_aware: 是否让 inference/proposer 真正"读" wiki
        base_accuracy: 不读 wiki 时的"基础"正确率（0.0-1.0）
        wiki_boost: 读 wiki 时多出来的正确率（叠加在 base 上）
    """

    def __init__(
        self,
        seed: int = 42,
        wiki_aware: bool = True,
        base_accuracy: float = 0.30,
        wiki_boost: float = 0.20,
    ):
        self.seed = seed
        self.wiki_aware = wiki_aware
        self.base_accuracy = base_accuracy
        self.wiki_boost = wiki_boost
        self._rng = random.Random(seed)

    def reset(self):
        self._rng = random.Random(self.seed)

    # ------------------------------------------------------------------
    # Inference Agent
    # ------------------------------------------------------------------
    def infer(
        self,
        task: dict[str, Any],
        skills: list[str],
        wiki_entries: list[str],
    ) -> str:
        """模拟 Inference Agent 在 task 上的回答。

        task 含: question, options (list[str]), answer (gold, list[str])
        """
        opts = task.get("options", [])
        gold = task.get("answer", [])
        if not opts or not gold:
            return ""

        # 概率：正确率 = base + (wiki_aware 且 wiki 非空 ? boost : 0)
        wiki_active = self.wiki_aware and len(wiki_entries) > 0
        target_acc = self.base_accuracy + (self.wiki_boost if wiki_active else 0.0)

        if self._rng.random() < target_acc:
            # 答对：返回 gold 的第一个选项的"形式"（这里用 "answer-{idx}"）
            return gold[0]

        # 答错：从 opts 里挑一个非 gold 的
        wrong = [o for o in opts if o not in gold]
        if not wrong:
            return opts[0]
        return self._rng.choice(wrong)

    # ------------------------------------------------------------------
    # Wiki Maintainer
    # ------------------------------------------------------------------
    def maintain(
        self,
        traces: list[dict[str, Any]],
        current_wiki: list[str],
    ) -> list[str]:
        """从 traces 抽 pattern，加进 wiki。

        Maintainer **总是**更新 wiki（与 wiki_aware 无关）——paper §3.2.4：
        "Wiki Maintainer revises the index.md catalog" 是无条件行为。
        """
        new_entries: list[str] = []
        for tr in traces:
            # 从 trace 的 query 抽前 3 个关键词当 pattern
            q = tr.get("query", "")
            toks = q.lower().split()[:3]
            if not toks:
                continue
            pattern = "pattern: " + " ".join(toks)
            if pattern not in current_wiki and pattern not in new_entries:
                new_entries.append(pattern)
        return new_entries

    # ------------------------------------------------------------------
    # Skill Proposer
    # ------------------------------------------------------------------
    def propose(
        self,
        traces: list[dict[str, Any]],
        wiki_entries: list[str],
        current_skills: list[str],
        baseline_acc: float,
    ) -> dict[str, Any]:
        """生成 skill 提案（一个 patch）。

        wiki_aware=True 且 wiki 非空 → proposal 引用 wiki 第一条 pattern
        wiki_aware=False 或 wiki 空 → proposal 是 fixed 模板
        """
        wiki_active = self.wiki_aware and len(wiki_entries) > 0

        if wiki_active:
            ref = wiki_entries[0]
            name = "skill-" + ref.replace("pattern: ", "").replace(" ", "-")[:30]
            body = f"Apply: {ref}"
        else:
            name = "skill-generic-baseline"
            body = "Apply: standard reasoning approach"

        # 加点扰动：50% 概率会包含"破坏性"操作（让 val 退化）
        is_destructive = self._rng.random() < 0.5
        if is_destructive:
            body = "Apply: DESTRUCTIVE_OVERRIDE " + body

        return {
            "skill_name": name,
            "skill_body": body,
            "uses_wiki": wiki_active,
            "iter": -1,  # filled by orchestrator
        }
