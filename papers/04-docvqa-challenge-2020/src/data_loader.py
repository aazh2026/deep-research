"""DocVQA Challenge 2020 数据加载。

- Task 1 (VQA on Document Images): 50K QA / 12,767 imgs — 用 nielsr/docvqa_1200_examples
- Task 2 (VQA on Document Image Collection): 14,362 imgs, 20 queries — 文档检索
"""

from __future__ import annotations

from dataclasses import dataclass

from datasets import load_dataset


@dataclass
class DocVQAQuestion:
    """Task 1 一道问题。"""

    uid: str
    query: str
    answers: list[str]
    words: list[str]
    n_words: int
    image_size: tuple[int, int] | None = None
    split: str = ""


def load_task1(name: str = "train", cache_dir: str = "./cache") -> list[DocVQAQuestion]:
    """加载 nielsr/docvqa_1200_examples（与 03-docvqa 共用）。"""
    print(f"[task1] 加载 split={name} ...")
    ds = load_dataset("nielsr/docvqa_1200_examples", split=name, cache_dir=cache_dir)
    out: list[DocVQAQuestion] = []
    for row in ds:
        q = row["query"]
        if isinstance(q, dict):
            query_en = q.get("en", next(iter(q.values())))
        else:
            query_en = str(q)
        out.append(
            DocVQAQuestion(
                uid=row["id"],
                query=query_en,
                answers=list(row.get("answers") or []),
                words=list(row.get("words") or []),
                n_words=len(row.get("words") or []),
                image_size=row["image"].size if "image" in row else None,
                split=name,
            )
        )
    print(f"[task1]   {name}: {len(out)} 题")
    return out


def words_to_text(words: list[str], sep: str = " ") -> str:
    return sep.join(w for w in words if w)
