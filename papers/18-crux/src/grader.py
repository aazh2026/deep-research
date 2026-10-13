"""Sub-question 生成 + Grader 函数。

论文原版：sub-questions 由 Llama-3.1-70B 生成；grader G(p, q, I_g) 由
LLM 给 0–5 评分。

复现：sub-questions 用启发式（从 summary 提取关键句子作为子问题本身，
gold info I_g = summary 句子的关键词集合），grader 用 lexical overlap
（passage vs gold info 的 token-level F1 缩放到 0–5）做替代。
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

# 简单停用词（不依赖 nltk corpus 下载）
STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "shall", "can",
    "of", "in", "on", "at", "by", "for", "with", "about", "as", "into",
    "through", "during", "to", "from", "up", "down", "out", "off", "over",
    "under", "again", "further", "then", "once", "here", "there", "when",
    "where", "why", "how", "all", "any", "both", "each", "few", "more",
    "most", "other", "some", "such", "no", "nor", "not", "only", "own",
    "same", "so", "than", "too", "very", "s", "t", "just", "this", "that",
    "these", "those", "i", "you", "he", "she", "it", "we", "they", "what",
    "which", "who", "whom", "whose", "if", "because", "while", "although",
    "since", "until", "before", "after", "above", "below", "between",
    "against", "around", "also",
}

TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def tokenize(text: str, drop_stop: bool = True) -> list[str]:
    """小写 + 简单分词；可选去掉停用词。"""
    toks = [t.lower() for t in TOKEN_RE.findall(text)]
    if drop_stop:
        toks = [t for t in toks if t not in STOPWORDS and len(t) >= 2]
    return toks


def content_tokens(text: str) -> Counter:
    """分词后统计 content token 频次（用作 lexical overlap 比较）。"""
    return Counter(tokenize(text))


def generate_subquestions(
    summary: str,
    n_questions: int = 5,
    gold_info: list[str] | None = None,
) -> list[tuple[str, str]]:
    """启发式 sub-question 生成。

    论文原版：LLM 从 summary 生成 n 个 diverse 问题，每个问题对应一个
    I_g（gold info，是 summary 里的一小段）。

    简化：直接把 summary 的前 n 句作为「子问题」本身（视为简短问句），
    gold info 仍由 split_summary_into_gold_info 提供。每个 (q, I_g) 对
    由 summary 第 i 句 → 第 i 个 gold info 一一对应。
    """
    if gold_info is None:
        sents = re.split(r"(?<=[.!?])\s+", summary.strip())
        gold_info = [s.strip() for s in sents if len(s.strip()) >= 20]

    # 取前 n_questions 句
    pairs: list[tuple[str, str]] = []
    for i, info in enumerate(gold_info[:n_questions]):
        # 子问题：用 content-token 提取关键实体，拼成「what is X / who is X」问句
        toks = tokenize(info, drop_stop=True)
        # 选 3–6 个最长的 token 作为「实体关键词」
        kw = sorted(set(toks), key=lambda x: -len(x))[:6]
        if not kw:
            continue
        # 启发式：取句首 5–8 词作为问题（很多句就是简短陈述，当子问题足够）
        q = info[:80].rstrip(",.;:") + "?"
        pairs.append((q, info))
    return pairs


def grade_passage(
    passage: str,
    gold_info: str,
    scale: int = 5,
) -> int:
    """启发式 grader G(p, q, I_g)。

    论文原版：LLM 给 0–5 评分（5 = highly relevant & complete）。
    简化：用 passage 和 gold_info 的 content-token F1 缩放到 [0, scale]。

    F1 计算：对 token 多集合取交集。归一化：F1 * scale 然后 round。
    """
    p_toks = content_tokens(passage)
    g_toks = content_tokens(gold_info)
    if not g_toks:
        return 0
    # token 级别的 precision / recall
    common = sum((p_toks & g_toks).values())
    if common == 0:
        return 0
    p_sum = sum(p_toks.values())
    g_sum = sum(g_toks.values())
    precision = common / p_sum
    recall = common / g_sum
    if precision + recall == 0:
        return 0
    f1 = 2 * precision * recall / (precision + recall)
    return min(scale, max(0, round(f1 * scale)))


def grade_passages_for_query(
    passages: list[str],
    gold_info: str,
) -> list[int]:
    """对同一 query 的所有 passage 评分。"""
    return [grade_passage(p, gold_info) for p in passages]


def max_grade_for_query(
    passages: list[str],
    gold_info: str,
) -> int:
    """对 query q，返回 max G(p ∈ Z, q, I_g) — 论文里 Coverage 公式用。"""
    if not passages:
        return 0
    return max(grade_passage(p, gold_info) for p in passages)
