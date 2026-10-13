"""Test grader.grade_passage 与 generate_subquestions。"""

from __future__ import annotations

import os
import sys

# 路径设置
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.grader import (
    content_tokens,
    generate_subquestions,
    grade_passage,
    max_grade_for_query,
    tokenize,
)


def test_tokenize_basic():
    # drop_stop=False → 保留 "the"
    toks = tokenize("The quick brown fox jumps over the lazy dog.", drop_stop=False)
    assert "the" in toks, f"expected 'the' to be kept, got {toks}"
    # drop_stop=True → 去掉 "the"
    toks2 = tokenize("The quick brown fox", drop_stop=True)
    assert "the" not in toks2
    assert "fox" in toks2
    print("✓ test_tokenize_basic")


def test_content_tokens():
    c = content_tokens("Apple announces new iPhone today, analysts say Apple stock rising.")
    assert c["apple"] == 2
    assert c["iphone"] == 1
    print("✓ test_content_tokens")


def test_grade_passage_extremes():
    # 完全相同
    g = grade_passage("The president announced new sanctions today.", "The president announced new sanctions today.")
    assert g == 5, f"expected 5, got {g}"

    # 完全无关
    g = grade_passage("The cat sat on the mat.", "Federal judges ruled against the president today.")
    assert g == 0, f"expected 0, got {g}"
    print("✓ test_grade_passage_extremes")


def test_grade_passage_partial():
    g = grade_passage("The federal judge ruled today.", "A federal judge ruled against the president.")
    # 部分重叠
    assert 1 <= g <= 4, f"expected 1–4, got {g}"
    print(f"✓ test_grade_passage_partial (G={g})")


def test_max_grade_for_query():
    passages = [
        "Cats are cute animals.",
        "The president announced sanctions.",
        "Markets fell today.",
    ]
    ig = "The president announced new sanctions today."
    max_g = max_grade_for_query(passages, ig)
    assert max_g >= 3, f"expected >=3 for the relevant passage, got {max_g}"
    print(f"✓ test_max_grade_for_query (max G={max_g})")


def test_generate_subquestions():
    summary = (
        "The president announced sanctions today. "
        "The senate voted to approve the bill. "
        "Markets responded positively to the news."
    )
    qs = generate_subquestions(summary, n_questions=2)
    assert len(qs) == 2
    for q, ig in qs:
        assert q.endswith("?")
        assert len(ig) > 10
    print(f"✓ test_generate_subquestions (got {len(qs)} pairs)")


if __name__ == "__main__":
    test_tokenize_basic()
    test_content_tokens()
    test_grade_passage_extremes()
    test_grade_passage_partial()
    test_max_grade_for_query()
    test_generate_subquestions()
    print("\n所有 grader 测试通过。")
