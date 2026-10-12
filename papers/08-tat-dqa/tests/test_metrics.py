"""测试评估指标。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.metrics import (
    compute_em_one,
    compute_f1_one,
    compute_metrics,
)
from utils.decode import safe_eval_expression


def test_safe_eval():
    """算式执行。"""
    assert safe_eval_expression("55 + 50") == 105.0
    assert safe_eval_expression("(100 - 60) / 2") == 20.0
    assert safe_eval_expression("100 * 1000") == 100000.0
    assert safe_eval_expression("invalid expr") is None
    assert safe_eval_expression("") is None
    print("  ✓ safe_eval_expression OK")


def test_em_text():
    """文本 EM。"""
    assert compute_em_one("hello", "hello") is True
    assert compute_em_one("hello", "Hello") is True  # case-insensitive
    assert compute_em_one("hello", "world") is False
    assert compute_em_one("  hello  ", "hello") is True
    print("  ✓ EM 文本 OK")


def test_em_number_with_scale():
    """带 scale 的数字 EM。

    TAT-DQA 论文语义：scale 仅属于 pred，gold 已是绝对量。
    """
    # 100 million vs 100000000 -> 不严格 equal，但 scale 应用后绝对值相等
    assert compute_em_one(100, 100000000, scale="million") is True
    # 50 thousand vs 50000 -> scale 应用后绝对值相等
    assert compute_em_one(50, 50000, scale="thousand") is True
    # 50 thousand vs 60000 -> 不等
    assert compute_em_one(50, 60000, scale="thousand") is False
    # 无 scale: 50 vs 50 直接相等
    assert compute_em_one(50, 50, scale="") is True
    print("  ✓ EM 数字+scale OK")


def test_em_list():
    """list EM。"""
    assert compute_em_one(["a", "b"], ["a", "b"]) is True
    assert compute_em_one(["a", "b"], ["b", "a"]) is True  # set-wise
    assert compute_em_one(["a", "b"], ["a", "c"]) is False
    print("  ✓ EM list OK")


def test_f1_one():
    """F1 单条。"""
    assert compute_f1_one("foo", "foo") == 1.0
    assert compute_f1_one("foo", "bar") == 0.0
    # 数字 + scale（scale 仅作用于 pred）
    # 100 million vs 100000000 -> scale 应用后绝对值相等
    assert compute_f1_one(100, 100000000, scale="million") == 1.0
    # 100 million vs 50 million -> 不等
    assert compute_f1_one(100, 50000000, scale="million") == 0.0
    print("  ✓ F1 OK")


def test_compute_metrics_batch():
    """批量指标计算。"""
    preds = ["$100M", "$50M", "foo", "bar", 100, ["a", "b"]]
    golds = ["100 million", "50 million", "foo", "baz", 100, ["a", "b", "c"]]
    scales = ["million", "million", "", "", "million", ""]
    types = ["span", "span", "span", "span", "arithmetic", "multi-span"]

    m = compute_metrics(preds, golds, scales, types)
    assert "overall" in m
    assert "per_type" in m
    assert m["overall"]["n"] == 6
    print(f"  ✓ compute_metrics OK: overall EM={m['overall']['EM']:.3f}")


if __name__ == "__main__":
    print("[test_metrics]")
    test_safe_eval()
    test_em_text()
    test_em_number_with_scale()
    test_em_list()
    test_f1_one()
    test_compute_metrics_batch()
    print("\n全部通过 ✓")