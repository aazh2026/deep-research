"""ChartQA 答案评估测试（metrics + baselines）。

覆盖：
- is_numeric（千分位、百分号、美元符号、负数、小数）
- to_float
- relaxed_numeric_match（5% 相对 / 0.02 绝对 / 1.0 绝对 三档容差）
- is_correct（strict + relaxed，numeric + text，多 gold 候选）
- compute_majority_predictor + majority_predict
- random_predict 形状 + 答案类型路由

跑法：python tests/test_metrics.py
"""

from __future__ import annotations

import os
import sys
import unittest

# 让脚本能 import src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.baselines import (
    compute_majority_predictor,
    majority_predict,
    random_predict,
)
from src.data_loader import ChartQAQuestion
from src.metrics import (
    is_correct,
    is_numeric,
    relaxed_numeric_match,
    to_float,
)


class TestIsNumeric(unittest.TestCase):
    def test_integers(self):
        self.assertTrue(is_numeric("42"))
        self.assertTrue(is_numeric("0"))
        self.assertTrue(is_numeric("-7"))

    def test_floats(self):
        self.assertTrue(is_numeric("3.14"))
        self.assertTrue(is_numeric("-0.5"))

    def test_commas(self):
        self.assertTrue(is_numeric("1,234"))
        self.assertTrue(is_numeric("5,000,000,000,000"))

    def test_percent(self):
        self.assertTrue(is_numeric("50%"))
        self.assertTrue(is_numeric("12.5%"))

    def test_currency(self):
        self.assertTrue(is_numeric("$100"))
        self.assertTrue(is_numeric("€50"))

    def test_non_numeric(self):
        self.assertFalse(is_numeric("Yes"))
        self.assertFalse(is_numeric("blue"))
        self.assertFalse(is_numeric("United States"))
        self.assertFalse(is_numeric(""))


class TestToFloat(unittest.TestCase):
    def test_basic(self):
        self.assertAlmostEqual(to_float("42"), 42.0)
        self.assertAlmostEqual(to_float("3.14"), 3.14)
        self.assertAlmostEqual(to_float("1,234"), 1234.0)
        self.assertAlmostEqual(to_float("$100"), 100.0)
        self.assertAlmostEqual(to_float("50%"), 50.0)


class TestRelaxedNumericMatch(unittest.TestCase):
    """ChartQA 官方 tolerance（vis-nlp/ChartBERT/utils.py）：

    ``abs(a - b) <= max(0.05 * max(|a|, |b|), 0.5)``
    """

    def test_exact_match(self):
        self.assertTrue(relaxed_numeric_match(100.0, 100.0))

    def test_within_5_percent_boundary(self):
        # 100, 95：误差=5，max(0.05*100, 0.5)=5 → ≤ 即真
        self.assertTrue(relaxed_numeric_match(95.0, 100.0))
        # 100, 94：误差=6，max=5 → 假
        self.assertFalse(relaxed_numeric_match(94.0, 100.0))

    def test_outside_5_percent(self):
        self.assertFalse(relaxed_numeric_match(80.0, 100.0))

    def test_large_gold(self):
        # gold=1000：max(0.05*1000, 0.5)=50
        # pred=960：误差=40 ≤ 50 → 真
        self.assertTrue(relaxed_numeric_match(960.0, 1000.0))
        # pred=940：误差=60 > 50 → 假
        self.assertFalse(relaxed_numeric_match(940.0, 1000.0))

    def test_abs_tol_0p5_for_small(self):
        # gold=0.5，0.05 * 0.5 = 0.025 < 0.5 → 用 abs_tol=0.5
        self.assertTrue(relaxed_numeric_match(0.9, 0.5))  # 误差 0.4 < 0.5
        self.assertTrue(relaxed_numeric_match(0.0, 0.5))  # 误差 0.5 == 0.5 (≤)
        self.assertFalse(relaxed_numeric_match(1.5, 0.5))  # 误差 1.0 > 0.5

    def test_zero_gold(self):
        # gold=0：rel_tol * 0 = 0，max(0, 0.5) = 0.5
        self.assertTrue(relaxed_numeric_match(0.3, 0.0))  # 误差 0.3 < 0.5
        self.assertFalse(relaxed_numeric_match(0.6, 0.0))  # 误差 0.6 > 0.5

    def test_negative_gold(self):
        # gold=-100，max(0.05*100, 0.5) = 5
        self.assertTrue(relaxed_numeric_match(-95.0, -100.0))
        self.assertTrue(relaxed_numeric_match(-105.0, -100.0))
        self.assertFalse(relaxed_numeric_match(-90.0, -100.0))


class TestIsCorrect(unittest.TestCase):
    def test_strict_exact_match(self):
        self.assertTrue(is_correct("Yes", ["Yes"], mode="strict"))
        self.assertTrue(is_correct("yes", ["Yes"], mode="strict"))  # case-insensitive
        self.assertTrue(is_correct("  Blue  ", ["blue"], mode="strict"))  # strip

    def test_strict_mismatch(self):
        self.assertFalse(is_correct("Yes", ["No"], mode="strict"))
        self.assertFalse(is_correct("Red", ["blue"], mode="strict"))

    def test_relaxed_numeric_close(self):
        # 100 vs 101, 5% 容差
        self.assertTrue(is_correct("101", ["100"], mode="relaxed"))

    def test_relaxed_numeric_too_far(self):
        # 100 vs 50, 超出 5%
        self.assertFalse(is_correct("50", ["100"], mode="relaxed"))

    def test_relaxed_text_strict(self):
        # 文本题 relaxed == strict
        self.assertTrue(is_correct("Yes", ["Yes"], mode="relaxed"))
        self.assertFalse(is_correct("yes", ["No"], mode="relaxed"))

    def test_multi_gold_any_match(self):
        # 多 gold 候选时，任一匹配即对
        self.assertTrue(is_correct("50", ["40", "50", "60"], mode="strict"))
        # 5% 容差：50 vs 40 误差 10 = 20% > 5%；50 vs 55 误差 5 = 10% > 5%
        # 50 vs 60 误差 10 = 16.7% > 5%
        # 用 abs_tol=0.5 也不够 → 全 miss
        self.assertFalse(is_correct("50", ["40", "55", "60"], mode="relaxed"))
        # 但 50 vs 51 误差 1 = max(2.5, 0.5) = 2.5 ≤ → 中
        self.assertTrue(is_correct("51", ["50"], mode="relaxed"))

    def test_empty_prediction(self):
        self.assertFalse(is_correct("", ["Yes"], mode="relaxed"))
        self.assertFalse(is_correct("   ", ["Yes"], mode="strict"))

    def test_numeric_with_currency(self):
        # "$100" 解析为 100，与 gold "100" 匹配
        self.assertTrue(is_correct("$100", ["100"], mode="relaxed"))


class TestMajorityPredictor(unittest.TestCase):
    def _qs(self, labels_and_types):
        return [
            ChartQAQuestion(
                uid=f"q-{i:03d}",
                query="x",
                label=[lbl],
                human_or_machine=0,
                answer_type=t,
            )
            for i, (lbl, t) in enumerate(labels_and_types)
        ]

    def test_numeric_median(self):
        qs = self._qs([("10", "numeric"), ("20", "numeric"),
                       ("30", "numeric"), ("40", "numeric")])
        num_pred, text_pred = compute_majority_predictor(qs)
        self.assertEqual(float(num_pred), 25.0)  # 中位数 (10+20+30+40)/2=50/2=25
        # text_pred 用默认值 'yes'
        self.assertEqual(text_pred, "yes")

    def test_text_majority(self):
        qs = self._qs([
            ("yes", "text"), ("yes", "text"), ("yes", "text"),
            ("no", "text"),
        ])
        num_pred, text_pred = compute_majority_predictor(qs)
        self.assertEqual(text_pred, "yes")

    def test_mixed(self):
        qs = self._qs([
            ("100", "numeric"), ("200", "numeric"),
            ("yes", "text"), ("yes", "text"), ("yes", "text"),
            ("no", "text"),
        ])
        num_pred, text_pred = compute_majority_predictor(qs)
        self.assertEqual(float(num_pred), 150.0)
        self.assertEqual(text_pred, "yes")

    def test_majority_predict_routing(self):
        qs = self._qs([("100", "numeric"), ("yes", "text")])
        preds = majority_predict(qs, num_pred="42", text_pred="yes")
        self.assertEqual(preds[0]["prediction"], "42")
        self.assertEqual(preds[1]["prediction"], "yes")


class TestRandomPredict(unittest.TestCase):
    def _qs(self, types):
        return [
            ChartQAQuestion(
                uid=f"q-{i:03d}",
                query="x",
                label=[t],
                human_or_machine=0,
                answer_type=t,
            )
            for i, t in enumerate(types)
        ]

    def test_shape(self):
        qs = self._qs(["numeric"] * 5 + ["text"] * 5)
        preds = random_predict(qs, text_vocab=["yes", "no"], seed=42)
        self.assertEqual(len(preds), 10)
        for p in preds:
            self.assertIn("prediction", p)
            self.assertIn("uid", p)

    def test_numeric_range(self):
        qs = self._qs(["numeric"] * 50)
        preds = random_predict(qs, num_low=0, num_high=10, seed=42)
        for p in preds:
            v = float(p["prediction"])
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 10.0)

    def test_text_in_vocab(self):
        qs = self._qs(["text"] * 20)
        vocab = ["yes", "no", "blue"]
        preds = random_predict(qs, text_vocab=vocab, seed=42)
        for p in preds:
            self.assertIn(p["prediction"], vocab)

    def test_seed_reproducibility(self):
        qs = self._qs(["text"] * 5)
        p1 = random_predict(qs, text_vocab=["a", "b"], seed=123)
        p2 = random_predict(qs, text_vocab=["a", "b"], seed=123)
        for a, b in zip(p1, p2):
            self.assertEqual(a["prediction"], b["prediction"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
