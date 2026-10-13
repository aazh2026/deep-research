"""ChartQA 答案评估：relaxed / strict accuracy。

论文 Section 4.1 的指标定义：
- **Strict Acc**：预测必须与 gold 字符串完全一致（lowercase + strip）
- **Relaxed Acc**（数值题）：预测 parse 成 float，与 gold float 的相对误差
  - 5% tolerance（"within 5% of gold"）
  - 若 gold < 1，则绝对误差 < 0.02
  - 若 gold >= 100，则绝对误差 < 1
  - 等价实现：max(0.05 * gold, 0.02 if gold < 1 else 1.0)
- **Relaxed Acc**（文本题）：和 strict 一样

实测：ChartQA 论文的数值题评估逻辑（来自官方 evaluation script）：
```python
def relaxed_correctness(target, prediction):
    if numeric_answer(target) and numeric_answer(prediction):
        return isclose_relaxed(float(target), float(prediction))
    return target.lower() == prediction.lower()
```
其中 isclose_relaxed 用 5% / 0.02 / 1.0 三档容差。
"""

from __future__ import annotations

import re

NUM_RE = re.compile(r"^-?[\d,]+(?:\.\d+)?%?$")


def is_numeric(s: str) -> bool:
    """判断字符串是否可解析为数字（含千分位 + 百分号）。"""
    if not s:
        return False
    s = s.strip()
    # 移除常见前缀/后缀
    for ch in [",", "$", "%", "£", "€"]:
        s = s.replace(ch, "")
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def to_float(s: str) -> float:
    """字符串 → float。已确认 numeric。"""
    s = s.strip()
    for ch in [",", "$", "%", "£", "€"]:
        s = s.replace(ch, "")
    return float(s)


def relaxed_numeric_match(pred: float, gold: float,
                          rel_tol: float = 0.05, abs_tol: float = 0.5) -> bool:
    """ChartQA 官方 tolerance（来自 vis-nlp/ChartQA Models/ChartBERT/utils.py）：

    ``abs(a - b) <= max(rel_tol * max(|a|, |b|), abs_tol)``

    默认 rel_tol=0.05（5%），abs_tol=0.5。

    例子：
    - gold=100, pred=95  → |100-95|=5 ≤ max(0.05*100, 0.5) = 5 ✓（boundary）
    - gold=100, pred=94  → 6 > 5 ✗
    - gold=0, pred=0.4   → 0.4 ≤ max(0, 0.5) = 0.5 ✓
    - gold=-100, pred=-95 → 5 ≤ max(5, 0.5) = 5 ✓
    """
    return abs(pred - gold) <= max(rel_tol * max(abs(pred), abs(gold)), abs_tol)


def is_correct(prediction: str, gold_list: list[str], mode: str = "relaxed") -> bool:
    """单题判定：pred 是否与 gold_list 任一项匹配。

    mode ∈ {"relaxed", "strict"}。
    """
    if not prediction:
        return False
    pred = prediction.strip()
    if not pred:
        return False

    for gold in gold_list:
        gold = gold.strip()
        if not gold:
            continue
        # 数值题 → relaxed 比较
        if is_numeric(gold) and is_numeric(pred) and mode == "relaxed":
            try:
                if relaxed_numeric_match(to_float(pred), to_float(gold)):
                    return True
            except (ValueError, TypeError):
                pass
        # strict / 文本题 → lowercase 字符串比较
        if pred.lower() == gold.lower():
            return True
    return False
