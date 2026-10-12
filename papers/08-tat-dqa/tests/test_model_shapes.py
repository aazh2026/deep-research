"""测试 MHST 模型的前向传播形状。"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import torch

from models.mhst import MHSTModel


def test_forward_shape():
    """B=4, L=128 的 mock batch，forward 输出形状。"""
    model = MHSTModel(backbone_name="roberta-base")
    model.eval()

    B, L = 4, 128
    input_ids = torch.randint(0, 1000, (B, L))
    attention_mask = torch.ones(B, L, dtype=torch.long)

    with torch.no_grad():
        out = model(input_ids, attention_mask)

    assert out.type_logits.shape == (B, 4), f"type_logits: {out.type_logits.shape}"
    assert out.span_start_logits.shape == (B, L)
    assert out.span_end_logits.shape == (B, L)
    assert out.tag_logits.shape == (B, L, 3)
    assert out.arith_op_logits.shape == (B, 4)
    assert out.arith_count_logits.shape == (B, 6)
    assert out.scale_logits.shape == (B, 5)

    print(f"  ✓ forward 形状 OK")
    print(f"    模型总参数: {model.num_parameters():,}")


def test_backward_step():
    """一次 loss.backward() 不报错。"""
    from data.collator import TATCollator, TATCollatorConfig
    from data.parse import TATSample
    from training.losses import LossWeights, compute_losses

    collator = TATCollator(TATCollatorConfig(tokenizer_name="roberta-base", max_length=128))

    samples = [
        TATSample(
            uid=f"t-{i}",
            question=f"Question {i}?",
            context=f"Context for question {i} with number {i*100}.",
            answer=str(i * 100) if i % 2 == 0 else i,
            answer_type="span" if i % 2 == 0 else "count",
            answer_type_id=0 if i % 2 == 0 else 2,
            scale="thousand",
            scale_id=1,
            derivation="",
            arith_op=-1,
            arith_count=0,
        )
        for i in range(4)
    ]
    batch = collator(samples)

    model = MHSTModel(backbone_name="roberta-base")
    model.train()

    output = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"])
    losses = compute_losses(output, batch, LossWeights())
    total_loss = losses["total"]

    # 检查没有 NaN
    assert not torch.isnan(total_loss), "loss 含 NaN"
    total_loss.backward()

    print(f"  ✓ backward 成功, total_loss = {total_loss.item():.4f}")
    print(f"    type loss: {losses.get('type', torch.tensor(0)).item():.4f}")


if __name__ == "__main__":
    print("[test_model_shapes]")
    test_forward_shape()
    print()
    test_backward_step()
    print("\n全部通过 ✓")