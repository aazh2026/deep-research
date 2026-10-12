"""数据探索脚本：打印 4 类样本各一份。"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.parse import load_hf_samples


def main() -> None:
    parser = argparse.ArgumentParser(description="探索 TAT-DQA 数据")
    parser.add_argument("--cache_dir", default="./cache")
    parser.add_argument("--per_type", type=int, default=1, help="每类打印几条")
    args = parser.parse_args()

    samples = load_hf_samples(
        cache_dir=args.cache_dir,
        split="train",
        max_samples=200,
    )
    print(f"加载了 {len(samples)} 条样本\n")

    type_count = {"span": 0, "multi-span": 0, "count": 0, "arithmetic": 0}
    for s in samples:
        if all(type_count[t] >= args.per_type for t in type_count):
            break
        if type_count[s.answer_type] >= args.per_type:
            continue
        type_count[s.answer_type] += 1
        print(f"=== {s.answer_type.upper()} (uid={s.uid}) ===")
        print(f"Q: {s.question[:200]}")
        print(f"Answer: {s.answer}")
        print(f"Scale: {s.scale}")
        if s.derivation:
            print(f"Derivation: {s.derivation}")
        print(f"Context (前 300 chars): {s.context[:300]}")
        print()

    print(f"类型计数: {type_count}")


if __name__ == "__main__":
    main()