"""MHST 评估指标：EM + scale-aware macro-F1。

参考 TAT-DQA 论文：
- EM: Exact Match（考虑 scale 转换）
- F1: macro-F1，只在「预测数值 × 预测 scale」== 「真值数值 × 真值 scale」时计 1
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict

from utils.decode import ID2ANSWER_TYPE, ID2OP, ID2SCALE, safe_eval_expression


# Scale 因子
SCALE_FACTOR = {
    "": 1.0,
    "thousand": 1e3,
    "million": 1e6,
    "billion": 1e9,
    "percent": 1.0,  # percent 单独处理（百分比本身）
}


def _normalize_text(s: str) -> str:
    """文本规整：去除空白、转小写。"""
    if s is None:
        return ""
    return re.sub(r"\s+", "", str(s)).strip().lower()


def _to_number(s: Any) -> float | None:
    """字符串 → 数字。失败返回 None。"""
    if s is None:
        return None
    if isinstance(s, (int, float)):
        return float(s)
    try:
        # 处理 "1,234.56" 这种带千分位的
        cleaned = str(s).replace(",", "").replace("$", "").strip()
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _apply_scale(value: float, scale: str) -> float:
    """把带 scale 的数值转换为绝对值。"""
    factor = SCALE_FACTOR.get(scale, 1.0)
    return value * factor


def compute_em_one(pred: Any, gold: Any, scale: str = "") -> bool:
    """单条 EM 判断。

    Args:
        pred: 模型预测。数字+scale 表示「相对量」（如 100 million）。
        gold: 真值，已是绝对量。
        scale: 仅作用于 pred。
    """
    # 数字答案
    g_num = _to_number(gold)
    if g_num is not None:
        p_num = _to_number(pred)
        if p_num is None:
            return False
        try:
            # scale 只应用于 pred（gold 已是绝对量）
            p_abs = _apply_scale(p_num, scale)
            g_abs = float(g_num)
            # 容差比较（浮点）
            if abs(g_abs - p_abs) < max(1e-3, abs(g_abs) * 1e-3):
                return True
            return False
        except (ValueError, TypeError):
            return False

    # 文本答案
    if isinstance(gold, list):
        if not isinstance(pred, list):
            return False
        return sorted([_normalize_text(x) for x in gold]) == sorted(
            [_normalize_text(x) for x in pred]
        )

    return _normalize_text(pred) == _normalize_text(gold)


def compute_f1_one(pred: Any, gold: Any, scale: str = "") -> float:
    """单条 F1（0 或 1，因为 macro-F1 阈值严格）。"""
    # 数字答案：scale 仅作用于 pred
    g_num = _to_number(gold)
    if g_num is not None:
        p_num = _to_number(pred)
        if p_num is None:
            return 0.0
        try:
            p_abs = _apply_scale(p_num, scale)
            g_abs = float(g_num)
            if abs(g_abs - p_abs) < max(1e-3, abs(g_abs) * 1e-3):
                return 1.0
            return 0.0
        except (ValueError, TypeError):
            return 0.0

    # 文本答案：token-level F1
    if isinstance(gold, list):
        # set-level F1
        if not isinstance(pred, list):
            pred = [pred]
        gold_set = set(_normalize_text(x) for x in gold if x)
        pred_set = set(_normalize_text(x) for x in pred if x)
        if not gold_set and not pred_set:
            return 1.0
        if not gold_set or not pred_set:
            return 0.0
        tp = len(gold_set & pred_set)
        if tp == 0:
            return 0.0
        precision = tp / len(pred_set)
        recall = tp / len(gold_set)
        return 2 * precision * recall / (precision + recall)

    # 单文本：全等即 1
    return 1.0 if _normalize_text(pred) == _normalize_text(gold) else 0.0


def compute_metrics(
    preds: list[Any],
    golds: list[Any],
    scales: list[str],
    types: list[str],
) -> dict:
    """批量计算 EM 和 F1，按 answer_type 分桶。"""
    n = len(preds)
    em_total = 0.0
    f1_total = 0.0

    by_type_em: dict[str, list[float]] = defaultdict(list)
    by_type_f1: dict[str, list[float]] = defaultdict(list)

    for p, g, s, t in zip(preds, golds, scales, types):
        em = float(compute_em_one(p, g, s))
        f1 = compute_f1_one(p, g, s)
        em_total += em
        f1_total += f1
        by_type_em[t].append(em)
        by_type_f1[t].append(f1)

    overall = {
        "EM": em_total / max(n, 1),
        "F1": f1_total / max(n, 1),
        "n": n,
    }
    per_type = {}
    for t in ID2ANSWER_TYPE.values():
        em_list = by_type_em.get(t, [])
        f1_list = by_type_f1.get(t, [])
        if em_list:
            per_type[t] = {
                "EM": sum(em_list) / len(em_list),
                "F1": sum(f1_list) / len(f1_list),
                "n": len(em_list),
            }
        else:
            per_type[t] = {"EM": 0.0, "F1": 0.0, "n": 0}

    return {"overall": overall, "per_type": per_type}


def decode_predictions(
    batch: dict,
    output,
    tokenizer,
    id2scale: dict[int, str],
    id2op: dict[int, str],
    id2type: dict[int, str],
    n_max: int = 5,
) -> list[Any]:
    """把模型输出解码为最终答案列表。"""
    import torch

    type_preds = output.type_logits.argmax(dim=-1).cpu().tolist()  # [B]
    scale_preds = output.scale_logits.argmax(dim=-1).cpu().tolist()  # [B]
    arith_op_preds = output.arith_op_logits.argmax(dim=-1).cpu().tolist()
    arith_count_preds = output.arith_count_logits.argmax(dim=-1).cpu().tolist()

    # Span
    span_start_preds = output.span_start_logits.argmax(dim=-1).cpu().tolist()
    span_end_preds = output.span_end_logits.argmax(dim=-1).cpu().tolist()

    # Tag (BIO)
    tag_preds = output.tag_logits.argmax(dim=-1).cpu().tolist()  # [B, L]

    input_ids = batch["input_ids"].cpu().tolist()  # [B, L]
    is_number_mask = batch["is_number_mask"].cpu().tolist()  # [B, L]

    B = len(type_preds)
    decoded = []

    for i in range(B):
        t_id = type_preds[i]
        t_name = id2type[t_id]
        scale_name = id2scale.get(scale_preds[i], "")

        if t_name == "span":
            s = span_start_preds[i]
            e = span_end_preds[i]
            if s > e:
                s, e = e, s
            tokens = input_ids[i][s:e + 1]
            text = tokenizer.decode(tokens, skip_special_tokens=True)
            decoded.append(text.strip())

        elif t_name == "multi-span":
            # 从 BIO 标签收集所有 span
            tags = tag_preds[i]
            spans = []
            current = []
            for j, tag in enumerate(tags):
                if tag == 1:  # B
                    if current:
                        spans.append(current)
                        current = []
                    current = [j]
                elif tag == 2:  # I
                    if current:
                        current.append(j)
                else:
                    if current:
                        spans.append(current)
                        current = []
            if current:
                spans.append(current)
            # 转文本
            texts = []
            for sp in spans:
                tokens = input_ids[i][sp[0]:sp[-1] + 1]
                texts.append(tokenizer.decode(tokens, skip_special_tokens=True).strip())
            decoded.append(texts)

        elif t_name == "count":
            # 数 BIO 中 B 的数量
            tags = tag_preds[i]
            count = sum(1 for tag in tags if tag == 1)
            decoded.append(int(count))

        elif t_name == "arithmetic":
            # 简化版：从输入数字 token 中提取最多 arith_count_preds 个数字，
            # 用 arith_op_preds 连接
            op = id2op.get(arith_op_preds[i], "+")
            n_nums = arith_count_preds[i] + 1  # count 是桶 0..max_count-1，对应 1..max_count
            num_mask = is_number_mask[i]
            num_positions = [j for j, m in enumerate(num_mask) if m == 1]
            # 取前 n_nums 个
            chosen = num_positions[:n_nums]
            # 拼接算式
            numbers = []
            for j in chosen:
                tok = tokenizer.convert_ids_to_tokens(input_ids[i][j])
                tok_clean = tok.lstrip("Ġ").lstrip("▁")
                if tok_clean:
                    numbers.append(tok_clean)
            if not numbers:
                decoded.append(0)
            elif len(numbers) == 1:
                decoded.append(numbers[0])
            else:
                expr = op.join(numbers)
                result = safe_eval_expression(expr)
                if result is None:
                    decoded.append("INVALID")
                else:
                    # 应用 scale
                    if scale_name == "thousand":
                        result *= 1000
                    elif scale_name == "million":
                        result *= 1e6
                    elif scale_name == "billion":
                        result *= 1e9
                    decoded.append(result)
        else:
            decoded.append("")

    return decoded