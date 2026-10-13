"""ANLS metric 单元测试（与 03-docvqa 复用）。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.metrics import levenshtein, anls_score, anls_dataset


def test_levenshtein_basic():
    assert levenshtein("cat", "bat") == 1
    assert levenshtein("cat", "cats") == 1
    assert levenshtein("", "abc") == 3


def test_anls_perfect():
    assert anls_score("hello", ["hello"]) == 1.0


def test_anls_partial():
    s = anls_score("hallo", ["hello"])
    assert abs(s - 0.8) < 1e-9


def test_anls_threshold():
    # NED = 0.5 → 0
    assert anls_score("a", ["ab"]) == 0.0


def test_anls_multi_gold():
    s = anls_score("January 5, 2020", ["January 5, 2020", "Jan 5 2020"])
    assert s == 1.0


def test_anls_case_insensitive():
    assert anls_score("HELLO", ["hello"]) == 1.0


def test_anls_both_empty():
    assert anls_score("", [""]) == 1.0


def test_anls_pred_empty():
    assert anls_score("", ["hello"]) == 0.0


def test_anls_dataset():
    preds = ["hello", "world", "foo"]
    gts = [["hello"], ["world"], ["bar"]]
    res = anls_dataset(preds, gts)
    assert abs(res["anls"] - 2.0/3) < 1e-9
    assert res["n"] == 3


def test_anls_dataset_empty():
    res = anls_dataset([], [])
    assert res["anls"] == 0.0
    assert res["n"] == 0
