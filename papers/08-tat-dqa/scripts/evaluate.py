"""评估入口脚本。"""

from __future__ import annotations

import argparse
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation.evaluate import EvalConfig, run_evaluation


def main() -> None:
    parser = argparse.ArgumentParser(description="MHST 评估入口")
    parser.add_argument("--checkpoint", default="./outputs/checkpoints/best.pt")
    parser.add_argument("--test_size", type=int, default=500)
    parser.add_argument("--backbone", default="roberta-base")
    parser.add_argument("--metrics_path", default="./outputs/test_metrics.json")
    args = parser.parse_args()

    config = EvalConfig(
        checkpoint=args.checkpoint,
        test_size=args.test_size,
        backbone=args.backbone,
        metrics_path=args.metrics_path,
    )
    run_evaluation(config)


if __name__ == "__main__":
    main()