"""Skills Layer：门控（gating）+ 回滚（rollback）。

paper §3.2.4 Algorithm 1 lines 12-16：

  12:  Validate: T_val,k ← {τ_i ~ π(x_i; S'_k)}_{x_i ∈ D_val}
  13:  if R(T_val,k) > R_best then
  14:    S_k ← S'_k,  R_best ← R(T_val,k),  a_k ← Accepted
  15:  else
  16:    S_k ← S_{k-1},  a_k ← Rejected
  17:  end if
  18:  Update Wiki Log: W_k ← Update(W'_k, P_k, R(T_val,k), a_k)

关键 invariant：
- 接受：candidate S'_k 替换 S_k，wiki 保留
- 拒绝：S_k 回到 S_{k-1}（**wiki 不回滚**）
- 即「skill 可逆，wiki 不可逆」
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillPatch:
    """一个 skill 提案。"""

    skill_name: str
    skill_body: str
    uses_wiki: bool = False
    iter: int = -1

    def to_dict(self) -> dict:
        return {
            "skill_name": self.skill_name,
            "skill_body": self.skill_body,
            "uses_wiki": self.uses_wiki,
            "iter": self.iter,
        }


@dataclass
class SkillRecord:
    """已 commit 的 skill 记录。"""

    name: str
    body: str
    iter_committed: int
    uses_wiki: bool


class SkillsStore:
    """当前活跃 skill 集 + ledger + gating + rollback。

    接口：
    - `current() -> list[str]`：返回当前 skills 的字符串表示
    - `stage(patch) -> list[str]`：把 patch 应用到一份临时副本，返回 staged skills
    - `commit() / rollback()`：根据 val score 决定接受还是回退
    - `ledger`：所有已 commit skill 的历史
    """

    def __init__(self, initial: list[SkillRecord] | None = None):
        self._active: list[SkillRecord] = list(initial or [])
        self._staged: list[SkillRecord] | None = None
        self.n_rollbacks = 0
        self.n_commits = 0
        # 全局 skill ledger（包含被回滚的）
        self.ledger: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # 当前活跃
    # ------------------------------------------------------------------
    def current(self) -> list[str]:
        """返回当前 skills 的"文本"列表（用于注入 inference agent prompt）。"""
        return [r.body for r in self._active]

    def staged_text(self) -> list[str]:
        """返回 staged skills 的文本（仅在 stage 之后、commit/rollback 之前有效）。"""
        if self._staged is None:
            return self.current()
        return [r.body for r in self._staged]

    def has_staged(self) -> bool:
        return self._staged is not None

    def active_records(self) -> list[SkillRecord]:
        return list(self._active)

    def n_skills(self) -> int:
        return len(self._active)

    # ------------------------------------------------------------------
    # Stage（临时副本，不影响 self._active）
    # ------------------------------------------------------------------
    def stage(self, patch: SkillPatch) -> list[str]:
        """把 patch 应用到副本；返回副本的 skills 文本列表。"""
        # 简化版：每个 proposal 替换一个名为 patch.skill_name 的 skill；
        # 没有则追加。
        new_active = list(self._active)
        replaced = False
        for i, rec in enumerate(new_active):
            if rec.name == patch.skill_name:
                new_active[i] = SkillRecord(
                    name=patch.skill_name,
                    body=patch.skill_body,
                    iter_committed=patch.iter,
                    uses_wiki=patch.uses_wiki,
                )
                replaced = True
                break
        if not replaced:
            new_active.append(SkillRecord(
                name=patch.skill_name,
                body=patch.skill_body,
                iter_committed=patch.iter,
                uses_wiki=patch.uses_wiki,
            ))
        self._staged = new_active
        return [r.body for r in new_active]

    # ------------------------------------------------------------------
    # Commit / Rollback
    # ------------------------------------------------------------------
    def commit(self) -> bool:
        """把 staged 设为 active。返回 True。"""
        if self._staged is None:
            return False
        self._active = self._staged
        self._staged = None
        self.n_commits += 1
        # 追加 ledger
        for rec in self._active:
            self.ledger.append({
                "name": rec.name,
                "body": rec.body,
                "iter_committed": rec.iter_committed,
                "uses_wiki": rec.uses_wiki,
                "status": "active",
            })
        return True

    def rollback(self) -> bool:
        """丢弃 staged，active 保持不变（**wiki 不动**）。返回 True。"""
        if self._staged is None:
            return False
        self._staged = None
        self.n_rollbacks += 1
        # 记录被回滚的 skill
        return True

    # ------------------------------------------------------------------
    # 验证入口（Algorithm 1 line 12-13 的"门控"）
    # ------------------------------------------------------------------
    def gate(self, val_score: float, R_best: float) -> bool:
        """根据 val score 决定 commit 还是 rollback。

        Returns:
            True if accepted, False if rejected
        """
        if val_score > R_best:
            self.commit()
            return True
        else:
            self.rollback()
            return False

    # ------------------------------------------------------------------
    # 快照（用于测试）
    # ------------------------------------------------------------------
    def snapshot(self) -> dict:
        return {
            "active": [r.__dict__ for r in self._active],
            "n_rollbacks": self.n_rollbacks,
            "n_commits": self.n_commits,
        }

    def restore(self, snap: dict):
        self._active = [SkillRecord(**r) for r in snap["active"]]
        self.n_rollbacks = snap["n_rollbacks"]
        self.n_commits = snap["n_commits"]
        self._staged = None
