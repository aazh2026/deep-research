"""Span Head：SQuAD-style start/end 位置预测。"""

from __future__ import annotations

import torch
import torch.nn as nn


class SpanHead(nn.Module):
    """对每个 token 预测 start/end 概率（SQuAD 风格）。"""

    def __init__(self, hidden_size: int = 768, dropout: float = 0.1):
        super().__init__()
        self.start_proj = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 1),
        )
        self.end_proj = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, 1),
        )

    def forward(self, token_hidden: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """返回 (start_logits, end_logits)，形状 [B, L]。"""
        start = self.start_proj(token_hidden).squeeze(-1)  # [B, L]
        end = self.end_proj(token_hidden).squeeze(-1)
        return start, end