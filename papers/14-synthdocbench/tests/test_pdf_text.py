"""PDF 文本提取 + 答案检索性测试。

覆盖：
- extract_numbers（数字正则）
- normalize_text（小写、空白压缩）
- find_answer_in_text（substring / num / phrase hit）
- evidence_page 定位逻辑

跑法：python tests/test_pdf_text.py
或：  pytest tests/test_pdf_text.py -v（如果装了 pytest）
"""

from __future__ import annotations

import os
import sys
import unittest

# 让脚本能 import src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.pdf_text import (
    extract_numbers,
    find_answer_in_text,
    normalize_text,
)


class TestExtractNumbers(unittest.TestCase):
    def test_simple_integers(self):
        self.assertEqual(extract_numbers("I have 42 apples"), ["42"])

    def test_commas(self):
        self.assertEqual(extract_numbers("5,000,000,000,000"), ["5,000,000,000,000"])

    def test_decimals(self):
        self.assertEqual(extract_numbers("pi is 3.14159"), ["3.14159"])

    def test_percent(self):
        self.assertEqual(extract_numbers("growth was 12.5%"), ["12.5%"])

    def test_negative(self):
        self.assertEqual(extract_numbers("decline of -3.2%"), ["-3.2%"])

    def test_multiple(self):
        # "from 10 to 20, growth 5%" → "10", "20,", "5%"
        # 注：NUM_RE 允许 digit 后接逗号，所以 "20," 整体被匹配
        # 这是设计选择：保留 ", 1234" 这类千分位数字
        self.assertEqual(
            extract_numbers("from 10 to 20, growth 5%"),
            ["10", "20,", "5%"],
        )

    def test_no_numbers(self):
        self.assertEqual(extract_numbers("no numbers here"), [])

    def test_word_with_number(self):
        # "x86_64" 实际会被识别为 ["86", "64"]
        # NUM_RE 允许 underscore 前的数字被切出来
        # 这是已知设计选择：宽松匹配优先，避免漏掉真实数字
        self.assertEqual(extract_numbers("x86_64"), ["86", "64"])


class TestNormalizeText(unittest.TestCase):
    def test_lowercase(self):
        self.assertEqual(normalize_text("HELLO World"), "hello world")

    def test_collapse_whitespace(self):
        self.assertEqual(
            normalize_text("hello\n\n  world\t\tfoo"),
            "hello world foo",
        )

    def test_empty(self):
        self.assertEqual(normalize_text(""), "")


class TestFindAnswerInText(unittest.TestCase):
    def test_substring_hit_simple(self):
        text = "The token count for Natural Language Text is 5,000,000,000,000."
        gold = "The token count for Natural Language Text is 5,000,000,000,000"
        hit = find_answer_in_text(gold, text)
        self.assertTrue(hit["substring_hit"])
        self.assertEqual(hit["num_hits"], 1)
        self.assertEqual(hit["num_total"], 1)

    def test_substring_miss(self):
        # 文本里没那句话，只有别的数字
        text = "Some unrelated report about 5,000 items."
        gold = "The token count for Natural Language Text is 5,000,000,000,000"
        hit = find_answer_in_text(gold, text)
        self.assertFalse(hit["substring_hit"])
        # 5,000,000,000,000 不在文本里
        self.assertEqual(hit["num_hits"], 0)
        self.assertEqual(hit["num_total"], 1)

    def test_partial_num_match(self):
        # 文本里只出现部分数字
        text = "Total: 1,000,000. Other: 2,000."
        gold = "Total: 1,000,000 and Average: 2,000,000"
        hit = find_answer_in_text(gold, text)
        self.assertFalse(hit["substring_hit"])
        # 1,000,000 在, 2,000,000 不在
        self.assertEqual(hit["num_hits"], 1)
        self.assertEqual(hit["num_total"], 2)

    def test_no_numbers_in_gold(self):
        # gold 答案没数字
        text = "The answer is the second one."
        gold = "the second one"
        hit = find_answer_in_text(gold, text)
        self.assertTrue(hit["substring_hit"])
        self.assertEqual(hit["num_total"], 0)
        self.assertEqual(hit["num_hits"], 0)

    def test_phrase_match(self):
        # 没有 substring hit，但有关键短语
        text = "The Transformer architecture is a major innovation."
        gold = "The Transformer model is a critical innovation"
        hit = find_answer_in_text(gold, text)
        self.assertFalse(hit["substring_hit"])
        # transformer, architecture, innovation 应至少有一部分命中
        self.assertGreater(hit["phrase_hits"], 0)
        self.assertGreater(hit["phrase_total"], 0)

    def test_phrase_stop_words_filtered(self):
        # 5+ 字符停用词（about, which, these 等）应被剔除
        text = "This is about something"
        gold = "about which these there"
        hit = find_answer_in_text(gold, text)
        # 所有 5+ 字符的"短语"都是停用词 → phrase_total = 0
        self.assertEqual(hit["phrase_total"], 0)

    def test_evidence_page_substring(self):
        pages = [
            "Page one with intro text.",
            "Page two with the answer The token count is 5 trillion.",
            "Page three with conclusion.",
        ]
        gold = "The token count is 5 trillion"
        hit = find_answer_in_text(gold, "\n".join(pages), pages)
        self.assertTrue(hit["substring_hit"])
        self.assertEqual(hit["evidence_page"], 1)

    def test_evidence_page_none_when_no_hit(self):
        pages = ["Page one", "Page two"]
        gold = "Some non-existent answer"
        hit = find_answer_in_text(gold, "\n".join(pages), pages)
        self.assertIsNone(hit["evidence_page"])

    def test_evidence_page_first_number(self):
        # substring miss，但 num hit → 定位到第一个数字所在页
        pages = [
            "Page one.",
            "Page two with 5,000,000,000,000 tokens.",
            "Page three.",
        ]
        gold = "The count is 5,000,000,000,000 widgets"
        hit = find_answer_in_text(gold, "\n".join(pages), pages)
        self.assertFalse(hit["substring_hit"])
        self.assertEqual(hit["num_hits"], 1)
        self.assertEqual(hit["evidence_page"], 1)

    def test_any_hit(self):
        # any_hit = substring or num or phrase
        text = "Random discussion with the word model"
        gold = "The answer uses the model"
        hit = find_answer_in_text(gold, text)
        self.assertTrue(hit["any_hit"])  # phrase 命中


if __name__ == "__main__":
    unittest.main(verbosity=2)
