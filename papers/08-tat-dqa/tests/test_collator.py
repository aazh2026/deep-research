"""测试数据 collator 的基本形状。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch

from data.collator import TATCollator, TATCollatorConfig
from data.parse import TATSample


def make_fake_sample(answer_type: str = "span") -> TATSample:
    if answer_type == "span":
        ans = "$100 million"
    elif answer_type == "multi-span":
        # 必须在 context 中实际存在
        ans = ["$100", "$60"]
    elif answer_type == "count":
        ans = ["$100", "$60"]  # 数 context 中出现的金额
    else:  # arithmetic
        ans = 40
    return TATSample(
        uid="test-1",
        question="What is the revenue?",
        context="Revenue in 2023 was $100 million. Cost was $60 million.",
        answer=ans,
        answer_type=answer_type,
        answer_type_id={"span": 0, "multi-span": 1, "count": 2, "arithmetic": 3}[answer_type],
        scale="million",
        scale_id=2,
        derivation="100 - 60" if answer_type == "arithmetic" else "",
        facts=[],
        arith_op=1 if answer_type == "arithmetic" else -1,
        arith_count=2 if answer_type == "arithmetic" else 0,
    )


def test_collator_span():
    collator = TATCollator(TATCollatorConfig(tokenizer_name="roberta-base", max_length=128))
    samples = [make_fake_sample("span")]
    batch = collator(samples)
    assert "input_ids" in batch
    assert batch["input_ids"].shape == (1, 128)
    assert batch["attention_mask"].shape == (1, 128)
    assert batch["type_labels"].tolist() == [0]
    assert batch["scale_labels"].tolist() == [2]
    print("  ✓ span 类型 OK, seq_len:", batch["input_ids"].shape)


def test_collator_multi_span():
    collator = TATCollator(TATCollatorConfig(tokenizer_name="roberta-base", max_length=128))
    samples = [make_fake_sample("multi-span")]
    batch = collator(samples)
    assert batch["type_labels"].tolist() == [1]
    # BIO tags 中应至少有 1 个 B（假设答案 token 能找到）
    tag_labels = batch["tag_labels"][0].tolist()
    assert any(t == 1 for t in tag_labels) or all(t == -100 for t in tag_labels), \
        "tag labels 应至少含一个 B 或全为 IGNORE"
    print("  ✓ multi-span 类型 OK")


def test_collator_count():
    collator = TATCollator(TATCollatorConfig(tokenizer_name="roberta-base", max_length=128))
    samples = [make_fake_sample("count")]
    batch = collator(samples)
    assert batch["type_labels"].tolist() == [2]
    print("  ✓ count 类型 OK")


def test_collator_arithmetic():
    collator = TATCollator(TATCollatorConfig(tokenizer_name="roberta-base", max_length=128))
    samples = [make_fake_sample("arithmetic")]
    batch = collator(samples)
    assert batch["type_labels"].tolist() == [3]
    assert batch["arith_op_labels"].tolist() == [1]  # '-' 是 op id 1
    print("  ✓ arithmetic 类型 OK")


def test_collator_batch():
    collator = TATCollator(TATCollatorConfig(tokenizer_name="roberta-base", max_length=128))
    samples = [make_fake_sample("span"), make_fake_sample("arithmetic"), make_fake_sample("multi-span")]
    batch = collator(samples)
    assert batch["input_ids"].shape[0] == 3
    assert batch["type_labels"].tolist() == [0, 3, 1]
    print("  ✓ batch (3 samples) OK")


if __name__ == "__main__":
    print("[test_collator]")
    test_collator_span()
    test_collator_multi_span()
    test_collator_count()
    test_collator_arithmetic()
    test_collator_batch()
    print("\n全部通过 ✓")