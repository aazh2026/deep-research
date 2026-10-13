"""ChartQA 数据加载。

Paper: Masry et al. "ChartQA: A Benchmark for Question Answering about Charts
with Visual and Logical Reasoning" (Findings of ACL 2022)

Dataset: https://huggingface.co/datasets/HuggingFaceM4/ChartQA
- train: 28,299 题（26% 人工 + 74% 模板）
- val:   1,920 题（50% 人工 + 50% 模板）← 主评测
- test:  2,500 题（50% 人工 + 50% 模板）

每题结构：
- image: PIL.Image（图表截图）
- query: str（问题）
- label: List[str]（可接受的答案列表，通常 1 个）
- human_or_machine: 0 = 人工, 1 = 模板

Paper 关键观察：
- 人工问题比模板问题**显著更难**（baseline T5 简单版 ~30% vs 模板 ~80%）
- ~62% 数值答案（需 relaxed/strict Acc 区分）/ ~38% 文本答案
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from datasets import load_dataset


@dataclass
class ChartQAQuestion:
    """ChartQA 一道问题。"""

    uid: str
    query: str
    label: list[str]  # 可接受答案列表
    human_or_machine: int  # 0=human, 1=machine
    answer_type: str  # 'numeric' | 'text'（启发式判断）
    image_size: tuple[int, int] | None = None  # 不存图本身，只记尺寸
    split: str = ""


def _classify_answer(label: str) -> str:
    """简单启发式：能 parse 成 float 视为 numeric。

    处理：
    - 千分位逗号 (1,234)
    - 百分号 (50%)
    - 美元符号 ($100)
    - 负号 (-3.2)
    - 句号 (3.14)
    """
    s = label.strip()
    # 去常见前缀/后缀
    for ch in [",", "$", "%", "£", "€", "°"]:
        s = s.replace(ch, "")
    try:
        float(s)
        return "numeric"
    except (ValueError, TypeError):
        return "text"


def load_split(
    name: str = "val",
    cache_dir: str = "./cache",
) -> list[ChartQAQuestion]:
    """加载一个 split。

    name ∈ {train, val, test}。
    """
    print(f"[data] 加载 ChartQA split={name} ...")
    ds = load_dataset("HuggingFaceM4/ChartQA", split=name, cache_dir=cache_dir)
    out: list[ChartQAQuestion] = []
    for i, row in enumerate(ds):
        label = row.get("label") or [""]
        primary = label[0] if label else ""
        out.append(
            ChartQAQuestion(
                uid=f"{name}-{i:05d}",
                query=row["query"],
                label=list(label),
                human_or_machine=int(row["human_or_machine"]),
                answer_type=_classify_answer(primary),
                image_size=row["image"].size if "image" in row else None,
                split=name,
            )
        )
    print(f"[data]   {name}: {len(out)} 题")
    return out


def stats_summary(qs: list[ChartQAQuestion]) -> dict:
    """按 human/machine × numeric/text 统计。"""
    from collections import Counter

    by_source: Counter = Counter()
    by_type: Counter = Counter()
    by_source_type: Counter = Counter()
    for q in qs:
        src = "human" if q.human_or_machine == 0 else "machine"
        by_source[src] += 1
        by_type[q.answer_type] += 1
        by_source_type[(src, q.answer_type)] += 1
    return {
        "total": len(qs),
        "by_source": dict(by_source),
        "by_answer_type": dict(by_type),
        "by_source_x_type": {f"{s}_{t}": v for (s, t), v in by_source_type.items()},
    }
