"""baseline 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import InfoVQAQuestion
from src.baselines import (
    is_numeric_answer, to_float,
    compute_majority_answer, majority_predict,
    compute_random_pool, random_predict,
    compute_type_majority, type_majority_predict,
    compute_numeric_stats, numeric_median_predict, numeric_mode_predict,
    evaluate_baseline,
)


def make_q(uid, query, answers, qt="open"):
    return InfoVQAQuestion(
        uid=uid, query=query, answers=answers, question_type=qt,
    )


# ---------------------------------------------------------------------------
# is_numeric_answer / to_float
# ---------------------------------------------------------------------------

def test_is_numeric_basic():
    assert is_numeric_answer("42")
    assert is_numeric_answer("3.14")
    assert is_numeric_answer("2020")


def test_is_numeric_with_symbols():
    assert is_numeric_answer("50%")
    assert is_numeric_answer("1,234")


def test_is_numeric_text():
    assert not is_numeric_answer("hello")
    assert not is_numeric_answer("")
    assert not is_numeric_answer("2020-01-15")  # 含连字符


def test_to_float_basic():
    assert to_float("42") == 42.0
    assert to_float("3.14") == 3.14


def test_to_float_with_commas():
    assert to_float("1,234") == 1234.0


def test_to_float_invalid():
    assert to_float("hello") is None
    assert to_float("") is None


# ---------------------------------------------------------------------------
# Majority / Random
# ---------------------------------------------------------------------------

def test_majority_picks_most_common():
    qs = [
        make_q("1", "q", ["yes", "no"], "yes_no"),
        make_q("2", "q", ["yes", "maybe"], "yes_no"),
        make_q("3", "q", ["yes"], "yes_no"),
    ]
    assert compute_majority_answer(qs) == "yes"


def test_majority_predict_uniform():
    qs = [make_q(str(i), f"q{i}", ["a"], "open") for i in range(3)]
    assert majority_predict(qs, "a") == ["a", "a", "a"]


def test_random_pool_weights():
    qs = [
        make_q("1", "q", ["a", "b"]),
        make_q("2", "q", ["a", "b"]),
        make_q("3", "q", ["c"]),
    ]
    pool = compute_random_pool(qs)
    assert ("a", 0.4) in pool
    assert ("c", 0.2) in pool


def test_random_predict_length():
    qs = [make_q(str(i), f"q{i}", ["a", "b"]) for i in range(5)]
    pool = compute_random_pool(qs)
    preds = random_predict(qs, pool, seed=0)
    assert len(preds) == 5


# ---------------------------------------------------------------------------
# Type-Majority
# ---------------------------------------------------------------------------

def test_type_majority_per_type():
    qs = [
        make_q("1", "q", ["5"], "numeric"),
        make_q("2", "q", ["5"], "numeric"),
        make_q("3", "q", ["3"], "numeric"),
        make_q("4", "q", ["yes"], "yes_no"),
        make_q("5", "q", ["no"], "yes_no"),
    ]
    tm = compute_type_majority(qs)
    assert tm["numeric"] == "5"
    assert tm["yes_no"] == "yes"


def test_type_majority_predict():
    qs = [
        make_q("1", "q", ["5"], "numeric"),
        make_q("2", "q", ["yes"], "yes_no"),
    ]
    tm = {"numeric": "7", "yes_no": "no"}
    preds = type_majority_predict(qs, tm)
    assert preds == ["7", "no"]


# ---------------------------------------------------------------------------
# Numeric stats
# ---------------------------------------------------------------------------

def test_numeric_stats_median():
    qs = [
        make_q("1", "q", ["1"], "numeric"),
        make_q("2", "q", ["5"], "numeric"),
        make_q("3", "q", ["10"], "numeric"),
    ]
    stats = compute_numeric_stats(qs)
    assert stats["median"] == 5.0
    assert stats["mode"] == "1"  # "1" 出现 1 次，"5" 1 次，"10" 1 次 → tie, first


def test_numeric_stats_no_numeric():
    qs = [make_q("1", "q", ["hello"], "open")]
    stats = compute_numeric_stats(qs)
    assert stats["median"] == 0.0


def test_numeric_median_predict_int():
    qs = [
        make_q("1", "q", ["1"], "numeric"),
        make_q("2", "q", ["x"], "open"),
    ]
    preds = numeric_median_predict(qs, 7.0)
    # numeric → 整数 7, open → 0
    assert preds == ["7", "0"]


def test_numeric_median_predict_float():
    qs = [make_q("1", "q", ["1.5"], "numeric")]
    preds = numeric_median_predict(qs, 3.14)
    # 3.14 不是整数 → "3.14"
    assert preds == ["3.14"]


def test_numeric_mode_predict():
    qs = [
        make_q("1", "q", ["5"], "numeric"),
        make_q("2", "q", ["x"], "open"),
    ]
    preds = numeric_mode_predict(qs, "42")
    assert preds == ["42", "0"]


# ---------------------------------------------------------------------------
# evaluate_baseline
# ---------------------------------------------------------------------------

def test_evaluate_perfect():
    qs = [make_q("1", "q", ["hello"]), make_q("2", "q", ["world"])]
    res = evaluate_baseline(qs, ["hello", "world"])
    assert res["anls"] == 1.0
    assert res["n"] == 2


def test_evaluate_zero():
    qs = [make_q("1", "q", ["hello"]), make_q("2", "q", ["world"])]
    res = evaluate_baseline(qs, ["completely", "different"])
    assert res["anls"] == 0.0
