"""SynthDocBench 主实验。

复现目标（受 CPU 限制）：

1. 加载全部 6 个 subset
2. **Text-only baseline**：在 PDF 抽出的文本里搜 gold answer
   - 输出：每题 text_evidence_score + ACC(τ=0.5)
   - 按 subset × difficulty 切片
3. **Random baseline**（对照组）
4. 验证 paper 核心 claim：
   - 「chart 问题的 gold 答案在文本里找不到 → 真的需要 vision」
   - 「complex 问题的 gold 答案可从文本中拼凑 → text-only 反而能答」
5. 写 JSON 报告

不跑：
- 任何 VLM（GPU 不可用）
- 任何 LLM 推理（即使是 Qwen-0.5B 在 CPU 上也慢）
- judge 评分（无 GPT-5）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter

# 让脚本能 import src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import SDBQuestion, load_all, load_subset
from src.retrieval import (
    aggregate_acc,
    aggregate_by_difficulty,
    aggregate_by_subset,
    random_evaluate,
    text_only_evaluate,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--subsets", nargs="+",
                        default=["chart", "complex", "cross_modal"],
                        help="要跑的 subset")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="ACC 阈值 τ（text evidence score）")
    parser.add_argument("--score_mode", type=str, default="conservative",
                        choices=["lenient", "strict", "number_only",
                                 "conservative", "high_bar"],
                        help="text_evidence_score 模式（默认 conservative：仅 substring 命中算对）")
    parser.add_argument("--output", type=str, default="./outputs/results.json")
    parser.add_argument("--pdf_dir", type=str, default="./data/pdfs")
    parser.add_argument("--cache_dir", type=str, default="./cache")
    parser.add_argument("--use_cache", action="store_true",
                        help="跳过 PDF 重新评估，只跑 random 部分")
    args = parser.parse_args()

    t0 = time.time()

    # 1) 加载数据
    all_qs: list[SDBQuestion] = []
    for s in args.subsets:
        all_qs.extend(load_subset(s, args.cache_dir))
    print(f"\n[exp] 共 {len(all_qs)} 道题")

    # 2) Random baseline
    print("\n[exp] === Random baseline ===")
    rnd = random_evaluate(all_qs, seed=42)
    rnd_acc = aggregate_acc(rnd, args.threshold)
    rnd_by_subset = aggregate_by_subset(rnd, args.threshold)
    rnd_by_diff = aggregate_by_difficulty(rnd, args.threshold)
    print(f"  Overall ACC: {rnd_acc['acc']:.3f}  (n_valid={rnd_acc['n_valid']})")
    print(f"  By subset:")
    for s, m in rnd_by_subset.items():
        print(f"    {s:20s}: ACC={m['acc']:.3f}  n={m['n_valid']}")
    print(f"  By difficulty:")
    for d, m in rnd_by_diff.items():
        print(f"    L{d}: ACC={m['acc']:.3f}  n={m['n_valid']}")

    # 3) Text-only baseline
    if args.use_cache and os.path.exists(args.output):
        with open(args.output, "r", encoding="utf-8") as f:
            report = json.load(f)
        print(f"[exp] 从 {args.output} 读取已缓存结果")
        txt_by_subset = report["text_only_baseline"]["by_subset"]
        txt_by_diff = report["text_only_baseline"]["by_difficulty"]
        txt_acc = report["text_only_baseline"]["overall"]
        by_subset_substring = report["paper_claim_validation"]["substring_hit_by_subset"]
        by_diff_substring = report["paper_claim_validation"]["substring_hit_by_difficulty"]
    else:
        print(f"\n[exp] === Text-only baseline (PDF → PyMuPDF → lexical search, mode={args.score_mode}) ===")
        t1 = time.time()
        txt = text_only_evaluate(
            all_qs, pdf_dir=args.pdf_dir, cache_dir=args.cache_dir,
            score_mode=args.score_mode,
        )
        print(f"[exp] text-only 评估耗时 {time.time() - t1:.1f}s")
        txt_acc = aggregate_acc(txt, args.threshold)
        txt_by_subset = aggregate_by_subset(txt, args.threshold)
        txt_by_diff = aggregate_by_difficulty(txt, args.threshold)
        print(f"  Overall ACC: {txt_acc['acc']:.3f}  (n_valid={txt_acc['n_valid']})")
        print(f"  By subset:")
        for s, m in txt_by_subset.items():
            print(f"    {s:20s}: ACC={m['acc']:.3f}  n={m['n_valid']}")
        print(f"  By difficulty:")
        for d, m in txt_by_diff.items():
            print(f"    L{d}: ACC={m['acc']:.3f}  n={m['n_valid']}")

        # 4) 关键 paper claim 验证
        print(f"\n[exp] === Paper Claim 验证 ===")
        by_subset_substring = {}
        for r in txt:
            if r.get("skipped", False):
                continue
            by_subset_substring.setdefault(r["subset"], []).append(r["substring_hit"])
        for s, hits in by_subset_substring.items():
            if hits:
                n = len(hits)
                n_hit = sum(hits)
                print(f"  {s:20s}: substring_hit = {n_hit}/{n} = {n_hit/n:.3f}")

        by_diff_substring = {}
        for r in txt:
            if r.get("skipped", False):
                continue
            by_diff_substring.setdefault(r["difficulty"], []).append(r["substring_hit"])
        print("  Substring hit rate by difficulty:")
        for d in sorted(by_diff_substring):
            hits = by_diff_substring[d]
            n = len(hits)
            n_hit = sum(hits)
            print(f"    L{d}: {n_hit}/{n} = {n_hit/n:.3f}")

        # 5) 写报告
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        report = {
            "config": {
                "subsets": args.subsets,
                "threshold": args.threshold,
                "score_mode": args.score_mode,
                "n_questions": len(all_qs),
                "elapsed_sec": time.time() - t0,
            },
            "random_baseline": {
                "overall": rnd_acc,
                "by_subset": rnd_by_subset,
                "by_difficulty": rnd_by_diff,
            },
            "text_only_baseline": {
                "overall": txt_acc,
                "by_subset": txt_by_subset,
                "by_difficulty": txt_by_diff,
            },
            "paper_claim_validation": {
                "substring_hit_by_subset": {
                    s: {
                        "n_hit": sum(h),
                        "n_total": len(h),
                        "rate": (sum(h) / len(h)) if h else 0.0,
                    }
                    for s, h in by_subset_substring.items()
                },
                "substring_hit_by_difficulty": {
                    str(d): {
                        "n_hit": sum(h),
                        "n_total": len(h),
                        "rate": (sum(h) / len(h)) if h else 0.0,
                    }
                    for d, h in by_diff_substring.items()
                },
            },
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n[exp] → {args.output}")


if __name__ == "__main__":
    main()
