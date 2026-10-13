"""Multi-News 数据加载 + passage 切分。

CRUX-Multi-News 原版：100 查询（来自 test split），每查询对应多文档
（来自 Multi-News 原始 articles，文档先按句子切分 passage），共 ~500K passage。

复现策略：取 Multi-News test split 的 50 个 sample（CPU 限制），把每个 sample
的 `document` 字段按 `|||||` 拆分得多个 source articles，再按段落/句子切
成 passage 集合 Z。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from datasets import load_dataset


@dataclass
class CRUXSample:
    """一个 CRUX 样本（对应 Multi-News 一个 sample）。"""

    uid: str
    summary: str  # 人工摘要
    passages: list[str]  # 候选 passage 集合 Z
    # gold 信息片段（用于 grader）：把 summary 切为「句子级」信息单元
    gold_info: list[str]


def split_passages(article: str, min_len: int = 30, max_len: int = 400) -> list[str]:
    """把一篇文章切成 passage 列表（CRUX 把 doc 视为长 passage 集合）。

    论文原版：每个 passage 平均 109 tokens。我们按段落 → 句子切，最后控
    制长度区间。
    """
    # 先按段落切
    paragraphs = re.split(r"\n\s*\n", article.strip())
    out: list[str] = []
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        # 段落已经够短就直接保留
        if min_len <= len(p) <= max_len:
            out.append(p)
            continue
        # 否则按句子切
        sents = re.split(r"(?<=[.!?])\s+", p)
        buf = ""
        for s in sents:
            s = s.strip()
            if not s:
                continue
            if len(buf) + len(s) + 1 <= max_len:
                buf = (buf + " " + s).strip()
            else:
                if len(buf) >= min_len:
                    out.append(buf)
                buf = s
        if len(buf) >= min_len:
            out.append(buf)
    return out


def split_summary_into_gold_info(summary: str, min_len: int = 20) -> list[str]:
    """把 summary 按句子切成 gold 信息单元 I_g。

    论文原版：每个 sub-question 都对应 summary 里一段文字作为 ground truth。
    我们把 summary 按句子切，每句作为一个 gold_info 单元。
    """
    sents = re.split(r"(?<=[.!?])\s+", summary.strip())
    return [s.strip() for s in sents if len(s.strip()) >= min_len]


def load_crux_samples(
    n_queries: int = 50,
    cache_dir: str = "./cache",
    min_passage_len: int = 30,
    max_passage_len: int = 400,
) -> list[CRUXSample]:
    """从 Multi-News test 加载 n_queries 个 CRUX 样本。

    数据源：Awesome075/multi_news_parquet（原 alexfabbri/multi_news
    的 Parquet 修复版，与最新 datasets 库兼容）。
    """
    print(f"[data] 加载 Multi-News test split，n_queries={n_queries}...")
    ds = load_dataset(
        "Awesome075/multi_news_parquet",
        split="test",
        cache_dir=cache_dir,
    )
    samples: list[CRUXSample] = []
    n = min(n_queries, len(ds))
    for i in range(n):
        doc = ds[i]["document"]
        summary = ds[i]["summary"]

        # 把 `document` 按 `|||||` 拆成多篇 article
        articles = doc.split("|||||")

        # 每篇 article 切 passage
        passages: list[str] = []
        for a in articles:
            passages.extend(split_passages(a, min_passage_len, max_passage_len))

        # gold info：summary 切句
        gold_info = split_summary_into_gold_info(summary)

        if len(passages) < 5 or len(gold_info) < 2:
            # 跳过太短/没结构的样本
            continue

        samples.append(
            CRUXSample(
                uid=f"mn-{i:04d}",
                summary=summary,
                passages=passages,
                gold_info=gold_info,
            )
        )

    print(
        f"[data] 加载完成：{len(samples)} 样本；"
        f"平均 passages/样本={sum(len(s.passages) for s in samples) / max(len(samples), 1):.1f}；"
        f"平均 gold_info/样本={sum(len(s.gold_info) for s in samples) / max(len(samples), 1):.1f}"
    )
    return samples
