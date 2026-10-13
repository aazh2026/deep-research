"""SynthDocBench 数据加载。

Paper: Verma et al. "SynthDocBench: Controlled Benchmark for Long-Context
Visual Document Understanding" (COLM 2026, arXiv 2607.10400)

Dataset: https://huggingface.co/datasets/ServiceNow-AI/SynthDocBench
- 3 个 question family（v1）：chart_reading (171), complex_multi-hop (171),
  cross_modal (171)。共 513 问。
- 3 个 v2 子集：chart_v2 (426), complex_v2 (426), cross_modal_v2 (423)。约 1275 问。
- 全部问题都带 difficulty (1-5)、question_type、category 等元数据
- 真实 PDF 在 pdfs/ 目录下，每个 ~2 MB；本次只下载用到的那部分
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from datasets import load_dataset


@dataclass
class SDBQuestion:
    """SynthDocBench 一道问题。"""

    uid: str
    pdf_filename: str
    topic: str
    question: str
    answer: str
    difficulty: int  # 1-5
    question_type: str
    category: str | None
    # 元数据
    figure_number: int | None = None
    chart_title: str | None = None
    required_facts: list | None = None
    required_text_facts: list | None = None
    subset: str = ""  # chart / complex / cross_modal / *_v2


def _normalize_category(cat: str | None) -> str | None:
    """规范化 category 字符串（v1 / v2 大小写不一致）。"""
    if not cat:
        return None
    return cat.lower().replace("_", " ")


def load_subset(name: str = "chart", cache_dir: str = "./cache") -> list[SDBQuestion]:
    """加载单个 subset。name ∈ {chart, complex, cross_modal, *_v2}。"""
    print(f"[data] 加载 subset={name} ...")
    ds = load_dataset(
        "ServiceNow-AI/SynthDocBench",
        name,
        split="train",
        cache_dir=cache_dir,
    )
    out: list[SDBQuestion] = []
    for i, row in enumerate(ds):
        out.append(
            SDBQuestion(
                uid=f"{name}-{i:04d}",
                pdf_filename=row.get("pdf_filename", ""),
                topic=row.get("topic", ""),
                question=row["question"],
                answer=row["answer"],
                difficulty=int(row["difficulty"]),
                question_type=row.get("question_type", ""),
                category=_normalize_category(row.get("category")),
                figure_number=row.get("figure_number"),
                chart_title=row.get("chart_title"),
                required_facts=row.get("required_facts"),
                required_text_facts=row.get("required_text_facts"),
                subset=name,
            )
        )
    print(f"[data]   {name}: {len(out)} 问")
    return out


def load_all(cache_dir: str = "./cache") -> list[SDBQuestion]:
    """加载全部 6 个 subset。"""
    all_qs: list[SDBQuestion] = []
    for name in ["chart", "complex", "cross_modal",
                 "chart_v2", "complex_v2", "cross_modal_v2"]:
        try:
            all_qs.extend(load_subset(name, cache_dir))
        except Exception as e:
            print(f"[data] 加载 {name} 失败: {e}")
    print(f"[data] 全部: {len(all_qs)} 问")
    return all_qs


def stats_summary(qs: list[SDBQuestion]) -> dict:
    """按 subset × difficulty 统计。"""
    from collections import Counter
    by_subset_diff: dict[str, Counter] = {}
    by_subset: Counter = Counter()
    for q in qs:
        by_subset[q.subset] += 1
        by_subset_diff.setdefault(q.subset, Counter())[q.difficulty] += 1
    return {
        "total": len(qs),
        "by_subset": dict(by_subset),
        "by_subset_difficulty": {
            k: dict(v) for k, v in by_subset_diff.items()
        },
    }
