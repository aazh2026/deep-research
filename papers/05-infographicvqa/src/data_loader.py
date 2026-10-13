"""InfographicVQA 数据加载。

Paper: Mathew et al. "InfographicVQA" (WACV 2022, arXiv:2104.12756)
Dataset: mm-eval/InfographicVQA on HF
  - validation: 2801 问
  - test: 3288 问

每题结构：
- id: int（如 69369）
- media: list[PIL.Image]（单图）
- messages: JSON 字符串，list of {role, question, hint, options, choices}
- answer: list[str]（多 gold，与 03-docvqa ANLS 多 gold 取 max 一致）
- question_type: 'numeric' / 'open' / 'yes_no'

复现目标（受 CPU 限制）：
- ANLS 官方公式（与 03-docvqa 共用）
- Question-type-aware 盲 baseline
  - numeric → 中位数 / 众数
  - open → 多数文本
  - yes_no → 多数 yes/no
- 验证「信息图 VQA 比 DocVQA 难」——paper 核心 claim
"""

from __future__ import annotations

import json
from dataclasses import dataclass

from datasets import load_dataset


@dataclass
class InfoVQAQuestion:
    """InfographicVQA 一道问题。"""

    uid: str
    query: str
    answers: list[str]
    question_type: str  # numeric / open / yes_no
    image_size: tuple[int, int] | None = None


def _parse_messages(messages_str: str) -> str:
    """从 messages JSON 字符串里抽 question 文本。"""
    msgs = json.loads(messages_str)
    if not msgs:
        return ""
    return msgs[0].get("question", "")


def load_split(name: str = "validation",
               cache_dir: str = "./cache",
               max_questions: int | None = None) -> list[InfoVQAQuestion]:
    """加载 mm-eval/InfographicVQA。

    name: 'validation' (2801) 或 'test' (3288)
    """
    print(f"[data] 加载 InfographicVQA split={name} ...")
    ds = load_dataset("mm-eval/InfographicVQA", split=name, cache_dir=cache_dir)
    out: list[InfoVQAQuestion] = []
    for row in ds:
        media = row.get("media") or []
        img_size = media[0].size if media else None
        out.append(
            InfoVQAQuestion(
                uid=str(row.get("id", "")),
                query=_parse_messages(row.get("messages", "[]")),
                answers=[str(a).lower().strip() for a in (row.get("answer") or [])],
                question_type=row.get("question_type", "open"),
                image_size=img_size,
            )
        )
        if max_questions and len(out) >= max_questions:
            break
    print(f"[data]   {name}: {len(out)} 题")
    return out


def stats_summary(qs: list[InfoVQAQuestion]) -> dict:
    from collections import Counter
    qt = Counter(q.question_type for q in qs)
    n_ans = Counter(len(q.answers) for q in qs)
    avg_q_len = sum(len(q.query.split()) for q in qs) / len(qs) if qs else 0
    avg_ans_len = sum(
        sum(len(a.split()) for a in q.answers) / max(1, len(q.answers))
        for q in qs
    ) / len(qs) if qs else 0
    return {
        "total": len(qs),
        "question_type_dist": dict(qt),
        "n_answers_dist": dict(n_ans),
        "avg_question_words": avg_q_len,
        "avg_answer_words": avg_ans_len,
    }
