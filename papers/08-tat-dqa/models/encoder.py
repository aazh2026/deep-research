"""文本编码器封装。

默认 RoBERTa-base，提取 [CLS] 与 token-level hidden states。
可通过 config.backbone 替换为其他 AutoModel。
"""

from __future__ import annotations

import torch
import torch.nn as nn
from transformers import AutoConfig, AutoModel


class TextEncoder(nn.Module):
    """基于 HuggingFace AutoModel 的文本编码器。"""

    def __init__(self, backbone_name: str = "roberta-base", cache_dir: str | None = None):
        super().__init__()
        self.backbone_name = backbone_name
        config = AutoConfig.from_pretrained(backbone_name, cache_dir=cache_dir)
        self.hidden_size = config.hidden_size
        self.model = AutoModel.from_pretrained(backbone_name, cache_dir=cache_dir)

    def forward(
        self, input_ids: torch.Tensor, attention_mask: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """返回 (cls_hidden [B, H], token_hidden [B, L, H])。"""
        outputs = self.model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            return_dict=True,
        )
        last_hidden = outputs.last_hidden_state  # [B, L, H]
        cls_hidden = last_hidden[:, 0]  # RoBERTa 的 <s> 在首位
        return cls_hidden, last_hidden