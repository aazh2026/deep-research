"""MHST 主模型：编码器 + 4 个多头预测器。"""

from __future__ import annotations

from dataclasses import dataclass

import torch
import torch.nn as nn

from models.encoder import TextEncoder
from models.heads import ArithHead, SpanHead, TagHead, TypeHead


@dataclass
class MHSTOutput:
    """模型 forward 输出。"""

    type_logits: torch.Tensor           # [B, 4]
    span_start_logits: torch.Tensor     # [B, L]
    span_end_logits: torch.Tensor       # [B, L]
    tag_logits: torch.Tensor            # [B, L, 3]
    arith_op_logits: torch.Tensor       # [B, 4]
    arith_count_logits: torch.Tensor    # [B, max_count]
    scale_logits: torch.Tensor          # [B, 5]


class MHSTModel(nn.Module):
    """MHST 主模型。"""

    def __init__(
        self,
        backbone_name: str = "roberta-base",
        dropout: float = 0.1,
        n_types: int = 4,
        n_tags: int = 3,
        n_ops: int = 4,
        n_scales: int = 5,
        max_arith_count: int = 6,
        cache_dir: str | None = None,
    ):
        super().__init__()
        self.encoder = TextEncoder(backbone_name=backbone_name, cache_dir=cache_dir)
        h = self.encoder.hidden_size

        self.dropout = nn.Dropout(dropout)
        self.type_head = TypeHead(hidden_size=h, n_types=n_types, dropout=dropout)
        self.span_head = SpanHead(hidden_size=h, dropout=dropout)
        self.tag_head = TagHead(hidden_size=h, n_tags=n_tags, dropout=dropout)
        self.arith_head = ArithHead(
            hidden_size=h, n_ops=n_ops, max_count=max_arith_count, dropout=dropout
        )
        self.scale_head = nn.Sequential(
            nn.Linear(h, h),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(h, n_scales),
        )

    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
    ) -> MHSTOutput:
        """前向传播。"""
        cls_h, tok_h = self.encoder(input_ids, attention_mask)
        cls_h_d = self.dropout(cls_h)
        tok_h_d = self.dropout(tok_h)

        type_logits = self.type_head(cls_h_d)
        span_start_logits, span_end_logits = self.span_head(tok_h_d)
        tag_logits = self.tag_head(tok_h_d)
        arith_op_logits, arith_count_logits = self.arith_head(cls_h_d)
        scale_logits = self.scale_head(cls_h_d)

        return MHSTOutput(
            type_logits=type_logits,
            span_start_logits=span_start_logits,
            span_end_logits=span_end_logits,
            tag_logits=tag_logits,
            arith_op_logits=arith_op_logits,
            arith_count_logits=arith_count_logits,
            scale_logits=scale_logits,
        )

    def num_parameters(self, only_trainable: bool = False) -> int:
        return sum(
            p.numel() for p in self.parameters() if not only_trainable or p.requires_grad
        )