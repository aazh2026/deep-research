"""LiveMathematicianBench 加载 + 50 题子集。

Paper Table 6：LiveMath = 35 train / 18 val / 124 test, single-step, no tools。
我们因为 compute 限制用 35 train / 10 val / 5 test = 50 题。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datasets import load_dataset


@dataclass
class LiveMathTask:
    """一道 LiveMath 题（MCQ）。"""

    uid: str
    question: str
    options: list[str]
    answer: list[str]  # 多 gold (list)，与 paper 一致
    month: str
    theorem_type: str


def load_livemath_subset(
    n_total: int = 50,
    seed: int = 42,
    cache_dir: str = "./cache",
) -> dict[str, list[LiveMathTask]]:
    """加载 LiveMath 50 题子集，切分为 35/10/5 train/val/test。

    HF: `LiveMathematicianBench/LiveMathematicianBench`（608 train，public）
    """
    print(f"[data] loading LiveMath subset n={n_total} seed={seed} ...")
    ds = load_dataset(
        "LiveMathematicianBench/LiveMathematicianBench",
        split="train",
        cache_dir=cache_dir,
    )

    # shuffle + select n_total
    ds = ds.shuffle(seed=seed).select(range(min(n_total, len(ds))))

    tasks: list[LiveMathTask] = []
    for row in ds:
        mcq = row.get("mcq", {}) or {}
        q_text = mcq.get("question", "")
        correct = mcq.get("correct_choice", "")
        wrong = mcq.get("distractors", []) or []
        # 兼容两种 schema
        if isinstance(mcq.get("choices"), list):
            opts = mcq["choices"]
        else:
            opts = [correct] + list(wrong)
            # 不再依赖顺序，因为 infer 阶段不读位置
        if not q_text or not correct:
            continue
        tasks.append(LiveMathTask(
            uid=str(row.get("no", len(tasks))),
            question=q_text,
            options=opts,
            answer=[correct],
            month=row.get("month", ""),
            theorem_type=row.get("theorem_type", ""),
        ))

    n_train, n_val, n_test = 35, 10, 5
    n_use = min(n_total, n_train + n_val + n_test)
    if len(tasks) < n_use:
        # pad with repetition if necessary
        while len(tasks) < n_use:
            tasks.append(tasks[0])

    train = tasks[:n_train]
    val = tasks[n_train:n_train + n_val]
    test = tasks[n_train + n_val:n_train + n_val + n_test]
    print(f"[data]   train={len(train)} val={len(val)} test={len(test)}")

    return {"train": train, "val": val, "test": test}


def task_to_dict(t: LiveMathTask) -> dict[str, Any]:
    """给 MockLLM 的统一 dict 形式。"""
    return {
        "uid": t.uid,
        "question": t.question,
        "options": t.options,
        "answer": t.answer,
    }
