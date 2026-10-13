"""检索器：BM25 + Oracle（已移到 density.py）+ Random baseline。

CRUX 原版对比的 retrieval 系统：
- Oracle：贪心构造（见 density.build_oracle）
- BM25（用 Pyserini / rank_bm25）
- 论文还对比了 dense retrieval（E5 / BGE），本地 CPU 跑不动
"""

from __future__ import annotations

import random
import re
from typing import Callable

from rank_bm25 import BM25Okapi

from src.density import build_oracle
from src.grader import tokenize


def bm25_retrieve(
    query: str,
    passages: list[str],
    top_k: int = 20,
) -> list[str]:
    """对 query 在 passages 上做 BM25 检索，返回 top_k 个 passage。

    使用 rank_bm25（pure Python，CPU 友好）。
    """
    if not passages:
        return []
    tokenized_corpus = [tokenize(p) for p in passages]
    bm25 = BM25Okapi(tokenized_corpus)
    q_toks = tokenize(query)
    if not q_toks:
        return []
    scores = bm25.get_scores(q_toks)
    # top_k
    top_idx = sorted(range(len(scores)), key=lambda i: -scores[i])[:top_k]
    return [passages[i] for i in top_idx]


def bm25_retrieve_per_query(
    queries_Q: list[tuple[str, str]],
    passages: list[str],
    top_k: int = 20,
    dedup: bool = True,
) -> list[str]:
    """对一组 sub-question 各自 BM25 检索，合并去重 → top_k passage。

    这是 BM25 在 RAG 里的常见做法：多 query 检索后合并。
    """
    seen: set[str] = set()
    collected: list[str] = []
    for q_text, _ in queries_Q:
        for p in bm25_retrieve(q_text, passages, top_k=top_k):
            if dedup and p in seen:
                continue
            seen.add(p)
            collected.append(p)
            if len(collected) >= top_k:
                return collected
    return collected


def bm25_retrieve_against_summary(
    summary: str,
    passages: list[str],
    top_k: int = 20,
) -> list[str]:
    """直接用 summary 当 query 做 BM25 检索（等价于「答案相关」检索）。"""
    return bm25_retrieve(summary, passages, top_k=top_k)


def random_retrieve(passages: list[str], top_k: int = 20, seed: int = 0) -> list[str]:
    """Random baseline：随机抽 top_k passage。"""
    if not passages:
        return []
    rng = random.Random(seed)
    idx = list(range(len(passages)))
    rng.shuffle(idx)
    return [passages[i] for i in idx[:top_k]]


def oracle_retrieve(
    passages: list[str],
    queries_Q: list[tuple[str, str]],
    grader,
    eta: int = 3,
) -> list[str]:
    """Oracle 检索 = density.build_oracle 的别名。"""
    return build_oracle(passages, queries_Q, grader, eta)
