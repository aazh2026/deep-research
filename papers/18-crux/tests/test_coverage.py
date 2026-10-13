"""Test Coverage。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.coverage import compute_coverage, compute_coverage_batch
from src.grader import grade_passage


def test_empty():
    cov = compute_coverage([], [], grade_passage, eta=3)
    assert cov == 0.0
    print("✓ test_empty")


def test_perfect_coverage():
    # 2 个 query，每个都恰好有 passage 完全匹配
    passages = [
        "The president announced new sanctions today.",
        "Markets fell sharply in response.",
    ]
    queries = [
        ("Q1", "The president announced new sanctions today."),
        ("Q2", "Markets fell sharply in response."),
    ]
    cov = compute_coverage(passages, queries, grade_passage, eta=3)
    assert cov == 1.0, f"expected 1.0, got {cov}"
    print("✓ test_perfect_coverage")


def test_partial_coverage():
    passages = [
        "The president announced new sanctions today.",
        "Markets fell sharply in response.",
    ]
    queries = [
        ("Q1", "The president announced new sanctions today."),  # 可答
        ("Q2", "The senate voted to approve the bill."),  # 不可答
    ]
    cov = compute_coverage(passages, queries, grade_passage, eta=3)
    assert abs(cov - 0.5) < 1e-6, f"expected 0.5, got {cov}"
    print(f"✓ test_partial_coverage (Cov={cov})")


def test_no_coverage():
    passages = ["The cat sat on the mat."]
    queries = [
        ("Q1", "The president announced sanctions."),
        ("Q2", "Markets fell today."),
    ]
    cov = compute_coverage(passages, queries, grade_passage, eta=3)
    assert cov == 0.0
    print("✓ test_no_coverage")


def test_batch():
    Z_list = [
        ["The president announced new sanctions today."],
        ["The cat sat on the mat."],
    ]
    Q_list = [
        [("Q1", "The president announced new sanctions today.")],
        [("Q2", "Markets fell today.")],
    ]
    covs = compute_coverage_batch(Z_list, Q_list, grade_passage, eta=3)
    assert covs[0] == 1.0
    assert covs[1] == 0.0
    print(f"✓ test_batch (covs={covs})")


def test_eta_threshold_effect():
    passages = ["The federal judge ruled today."]
    queries = [("Q", "A federal judge ruled against the president.")]
    # 部分重叠 → G 介于 1–4
    cov_strict = compute_coverage(passages, queries, grade_passage, eta=4)
    cov_loose = compute_coverage(passages, queries, grade_passage, eta=1)
    assert cov_loose >= cov_strict, "lower eta should give higher cov"
    print(f"✓ test_eta_threshold_effect (strict={cov_strict}, loose={cov_loose})")


if __name__ == "__main__":
    test_empty()
    test_perfect_coverage()
    test_partial_coverage()
    test_no_coverage()
    test_batch()
    test_eta_threshold_effect()
    print("\n所有 coverage 测试通过。")
