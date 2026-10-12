"""TAT-DQA 数据 collator：把 TATSample 列表转成模型所需的 batch 张量。

设计要点：
- question (max 64 tokens) + [SEP] + context (max 448 tokens)
- 不同 answer_type 走不同 head，其他 head label 填 -100
- 不依赖布局 bbox，纯文本输入（CPU 友好）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import torch
from transformers import AutoTokenizer, PreTrainedTokenizerBase

from data.parse import TATSample


@dataclass
class TATCollatorConfig:
    """collator 配置。"""

    tokenizer_name: str = "roberta-base"
    max_length: int = 512
    question_max_length: int = 64
    context_max_length: int = 448
    padding: str = "max_length"
    truncation: str = "only_second"


class TATCollator:
    """把 list[TATSample] 转成 dict[str, torch.Tensor]。"""

    def __init__(self, config: TATCollatorConfig, tokenizer: PreTrainedTokenizerBase | None = None):
        self.config = config
        if tokenizer is None:
            tokenizer = AutoTokenizer.from_pretrained(config.tokenizer_name)
        self.tokenizer = tokenizer

    def _tokenize_one(self, sample: TATSample) -> dict[str, Any]:
        """对单条样本做 tokenize，并构造各 head 的 label。"""
        question = sample.question
        context = sample.context

        # RoBERTa 的分词
        encoded = self.tokenizer(
            question,
            context,
            max_length=self.config.max_length,
            padding=self.config.padding,
            truncation="only_second",  # 只截断 context
            return_tensors=None,
            return_offsets_mapping=False,
        )

        input_ids = encoded["input_ids"]
        attention_mask = encoded["attention_mask"]
        seq_len = len(input_ids)

        # 找到 context 的 token 起始位置（question + [SEP] 之后）
        # RoBERTa: <s> Q </s> C </s>
        sep_positions = [i for i, tid in enumerate(input_ids) if tid == self.tokenizer.sep_token_id]
        if len(sep_positions) >= 2:
            ctx_start = sep_positions[0] + 1
        else:
            ctx_start = self.config.question_max_length + 2  # <s> + question + </s>

        # 各 head 的 label
        # 默认 -100 表示忽略
        IGNORE = -100

        # 1) type label：单值
        type_label = sample.answer_type_id

        # 2) span start/end：SQuAD-style。begin ≤ end。
        # 若类型不是 span，填 IGNORE
        if sample.answer_type == "span" and isinstance(sample.answer, str):
            span_start, span_end = self._find_span_in_context(
                input_ids, ctx_start, sample.answer
            )
        else:
            span_start, span_end = IGNORE, IGNORE

        # 3) tag labels (BIO)：对 spans/count 类型
        # 0=O, 1=B, 2=I
        tag_labels = [0] * seq_len  # 默认 O
        if sample.answer_type in ("multi-span", "count") and isinstance(sample.answer, list):
            self._mark_bio_tags(input_ids, ctx_start, sample.answer, tag_labels)
        # 非 span 系列时，所有位置都设为 IGNORE 让 loss 跳过
        if sample.answer_type not in ("multi-span", "count"):
            tag_labels = [IGNORE] * seq_len

        # 4) arith_op / arith_count：仅 arithmetic 有效
        arith_op_label = sample.arith_op if sample.answer_type == "arithmetic" else IGNORE
        arith_count_label = sample.arith_count if sample.answer_type == "arithmetic" else IGNORE

        # 5) scale label：所有类型都预测（避免空 label 浪费）
        scale_label = sample.scale_id

        # 6) 数字 token mask：仅 arithmetic 时使用（推理时为操作数指针用）
        is_number_mask = self._mark_number_tokens(input_ids, ctx_start)

        return {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
            "type_label": type_label,
            "span_start_label": span_start,
            "span_end_label": span_end,
            "tag_labels": tag_labels,
            "arith_op_label": arith_op_label,
            "arith_count_label": arith_count_label,
            "scale_label": scale_label,
            "is_number_mask": is_number_mask,
            "seq_len": seq_len,
        }

    def _find_span_in_context(
        self, input_ids: list[int], ctx_start: int, answer_text: str
    ) -> tuple[int, int]:
        """在 context 部分找答案的 token 起止。返回 (start, end)，找不到则 (-100, -100)。

        RoBERTa 等子词分词器对「有前导空格」的 token 会加 Ġ 前缀。
        若 answer 没有前导空格，先尝试加空格后再 tokenize 一次。
        """
        if not answer_text:
            return -100, -100

        candidates: list[str] = [answer_text]
        if not answer_text.startswith(" "):
            candidates.append(" " + answer_text)

        ctx_ids = input_ids[ctx_start:]
        for cand in candidates:
            ans_ids = self.tokenizer.encode(cand, add_special_tokens=False)
            if not ans_ids:
                continue
            n = len(ans_ids)
            for i in range(len(ctx_ids) - n + 1):
                if ctx_ids[i:i + n] == ans_ids:
                    return ctx_start + i, ctx_start + i + n - 1
        return -100, -100

    def _mark_bio_tags(
        self,
        input_ids: list[int],
        ctx_start: int,
        answers: list[str],
        tag_labels: list[int],
    ) -> None:
        """对每个 answer 在 context 中标记 B/I。同 _find_span_in_context 兼容空格前缀。"""
        ctx_ids = input_ids[ctx_start:]
        for ans_text in answers:
            if not ans_text:
                continue
            candidates: list[str] = [ans_text]
            if not ans_text.startswith(" "):
                candidates.append(" " + ans_text)

            matched = False
            for cand in candidates:
                if matched:
                    break
                ans_ids = self.tokenizer.encode(cand, add_special_tokens=False)
                if not ans_ids:
                    continue
                n = len(ans_ids)
                for i in range(len(ctx_ids) - n + 1):
                    if ctx_ids[i:i + n] == ans_ids:
                        s = ctx_start + i
                        e = ctx_start + i + n - 1
                        if s < len(tag_labels):
                            tag_labels[s] = 1  # B
                        for j in range(s + 1, e + 1):
                            if j < len(tag_labels):
                                tag_labels[j] = 2  # I
                        matched = True
                        break

    def _mark_number_tokens(self, input_ids: list[int], ctx_start: int) -> list[int]:
        """标记 context 中的数字 token（启发式：token 是纯数字或以数字开头）。"""
        mask = [0] * len(input_ids)
        for i in range(ctx_start, len(input_ids)):
            tid = input_ids[i]
            tok = self.tokenizer.convert_ids_to_tokens(tid)
            # RoBERTa 的数字常以 "Ġ123" 形式
            stripped = tok.lstrip("Ġ").lstrip("▁")
            if stripped and stripped[0].isdigit():
                mask[i] = 1
        return mask

    def __call__(self, batch: list[TATSample]) -> dict[str, torch.Tensor]:
        """把 batch 转成 dict 张量。"""
        encoded = [self._tokenize_one(s) for s in batch]

        # padding 到 batch 内最大长度
        max_len = max(e["seq_len"] for e in encoded)

        input_ids_list = []
        attn_mask_list = []
        type_labels = []
        span_start_labels = []
        span_end_labels = []
        tag_labels_list = []
        arith_op_labels = []
        arith_count_labels = []
        scale_labels = []
        is_number_mask_list = []

        for e in encoded:
            pad_len = max_len - e["seq_len"]
            input_ids_list.append(e["input_ids"] + [self.tokenizer.pad_token_id] * pad_len)
            attn_mask_list.append(e["attention_mask"] + [0] * pad_len)
            type_labels.append(e["type_label"])
            span_start_labels.append(e["span_start_label"])
            span_end_labels.append(e["span_end_label"])
            # tag 标签 padding 用 IGNORE
            tag_labels_list.append(e["tag_labels"] + [-100] * pad_len)
            arith_op_labels.append(e["arith_op_label"])
            arith_count_labels.append(e["arith_count_label"])
            scale_labels.append(e["scale_label"])
            is_number_mask_list.append(e["is_number_mask"] + [0] * pad_len)

        return {
            "input_ids": torch.tensor(input_ids_list, dtype=torch.long),
            "attention_mask": torch.tensor(attn_mask_list, dtype=torch.long),
            "type_labels": torch.tensor(type_labels, dtype=torch.long),
            "span_start_labels": torch.tensor(span_start_labels, dtype=torch.long),
            "span_end_labels": torch.tensor(span_end_labels, dtype=torch.long),
            "tag_labels": torch.tensor(tag_labels_list, dtype=torch.long),
            "arith_op_labels": torch.tensor(arith_op_labels, dtype=torch.long),
            "arith_count_labels": torch.tensor(arith_count_labels, dtype=torch.long),
            "scale_labels": torch.tensor(scale_labels, dtype=torch.long),
            "is_number_mask": torch.tensor(is_number_mask_list, dtype=torch.float),
        }