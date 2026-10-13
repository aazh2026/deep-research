"""Test Density + Oracle construction。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.density import (
    build_oracle,
    compute_density,
    count_tokens,
    token_count_of_passages,
)
from src.grader import grade_passage


def test_count_tokens():
    n = count_tokens("Hello world, this is a test.")
    assert n == 6, f"expected 6, got {n}"
    print("✓ test_count_tokens")


def test_token_count_of_passages():
    total = token_count_of_passages(["Hello world.", "Foo bar."])
    assert total == 4
    print("✓ test_token_count_of_passages")


def test_oracle_greedy():
    # 3 passages: p0 covers Q0, p1 covers Q1, p2 irrelevant
    passages = [
        "The president announced new sanctions today.",
        "Markets fell sharply in response.",
        "Cats are cute animals.",
    ]
    queries = [
        ("Q0", "The president announced new sanctions today."),
        ("Q1", "Markets fell sharply in response."),
    ]
    oracle = build_oracle(passages, queries, grade_passage, eta=3)
    assert len(oracle) == 2
    # 不应包含 p2
    assert not any("Cats" in p for p in oracle)
    print(f"✓ test_oracle_greedy (oracle has {len(oracle)} passages)")


def test_density_self_normalization():
    """Density(Z=Z*) 应该等于 1.0。"""
    passages = [
        "The president announced new sanctions today.",
        "Markets fell sharply in response.",
        "Cats are cute animals.",
    ]
    queries = [
        ("Q0", "The president announced new sanctions today."),
        ("Q1", "Markets fell sharply in response."),
    ]
    oracle = build_oracle(passages, queries, grade_passage, eta=3)
    den = compute_density(oracle, oracle, queries, grade_passage, eta=3, w=0.5)
    assert abs(den - 1.0) < 1e-6, f"expected 1.0, got {den}"
    print(f"✓ test_density_self_normalization (Den={den})")


def test_density_more_tokens_lower():
    """加更多冗余 passage，Density 应该下降。"""
    passages = [
        "The president announced new sanctions today.",
        "Markets fell sharply in response.",
        "Cats are cute animals.",  # 冗余
        "Dogs are loyal pets.",  # 冗余
        "Birds can fly.",  # 冗余
    ]
    queries = [
        ("Q0", "The president announced new sanctions today."),
        ("Q1", "Markets fell sharply in response."),
    ]
    oracle = build_oracle(passages, queries, grade_passage, eta=3)
    cov_oracle = 1.0
    cov_full = 1.0
    den_full = compute_density(passages, oracle, queries, grade_passage,
                                cov_Z=cov_full, cov_oracle=cov_oracle, eta=3, w=0.5)
    den_oracle = compute_density(oracle, oracle, queries, grade_passage,
                                  cov_Z=cov_oracle, cov_oracle=cov_oracle, eta=3, w=0.5)
    assert den_full < den_oracle, "full Z should have lower density than oracle"
    print(f"✓ test_density_more_tokens_lower (full={den_full:.3f} < oracle={den_oracle:.3f})")


def test_density_irrelevant_zero():
    """完全不相关的 Z → Density ≈ 0。"""
    passages_oracle = [
        "The president announced new sanctions today.",
    ]
    queries = [("Q", "The president announced new sanctions today.")]
    oracle = build_oracle(passages_oracle, queries, grade_passage, eta=3)
    z_irrelevant = ["The cat sat on the mat."]
    den = compute_density(z_irrelevant, oracle, queries, grade_passage, eta=3, w=0.5)
    assert den == 0.0, f"expected 0, got {den}"
    print(f"✓ test_density_irrelevant_zero (Den={den})")


def test_density_w_parameter():
    """w 越大，对 base<1 的值越接近 base（不动）；w 越小，越拉近 1。"""
    passages = [
        "The president announced new sanctions today.",
        "Markets fell sharply in response.",
        "Cats are cute animals.",
    ]
    queries = [
        ("Q0", "The president announced new sanctions today."),
        ("Q1", "Markets fell sharply in response."),
    ]
    oracle = build_oracle(passages, queries, grade_passage, eta=3)
    den_w05 = compute_density(passages, oracle, queries, grade_passage, eta=3, w=0.5)
    den_w10 = compute_density(passages, oracle, queries, grade_passage, eta=3, w=1.0)
    # w=0.5 拉得更近 1；w=1.0 保持原值。base < 1 时 w=0.5 > w=1.0
    assert den_w05 >= den_w10, f"w=0.5 should give higher Den than w=1.0 (got {den_w05} vs {den_w10})"
    print(f"✓ test_density_w_parameter (w=0.5: {den_w05:.3f}, w=1.0: {den_w10:.3f})")


if __name__ == "__main__":
    test_count_tokens()
    test_token_count_of_passages()
    test_oracle_greedy()
    test_density_self_normalization()
    test_density_more_tokens_lower()
    test_density_irrelevant_zero()
    test_density_w_parameter()
    print("\n所有 density 测试通过。")
