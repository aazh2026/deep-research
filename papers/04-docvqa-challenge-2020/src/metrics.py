"""DocVQA Challenge 2020 metric 实现。

论文：Mathew et al. "Document Visual Question Answering Challenge 2020" (arXiv:2008.08899)

包含两个 metric：

1. **ANLS** (Average Normalized Levenshtein Similarity)
   - Task 1 用，公式与 DocVQA 主 paper 一致
   - NED = edit_distance / max(|a|, |b|)
   - S = 1 - NED  if NED < τ
   - 多 gold 取 max
   - τ = 0.5

2. **MAP** (Mean Average Precision)
   - Task 2 用，文档检索场景
   - 对每个 query，计算 AP = mean of (precision @ k for k in ranked hits)
   - 然后 mean over queries
"""

from __future__ import annotations

import editdistance


# ---------------------------------------------------------------------------
# ANLS（与 03-docvqa 严格对齐）
# ---------------------------------------------------------------------------

def levenshtein(s1: str, s2: str) -> int:
    return editdistance.eval(s1, s2)


def anls_score(prediction: str, ground_truths: list[str], tau: float = 0.5) -> float:
    pred = prediction.lower().strip()
    best = 0.0
    for gt in ground_truths:
        gt = gt.lower().strip()
        if not pred and not gt:
            return 1.0
        if not pred or not gt:
            continue
        d = levenshtein(pred, gt)
        nld = d / max(len(pred), len(gt))
        if nld < tau:
            score = 1.0 - nld
            if score > best:
                best = score
    return best


def anls_dataset(predictions: list[str],
                 ground_truths_list: list[list[str]],
                 tau: float = 0.5) -> dict:
    assert len(predictions) == len(ground_truths_list)
    scores = [
        anls_score(p, gts, tau)
        for p, gts in zip(predictions, ground_truths_list)
    ]
    n = len(scores)
    return {
        "anls": sum(scores) / n if n else 0.0,
        "n": n,
        "scores": scores,
    }


# ---------------------------------------------------------------------------
# MAP (Mean Average Precision) for Task 2 retrieval
# ---------------------------------------------------------------------------

def average_precision(retrieved: list[str], relevant: set[str]) -> float:
    """单个 query 的 AP。

    参数：
    - retrieved: 按预测相关性降序的文档 ID 列表
    - relevant: gold 相关文档 ID 集合

    AP = (1/|R|) * sum over k where retrieved[k] in R of (precision at k)

    注：这是 standard AP 公式，对"无召回"的情况返回 0（不是 0.5）。
    """
    if not relevant:
        return 0.0
    hits = 0
    sum_precisions = 0.0
    for k, doc_id in enumerate(retrieved, start=1):
        if doc_id in relevant:
            hits += 1
            sum_precisions += hits / k
    return sum_precisions / len(relevant)


def mean_average_precision(predictions: list[list[str]],
                           gold_relevant: list[set[str]]) -> dict:
    """MAP = mean over queries of AP.

    参数：
    - predictions: list of [retrieved_doc_ids_in_order] for each query
    - gold_relevant: list of {relevant_doc_ids} for each query
    """
    assert len(predictions) == len(gold_relevant)
    aps = [average_precision(p, r) for p, r in zip(predictions, gold_relevant)]
    n = len(aps)
    return {
        "map": sum(aps) / n if n else 0.0,
        "n": n,
        "aps": aps,
    }


def precision_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """P@k = |top-k ∩ relevant| / k。"""
    if k <= 0 or not retrieved:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for d in top_k if d in relevant)
    return hits / k


def recall_at_k(retrieved: list[str], relevant: set[str], k: int) -> float:
    """R@k = |top-k ∩ relevant| / |relevant|。"""
    if not relevant or k <= 0:
        return 0.0
    top_k = retrieved[:k]
    hits = sum(1 for d in top_k if d in relevant)
    return hits / len(relevant)
