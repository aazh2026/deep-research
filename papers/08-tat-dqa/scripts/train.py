"""训练入口脚本。"""

from __future__ import annotations

import argparse
import os
import sys

import yaml

# 把项目根加到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from training.train import TrainConfig, train


def load_config(path: str) -> TrainConfig:
    """加载 yaml 并打平嵌套为 TrainConfig 字段。"""
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    flat: dict = {}
    for section in ("model", "data", "training", "eval"):
        if section in cfg and isinstance(cfg[section], dict):
            flat.update(cfg[section])
    # 顶层字段（experiment、seed、loss_weights）也保留
    for k, v in cfg.items():
        if k in ("model", "data", "training", "eval"):
            continue
        flat[k] = v
    # 只保留 TrainConfig 已定义的字段
    import dataclasses
    valid_keys = {f.name for f in dataclasses.fields(TrainConfig)}
    flat = {k: v for k, v in flat.items() if k in valid_keys}
    return TrainConfig(**flat)


def main() -> None:
    parser = argparse.ArgumentParser(description="MHST 训练入口")
    parser.add_argument("--config", default="configs/roberta_base.yaml")
    parser.add_argument("--train_size", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--batch_size", type=int, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    # 命令行覆盖
    if args.train_size is not None:
        config.train_size = args.train_size
    if args.epochs is not None:
        config.epochs = args.epochs
    if args.batch_size is not None:
        config.batch_size = args.batch_size

    print(f"[train] 配置: {config.__dict__}")
    train(config)


if __name__ == "__main__":
    main()