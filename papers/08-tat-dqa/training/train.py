"""训练主循环：多任务损失 + AdamW 分组 lr + 早停 + checkpoint。"""

from __future__ import annotations

import json
import math
import os
import time
from dataclasses import dataclass
from typing import Any

import torch
import torch.nn as nn
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
from transformers import get_linear_schedule_with_warmup

from data.collator import TATCollator, TATCollatorConfig
from data.parse import TATSample, load_hf_samples
from models.mhst import MHSTModel
from training.losses import LossWeights, compute_losses
from utils.seed import get_device, set_seed


@dataclass
class TrainConfig:
    """训练配置（与 configs/roberta_base.yaml 对应）。"""

    seed: int = 42
    backbone: str = "roberta-base"
    max_length: int = 512

    hf_dataset: str = "next-tat/TAT-DQA"
    cache_dir: str = "./cache"
    local_dir: str | None = None
    train_size: int = 1500
    dev_size: int = 300
    test_size: int = 500

    epochs: int = 3
    batch_size: int = 4
    grad_accum: int = 4
    backbone_lr: float = 2e-5
    head_lr: float = 1e-4
    warmup_ratio: float = 0.06
    weight_decay: float = 0.01
    grad_clip: float = 1.0
    early_stop_patience: int = 2

    save_dir: str = "./outputs/checkpoints"
    metrics_path: str = "./outputs/metrics.json"
    log_every: int = 10

    loss_weights: dict | None = None


class TATDataset(Dataset):
    """PyTorch 包装 TATSample 列表。"""

    def __init__(self, samples: list[TATSample]):
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> TATSample:
        return self.samples[idx]


def build_optimizer_and_scheduler(
    model: MHSTModel, config: TrainConfig, total_steps: int
) -> tuple[AdamW, Any]:
    """AdamW 分组 lr：backbone vs heads。"""
    backbone_params = list(model.encoder.parameters())
    head_params = []
    for name, param in model.named_parameters():
        if "encoder" not in name:
            head_params.append(param)

    optimizer = AdamW(
        [
            {"params": backbone_params, "lr": config.backbone_lr},
            {"params": head_params, "lr": config.head_lr},
        ],
        weight_decay=config.weight_decay,
    )
    warmup_steps = max(10, int(total_steps * config.warmup_ratio))
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps,
    )
    return optimizer, scheduler


def train(config: TrainConfig) -> dict:
    """主训练入口。返回 metrics dict。"""
    set_seed(config.seed)
    device = get_device()
    print(f"[train] device: {device}")

    # 1) 加载数据
    print(f"[train] 加载训练集 ({config.train_size})...")
    local_dir = getattr(config, "local_dir", None)
    train_samples = load_hf_samples(
        hf_dataset_name=config.hf_dataset,
        cache_dir=config.cache_dir,
        local_dir=local_dir,
        split="train",
        max_samples=config.train_size * 4 if local_dir is None else config.train_size,
    )
    if local_dir is not None:
        train_samples = train_samples[: config.train_size]
    else:
        train_samples = train_samples[: config.train_size]

    print(f"[train] 加载验证集 ({config.dev_size})...")
    dev_samples = load_hf_samples(
        hf_dataset_name=config.hf_dataset,
        cache_dir=config.cache_dir,
        local_dir=local_dir,
        split="validation",
        max_samples=config.dev_size * 4 if local_dir is None else config.dev_size,
    )[: config.dev_size]

    print(f"[train] train: {len(train_samples)}, dev: {len(dev_samples)}")

    # 2) collator + DataLoader
    collator_cfg = TATCollatorConfig(
        tokenizer_name=config.backbone,
        max_length=config.max_length,
    )
    collator = TATCollator(collator_cfg)

    train_loader = DataLoader(
        TATDataset(train_samples),
        batch_size=config.batch_size,
        shuffle=True,
        collate_fn=collator,
        num_workers=0,
    )
    dev_loader = DataLoader(
        TATDataset(dev_samples),
        batch_size=config.batch_size,
        shuffle=False,
        collate_fn=collator,
        num_workers=0,
    )

    # 3) 模型
    model = MHSTModel(backbone_name=config.backbone)
    model.to(device)
    print(f"[train] model params: {model.num_parameters():,}")

    # 4) 优化器 + scheduler
    total_steps = (len(train_loader) // config.grad_accum) * config.epochs
    optimizer, scheduler = build_optimizer_and_scheduler(model, config, total_steps)

    # 5) 损失权重
    weights = LossWeights(**(config.loss_weights or {}))

    # 6) 训练循环
    os.makedirs(config.save_dir, exist_ok=True)
    best_dev_loss = float("inf")
    no_improve = 0
    history = []

    for epoch in range(1, config.epochs + 1):
        model.train()
        epoch_loss = 0.0
        step_count = 0
        optimizer.zero_grad()

        pbar = tqdm(train_loader, desc=f"epoch {epoch}/{config.epochs}")
        for batch_idx, batch in enumerate(pbar):
            batch = {k: v.to(device) for k, v in batch.items()}
            output = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"])
            losses = compute_losses(output, batch, weights)
            loss = losses["total"] / config.grad_accum
            loss.backward()

            if (batch_idx + 1) % config.grad_accum == 0:
                torch.nn.utils.clip_grad_norm_(model.parameters(), config.grad_clip)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

            epoch_loss += loss.item() * config.grad_accum
            step_count += 1

            if step_count % config.log_every == 0:
                pbar.set_postfix(
                    loss=f"{loss.item() * config.grad_accum:.4f}",
                    type=f"{losses.get('type', torch.tensor(0)).item():.3f}",
                )

        avg_loss = epoch_loss / max(step_count, 1)

        # 验证
        dev_loss = evaluate_loss(model, dev_loader, weights, device)
        history.append({"epoch": epoch, "train_loss": avg_loss, "dev_loss": dev_loss})
        print(f"[epoch {epoch}] train_loss={avg_loss:.4f}, dev_loss={dev_loss:.4f}")

        if dev_loss < best_dev_loss:
            best_dev_loss = dev_loss
            no_improve = 0
            ckpt_path = os.path.join(config.save_dir, "best.pt")
            save_checkpoint(model, optimizer, scheduler, epoch, ckpt_path, config)
            print(f"  [ckpt] saved best → {ckpt_path}")
        else:
            no_improve += 1
            if no_improve >= config.early_stop_patience:
                print(f"[early stop] no improvement for {no_improve} epochs")
                break

    metrics = {
        "best_dev_loss": best_dev_loss,
        "history": history,
        "config": {k: v for k, v in config.__dict__.items() if not k.startswith("_")},
    }
    os.makedirs(os.path.dirname(config.metrics_path), exist_ok=True)
    with open(config.metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False, default=str)
    print(f"[train] metrics saved → {config.metrics_path}")
    return metrics


def evaluate_loss(
    model: MHSTModel, loader: DataLoader, weights: LossWeights, device: torch.device
) -> float:
    """在 dev set 上计算平均 loss。"""
    model.eval()
    total_loss = 0.0
    count = 0
    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            output = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"])
            losses = compute_losses(output, batch, weights)
            total_loss += losses["total"].item()
            count += 1
    return total_loss / max(count, 1)


def save_checkpoint(
    model: MHSTModel,
    optimizer: AdamW,
    scheduler: Any,
    epoch: int,
    path: str,
    config: TrainConfig,
) -> None:
    """保存模型 + 优化器 + 配置。"""
    state = {
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "scheduler_state_dict": scheduler.state_dict() if scheduler is not None else None,
        "epoch": epoch,
        "config": {k: v for k, v in config.__dict__.items() if not k.startswith("_")},
    }
    torch.save(state, path)


def load_checkpoint(path: str, model: MHSTModel, device: torch.device) -> int:
    """加载 checkpoint，返回 epoch。

    注意：MPS 设备加载 PyTorch state_dict 有 known bug
    （unaligned blit request）。先在 CPU 上 load，再 move 到目标 device。
    """
    state = torch.load(path, map_location="cpu", weights_only=False)
    model.load_state_dict(state["model_state_dict"])
    model.to(device)
    return state.get("epoch", 0)