"""text_evidence_score + 评估聚合测试。

覆盖：
- text_evidence_score 五个模式（lenient / strict / number_only /
  conservative / high_bar）
- aggregate_acc / aggregate_by_subset / aggregate_by_difficulty
- random_evaluate 行为
- 边界：empty results、所有跳过

跑法：python tests/test_retrieval.py
"""

from __future__ import annotations

import os
import sys
import unittest

# 让脚本能 import src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import SDBQuestion
from src.retrieval import (
    aggregate_acc,
    aggregate_by_difficulty,
    aggregate_by_subset,
    random_evaluate,
    text_evidence_score,
)


def _hit(substring=False, num_hits=0, num_total=0,
         phrase_hits=0, phrase_total=0) -> dict:
    return {
        "substring_hit": substring,
        "num_hits": num_hits,
        "num_total": num_total,
        "phrase_hits": phrase_hits,
        "phrase_total": phrase_total,
        "evidence_page": None,
        "any_hit": substring or num_hits > 0 or phrase_hits > 0,
    }


class TestTextEvidenceScore(unittest.TestCase):
    """text_evidence_score 5 个模式的语义对比。"""

    def test_substring_full_credit_all_modes(self):
        """substring 命中：所有模式都给 1.0"""
        h = _hit(substring=True, num_hits=0, num_total=0)
        for mode in ["lenient", "strict", "number_only",
                     "conservative", "high_bar"]:
            self.assertEqual(text_evidence_score(h, mode), 1.0, f"mode={mode}")

    def test_lenient_substring_miss_partial_credit(self):
        """lenient：0.5*num_ratio + 0.5*phrase_ratio"""
        h = _hit(num_hits=1, num_total=2, phrase_hits=2, phrase_total=4)
        # = 0.5 * 0.5 + 0.5 * 0.5 = 0.5
        self.assertAlmostEqual(text_evidence_score(h, "lenient"), 0.5)

    def test_lenient_zero_credit(self):
        h = _hit(num_hits=0, num_total=0, phrase_hits=0, phrase_total=0)
        self.assertEqual(text_evidence_score(h, "lenient"), 0.0)

    def test_strict_substring_miss_only_num(self):
        """strict：不看 phrase，只看 num_ratio"""
        h = _hit(num_hits=2, num_total=4, phrase_hits=4, phrase_total=4)
        # strict: 2/4 = 0.5（phrase 全部命中也不算）
        self.assertAlmostEqual(text_evidence_score(h, "strict"), 0.5)

    def test_strict_no_numbers(self):
        h = _hit(phrase_hits=5, phrase_total=5)  # 全部 phrase 命中
        # 没数字 → 0
        self.assertEqual(text_evidence_score(h, "strict"), 0.0)

    def test_number_only_all_match(self):
        h = _hit(num_hits=3, num_total=3)
        self.assertEqual(text_evidence_score(h, "number_only"), 1.0)

    def test_number_only_partial_match(self):
        h = _hit(num_hits=2, num_total=3)
        self.assertEqual(text_evidence_score(h, "number_only"), 0.0)

    def test_number_only_no_numbers(self):
        h = _hit(phrase_hits=3, phrase_total=3)
        self.assertEqual(text_evidence_score(h, "number_only"), 0.0)

    def test_conservative_only_substring(self):
        """conservative：text-only 答得出的唯一判据是 substring 命中"""
        h = _hit(num_hits=10, num_total=10, phrase_hits=10, phrase_total=10)
        # 数字+phrase 全命中但 substring miss → 0
        self.assertEqual(text_evidence_score(h, "conservative"), 0.0)

    def test_conservative_substring_hit(self):
        h = _hit(substring=True)
        self.assertEqual(text_evidence_score(h, "conservative"), 1.0)

    def test_high_bar_80_percent_num(self):
        h = _hit(num_hits=4, num_total=5)  # 80% 数字命中
        self.assertEqual(text_evidence_score(h, "high_bar"), 1.0)

    def test_high_bar_79_percent_num(self):
        h = _hit(num_hits=3, num_total=4)  # 75% 数字命中
        self.assertEqual(text_evidence_score(h, "high_bar"), 0.0)

    def test_high_bar_no_numbers(self):
        h = _hit(phrase_hits=5, phrase_total=5)
        self.assertEqual(text_evidence_score(h, "high_bar"), 0.0)

    def test_unknown_mode_raises(self):
        h = _hit()
        with self.assertRaises(ValueError):
            text_evidence_score(h, "bogus_mode")


class TestAggregateAcc(unittest.TestCase):
    def test_empty(self):
        r = aggregate_acc([], threshold=0.5)
        self.assertEqual(r["n_valid"], 0)
        self.assertEqual(r["acc"], 0.0)

    def test_all_correct(self):
        results = [
            {"score": 0.9, "skipped": False},
            {"score": 0.7, "skipped": False},
            {"score": 1.0, "skipped": False},
        ]
        r = aggregate_acc(results, threshold=0.5)
        self.assertEqual(r["n_valid"], 3)
        self.assertEqual(r["n_correct"], 3)
        self.assertAlmostEqual(r["acc"], 1.0)

    def test_mixed(self):
        results = [
            {"score": 0.9, "skipped": False},
            {"score": 0.3, "skipped": False},
            {"score": 0.6, "skipped": False},
        ]
        r = aggregate_acc(results, threshold=0.5)
        # 0.9, 0.6 ≥ 0.5 → 2 对
        self.assertEqual(r["n_correct"], 2)
        self.assertAlmostEqual(r["acc"], 2/3)

    def test_skip_filtered(self):
        results = [
            {"score": 0.9, "skipped": False},
            {"score": 1.0, "skipped": True},   # 跳过
            {"score": 0.7, "skipped": False},
        ]
        r = aggregate_acc(results, threshold=0.5)
        self.assertEqual(r["n_valid"], 2)
        self.assertEqual(r["n_correct"], 2)


class TestAggregateBySubset(unittest.TestCase):
    def test_split(self):
        results = [
            {"subset": "chart", "difficulty": 1, "score": 0.9, "skipped": False},
            {"subset": "chart", "difficulty": 2, "score": 0.3, "skipped": False},
            {"subset": "complex", "difficulty": 1, "score": 0.6, "skipped": False},
        ]
        r = aggregate_by_subset(results, threshold=0.5)
        self.assertIn("chart", r)
        self.assertIn("complex", r)
        # chart: 0.9 ≥ 0.5, 0.3 < 0.5 → 1/2 = 0.5
        self.assertAlmostEqual(r["chart"]["acc"], 0.5)
        # complex: 0.6 ≥ 0.5 → 1/1 = 1.0
        self.assertAlmostEqual(r["complex"]["acc"], 1.0)


class TestAggregateByDifficulty(unittest.TestCase):
    def test_split_ordered(self):
        results = [
            {"subset": "chart", "difficulty": 3, "score": 0.9, "skipped": False},
            {"subset": "complex", "difficulty": 1, "score": 0.3, "skipped": False},
            {"subset": "chart", "difficulty": 1, "score": 0.6, "skipped": False},
        ]
        r = aggregate_by_difficulty(results, threshold=0.5)
        # 应该按 difficulty 升序
        keys = list(r.keys())
        self.assertEqual(keys, [1, 3])
        # L1: 0.3 < 0.5, 0.6 ≥ 0.5 → 1/2 = 0.5
        self.assertAlmostEqual(r[1]["acc"], 0.5)
        # L3: 0.9 ≥ 0.5 → 1/1 = 1.0
        self.assertAlmostEqual(r[3]["acc"], 1.0)


class TestRandomEvaluate(unittest.TestCase):
    def _qs(self, n=10):
        return [
            SDBQuestion(
                uid=f"q-{i:03d}",
                pdf_filename="x.pdf",
                topic="t",
                question="q",
                answer="a",
                difficulty=1,
                question_type="t",
                category=None,
                subset="chart",
            )
            for i in range(n)
        ]

    def test_returns_one_per_question(self):
        qs = self._qs(10)
        r = random_evaluate(qs, seed=42)
        self.assertEqual(len(r), 10)
        for x in r:
            self.assertIn("score", x)
            self.assertIn("subset", x)
            self.assertFalse(x["skipped"])

    def test_scores_in_unit_interval(self):
        qs = self._qs(50)
        r = random_evaluate(qs, seed=42)
        for x in r:
            self.assertGreaterEqual(x["score"], 0.0)
            self.assertLessEqual(x["score"], 1.0)

    def test_about_half_above_threshold(self):
        # 50 题 × 100 个 sample：随机 score 期望 ~50% ≥ 0.5
        # （确切比例有 ±5% 波动，但应该不会偏太多）
        qs = self._qs(200)
        r = random_evaluate(qs, seed=42)
        n_above = sum(1 for x in r if x["score"] >= 0.5)
        self.assertGreater(n_above, 80)
        self.assertLess(n_above, 120)

    def test_seed_reproducibility(self):
        qs = self._qs(5)
        r1 = random_evaluate(qs, seed=123)
        r2 = random_evaluate(qs, seed=123)
        for a, b in zip(r1, r2):
            self.assertEqual(a["score"], b["score"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
