"""baseline 单元测试（Task 1 baselines + span-exact）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import DocVQAQuestion
from src.baselines import (
    compute_majority_answer, majority_predict,
    compute_random_pool, random_predict,
    lexical_predict, span_exact_predict,
    evaluate_task1, find_query_keywords,
)


def make_q(uid, query, answers, words):
    return DocVQAQuestion(
        uid=uid, query=query, answers=answers, words=words, n_words=len(words),
    )


# ---------------------------------------------------------------------------
# Majority + Random（与 03-docvqa 一致）
# ---------------------------------------------------------------------------

def test_majority_picks_most_common():
    qs = [
        make_q("1", "q", ["yes", "no"], []),
        make_q("2", "q", ["yes", "maybe"], []),
        make_q("3", "q", ["yes"], []),
    ]
    assert compute_majority_answer(qs) == "yes"


def test_majority_predict_uniform():
    qs = [make_q(str(i), f"q{i}", ["a"], []) for i in range(3)]
    assert majority_predict(qs, "a") == ["a", "a", "a"]


def test_random_pool():
    qs = [
        make_q("1", "q", ["a", "b"], []),
        make_q("2", "q", ["a", "b"], []),
        make_q("3", "q", ["c"], []),
    ]
    pool = compute_random_pool(qs)
    assert ("a", 0.4) in pool
    assert ("c", 0.2) in pool


def test_random_predict_length():
    qs = [make_q(str(i), f"q{i}", ["a", "b"], []) for i in range(5)]
    pool = compute_random_pool(qs)
    preds = random_predict(qs, pool, seed=0)
    assert len(preds) == 5


# ---------------------------------------------------------------------------
# Lexical baseline
# ---------------------------------------------------------------------------

def test_lexical_title_heuristic():
    q = make_q("1", "What is the title?",
               ["My Document Title"],
               ["My", "Document", "Title", "is", "here"])
    pred = lexical_predict(q)
    assert "My" in pred and "Document" in pred


def test_lexical_date_heuristic():
    q = make_q("1", "What is the date?",
               ["2020"],
               ["Date", "of", "issue", ":", "2020", "/", "01", "/", "15"])
    pred = lexical_predict(q)
    assert pred == "2020"


def test_lexical_default():
    words = [f"word{i}" for i in range(50)]
    q = make_q("1", "What is the weather?", ["sunny"], words)
    pred = lexical_predict(q)
    assert len(pred.split()) == 30


# ---------------------------------------------------------------------------
# Span-Exact baseline（核心）
# ---------------------------------------------------------------------------

def test_span_exact_picks_best_window():
    # "Who is the author?" → keyword = author
    # 文档：[..., "Author", "John", "Doe", "Senior", "Analyst", ...]
    # best window 含 keyword "Author" 最多
    q = make_q(
        "1", "Who is the author?",
        ["John Doe"],
        ["Some", "intro", "text", "Author", "John", "Doe", "Senior", "Analyst", "X"],
    )
    pred = span_exact_predict(q)
    # 5-token window starting at index 3: "Author John Doe Senior Analyst"
    assert "Author" in pred
    assert "John" in pred
    assert "Doe" in pred


def test_span_exact_no_keywords():
    q = make_q("1", "to be or not", ["x"], ["a", "b", "c", "d", "e"])
    pred = span_exact_predict(q)
    # 无 keyword → 前 5 词
    assert pred == "a b c d e"


def test_span_exact_empty_words():
    q = make_q("1", "What is the title?", ["x"], [])
    pred = span_exact_predict(q)
    assert pred == ""


def test_span_exact_short_doc():
    q = make_q("1", "What is the date?", ["2020"], ["Jan", "2020"])
    pred = span_exact_predict(q)
    # 文档 < 5 词 → 直接返回
    assert pred == "Jan 2020"


# ---------------------------------------------------------------------------
# find_query_keywords
# ---------------------------------------------------------------------------

def test_keywords_filters_stopwords():
    kws = find_query_keywords("What is the title of the document?")
    assert "title" in kws
    assert "document" in kws
    assert "what" not in kws


def test_keywords_keeps_date():
    kws = find_query_keywords("What is the publication date?")
    assert "publication" in kws
    assert "date" in kws


# ---------------------------------------------------------------------------
# evaluate_task1
# ---------------------------------------------------------------------------

def test_evaluate_perfect():
    qs = [make_q("1", "q1", ["hello"], []), make_q("2", "q2", ["world"], [])]
    res = evaluate_task1(qs, ["hello", "world"])
    assert res["anls"] == 1.0
    assert res["n"] == 2


def test_evaluate_zero():
    qs = [make_q("1", "q1", ["hello"], []), make_q("2", "q2", ["world"], [])]
    res = evaluate_task1(qs, ["completely", "different"])
    assert res["anls"] == 0.0
