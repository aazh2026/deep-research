"""Density 指标。

论文公式 (Eq. 6)：
  Den(Z) = ( Cov(Z) / token(Z) / (Cov(Z*) / token(Z*)) )^w

其中：
- Cov(Z): Z 的 Coverage
- token(Z): Z 中 passage 的总 token 数
- Z*: oracle 检索（贪心构造的最小 passage 集，能 answer 所有 sub-questions）
- w: 权重（论文默认 0.5）

Density 是「单位 token 的覆盖率」：以 oracle 为基准做归一化。
"""

from __future__ import annotations

from typing import Callable

Grader = Callable[[str, str], int]


def count_tokens(text: str) -> int:
    """简单 token 计数（按空白 + 标点拆），与论文 token 化口径近似。"""
    import re
    return len(re.findall(r"\S+", text))


def token_count_of_passages(passages: list[str]) -> int:
    """Z 的总 token 数。"""
    return sum(count_tokens(p) for p in passages)


def build_oracle(
    passages: list[str],
    queries_Q: list[tuple[str, str]],
    grader: Grader,
    eta: int = 3,
) -> list[str]:
    """贪心构造 oracle Z*。

    论文：迭代地选「能 answer 最多未覆盖 sub-questions」的 passage ，
    直到所有 sub-questions 都答得上为止。
    """
    if not queries_Q or not passages:
        return []

    # 每个 passage 预计算它能 answer 的 sub-questions
    passage_answers: list[set[int]] = []
    for p in passages:
        answered: set[int] = set()
        for i, (_, ig) in enumerate(queries_Q):
            if grader(p, ig) >= eta:
                answered.add(i)
        passage_answers.append(answered)

    uncovered: set[int] = set(range(len(queries_Q)))
    oracle: list[str] = []
    while uncovered:
        # 选能 answer 最多未覆盖 sub-questions 的 passage
        best_idx = -1
        best_count = 0
        for i, answered in enumerate(passage_answers):
            new_covered = len(answered & uncovered)
            if new_covered > best_count:
                best_count = new_covered
                best_idx = i
        if best_idx < 0 or best_count == 0:
            # 没有 passage 能再覆盖任何未覆盖问题 — 提前终止
            break
        oracle.append(passages[best_idx])
        uncovered -= passage_answers[best_idx]
    return oracle


def compute_density(
    passages_Z: list[str],
    oracle_Z_star: list[str],
    queries_Q: list[tuple[str, str]],
    grader: Grader,
    cov_Z: float | None = None,
    cov_oracle: float | None = None,
    eta: int = 3,
    w: float = 0.5,
) -> float:
    """对单个样本计算 Density。

    Args:
        passages_Z: 检索返回的 passage 集合。
        oracle_Z_star: 贪心 oracle 集合（已构造好或传 None 自动构造）。
        queries_Q: sub-question 列表。
        grader: G(passage, I_g) -> int。
        cov_Z, cov_oracle: 预计算的 Coverage（避免重复调用）。
        eta: 阈值。
        w: 权重（论文默认 0.5）。

    Returns:
        density ∈ [0, 1]（论文定义 Z 比 oracle 更密时 ≥ 1）
    """
    from src.coverage import compute_coverage

    token_Z = token_count_of_passages(passages_Z)
    if token_Z == 0:
        return 0.0

    if cov_Z is None:
        cov_Z = compute_coverage(passages_Z, queries_Q, grader, eta)

    # 如果 oracle 为空或 token=0，视为边界情况
    if not oracle_Z_star:
        return 0.0
    token_oracle = token_count_of_passages(oracle_Z_star)
    if token_oracle == 0:
        return 0.0

    if cov_oracle is None:
        cov_oracle = compute_coverage(oracle_Z_star, queries_Q, grader, eta)
    if cov_oracle == 0:
        return 0.0

    # (Cov / tok) / (Cov_oracle / tok_oracle)
    base = (cov_Z / token_Z) / (cov_oracle / token_oracle)
    if base <= 0:
        return 0.0
    return base ** w
