"""ChartQA 简单 baseline。

本地无 VLM，无 OCR + GPT 流水线；可跑的「下限」baseline：

1. **Random guess**（按 answer_type 决定猜数字还是文本）
   - numeric: 在 [0, 100] 随机
   - text: 从训练集 top-K 文本答案里随机选
2. **Majority baseline**（每个 split 内统计最常见答案，直接猜）
   - numeric: 训练集所有 numeric 答案的**中位数**
   - text: 训练集所有 text 答案的**众数**

这些 baseline 的价值：
- 验证 metric 实现正确（majority 应该有 ~5-10% Acc）
- 作为「视觉盲」系统的下限锚点
- 对比 paper 报的 VLM baseline 数字，量化「视觉」单独贡献多少

不跑：
- VLM（GPT-4V、Gemini、Qwen-VL 等）
- OCR + LLM 流水线（T5 / TaPas / UniChart 等）
- 任何需要 GPU 的方法
"""

from __future__ import annotations

import random
import re
from collections import Counter
from statistics import median

from src.data_loader import ChartQAQuestion
from src.metrics import is_numeric, to_float


# 数字 token 正则：用于从 text 答案里抽数字做 majority numeric guess
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def compute_majority_predictor(
    qs: list[ChartQAQuestion],
) -> tuple[str, str]:
    """从训练集统计两个 majority predictor。

    返回 (numeric_predictor_str, text_predictor_str)。
    """
    nums: list[float] = []
    texts: Counter[str] = Counter()
    for q in qs:
        for lbl in q.label:
            lbl = lbl.strip()
            if not lbl:
                continue
            if is_numeric(lbl):
                try:
                    nums.append(to_float(lbl))
                except (ValueError, TypeError):
                    pass
            else:
                texts[lbl.lower()] += 1
    num_pred = str(median(nums)) if nums else "0"
    text_pred = texts.most_common(1)[0][0] if texts else "yes"
    return num_pred, text_pred


def majority_predict(
    qs: list[ChartQAQuestion],
    num_pred: str,
    text_pred: str,
) -> list[dict]:
    """对每个 question 返回 majority guess 结果。"""
    out = []
    for q in qs:
        pred = num_pred if q.answer_type == "numeric" else text_pred
        out.append({
            "uid": q.uid,
            "split": q.split,
            "human_or_machine": q.human_or_machine,
            "answer_type": q.answer_type,
            "prediction": pred,
            "gold": q.label[0] if q.label else "",
        })
    return out


def random_predict(
    qs: list[ChartQAQuestion],
    text_vocab: list[str] | None = None,
    num_low: float = 0.0,
    num_high: float = 100.0,
    seed: int = 42,
) -> list[dict]:
    """对每个 question 返回随机猜答案。

    text_vocab: 文本答案候选词表；None 时用 ['yes', 'no', '0', '1']。
    numeric: 在 [num_low, num_high] 随机 uniform。
    """
    rng = random.Random(seed)
    if text_vocab is None:
        text_vocab = ["yes", "no"]
    out = []
    for q in qs:
        if q.answer_type == "numeric":
            pred = f"{rng.uniform(num_low, num_high):.2f}"
        else:
            pred = rng.choice(text_vocab)
        out.append({
            "uid": q.uid,
            "split": q.split,
            "human_or_machine": q.human_or_machine,
            "answer_type": q.answer_type,
            "prediction": pred,
            "gold": q.label[0] if q.label else "",
        })
    return out
