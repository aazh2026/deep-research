"""ANLS metric 单元测试（~20 测试）。

覆盖：
- 编辑距离工具
- 完美匹配 / 部分匹配 / 完全错
- 阈值 τ 边界（< 0.5 vs >= 0.5）
- 多 gold 取 max
- 大小写 + strip
- 空字符串 / 一空一非空
- 整个 dataset 的 ANLS
- τ 参数的影响
"""

from __future__ import annotations

import sys
from pathlib import Path

# 让测试能 import src
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.metrics import levenshtein, anls_score, anls_dataset


# ---------------------------------------------------------------------------
# Levenshtein
# ---------------------------------------------------------------------------

def test_levenshtein_identical():
    assert levenshtein("hello", "hello") == 0


def test_levenshtein_one_substitution():
    assert levenshtein("cat", "bat") == 1


def test_levenshtein_one_insertion():
    assert levenshtein("cat", "cats") == 1


def test_levenshtein_one_deletion():
    assert levenshtein("cats", "cat") == 1


def test_levenshtein_completely_different():
    assert levenshtein("abc", "xyz") == 3


def test_levenshtein_empty_string():
    assert levenshtein("", "abc") == 3
    assert levenshtein("abc", "") == 3
    assert levenshtein("", "") == 0


# ---------------------------------------------------------------------------
# ANLS: 完美匹配
# ---------------------------------------------------------------------------

def test_perfect_match():
    assert anls_score("hello", ["hello"]) == 1.0


def test_perfect_match_case_insensitive():
    # lowercase + strip 默认开启
    assert anls_score("HELLO", ["hello"]) == 1.0


def test_perfect_match_with_whitespace():
    assert anls_score("  hello  ", ["hello"]) == 1.0


# ---------------------------------------------------------------------------
# ANLS: 部分匹配
# ---------------------------------------------------------------------------

def test_one_char_off():
    # "hello" vs "hallo" 距离 1，max_len=5，NED=0.2，1-0.2=0.8
    s = anls_score("hallo", ["hello"])
    assert abs(s - 0.8) < 1e-9, f"expected 0.8 got {s}"


def test_half_match():
    # "ab" vs "cd" 距离 2，max_len=2，NED=1.0，>= 0.5 → 0
    s = anls_score("cd", ["ab"])
    assert s == 0.0


def test_one_char_in_long_string():
    # "January" vs "Januar" 距离 1，max_len=7，NED≈0.143
    s = anls_score("Januar", ["January"])
    expected = 1.0 - 1.0 / 7
    assert abs(s - expected) < 1e-9, f"expected {expected} got {s}"


# ---------------------------------------------------------------------------
# ANLS: 阈值 τ 边界
# ---------------------------------------------------------------------------

def test_threshold_just_below():
    # NED = 0.4 < 0.5 → 0.6
    s = anls_score("hello!", ["hello?"])
    # 距离 1, max_len 6, NED = 1/6 ≈ 0.1667
    # 实际 1-1/6 ≈ 0.833
    assert s > 0.5


def test_threshold_at_boundary_returns_zero():
    # NED = 0.5 整 → 0（条件 NED < tau）
    # "ab" vs "a" 距离 1, max_len=2, NED=0.5, tau=0.5 → 0
    s = anls_score("a", ["ab"])
    assert s == 0.0, f"边界 NED=0.5 应该返回 0，得到 {s}"


def test_threshold_above_returns_zero():
    # NED = 0.67 > 0.5 → 0
    s = anls_score("a", ["abc"])
    assert s == 0.0


def test_custom_tau():
    # tau = 0.3 时 NED=0.4 应该给 0
    s = anls_score("hello!", ["hello?"], tau=0.3)
    # 距离 1, max_len 6, NED ≈ 0.167 < 0.3 → 0.833
    assert abs(s - (1 - 1.0/6)) < 1e-9
    # tau = 0.1 时同样输入给 0
    s2 = anls_score("hello!", ["hello?"], tau=0.1)
    assert s2 == 0.0


# ---------------------------------------------------------------------------
# ANLS: 多 gold 取 max
# ---------------------------------------------------------------------------

def test_multi_gold_max():
    # 两个 gold：一个匹配差（NED < 0.5），一个完美
    # 应取完美的 1.0
    s = anls_score("January 5, 2020", ["January 5, 2020", "Jan 5 2020"])
    assert s == 1.0


def test_multi_gold_max_among_partial():
    # 两个 gold：都部分匹配
    # "Jan 5" 距离 "January 5, 2020" 大，NED > 0.5 → 0
    # "January 5" 距离 "January 5, 2020"：插入 ", 2020" = 6 字符
    # max_len = 15, NED = 6/15 = 0.4, score = 0.6
    s = anls_score("January 5, 2020", ["Jan 5", "January 5"])
    expected = 1.0 - 6.0/15  # = 0.6
    assert abs(s - expected) < 1e-9, f"expected {expected} got {s}"


def test_multi_gold_all_fail():
    s = anls_score("xyz", ["abc", "def"])
    assert s == 0.0


# ---------------------------------------------------------------------------
# ANLS: 空字符串
# ---------------------------------------------------------------------------

def test_both_empty():
    assert anls_score("", [""]) == 1.0


def test_pred_empty_gold_nonempty():
    # pred 空，gold 非空 → NED=1（>0.5）→ 0
    s = anls_score("", ["hello"])
    assert s == 0.0


def test_pred_nonempty_gold_empty():
    s = anls_score("hello", [""])
    assert s == 0.0


def test_pred_empty_all_gold_empty():
    s = anls_score("", ["", ""])
    assert s == 1.0


# ---------------------------------------------------------------------------
# ANLS: dataset
# ---------------------------------------------------------------------------

def test_dataset_simple():
    preds = ["hello", "world", "foo"]
    gts = [["hello"], ["world"], ["bar"]]
    res = anls_dataset(preds, gts)
    # hello=1.0, world=1.0, foo vs bar NED=1 → 0
    assert abs(res["anls"] - 2.0/3) < 1e-9
    assert res["n"] == 3
    assert res["scores"] == [1.0, 1.0, 0.0]


def test_dataset_empty():
    res = anls_dataset([], [])
    assert res["anls"] == 0.0
    assert res["n"] == 0
    assert res["scores"] == []


def test_dataset_mismatch_raises():
    try:
        anls_dataset(["a", "b"], [["x"]])
        raise AssertionError("应该 raise AssertionError")
    except AssertionError:
        pass


def test_dataset_with_partial_matches():
    # 平均化算的
    preds = ["hello", "hallo", "world"]
    gts = [["hello"], ["hello"], ["earth"]]
    res = anls_dataset(preds, gts)
    # 1.0 + 0.8 + 0.0 = 1.8 / 3 = 0.6
    expected = (1.0 + 0.8 + 0.0) / 3
    assert abs(res["anls"] - expected) < 1e-9, f"expected {expected} got {res['anls']}"
