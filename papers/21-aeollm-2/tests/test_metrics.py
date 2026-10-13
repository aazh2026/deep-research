"""AEOLLM-2 metric 单元测试。

设计目标：
- Pairwise Accuracy 覆盖：完美匹配 / 完全反 / 半数 / 全 tie
- Spearman ρ 覆盖：完美正 / 完美负 / 部分
- Kendall τ_b 覆盖：concordant / discordant / participant-only tie / human-only tie / 双 tie

参照：paper Section 3.2 + Table 4 的 RSLIR best 0.7071 ρ / 0.5592 τ / 0.7796 acc
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.metrics import (
    preference_relation,
    pairwise_accuracy,
    _rank_with_ties,
    spearman_rho,
    kendall_tau_b,
    evaluate_all,
    _pearson,
)


# ---------------------------------------------------------------------------
# preference_relation
# ---------------------------------------------------------------------------

def test_preference_relation_lt():
    assert preference_relation(1.0, 2.0) == -1


def test_preference_relation_gt():
    assert preference_relation(3.0, 1.0) == 1


def test_preference_relation_tie():
    assert preference_relation(2.0, 2.0) == 0


# ---------------------------------------------------------------------------
# Pairwise Accuracy
# ---------------------------------------------------------------------------

def test_pw_perfect():
    # 完全相同排序
    p = [1.0, 2.0, 3.0, 4.0]
    h = [0.5, 1.5, 2.5, 3.5]
    res = pairwise_accuracy(p, h)
    assert res["acc"] == 1.0
    assert res["n_pairs"] == 6  # C(4,2) = 6


def test_pw_perfect_reverse():
    # 反向排序 → 偏好全错
    p = [4.0, 3.0, 2.0, 1.0]
    h = [1.0, 2.0, 3.0, 4.0]
    res = pairwise_accuracy(p, h)
    assert res["acc"] == 0.0


def test_pw_half():
    # p = [1, 2, 3, 4]（完美）, h = [1, 2, 4, 3]（仅最后 1 对错）
    p = [1.0, 2.0, 3.0, 4.0]
    h = [1.0, 2.0, 4.0, 3.0]
    res = pairwise_accuracy(p, h)
    # 6 对中 5 对正确（仅 h 中 3 vs 4 反向）
    assert abs(res["acc"] - 5.0/6) < 1e-9


def test_pw_all_tie_in_both():
    # participant 全 tie + human 全 tie → 所有对都 z=0=z' → 全对
    p = [2.0, 2.0, 2.0]
    h = [3.0, 3.0, 3.0]
    res = pairwise_accuracy(p, h)
    assert res["acc"] == 1.0
    assert res["n_correct"] == 3


def test_pw_participant_tie_human_not():
    # p 全 tie, h 完全有序 → participant 错所有非 tie 对
    p = [1.0, 1.0, 1.0]
    h = [1.0, 2.0, 3.0]
    res = pairwise_accuracy(p, h)
    # 3 对：p 全 0, h 三种 -1/+1 都不等于 0
    assert res["acc"] == 0.0


def test_pw_two_questions():
    # 类似 paper：4 个 answer，2 个 question
    p1 = [4.0, 3.0, 2.0, 1.0]  # 反向
    h1 = [1.0, 2.0, 3.0, 4.0]
    p2 = [1.0, 2.0, 3.0, 4.0]  # 完美
    h2 = [1.0, 2.0, 3.0, 4.0]
    acc1 = pairwise_accuracy(p1, h1)["acc"]
    acc2 = pairwise_accuracy(p2, h2)["acc"]
    # 平均: (0 + 1) / 2 = 0.5
    assert abs((acc1 + acc2) / 2 - 0.5) < 1e-9


# ---------------------------------------------------------------------------
# rank_with_ties
# ---------------------------------------------------------------------------

def test_rank_no_ties():
    r = _rank_with_ties([1.0, 2.0, 3.0, 4.0])
    assert r == [1.0, 2.0, 3.0, 4.0]


def test_rank_one_tie_pair():
    # [1, 2, 2, 4] → [1, 2.5, 2.5, 4]
    r = _rank_with_ties([1.0, 2.0, 2.0, 4.0])
    assert r == [1.0, 2.5, 2.5, 4.0]


def test_rank_all_tied():
    r = _rank_with_ties([5.0, 5.0, 5.0])
    # 3 个都 tie → 全部 rank 2.0
    assert r == [2.0, 2.0, 2.0]


def test_rank_three_tied():
    # [1, 2, 2, 2, 5] → [1, 3, 3, 3, 5]
    r = _rank_with_ties([1.0, 2.0, 2.0, 2.0, 5.0])
    assert r == [1.0, 3.0, 3.0, 3.0, 5.0]


# ---------------------------------------------------------------------------
# Pearson（内部函数）
# ---------------------------------------------------------------------------

def test_pearson_perfect():
    assert abs(_pearson([1, 2, 3, 4], [2, 4, 6, 8]) - 1.0) < 1e-9


def test_pearson_anti():
    assert abs(_pearson([1, 2, 3, 4], [4, 3, 2, 1]) - (-1.0)) < 1e-9


def test_pearson_zero_var():
    # 同一 x 全部相同 → var=0 → 返回 0（避免除零）
    assert _pearson([5, 5, 5], [1, 2, 3]) == 0.0


# ---------------------------------------------------------------------------
# Spearman ρ
# ---------------------------------------------------------------------------

def test_spearman_perfect():
    p = [1.0, 2.0, 3.0, 4.0]
    h = [10.0, 20.0, 30.0, 40.0]
    res = spearman_rho(p, h)
    assert abs(res["rho"] - 1.0) < 1e-9


def test_spearman_perfect_reverse():
    p = [4.0, 3.0, 2.0, 1.0]
    h = [1.0, 2.0, 3.0, 4.0]
    res = spearman_rho(p, h)
    assert abs(res["rho"] - (-1.0)) < 1e-9


def test_spearman_with_ties():
    # p: [1, 2, 2, 4] → ranks [1, 2.5, 2.5, 4]
    # h: [1, 2, 3, 4] → ranks [1, 2, 3, 4]
    # Pearson of [1, 2.5, 2.5, 4] vs [1, 2, 3, 4] ≈ 0.9487
    p = [1.0, 2.0, 2.0, 4.0]
    h = [1.0, 2.0, 3.0, 4.0]
    res = spearman_rho(p, h)
    assert abs(res["rho"] - 0.9487) < 0.005
    assert res["rho"] < 1.0


def test_spearman_two_questions_avg():
    # 第一个 perfect, 第二个 reverse → mean = 0
    p1 = [1, 2, 3, 4]
    h1 = [1, 2, 3, 4]
    p2 = [4, 3, 2, 1]
    h2 = [1, 2, 3, 4]
    r1 = spearman_rho(p1, h1)["rho"]
    r2 = spearman_rho(p2, h2)["rho"]
    assert abs((r1 + r2) / 2 - 0.0) < 1e-9


# ---------------------------------------------------------------------------
# Kendall τ_b
# ---------------------------------------------------------------------------

def test_tau_perfect():
    p = [1, 2, 3, 4]
    h = [1, 2, 3, 4]
    res = kendall_tau_b(p, h)
    assert res["tau"] == 1.0
    assert res["C"] == 6
    assert res["D"] == 0


def test_tau_perfect_reverse():
    p = [4, 3, 2, 1]
    h = [1, 2, 3, 4]
    res = kendall_tau_b(p, h)
    assert res["tau"] == -1.0
    assert res["C"] == 0
    assert res["D"] == 6


def test_tau_no_ties_partial():
    # 4 个 answer，p=[1,2,3,4], h=[1,2,4,3]
    # 6 对：(0,1)✓ (0,2)✓ (0,3)✓ (1,2)✓ (1,3)✓ (2,3)✗
    # C=5, D=1
    p = [1, 2, 3, 4]
    h = [1, 2, 4, 3]
    res = kendall_tau_b(p, h)
    assert res["C"] == 5
    assert res["D"] == 1
    # τ = (5-1) / sqrt((5+1)(5+1)) = 4/6
    assert abs(res["tau"] - 4.0/6) < 1e-9


def test_tau_participant_only_ties():
    # p: [1, 1, 3], h: [1, 2, 3]
    # 对 (0,1): p tie, h 不 tie → U += 1
    # 对 (0,2): p 1<3, h 1<3 → concordant
    # 对 (1,2): p 1<3, h 2<3 → concordant
    # C=2, D=0, T=0, U=1
    p = [1.0, 1.0, 3.0]
    h = [1.0, 2.0, 3.0]
    res = kendall_tau_b(p, h)
    assert res["C"] == 2
    assert res["D"] == 0
    assert res["T"] == 0
    assert res["U"] == 1
    # τ = (2-0) / sqrt((2+0+0)(2+0+1)) = 2/sqrt(6)
    assert abs(res["tau"] - 2.0/(6**0.5)) < 1e-9


def test_tau_human_only_ties():
    # p: [1, 2, 3], h: [1, 1, 3]
    # 对 (0,1): p 1<2, h tie → T += 1
    # 对 (0,2): p 1<3, h 1<3 → C
    # 对 (1,2): p 2<3, h 1<3 → C
    p = [1.0, 2.0, 3.0]
    h = [1.0, 1.0, 3.0]
    res = kendall_tau_b(p, h)
    assert res["C"] == 2
    assert res["T"] == 1
    assert res["U"] == 0
    # τ = 2 / sqrt((2+0+1)(2+0+0)) = 2/sqrt(6)
    assert abs(res["tau"] - 2.0/(6**0.5)) < 1e-9


def test_tau_double_tie_excluded():
    # p: [1, 1, 1], h: [2, 2, 2]
    # 全部双 tie → C=D=T=U=0
    p = [1.0, 1.0, 1.0]
    h = [2.0, 2.0, 2.0]
    res = kendall_tau_b(p, h)
    assert res["C"] == 0
    assert res["D"] == 0
    assert res["T"] == 0
    assert res["U"] == 0


def test_tau_paper_rslir_approx():
    """复现 paper Table 4: RSLIR weighted overall: ρ=0.7071, τ=0.5592, acc=0.7796。

    不期望精确数字（需要真实评测数据），但期望三个 metric 都在 0.5-0.8 范围。
    """
    # 模拟「较好的对齐」：participant scores 与 human 强相关但有 noise
    import random
    rng = random.Random(42)
    per_q = []
    for _ in range(40):  # 40 个 question（paper 报告的是 40 questions 总和）
        h = sorted([rng.uniform(0, 5) for _ in range(4)], reverse=True)  # 真实排序
        p = [h[i] + rng.gauss(0, 0.7) for i in range(4)]
        per_q.append((p, h))
    res = evaluate_all(per_q)
    assert 0.5 < res["accuracy"] < 0.9
    assert 0.4 < res["spearman"] < 0.9
    assert 0.3 < res["kendall"] < 0.8


# ---------------------------------------------------------------------------
# evaluate_all
# ---------------------------------------------------------------------------

def test_evaluate_all_aggregate():
    per_q = [
        ([1, 2, 3], [1, 2, 3]),  # perfect
        ([3, 2, 1], [1, 2, 3]),  # reverse
    ]
    res = evaluate_all(per_q)
    assert abs(res["accuracy"] - 0.5) < 1e-9  # (1 + 0) / 2
    assert abs(res["spearman"] - 0.0) < 1e-9  # (1 + -1) / 2
    assert abs(res["kendall"] - 0.0) < 1e-9
    assert res["n_questions"] == 2


def test_evaluate_all_empty():
    res = evaluate_all([])
    assert res["accuracy"] == 0.0
    assert res["spearman"] == 0.0
    assert res["kendall"] == 0.0
    assert res["n_questions"] == 0
