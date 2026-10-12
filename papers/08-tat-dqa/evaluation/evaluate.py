"""评估入口：加载 checkpoint → 推理 → 计算 EM/F1 → 写报告。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import torch
from torch.utils.data import DataLoader

from data.collator import TATCollator, TATCollatorConfig
from data.parse import load_hf_samples
from evaluation.metrics import ID2ANSWER_TYPE, ID2OP, ID2SCALE, compute_metrics, decode_predictions
from models.mhst import MHSTModel
from training.train import TATDataset, load_checkpoint
from utils.seed import get_device, set_seed


@dataclass
class EvalConfig:
    """评估配置。"""

    seed: int = 42
    backbone: str = "roberta-base"
    max_length: int = 512

    hf_dataset: str = "next-tat/TAT-DQA"
    cache_dir: str = "./cache"
    local_dir: str | None = "./data_local"
    test_size: int = 500

    checkpoint: str = "./outputs/checkpoints/best.pt"
    metrics_path: str = "./outputs/test_metrics.json"
    batch_size: int = 4


def run_evaluation(config: EvalConfig) -> dict:
    """主评估入口。"""
    set_seed(config.seed)
    device = get_device()
    print(f"[eval] device: {device}")

    # 1) 加载测试数据
    print(f"[eval] 加载测试集 ({config.test_size})...")
    test_samples = load_hf_samples(
        hf_dataset_name=config.hf_dataset,
        cache_dir=config.cache_dir,
        local_dir=config.local_dir,
        split="test",
        max_samples=config.test_size,
    )
    print(f"[eval] test samples: {len(test_samples)}")

    # 2) collator + loader
    collator_cfg = TATCollatorConfig(
        tokenizer_name=config.backbone,
        max_length=config.max_length,
    )
    collator = TATCollator(collator_cfg)
    test_loader = DataLoader(
        TATDataset(test_samples),
        batch_size=config.batch_size,
        shuffle=False,
        collate_fn=collator,
        num_workers=0,
    )

    # 3) 加载模型
    model = MHSTModel(backbone_name=config.backbone)
    load_checkpoint(config.checkpoint, model, device)  # load_checkpoint 内部已 .to(device)
    model.eval()

    # 4) 推理
    all_preds = []
    all_golds = []
    all_scales = []
    all_types = []

    with torch.no_grad():
        for batch_idx, batch in enumerate(test_loader):
            batch_gpu = {k: v.to(device) for k, v in batch.items()}
            output = model(input_ids=batch_gpu["input_ids"], attention_mask=batch_gpu["attention_mask"])

            preds = decode_predictions(
                batch_gpu,
                output,
                collator.tokenizer,
                ID2SCALE,
                ID2OP,
                ID2ANSWER_TYPE,
            )
            # 对应的 gold
            start = batch_idx * config.batch_size
            end = start + len(preds)
            batch_samples = test_samples[start:end]

            for pred, sample in zip(preds, batch_samples):
                all_preds.append(pred)
                all_golds.append(sample.answer)
                all_scales.append(sample.scale)
                all_types.append(sample.answer_type)

    # 5) 计算指标
    metrics = compute_metrics(all_preds, all_golds, all_scales, all_types)

    # 6) 报告
    report = {
        "test_size": len(all_preds),
        "overall": metrics["overall"],
        "per_type": metrics["per_type"],
        "checkpoint": config.checkpoint,
        "samples": [
            {
                "uid": s.uid,
                "question": s.question[:200],
                "answer_type": s.answer_type,
                "gold": str(s.answer)[:100],
                "pred": str(p)[:100],
            }
            for s, p in list(zip(test_samples, all_preds))[:20]
        ],
    }
    os.makedirs(os.path.dirname(config.metrics_path), exist_ok=True)
    with open(config.metrics_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[eval] === TEST SET ===")
    print(f"  overall: EM={metrics['overall']['EM']:.4f}, F1={metrics['overall']['F1']:.4f}")
    for t, m in metrics["per_type"].items():
        print(f"  {t:12s}: EM={m['EM']:.4f}, F1={m['F1']:.4f}, n={m['n']}")
    print(f"\n[eval] metrics saved → {config.metrics_path}")
    return metrics