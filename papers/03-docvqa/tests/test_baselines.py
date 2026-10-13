"""baseline 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import DocVQAQuestion
from src.baselines import (
    compute_majority_answer,
    majority_predict,
    compute_random_pool,
    random_predict,
    lexical_predict,
    evaluate_baseline,
    extract_numbers,
    find_query_keywords,
)


def make_q(uid, query, answers, words):
    return DocVQAQuestion(
        uid=uid, query=query, answers=answers, words=words, n_words=len(words),
    )


# ---------------------------------------------------------------------------
# extract_numbers
# ---------------------------------------------------------------------------

def test_extract_numbers_simple():
    assert extract_numbers("in 2020 there are 42 items") == ["2020", "42"]


def test_extract_numbers_with_commas():
    assert extract_numbers("total: 1,234,567") == ["1,234,567"]


def test_extract_numbers_with_decimals():
    assert extract_numbers("price $3.14") == ["3.14"]


def test_extract_numbers_negative():
    assert extract_numbers("temp -5 degrees") == ["-5"]


def test_extract_numbers_none():
    assert extract_numbers("no numbers here") == []


# ---------------------------------------------------------------------------
# find_query_keywords
# ---------------------------------------------------------------------------

def test_keywords_filters_stopwords():
    kws = find_query_keywords("What is the title of the document?")
    assert "title" in kws
    assert "document" in kws
    assert "what" not in kws
    assert "the" not in kws
    assert "is" not in kws


def test_keywords_drops_short():
    kws = find_query_keywords("to be or not to be")
    # 全部 ≤ 2 字符，全部 drop
    assert kws == []


def test_keywords_keeps_multi_word():
    kws = find_query_keywords("What is the publication date?")
    assert "publication" in kws
    assert "date" in kws


# ---------------------------------------------------------------------------
# majority baseline
# ---------------------------------------------------------------------------

def test_majority_answer_picks_most_common():
    qs = [
        make_q("1", "q1", ["yes", "no"], ["a", "b"]),
        make_q("2", "q2", ["yes", "maybe"], ["c"]),
        make_q("3", "q3", ["yes", "yes"], ["d"]),
    ]
    m = compute_majority_answer(qs)
    assert m == "yes"


def test_majority_answer_empty_dataset():
    assert compute_majority_answer([]) == ""


def test_majority_predict_uniform():
    qs = [make_q(str(i), f"q{i}", ["a", "b"], ["x"]) for i in range(3)]
    preds = majority_predict(qs, "a")
    assert preds == ["a", "a", "a"]


# ---------------------------------------------------------------------------
# random baseline
# ---------------------------------------------------------------------------

def test_random_pool_weights():
    qs = [
        make_q("1", "q1", ["a", "b"], ["x"]),
        make_q("2", "q2", ["a", "b"], ["x"]),
        make_q("3", "q3", ["c"], ["x"]),
    ]
    pool = compute_random_pool(qs)
    # 答案集合: a(2), b(2), c(1) → 概率 0.4, 0.4, 0.2
    assert set(a for a, _ in pool) == {"a", "b", "c"}
    a_w = next(w for a, w in pool if a == "a")
    c_w = next(w for a, w in pool if a == "c")
    assert abs(a_w - 0.4) < 1e-9
    assert abs(c_w - 0.2) < 1e-9


def test_random_predict_length():
    qs = [make_q(str(i), f"q{i}", ["a", "b"], ["x"]) for i in range(5)]
    pool = compute_random_pool(qs)
    preds = random_predict(qs, pool, seed=0)
    assert len(preds) == 5
    assert all(p in {"a", "b"} for p in preds)


def test_random_predict_seed_deterministic():
    qs = [make_q(str(i), f"q{i}", ["a", "b"], ["x"]) for i in range(10)]
    pool = compute_random_pool(qs)
    p1 = random_predict(qs, pool, seed=42)
    p2 = random_predict(qs, pool, seed=42)
    assert p1 == p2


# ---------------------------------------------------------------------------
# lexical baseline
# ---------------------------------------------------------------------------

def test_lexical_predict_empty_words():
    q = make_q("1", "What is the title?", ["x"], [])
    assert lexical_predict(q) == ""


def test_lexical_predict_title_heuristic():
    q = make_q(
        "1", "What is the title?",
        ["My Document Title"],
        ["My", "Document", "Title", "is", "here"],
    )
    # 启发式 1：title 提问 → 第一个大写短语
    pred = lexical_predict(q)
    assert "My" in pred and "Document" in pred


def test_lexical_predict_date_heuristic():
    q = make_q(
        "1", "What is the date?",
        ["2020"],
        ["Date", "of", "issue", ":", "2020", "/", "01", "/", "15"],
    )
    pred = lexical_predict(q)
    # 启发式 2：date 提问 → 第一个数字
    assert pred == "2020"


def test_lexical_predict_default_returns_first_30_words():
    words = [f"word{i}" for i in range(50)]
    q = make_q("1", "What is the weather?", ["sunny"], words)
    pred = lexical_predict(q)
    # 默认启发式 4：前 30 词
    assert len(pred.split()) == 30
    assert pred == " ".join(words[:30])


def test_lexical_predict_keyword_followed_by_text():
    # 启发式 3：关键词后面取 1-4 词
    q = make_q(
        "1", "Who is the author?",
        ["John Doe"],
        ["Some", "intro", "text", "Author", "John", "Doe", "More"],
    )
    pred = lexical_predict(q)
    # "author" 后取 1-4 词
    assert "John" in pred


# ---------------------------------------------------------------------------
# evaluate_baseline
# ---------------------------------------------------------------------------

def test_evaluate_baseline_perfect():
    qs = [
        make_q("1", "q1", ["hello"], ["x"]),
        make_q("2", "q2", ["world"], ["y"]),
    ]
    res = evaluate_baseline(qs, ["hello", "world"])
    assert res["anls"] == 1.0
    assert res["n"] == 2


def test_evaluate_baseline_zero():
    qs = [
        make_q("1", "q1", ["hello"], ["x"]),
        make_q("2", "q2", ["world"], ["y"]),
    ]
    res = evaluate_baseline(qs, ["completely", "different"])
    assert res["anls"] == 0.0
