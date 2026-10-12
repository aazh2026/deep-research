"""算式解码与安全执行。

TAT-DQA 中 arithmetic 类型有 `derivation` 字段，例如 "(55 + 50) / 1000"。
需要规范化后用 numexpr 计算，避免直接 `eval` 的安全风险。
"""

import re
from typing import Optional

import numexpr as ne


# 仅保留数字、加减乘除、括号、小数点、空格
_SAFE_EXPR_RE = re.compile(r"[^0-9+\-*/().\s]")


def sanitize_expression(expr: str) -> str:
    """规整算式字符串，只保留安全字符。"""
    if expr is None:
        return ""
    expr = str(expr).strip()
    # 替换中文括号、运算符
    expr = expr.replace("（", "(").replace("）", ")")
    expr = expr.replace("×", "*").replace("÷", "/").replace("−", "-")
    # 移除不安全字符
    expr = _SAFE_EXPR_RE.sub("", expr)
    # 移除多余空白
    expr = re.sub(r"\s+", " ", expr).strip()
    return expr


def safe_eval_expression(expr: str) -> Optional[float]:
    """用 numexpr 计算规整后的算式；失败返回 None。"""
    cleaned = sanitize_expression(expr)
    if not cleaned:
        return None
    # 必须至少含一个数字和一个运算符（否则没意义）
    if not re.search(r"\d", cleaned):
        return None
    try:
        result = ne.evaluate(cleaned)
        result = float(result)
        # 检查是否为有限数
        if result != result or result in (float("inf"), float("-inf")):
            return None
        return result
    except Exception:
        return None


def parse_derivation(derivation: str) -> dict:
    """从原始 derivation 字段提取算式信息。"""
    if not derivation:
        return {"expr": "", "n_ops": 0, "n_numbers": 0}

    cleaned = sanitize_expression(derivation)
    n_ops = sum(1 for c in cleaned if c in "+-*/")
    # 数字计数：粗略以数字 token 计
    n_numbers = len(re.findall(r"\d+\.?\d*", cleaned))
    return {"expr": cleaned, "n_ops": n_ops, "n_numbers": n_numbers}


# 操作符 token id 映射（与 ArithHead 约定一致）
OP2ID = {"+": 0, "-": 1, "*": 2, "/": 3}
ID2OP = {v: k for k, v in OP2ID.items()}

# Scale 映射
SCALE2ID = {
    "": 0,
    "none": 0,
    "thousand": 1,
    "thousands": 1,
    "million": 2,
    "millions": 2,
    "billion": 3,
    "billions": 3,
    "percent": 4,
    "%": 4,
}
ID2SCALE = {v: k for k, v in SCALE2ID.items() if k != "none" and k != "" and k != "%"}

# Answer type 映射
ANSWER_TYPE2ID = {"span": 0, "multi-span": 1, "count": 2, "arithmetic": 3}
ID2ANSWER_TYPE = {v: k for k, v in ANSWER_TYPE2ID.items()}