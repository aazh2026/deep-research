"""三层 Workspace：Raw / Wiki / Skills。

按 paper §3.1 + Figure 2：
- **Raw Layer** (`raw/`)：不可变、write-once，存训练 trace
- **Wiki Layer** (`wiki/`)：持续累积、**永不重置**，存 pattern + log
- **Skills Layer** (`skills/`)：可逆，存当前活跃 skill 集

本文件只管 wiki + raw（workspace 部分）。
Skills 由 `skills.py::SkillsStore` 管，因为 skill 涉及 gating 逻辑。
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class WikiEntry:
    """Wiki 里的一条 pattern。"""

    entry_id: str
    text: str
    iter_added: int
    source: str  # "maintainer" / "log" / "skill_impact"


@dataclass
class WikiLog:
    """按迭代顺序记录的演化历史。"""

    entries: list[dict[str, Any]] = field(default_factory=list)

    def append(self, iter_k: int, proposal: dict, val_score: float, accepted: bool):
        self.entries.append({
            "iter": iter_k,
            "skill_name": proposal.get("skill_name"),
            "skill_body": proposal.get("skill_body"),
            "uses_wiki": proposal.get("uses_wiki"),
            "val_score": val_score,
            "accepted": accepted,
            "ts": time.time(),
        })


class WikiWorkspace:
    """三层 workspace（只管理 raw + wiki；skills 独立）。

    关键 invariant：**wiki 永远只增不减**，rollback 也不删。
    """

    def __init__(self, root: str = ""):
        # 持久化层（in-memory 模拟文件系统）
        self.raw: list[dict[str, Any]] = []
        self.wiki: list[WikiEntry] = []
        self.log = WikiLog()
        self._iter = 0
        self._root = root or "workspace"

    # ------------------------------------------------------------------
    # Raw layer（write-once）
    # ------------------------------------------------------------------
    def write_raw(self, trace: dict[str, Any]):
        """追加一条不可变 trace。"""
        trace = dict(trace)
        trace["_raw_id"] = hashlib.sha1(
            json.dumps(trace, sort_keys=True, default=str).encode()
        ).hexdigest()[:12]
        self.raw.append(trace)

    # ------------------------------------------------------------------
    # Wiki layer（monotonic add-only）
    # ------------------------------------------------------------------
    def update_wiki(self, new_entries: list[str], source: str = "maintainer"):
        """追加 pattern（去重、永不删）。

        paper §3.2.2："Updates to pattern pages are applied using incremental,
        patch-based editing ... The wiki is not reset between iterations."
        """
        existing_texts = {e.text for e in self.wiki}
        for txt in new_entries:
            if txt in existing_texts:
                continue
            entry_id = hashlib.sha1(txt.encode()).hexdigest()[:10]
            self.wiki.append(WikiEntry(
                entry_id=entry_id,
                text=txt,
                iter_added=self._iter,
                source=source,
            ))
            existing_texts.add(txt)

    def read_wiki(self) -> list[str]:
        """返回所有 wiki entries 的文本。"""
        return [e.text for e in self.wiki]

    def read_wiki_entries(self) -> list[WikiEntry]:
        return list(self.wiki)

    # ------------------------------------------------------------------
    # Log + iteration counter
    # ------------------------------------------------------------------
    def log_iteration(self, iter_k: int, proposal: dict, val_score: float, accepted: bool):
        """在 wiki 的 log.md 里追加本次迭代。paper §3.2.4。"""
        proposal = dict(proposal)
        proposal["iter"] = iter_k
        self.log.append(iter_k, proposal, val_score, accepted)
        self._iter = max(self._iter, iter_k)

    # ------------------------------------------------------------------
    # Invariants
    # ------------------------------------------------------------------
    def wiki_size(self) -> int:
        return len(self.wiki)

    def wiki_hash(self) -> str:
        """用于测试：wiki 字节级哈希。"""
        canon = "|".join(sorted(e.text for e in self.wiki))
        return hashlib.sha1(canon.encode()).hexdigest()

    def is_wiki_subset_of(self, other: "WikiWorkspace") -> bool:
        """测试用：self.wiki ⊆ other.wiki（按 entry_id）"""
        mine = {e.entry_id for e in self.wiki}
        theirs = {e.entry_id for e in other.wiki}
        return mine.issubset(theirs)

    # ------------------------------------------------------------------
    # Snapshot / restore（仅用于测试；生产 wiki 不应被 restore）
    # ------------------------------------------------------------------
    def snapshot(self) -> dict:
        return {
            "raw": list(self.raw),
            "wiki": [
                {"entry_id": e.entry_id, "text": e.text, "iter_added": e.iter_added}
                for e in self.wiki
            ],
            "log": list(self.log.entries),
            "iter": self._iter,
        }

    def restore(self, snap: dict):
        self.raw = list(snap["raw"])
        self.wiki = [
            WikiEntry(
                entry_id=e["entry_id"],
                text=e["text"],
                iter_added=e["iter_added"],
                source="restored",
            )
            for e in snap["wiki"]
        ]
        self.log = WikiLog(entries=list(snap["log"]))
        self._iter = snap["iter"]
