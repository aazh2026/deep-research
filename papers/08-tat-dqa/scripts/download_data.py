"""数据下载脚本：从 Hugging Face 加载 TAT-DQA 并缓存到本地。"""

from __future__ import annotations

import argparse
import os
import sys

# 把项目根加到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.parse import load_hf_samples


def main() -> None:
    parser = argparse.ArgumentParser(description="下载并解析 TAT-DQA 数据集")
    parser.add_argument("--dataset", default="next-tat/TAT-DQA")
    parser.add_argument("--cache_dir", default="./cache")
    parser.add_argument("--max_per_split", type=int, default=2000)
    args = parser.parse_args()

    os.makedirs(args.cache_dir, exist_ok=True)

    for split in ["train", "validation", "test"]:
        print(f"\n[download] split={split}")
        try:
            samples = load_hf_samples(
                hf_dataset_name=args.dataset,
                cache_dir=args.cache_dir,
                split=split,
                max_samples=args.max_per_split,
            )
            print(f"  ✓ 解析 {len(samples)} 条样本")
            if samples:
                s = samples[0]
                print(f"  示例: question='{s.question[:80]}', answer_type={s.answer_type}")
                print(f"         answer={s.answer}, scale={s.scale}")
        except Exception as e:
            print(f"  ✗ 失败: {e}")


if __name__ == "__main__":
    main()