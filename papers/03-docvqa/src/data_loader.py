"""DocVQA 数据加载。

Paper: Mathew et al. "DocVQA: A Dataset for VQA on Document Images" (WACV 2021)
Dataset: https://huggingface.co/datasets/nielsr/docvqa_1200_examples (1200 train)

每题结构：
- id: str（如 "train_0"）
- image: PIL.Image
- query: dict[lang → str]（多语言：de/en/es/fr/it）
- answers: list[str]（多个标注者给的答案，取 max similarity）
- words: list[str]（OCR 抽出的词）
- bounding_boxes: list[[x0, y0, x1, y1]]（每个词的位置，归一化到 [0, 1000]）
- answer: dict（match info，含 start/end 在 OCR 词序列中的位置）

复现目标（受 CPU 限制）：
- ANLS 官方公式（src/metrics.py）
- 用 OCR words 拼出文档纯文本（baseline text-only retrieval）
- 验证多答案 max-sim 机制
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from datasets import load_dataset


@dataclass
class DocVQAQuestion:
    """DocVQA 一道问题。"""

    uid: str
    query: str  # 用英文版本
    answers: list[str]  # 多 gold
    words: list[str]  # OCR 词列表
    n_words: int  # 词数量（不存完整 list 以节省内存时可用）
    image_size: tuple[int, int] | None = None
    split: str = ""


def load_split(name: str = "train", cache_dir: str = "./cache") -> list[DocVQAQuestion]:
    """加载 nielsr/docvqa_1200_examples 的一个 split。

    只有一个 split "train" 含 1200 题。
    """
    print(f"[data] 加载 DocVQA split={name} ...")
    ds = load_dataset("nielsr/docvqa_1200_examples", split=name, cache_dir=cache_dir)
    out: list[DocVQAQuestion] = []
    for row in ds:
        # 多语言 query 选英文
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
    print(f"[data]   {name}: {len(out)} 题")
    return out


def words_to_text(words: list[str], sep: str = " ") -> str:
    """把 OCR words 拼成一段文本（保留顺序）。

    注：words 是从左到右、从上到下扫描的（不一定按行）。这能保留词序用于
    lexical 检索，但会丢失「按行」的版式信息。
    """
    return sep.join(w for w in words if w)


def stats_summary(qs: list[DocVQAQuestion]) -> dict:
    """统计多答案分布 + OCR words 长度分布。"""
    from collections import Counter

    n_answers_dist: Counter = Counter()
    q_len_dist: Counter = Counter()
    words_len_dist: Counter = Counter()
    for q in qs:
        n_answers_dist[len(q.answers)] += 1
        # 问题长度按词数分桶
        qlen = len(q.query.split())
        q_len_dist[qlen // 5 * 5] += 1  # 0-4, 5-9, 10-14, ...
        # OCR words 长度按百分位分桶
        wlen = q.n_words
        words_len_dist[wlen // 100 * 100] += 1  # 0-99, 100-199, ...
    return {
        "total": len(qs),
        "n_answers_dist": dict(n_answers_dist),
        "q_len_buckets": dict(q_len_dist),
        "ocr_words_buckets": dict(words_len_dist),
        "avg_ocr_words": sum(q.n_words for q in qs) / len(qs) if qs else 0,
        "avg_answers_per_q": sum(len(q.answers) for q in qs) / len(qs) if qs else 0,
    }
