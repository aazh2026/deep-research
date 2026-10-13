"""InfographicVQA 盲 baseline。

设计动机：
- 没有 OCR 文本（mm-eval/InfographicVQA 不提供 words 字段）
- 不跑 VLM（本地无 GPU）
- 只能做「答案分布 / 启发式」baseline

6 个 baseline：
1. **Majority** —— 全数据集最常出现的答案
2. **Random** —— 按 train 答案分布采样
3. **Type-Majority** —— 按 question_type 分桶，桶内 majority
4. **Numeric-Median** —— numeric 问答中位数
5. **Numeric-Mode** —— numeric 问答案众数
6. **Type-Random** —— 按 question_type 桶内答案分布采样

注意：mm-eval/InfographicVQA 没 OCR words，所以无法做 03/04 那种"lexical over OCR"
baseline。本项目专注于「**纯答案分布**的 baseline 锚定」。
"""

from __future__ import annotations

import re
import random
from collections import Counter, defaultdict
from statistics import median

from .data_loader import InfoVQAQuestion
from .metrics import anls_dataset


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------

NUMBER_RE = re.compile(r"[-+]?\d+\.?\d*")


def is_numeric_answer(s: str) -> bool:
    """判断答案是否纯数字（含小数、负号、百分号）。"""
    s = s.strip().rstrip("%").replace(",", "")
    if not s:
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False


def to_float(s: str) -> float | None:
    s = s.strip().rstrip("%").replace(",", "")
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Baseline 1: 全数据集 Majority
# ---------------------------------------------------------------------------

def compute_majority_answer(qs: list[InfoVQAQuestion]) -> str:
    c = Counter()
    for q in qs:
        for a in q.answers:
            c[a] += 1
    return c.most_common(1)[0][0] if c else ""


def majority_predict(qs: list[InfoVQAQuestion], majority: str) -> list[str]:
    return [majority] * len(qs)


# ---------------------------------------------------------------------------
# Baseline 2: Random（按 train 答案分布采样）
# ---------------------------------------------------------------------------

def compute_random_pool(qs: list[InfoVQAQuestion]) -> list[tuple[str, float]]:
    c = Counter()
    for q in qs:
        for a in q.answers:
            c[a] += 1
    total = sum(c.values())
    if total == 0:
        return [("", 1.0)]
    return [(ans, cnt / total) for ans, cnt in c.items()]


def random_predict(qs: list[InfoVQAQuestion],
                   pool: list[tuple[str, float]],
                   seed: int = 42) -> list[str]:
    rng = random.Random(seed)
    if not pool:
        return [""] * len(qs)
    answers = [a for a, _ in pool]
    weights = [w for _, w in pool]
    return [rng.choices(answers, weights=weights, k=1)[0] for _ in qs]


# ---------------------------------------------------------------------------
# Baseline 3: Type-Majority（按 question_type 分桶 majority）
# ---------------------------------------------------------------------------

def compute_type_majority(qs: list[InfoVQAQuestion]) -> dict[str, str]:
    by_type: dict[str, Counter] = defaultdict(Counter)
    for q in qs:
        for a in q.answers:
            by_type[q.question_type][a] += 1
    return {t: c.most_common(1)[0][0] if c else "" for t, c in by_type.items()}


def type_majority_predict(qs: list[InfoVQAQuestion],
                          type_majority: dict[str, str]) -> list[str]:
    return [type_majority.get(q.question_type, "") for q in qs]


# ---------------------------------------------------------------------------
# Baseline 4: Numeric-Median / Numeric-Mode
# ---------------------------------------------------------------------------

def compute_numeric_stats(qs: list[InfoVQAQuestion]) -> dict:
    """从所有 numeric 题答案里抽数字，计算中位数与众数。

    返回 {"median": float, "mode": str}
    """
    nums = []
    str_counts: Counter = Counter()
    for q in qs:
        if q.question_type != "numeric":
            continue
        for a in q.answers:
            str_counts[a] += 1
            v = to_float(a)
            if v is not None:
                nums.append(v)
    if not nums:
        return {"median": 0.0, "mode": "0"}
    return {
        "median": median(nums),
        "mode": str_counts.most_common(1)[0][0] if str_counts else "0",
    }


def numeric_median_predict(qs: list[InfoVQAQuestion], median_val: float) -> list[str]:
    out = []
    for q in qs:
        if q.question_type == "numeric":
            # 整数化（如 7.0 → 7）
            v = median_val
            if v == int(v):
                out.append(str(int(v)))
            else:
                out.append(f"{v:g}")
        else:
            # 非 numeric：返回 0（不当 majority 用）
            out.append("0")
    return out


def numeric_mode_predict(qs: list[InfoVQAQuestion], mode_str: str) -> list[str]:
    out = []
    for q in qs:
        if q.question_type == "numeric":
            out.append(mode_str)
        else:
            out.append("0")
    return out


# ---------------------------------------------------------------------------
# 评估封装
# ---------------------------------------------------------------------------

def evaluate_baseline(qs: list[InfoVQAQuestion], predictions: list[str],
                      tau: float = 0.5) -> dict:
    gts = [q.answers for q in qs]
    res = anls_dataset(predictions, gts, tau=tau)
    return {"anls": res["anls"], "n": res["n"]}
