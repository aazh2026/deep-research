"""Type Head：4 分类（Span / Multi-Span / Count / Arithmetic）。"""

from __future__ import annotations

import torch
import torch.nn as nn


class TypeHead(nn.Module):
    """[CLS] hidden → 4 类答案类型。"""

    def __init__(self, hidden_size: int = 768, n_types: int = 4, dropout: float = 0.1):
        super().__init__()
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, n_types),
        )

    def forward(self, cls_hidden: torch.Tensor) -> torch.Tensor:
        """返回 [B, n_types] logits。"""
        return self.classifier(cls_hidden)