"""Tag Head：BIO 序列标注（用于 multi-span / counting）。"""

from __future__ import annotations

import torch
import torch.nn as nn


class TagHead(nn.Module):
    """对每个 token 预测 BIO 标签：0=O, 1=B, 2=I。"""

    def __init__(self, hidden_size: int = 768, n_tags: int = 3, dropout: float = 0.1):
        super().__init__()
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, n_tags),
        )

    def forward(self, token_hidden: torch.Tensor) -> torch.Tensor:
        """返回 [B, L, n_tags] logits。"""
        return self.classifier(token_hidden)