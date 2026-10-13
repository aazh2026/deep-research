"""DocVQA 盲 baseline：纯文本 / 多数 / 随机。

复现路径：把「模型读文档图像 + OCR + 推理」替换为「只用 OCR 抽出的 words」做
lexical 检索 + 启发式答案抽取。

设计动机：
- 验证「视觉」对 DocVQA 任务的实际贡献——baseline 锚点
- 验证 ANLS metric 对多 gold 取 max 的处理（不同 gold 长度差大时 metric 行为）
- 验证 question→answer 的 lexical overlap 是否解释答案（如「date of document?」→年/月）

注：这些 baseline **不读图像**——只看 OCR words 和问题。Paper 报的 BERT/RoBERTa
在 DocVQA 上 ~70-80% ANLS 来自视觉 + 文本联合，盲 baseline 上限 1-5%。
"""

from __future__ import annotations

import re
import random
from collections import Counter
from typing import Optional

from .data_loader import DocVQAQuestion, words_to_text
from .metrics import anls_dataset


# ---------------------------------------------------------------------------
# Baseline 1: Most-Frequent-Answer
# ---------------------------------------------------------------------------

def compute_majority_answer(qs: list[DocVQAQuestion]) -> str:
    """全数据集出现频率最高的答案（lowercase + strip）。"""
    c = Counter()
    for q in qs:
        for a in q.answers:
            c[a.lower().strip()] += 1
    if not c:
        return ""
    return c.most_common(1)[0][0]


def majority_predict(qs: list[DocVQAQuestion], majority: str) -> list[str]:
    """对所有题预测同一个多数答案。"""
    return [majority] * len(qs)


# ---------------------------------------------------------------------------
# Baseline 2: Random（用 train 答案词典中按频率采样）
# ---------------------------------------------------------------------------

def compute_random_pool(qs: list[DocVQAQuestion]) -> list[tuple[str, float]]:
    """构造 random baseline 的答案采样池（带频率权重）。"""
    c = Counter()
    for q in qs:
        for a in q.answers:
            c[a.lower().strip()] += 1
    total = sum(c.values())
    if total == 0:
        return [("", 1.0)]
    return [(ans, cnt / total) for ans, cnt in c.items()]


def random_predict(qs: list[DocVQAQuestion],
                   pool: list[tuple[str, float]],
                   seed: int = 42) -> list[str]:
    """按 train 答案分布独立采样（无任何问题信息）。"""
    rng = random.Random(seed)
    if not pool:
        return [""] * len(qs)
    answers = [a for a, _ in pool]
    weights = [w for _, w in pool]
    return [rng.choices(answers, weights=weights, k=1)[0] for _ in qs]


# ---------------------------------------------------------------------------
# Baseline 3: Lexical retrieval（核心 baseline）
# ---------------------------------------------------------------------------

NUMBER_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")


def extract_numbers(text: str) -> list[str]:
    """抽所有数字 token（含千分位逗号、小数、负号）。"""
    return NUMBER_RE.findall(text)


def find_query_keywords(query: str) -> list[str]:
    """从问题里抽出「信号词」（去 stopword、长度 > 2）。"""
    # 注意：title/date/name 等在 DocVQA 是「信号词」——它们是问题关键
    # 不是 stopword。
    stop = {
        "what", "when", "where", "which", "who", "whom", "whose", "how",
        "is", "are", "was", "were", "be", "been", "being",
        "the", "a", "an", "of", "in", "on", "at", "to", "for", "by",
        "this", "that", "these", "those",
        "it", "its", "i", "you", "he", "she", "we", "they",
        "and", "or", "but", "not", "no", "yes",
        "as", "with", "from", "into", "during", "until", "than",
        "page", "number", "total",
    }
    words = re.findall(r"\w+", query.lower())
    return [w for w in words if w not in stop and len(w) > 2]


def lexical_predict(q: DocVQAQuestion) -> str:
    """在 OCR words 里找含 query 关键词的句子/段，提取首句作为预测。

    这是**纯文本检索 baseline**——不读图，不跑 VLM，纯粹用 OCR 文本 + lexical
    overlap 猜答案。

    启发式（专为 DocVQA 常见问题模式优化）：
    - "what is the title?" → 第一行前几个词
    - "what is the date?" → 第一个含数字的短串
    - "who/what/where/when is X?" → 关键词后面的短串
    - 其他 → OCR 全文第一行

    这些规则**有意暴露** baseline 的局限：DocVQA 70-80% ANLS 来自 VLM 读图理解。
    """
    text = words_to_text(q.words)
    if not text.strip():
        return ""
    keywords = find_query_keywords(q.query)
    text_lower = text.lower()

    # 启发式 1：title 提问 → OCR 第一个「大写」起头的连续词
    if any(k in q.query.lower() for k in ["title", "header", "subject"]):
        # 找第一个长 1-8 词的纯字母短语
        m = re.match(r"\s*([A-Z][A-Za-z\-]+(?:\s+[A-Z][A-Za-z\-]+){0,7})", text)
        if m:
            return m.group(1).strip()

    # 启发式 2：date 提问 → 找第一个数字串
    if "date" in q.query.lower() or "year" in q.query.lower():
        nums = extract_numbers(text)
        return nums[0] if nums else ""

    # 启发式 3：含关键词 → 找第一个含关键词的窗口
    if keywords:
        # 找第一个关键词的索引
        words_lower = [w.lower() for w in q.words]
        kw_set = set(keywords)
        hit_idx = next((i for i, w in enumerate(words_lower) if w in kw_set), -1)
        if hit_idx >= 0 and hit_idx + 1 < len(q.words):
            # 关键词后取 1-4 词
            return " ".join(q.words[hit_idx + 1: hit_idx + 5]).strip()

    # 启发式 4：默认返回全文前 30 词
    return " ".join(q.words[:30]).strip()


# ---------------------------------------------------------------------------
# 评估封装
# ---------------------------------------------------------------------------

def evaluate_baseline(qs: list[DocVQAQuestion], predictions: list[str],
                      tau: float = 0.5) -> dict:
    """对一组 prediction 计算 ANLS。"""
    gts = [q.answers for q in qs]
    res = anls_dataset(predictions, gts, tau=tau)
    return {"anls": res["anls"], "n": res["n"]}
