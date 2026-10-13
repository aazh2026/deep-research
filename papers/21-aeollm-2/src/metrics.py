"""NTCIR-19 AEOLLM-2 metric 忠实复现。

论文：Chen et al. "Overview of the NTCIR-19 Automatic Evaluation of LLMs 2 (AEOLLM-2) Task"
       (NTCIR-19, December 8-10, 2026, Tokyo, Japan, arXiv:2610.11598)

3 个核心 metric 全部实现：

1. **Pairwise Accuracy (acc)**:
   - 对每对候选答案 (i, j)，比较 participant score s_i vs s_j 与
     human score h_i vs h_j 的「偏好方向」是否一致
   - z_ij = sign(s_i - s_j), z'_ij = sign(h_i - h_j)
   - z ∈ {-1, 0, 1}（-1: i<j, 0: tie, 1: i>j）
   - acc = mean over pairs of I[z_ij = z'_ij]
   - 双方都 tie 的对（z = 0 AND z' = 0）算 correct（按 paper "tied pair is correct only if both indicate tie"）

2. **Spearman ρ**: 经典 Pearson on ranks
   - r_q,i = rank of answer i from participant score
   - r'_q,i = rank of answer i from human score
   - 经典公式：cov(r, r') / (σ_r * σ_r')

3. **Kendall τ_b (with ties)**:
   - C = concordant pairs, D = discordant pairs
   - T = ties in participant only, U = ties in human only
   - 双 tie 的对**不计入** T 或 U
   - τ = (C - D) / √[(C + D + T)(C + D + U)]
"""

from __future__ import annotations

from itertools import combinations
from typing import Iterable


# ---------------------------------------------------------------------------
# Pairwise Accuracy
# ---------------------------------------------------------------------------

def preference_relation(s_i: float, s_j: float) -> int:
    """sign(s_i - s_j)：返回 -1, 0, 1。"""
    if s_i < s_j:
        return -1
    if s_i > s_j:
        return 1
    return 0


def pairwise_accuracy(participant_scores: list[float],
                      human_scores: list[float]) -> dict:
    """单 query 的 pairwise accuracy。

    参数：
    - participant_scores: 参赛系统对每个 answer 的评分（按 answerId 顺序）
    - human_scores: 人工对每个 answer 的评分（按 answerId 顺序）

    返回：
    - acc: float
    - n_pairs: 总对数
    - n_correct: 偏好一致的对数
    """
    assert len(participant_scores) == len(human_scores)
    n = len(participant_scores)
    if n < 2:
        return {"acc": 1.0, "n_pairs": 0, "n_correct": 0}
    n_correct = 0
    n_pairs = 0
    for i, j in combinations(range(n), 2):
        z = preference_relation(participant_scores[i], participant_scores[j])
        z_prime = preference_relation(human_scores[i], human_scores[j])
        n_pairs += 1
        if z == z_prime:
            n_correct += 1
    return {"acc": n_correct / n_pairs, "n_pairs": n_pairs, "n_correct": n_correct}


# ---------------------------------------------------------------------------
# Spearman ρ
# ---------------------------------------------------------------------------

def _rank_with_ties(values: list[float]) -> list[float]:
    """Average-rank for ties (competition / "1 2.5 2.5 4" ranking)。

    返回每个位置的平均 rank（浮点）。Ties 共享相同 rank = mean of positions。
    """
    n = len(values)
    # 排序后的 indices
    sorted_idx = sorted(range(n), key=lambda i: values[i])
    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        # 找 ties
        while j + 1 < n and values[sorted_idx[j + 1]] == values[sorted_idx[i]]:
            j += 1
        # tie group [i..j] 的平均 rank（1-based）
        avg_rank = (i + 1 + j + 1) / 2
        for k in range(i, j + 1):
            ranks[sorted_idx[k]] = avg_rank
        i = j + 1
    return ranks


def _pearson(xs: list[float], ys: list[float]) -> float:
    """Pearson 相关系数（无 NaN guard）。"""
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    if var_x == 0 or var_y == 0:
        return 0.0
    return cov / (var_x * var_y) ** 0.5


def spearman_rho(participant_scores: list[float],
                 human_scores: list[float]) -> dict:
    """单 query 的 Spearman ρ。

    用 average-rank for ties，按 Pearson on ranks 算。
    """
    r = _rank_with_ties(participant_scores)
    r_prime = _rank_with_ties(human_scores)
    rho = _pearson(r, r_prime)
    return {"rho": rho, "ranks": r, "ranks_human": r_prime}


# ---------------------------------------------------------------------------
# Kendall τ_b (with ties)
# ---------------------------------------------------------------------------

def kendall_tau_b(participant_scores: list[float],
                  human_scores: list[float]) -> dict:
    """单 query 的 Kendall τ_b（含 ties）。

    Paper 公式：
        τ = (C - D) / √[(C + D + T)(C + D + U)]

    其中：
    - C = concordant 对数
    - D = discordant 对数
    - T = 仅在 participant scores 中 tie 的对数（不在 human 中 tie）
    - U = 仅在 human scores 中 tie 的对数（不在 participant 中 tie）
    - 双 tie 的对**不计入** T 或 U

    实现说明：
    - 双 tie 对的处理：c=concordant/d=discordant/t=tied 中按 "neither" 算
      （既不算 C 也不算 D），不计入 T 或 U
    """
    assert len(participant_scores) == len(human_scores)
    n = len(participant_scores)
    if n < 2:
        return {"tau": 1.0, "C": 0, "D": 0, "T": 0, "U": 0}

    C = D = T = U = 0
    for i, j in combinations(range(n), 2):
        s_i, s_j = participant_scores[i], participant_scores[j]
        h_i, h_j = human_scores[i], human_scores[j]
        p_tied = (s_i == s_j)
        h_tied = (h_i == h_j)
        if p_tied and h_tied:
            # 双 tie：不算 C/D/T/U
            continue
        if p_tied and not h_tied:
            # participant tie, human not tied → U
            U += 1
            continue
        if h_tied and not p_tied:
            # human tie, participant not tied → T
            T += 1
            continue
        # 都不 tie → 看方向
        p_dir = (s_i > s_j) - (s_i < s_j)
        h_dir = (h_i > h_j) - (h_i < h_j)
        if p_dir == h_dir:
            C += 1
        else:
            D += 1

    denom = ((C + D + T) * (C + D + U)) ** 0.5
    tau = (C - D) / denom if denom > 0 else 0.0
    return {"tau": tau, "C": C, "D": D, "T": T, "U": U}


# ---------------------------------------------------------------------------
# Dataset-level：mean over questions
# ---------------------------------------------------------------------------

def aggregate_over_questions(per_q_metrics: list[dict], key: str) -> float:
    """简单平均 per-question metric。"""
    if not per_q_metrics:
        return 0.0
    return sum(q[key] for q in per_q_metrics) / len(per_q_metrics)


def evaluate_all(per_q_pairs: list[tuple[list[float], list[float]]]) -> dict:
    """对多个 question 算 acc / ρ / τ 的均值。

    per_q_pairs: list of (participant_scores, human_scores) per question.
    """
    accs, rhos, taus = [], [], []
    for p, h in per_q_pairs:
        accs.append(pairwise_accuracy(p, h)["acc"])
        rhos.append(spearman_rho(p, h)["rho"])
        taus.append(kendall_tau_b(p, h)["tau"])
    n = len(accs)
    return {
        "accuracy": sum(accs) / n if n else 0.0,
        "spearman": sum(rhos) / n if n else 0.0,
        "kendall": sum(taus) / n if n else 0.0,
        "n_questions": n,
        "per_question": {
            "accuracy": accs,
            "spearman": rhos,
            "kendall": taus,
        },
    }
