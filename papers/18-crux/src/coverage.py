"""Coverage 指标。

论文公式 (Eq. 3)：
  Cov(Z) = #{q ∈ Q | max(G(p ∈ Z, q, I_g)) ≥ η} / |Q|

其中：
- Z：检索返回的 passage 集合
- Q：sub-question 集合
- G(p, q, I_g)：grader 评分（0–5）
- η：阈值（论文默认 3）
"""

from __future__ import annotations

from typing import Callable

Grader = Callable[[str, str], int]


def compute_coverage(
    passages_Z: list[str],
    queries_Q: list[tuple[str, str]],
    grader: Grader,
    eta: int = 3,
) -> float:
    """对单个查询样本计算 Coverage。

    Args:
        passages_Z: 检索返回的 passage 列表。
        queries_Q: sub-question 列表，每项为 (q_text, I_g_text)。
        grader: G(passage, I_g) -> int in [0, 5]。
        eta: 阈值 η（论文默认 3）。

    Returns:
        coverage ∈ [0, 1]
    """
    if not queries_Q:
        return 0.0
    n_covered = 0
    for q_text, ig in queries_Q:
        max_g = 0
        for p in passages_Z:
            g = grader(p, ig)
            if g > max_g:
                max_g = g
            if max_g >= eta:
                break
        if max_g >= eta:
            n_covered += 1
    return n_covered / len(queries_Q)


def compute_coverage_batch(
    retrieved_Z_per_sample: list[list[str]],
    queries_Q_per_sample: list[list[tuple[str, str]]],
    grader: Grader,
    eta: int = 3,
) -> list[float]:
    """对多个样本批量计算 Coverage。"""
    return [
        compute_coverage(Z, Q, grader, eta)
        for Z, Q in zip(retrieved_Z_per_sample, queries_Q_per_sample)
    ]
