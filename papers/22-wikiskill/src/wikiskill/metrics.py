"""简单 metrics：exact match + accuracy。

复现不需要复杂 metric（paper 用 f(y_i, ỹ_i) ∈ [0,1] domain-specific score），
对 LiveMath MCQ 只需「预测 ∈ gold 集合？」。
"""

from __future__ import annotations

from typing import Any


def exact_match(pred: str, gold: list[str]) -> bool:
    if not pred or not gold:
        return False
    return pred in gold


def accuracy(predictions: list[str], gold_lists: list[list[str]]) -> float:
    if not predictions:
        return 0.0
    n = sum(1 for p, g in zip(predictions, gold_lists) if exact_match(p, g))
    return n / len(predictions)
