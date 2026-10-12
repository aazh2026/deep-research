"""Arithmetic Head：算术推理（GTS 替代方案）。

论文 GTS 用二叉树 + 自回归 beam search，CPU 太慢。
本实现做以下简化：
- 预测主运算符（4 类：+ - * /）
- 预测操作数数量（1..max_count 桶）
- 用操作数指针从输入数字 token 中选

推理时由 `utils/decode.py` 的 `safe_eval_expression` 拼成 infix 算式。
"""

from __future__ import annotations

import torch
import torch.nn as nn


class ArithHead(nn.Module):
    """算术推理 head。"""

    def __init__(
        self,
        hidden_size: int = 768,
        n_ops: int = 4,
        max_count: int = 6,  # 最多 6 个操作数
        dropout: float = 0.1,
    ):
        super().__init__()
        self.n_ops = n_ops
        self.max_count = max_count

        # 主运算符
        self.op_classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, n_ops),
        )
        # 操作数数量（桶分类）
        self.count_classifier = nn.Sequential(
            nn.Linear(hidden_size, hidden_size),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_size, max_count),
        )

    def forward(self, cls_h: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """返回 (op_logits [B, n_ops], count_logits [B, max_count])。"""
        op_logits = self.op_classifier(cls_h)
        count_logits = self.count_classifier(cls_h)
        return op_logits, count_logits