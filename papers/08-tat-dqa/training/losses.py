"""MHST 多任务损失。"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F
from dataclasses import dataclass

from models.mhst import MHSTOutput


@dataclass
class LossWeights:
    """各 head 损失的权重。"""

    type: float = 1.0
    span: float = 1.0
    tag: float = 1.0
    arith_op: float = 1.0
    arith_count: float = 0.5
    scale: float = 0.5


def compute_losses(
    output: MHSTOutput,
    batch: dict[str, torch.Tensor],
    weights: LossWeights,
) -> dict[str, torch.Tensor]:
    """计算 6 个 head 的联合损失。"""
    losses = {}

    # 1) type loss（全部样本参与）
    losses["type"] = F.cross_entropy(output.type_logits, batch["type_labels"])

    # 2) span start/end loss（仅 span 类型）
    # 我们用 mask 来标记 span 类型
    is_span = batch["type_labels"] == 0  # [B]
    if is_span.any():
        # 只对 is_span 样本计算
        span_start_logits = output.span_start_logits[is_span]  # [b, L]
        span_end_logits = output.span_end_logits[is_span]
        span_start_labels = batch["span_start_labels"][is_span]
        span_end_labels = batch["span_end_labels"][is_span]
        # 过滤掉 label = -100 的样本
        valid_start = span_start_labels != -100
        valid_end = span_end_labels != -100
        if valid_start.any():
            losses["span_start"] = F.cross_entropy(
                span_start_logits[valid_start], span_start_labels[valid_start]
            )
        if valid_end.any():
            losses["span_end"] = F.cross_entropy(
                span_end_logits[valid_end], span_end_labels[valid_end]
            )

    # 3) tag loss（仅 multi-span / count）
    is_tag = (batch["type_labels"] == 1) | (batch["type_labels"] == 2)
    if is_tag.any():
        tag_logits = output.tag_logits[is_tag]  # [b, L, 3]
        tag_labels = batch["tag_labels"][is_tag]  # [b, L]
        # cross_entropy 已支持 ignore_index=-100
        losses["tag"] = F.cross_entropy(
            tag_logits.reshape(-1, tag_logits.size(-1)),
            tag_labels.reshape(-1),
            ignore_index=-100,
        )

    # 4) arith_op loss（仅 arithmetic）
    is_arith = batch["type_labels"] == 3
    if is_arith.any():
        arith_op_logits = output.arith_op_logits[is_arith]
        arith_op_labels = batch["arith_op_labels"][is_arith]
        valid = arith_op_labels != -100
        if valid.any():
            losses["arith_op"] = F.cross_entropy(
                arith_op_logits[valid], arith_op_labels[valid]
            )
        arith_count_logits = output.arith_count_logits[is_arith]
        arith_count_labels = batch["arith_count_labels"][is_arith]
        # arith_count_labels 是操作数数量，需要 clamp 到 [0, max_count-1]
        clamped = torch.clamp(arith_count_labels, 0, arith_count_logits.size(-1) - 1)
        losses["arith_count"] = F.cross_entropy(arith_count_logits, clamped)

    # 5) scale loss（全部样本参与）
    losses["scale"] = F.cross_entropy(output.scale_logits, batch["scale_labels"])

    # 加权求和
    total = (
        weights.type * losses.get("type", torch.tensor(0.0))
        + weights.span * (losses.get("span_start", torch.tensor(0.0)) + losses.get("span_end", torch.tensor(0.0)))
        + weights.tag * losses.get("tag", torch.tensor(0.0))
        + weights.arith_op * losses.get("arith_op", torch.tensor(0.0))
        + weights.arith_count * losses.get("arith_count", torch.tensor(0.0))
        + weights.scale * losses.get("scale", torch.tensor(0.0))
    )

    losses["total"] = total
    return losses