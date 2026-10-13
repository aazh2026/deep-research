"""DocVQA Challenge 2020 盲 baseline。

设计动机：
- Task 1（抽取式 QA）：复现 paper Table 1 的 **Plain BERT QA = 0.35** 是 text-only
  baseline。**这正是我们能匹配的目标**——不读图，只用 OCR 文本。
- Task 2（文档集合检索）：复现 paper Table 2 的 **BM25-like** 检索
  锚定下限。

注：
- 我们的「OCR + 关键词」lexical baseline 在 03-docvqa 上是 3.7% ANLS
- paper 的 Plain BERT QA 是 0.35 ANLS = 35%
- 35% vs 3.7% 差距 9.4 倍——BERT 即使不带 layout 也能从 OCR 文本里
  抽出有用信息（不只是关键词匹配）
"""

from __future__ import annotations

import re
import random
from collections import Counter

from .data_loader import DocVQAQuestion, words_to_text
from .metrics import anls_dataset


# ---------------------------------------------------------------------------
# Task 1: Majority baseline
# ---------------------------------------------------------------------------

def compute_majority_answer(qs: list[DocVQAQuestion]) -> str:
    c = Counter()
    for q in qs:
        for a in q.answers:
            c[a.lower().strip()] += 1
    return c.most_common(1)[0][0] if c else ""


def majority_predict(qs: list[DocVQAQuestion], majority: str) -> list[str]:
    return [majority] * len(qs)


def compute_random_pool(qs: list[DocVQAQuestion]) -> list[tuple[str, float]]:
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
    rng = random.Random(seed)
    if not pool:
        return [""] * len(qs)
    answers = [a for a, _ in pool]
    weights = [w for _, w in pool]
    return [rng.choices(answers, weights=weights, k=1)[0] for _ in qs]


# ---------------------------------------------------------------------------
# Task 1: Lexical baseline（与 03-docvqa 一致：title/date/keyword）
# ---------------------------------------------------------------------------

NUMBER_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")


def find_query_keywords(query: str) -> list[str]:
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
    text = words_to_text(q.words)
    if not text.strip():
        return ""
    keywords = find_query_keywords(q.query)
    text_lower = text.lower()

    if any(k in q.query.lower() for k in ["title", "header", "subject"]):
        m = re.match(r"\s*([A-Z][A-Za-z\-]+(?:\s+[A-Z][A-Za-z\-]+){0,7})", text)
        if m:
            return m.group(1).strip()

    if "date" in q.query.lower() or "year" in q.query.lower():
        nums = NUMBER_RE.findall(text)
        return nums[0] if nums else ""

    if keywords:
        words_lower = [w.lower() for w in q.words]
        kw_set = set(keywords)
        hit_idx = next((i for i, w in enumerate(words_lower) if w in kw_set), -1)
        if hit_idx >= 0 and hit_idx + 1 < len(q.words):
            return " ".join(q.words[hit_idx + 1: hit_idx + 5]).strip()

    return " ".join(q.words[:30]).strip()


# ---------------------------------------------------------------------------
# Task 1: Span-Exact baseline（核心 baseline，匹配 paper "Plain BERT QA"）
# ---------------------------------------------------------------------------

def span_exact_predict(q: DocVQAQuestion) -> str:
    """Span 抽取式 baseline：找 OCR 文本里**含最多 query 关键词**的 5-token 窗口。

    设计动机：paper 的「Plain BERT QA」虽然不带 layout，但仍是一个**有监督的 span
    抽取模型**——它能从文档里抽出相关 span。我们没有监督信号，只能用关键词 overlap
    模拟「找到最相关的 span」。

    启发式：滑动 5-token 窗口，算窗口内 keyword 出现次数，取 max overlap 窗口作为答案。
    这是 Plain BERT QA 的**最弱文本下界**。
    """
    text = words_to_text(q.words)
    if not text.strip():
        return ""
    keywords = find_query_keywords(q.query)
    if not keywords or len(q.words) < 5:
        # 无关键词或文档太短 → 返回前 5 词
        return " ".join(q.words[:5]).strip()

    kw_set = set(keywords)
    window = 5
    best_count = -1
    best_span = " ".join(q.words[:5])
    for i in range(len(q.words) - window + 1):
        chunk = q.words[i: i + window]
        chunk_lower = [w.lower() for w in chunk]
        count = sum(1 for w in chunk_lower if w in kw_set)
        # >= 让靠后的命中优先（更接近"含 keyword 的 span"）
        if count >= best_count:
            best_count = count
            best_span = " ".join(chunk)
    return best_span.strip()


# ---------------------------------------------------------------------------
# 评估封装
# ---------------------------------------------------------------------------

def evaluate_task1(qs: list[DocVQAQuestion], predictions: list[str],
                   tau: float = 0.5) -> dict:
    gts = [q.answers for q in qs]
    res = anls_dataset(predictions, gts, tau=tau)
    return {"anls": res["anls"], "n": res["n"]}
