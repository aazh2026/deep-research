"""DocVQA 复现主实验。

策略：CPU 友好
- 加载 nielsr/docvqa_1200_examples（1200 题，train split）
- 切成 train(800) / dev(200) / test(200) 三段（paper 用 39K/5K/5K，这里按比例缩）
- 跑 3 个盲 baseline：
  1. **Majority** —— 全数据集最常出现的答案
  2. **Random** —— 按 train 答案分布采样
  3. **Lexical** —— OCR 文本上做关键词检索 + 启发式抽取
- 用 ANLS 评估

输出：
- outputs/results.json：完整报告
- 打印 ANLS + 按问题类别的分析
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# 让 import src.* 能跑
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import load_split, stats_summary
from src.baselines import (
    compute_majority_answer,
    majority_predict,
    compute_random_pool,
    random_predict,
    lexical_predict,
    evaluate_baseline,
)


def split_qs(qs, train_ratio=0.66, dev_ratio=0.17, test_ratio=0.17, seed=42):
    """按确定性顺序切分（用 seed 改的 random.shuffle）。"""
    import random
    rng = random.Random(seed)
    indices = list(range(len(qs)))
    rng.shuffle(indices)
    n = len(qs)
    n_train = int(n * train_ratio)
    n_dev = int(n * dev_ratio)
    train_idx = indices[:n_train]
    dev_idx = indices[n_train:n_train + n_dev]
    test_idx = indices[n_train + n_dev:]
    return [qs[i] for i in train_idx], [qs[i] for i in dev_idx], [qs[i] for i in test_idx]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cache", default="./cache")
    p.add_argument("--output", default="./outputs")
    p.add_argument("--max_questions", type=int, default=600,
                   help="最多加载多少题（CPU 时间限制）")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- 加载 ----
    t0 = time.time()
    all_qs = load_split("train", cache_dir=args.cache)
    if args.max_questions and args.max_questions < len(all_qs):
        all_qs = all_qs[:args.max_questions]
    print(f"[main] 加载用时 {time.time()-t0:.1f}s，{len(all_qs)} 题")

    stats = stats_summary(all_qs)
    print(f"[main] OCR words 平均 {stats['avg_ocr_words']:.0f} 个/题；"
          f"每题平均 gold 答案 {stats['avg_answers_per_q']:.2f} 个")
    print(f"[main] 多答案分布: {stats['n_answers_dist']}")

    # ---- 切分 ----
    train_qs, dev_qs, test_qs = split_qs(all_qs, seed=args.seed)
    print(f"[main] 切分: train={len(train_qs)} dev={len(dev_qs)} test={len(test_qs)}")

    # ---- Baseline 1: majority ----
    majority = compute_majority_answer(train_qs)
    print(f"[main] 多数答案: '{majority}'")

    # ---- Baseline 2: random pool ----
    pool = compute_random_pool(train_qs)
    print(f"[main] random pool 大小: {len(pool)} 个不同答案")

    # ---- 在 test 上跑全部 baseline ----
    results = {
        "config": {
            "max_questions": args.max_questions,
            "seed": args.seed,
            "n_train": len(train_qs),
            "n_dev": len(dev_qs),
            "n_test": len(test_qs),
        },
        "stats": stats,
        "majority_answer": majority,
        "random_pool_size": len(pool),
        "split_results": {},
    }

    for split_name, s_qs in [("train", train_qs), ("dev", dev_qs), ("test", test_qs)]:
        # majority
        preds_maj = majority_predict(s_qs, majority)
        res_maj = evaluate_baseline(s_qs, preds_maj)

        # random
        preds_rnd = random_predict(s_qs, pool, seed=args.seed)
        res_rnd = evaluate_baseline(s_qs, preds_rnd)

        # lexical
        preds_lex = [lexical_predict(q) for q in s_qs]
        res_lex = evaluate_baseline(s_qs, preds_lex)

        results["split_results"][split_name] = {
            "majority": res_maj,
            "random": res_rnd,
            "lexical": res_lex,
        }

        print(f"\n[{split_name}] (n={len(s_qs)})")
        print(f"  majority:  ANLS = {res_maj['anls']:.4f}")
        print(f"  random:    ANLS = {res_rnd['anls']:.4f}")
        print(f"  lexical:   ANLS = {res_lex['anls']:.4f}")

    # ---- 写报告 ----
    out_path = out_dir / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[main] 结果已写入 {out_path}")


if __name__ == "__main__":
    main()
