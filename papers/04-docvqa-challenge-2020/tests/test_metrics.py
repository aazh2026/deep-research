"""ANLS + MAP metric 单元测试。"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.metrics import (
    levenshtein, anls_score, anls_dataset,
    average_precision, mean_average_precision,
    precision_at_k, recall_at_k,
)


# ---------------------------------------------------------------------------
# Levenshtein + ANLS（与 03-docvqa 一致）
# ---------------------------------------------------------------------------

def test_levenshtein_identical():
    assert levenshtein("hello", "hello") == 0


def test_levenshtein_basic():
    assert levenshtein("cat", "bat") == 1
    assert levenshtein("cat", "cats") == 1
    assert levenshtein("abc", "xyz") == 3


def test_levenshtein_empty():
    assert levenshtein("", "abc") == 3
    assert levenshtein("abc", "") == 3
    assert levenshtein("", "") == 0


def test_anls_perfect():
    assert anls_score("hello", ["hello"]) == 1.0


def test_anls_one_char_off():
    # "hallo" vs "hello" 距离 1, NED = 1/5 = 0.2, score = 0.8
    assert abs(anls_score("hallo", ["hello"]) - 0.8) < 1e-9


def test_anls_threshold_boundary():
    # NED = 0.5 整 → 0
    assert anls_score("a", ["ab"]) == 0.0


def test_anls_threshold_above():
    # NED = 0.67 > 0.5 → 0
    assert anls_score("a", ["abc"]) == 0.0


def test_anls_multi_gold_max():
    # 两个 gold：完美 + 部分匹配 → 取 max = 1.0
    assert anls_score("January 5, 2020", ["January 5, 2020", "Jan 5 2020"]) == 1.0


def test_anls_case_insensitive():
    assert anls_score("HELLO", ["hello"]) == 1.0


def test_anls_strip():
    assert anls_score("  hello  ", ["hello"]) == 1.0


def test_anls_both_empty():
    assert anls_score("", [""]) == 1.0


def test_anls_pred_empty_gold_nonempty():
    assert anls_score("", ["hello"]) == 0.0


def test_anls_dataset():
    preds = ["hello", "world", "foo"]
    gts = [["hello"], ["world"], ["bar"]]
    res = anls_dataset(preds, gts)
    # 1.0 + 1.0 + 0.0 = 2/3
    assert abs(res["anls"] - 2.0/3) < 1e-9
    assert res["n"] == 3


def test_anls_dataset_empty():
    res = anls_dataset([], [])
    assert res["anls"] == 0.0
    assert res["n"] == 0


# ---------------------------------------------------------------------------
# MAP (Task 2 retrieval)
# ---------------------------------------------------------------------------

def test_ap_perfect():
    # 全部命中，顺序完美
    ap = average_precision(["d1", "d2", "d3"], {"d1", "d2", "d3"})
    # precision@k 始终 1.0，AP = (1/3) * (1 + 2/2 + 3/3) = (1+1+1)/3 = 1.0
    assert abs(ap - 1.0) < 1e-9


def test_ap_first_hit():
    # 只第一个命中，relevant = {d1}
    ap = average_precision(["d1", "d2", "d3"], {"d1"})
    # precision@1 = 1/1 = 1, AP = 1/1 * 1 = 1
    assert abs(ap - 1.0) < 1e-9


def test_ap_no_hits():
    ap = average_precision(["d1", "d2", "d3"], {"d4", "d5"})
    assert ap == 0.0


def test_ap_partial_order():
    # relevant = {d1, d3}, retrieved = [d1, d2, d3]
    # k=1: hit, prec=1/1
    # k=2: miss
    # k=3: hit, prec=2/3
    # AP = (1 + 2/3) / 2 = 5/6
    ap = average_precision(["d1", "d2", "d3"], {"d1", "d3"})
    expected = (1.0 + 2.0/3) / 2
    assert abs(ap - expected) < 1e-9, f"expected {expected} got {ap}"


def test_ap_empty_relevant():
    ap = average_precision(["d1", "d2"], set())
    assert ap == 0.0


def test_ap_empty_retrieved():
    ap = average_precision([], {"d1"})
    assert ap == 0.0


def test_map_simple():
    preds = [["d1", "d2"], ["d3", "d4"], ["d5", "d6"]]
    gold = [{"d1"}, {"d3"}, set()]
    res = mean_average_precision(preds, gold)
    # AP1 = 1.0, AP2 = 1.0, AP3 = 0.0
    # MAP = 2/3
    assert abs(res["map"] - 2.0/3) < 1e-9
    assert res["n"] == 3


def test_map_paper_target():
    """复现 paper Table 2: DQA 0.8090, DOCR 0.7915。"""
    # 模拟近似完美的 retrieval：20 个 query，每个 query 找到 ~3 个相关文档
    # 排在最前
    preds = [[f"d{i}_{j}" for j in range(3)] for i in range(20)]
    gold = [{f"d{i}_{j}" for j in range(3)} for i in range(20)]
    res = mean_average_precision(preds, gold)
    # 完美排序应该 MAP ≈ 1.0
    assert res["map"] > 0.99


def test_map_mixed_relevance():
    preds = [
        ["d1", "d2", "d3"],
        ["d4", "d5", "d6"],
    ]
    gold = [
        {"d1", "d3"},  # 两个命中
        {"d6"},       # 一个命中（排序差）
    ]
    res = mean_average_precision(preds, gold)
    # AP1 = (1 + 2/3) / 2 = 5/6   (k=1 命中 prec=1, k=3 命中 prec=2/3)
    # AP2 = (1/3) / 1 = 1/3       (k=3 才命中，prec=1/3)
    # MAP = (5/6 + 1/3) / 2 = 7/12
    expected = (5.0/6 + 1.0/3) / 2
    assert abs(res["map"] - expected) < 1e-9, f"expected {expected} got {res['map']}"


# ---------------------------------------------------------------------------
# Precision/Recall @ k
# ---------------------------------------------------------------------------

def test_p_at_k_basic():
    assert precision_at_k(["d1", "d2", "d3"], {"d1", "d3"}, k=3) == 2/3


def test_p_at_k_zero():
    assert precision_at_k(["d4", "d5"], {"d1", "d2"}, k=2) == 0.0


def test_p_at_k_k_zero():
    assert precision_at_k(["d1"], {"d1"}, k=0) == 0.0


def test_r_at_k_basic():
    assert recall_at_k(["d1", "d2", "d3"], {"d1", "d3", "d7"}, k=3) == 2/3


def test_r_at_k_zero():
    assert recall_at_k(["d4", "d5"], {"d1", "d2"}, k=2) == 0.0


def test_r_at_k_empty_relevant():
    assert recall_at_k(["d1"], set(), k=1) == 0.0
