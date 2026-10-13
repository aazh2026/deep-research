"""AEOLLM-2 metric 复现主实验。

策略：
- 本地无 AEOLLM 真实评测数据（hf.co/datasets/THUIR/AEOLLM 需申请）
- 用「模拟场景」验证 3 个 metric 的行为
- 关键场景：
  1. 完美对齐（acc=1, ρ=1, τ=1）
  2. 完全反（acc=0, ρ=-1, τ=-1）
  3. 中度对齐（模拟 paper 真实场景）
  4. Tie 处理（仅 participant / 仅 human / 双 tie）

与 paper Table 4 对比：
- 最佳参赛系统 RSLIR: acc=0.7796, ρ=0.7071, τ=0.5592
- 第二 SCUNLP: ρ=0.5197, τ=0.3827, acc=0.6883
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.metrics import (
    pairwise_accuracy,
    spearman_rho,
    kendall_tau_b,
    evaluate_all,
)


def simulate_scenario(name: str, n_questions: int, n_answers: int,
                      noise: float, tie_rate: float, seed: int = 42) -> dict:
    """生成模拟评测数据：participant scores 含 noise + 随机 tie。

    - h (human): 完全排序 0..n_answers-1
    - p (participant): h + Gaussian noise + 随机打 ties
    """
    rng = random.Random(seed)
    per_q = []
    for q in range(n_questions):
        # 真实评分：4 个 answer 评分 0/1/2/3（或者扩展到 0..n-1）
        h = [float(i) for i in range(n_answers)]
        rng.shuffle(h)  # 每个 question 顺序不同
        # participant 加 noise
        p = [max(0, h[i] + rng.gauss(0, noise)) for i in range(n_answers)]
        # 随机 tie
        if tie_rate > 0:
            n_tie = int(n_answers * tie_rate)
            for _ in range(n_tie):
                i, j = rng.sample(range(n_answers), 2)
                p[i] = p[j]
        per_q.append((p, h))

    res = evaluate_all(per_q)
    return {
        "scenario": name,
        "n_questions": n_questions,
        "n_answers": n_answers,
        "noise": noise,
        "tie_rate": tie_rate,
        "accuracy": res["accuracy"],
        "spearman": res["spearman"],
        "kendall": res["kendall"],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", default="./outputs")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print("=== AEOLLM-2 Metric 复现：3 场景模拟 ===\n")
    print("Paper Table 4 baseline: RSLIR acc=0.7796 ρ=0.7071 τ=0.5592")
    print()

    scenarios = [
        ("perfect", 0.0, 0.0),       # 完美对齐
        ("reverse", 10.0, 0.0),      # 完全反（noise 大到排序反过来）
        ("moderate", 0.5, 0.0),      # 中度对齐
        ("moderate_with_ties", 0.5, 0.3),  # 中度 + 30% tie
    ]

    results = []
    for name, noise, tie_rate in scenarios:
        res = simulate_scenario(
            name=name, n_questions=40, n_answers=4,
            noise=noise, tie_rate=tie_rate, seed=args.seed,
        )
        results.append(res)
        print(f"[{res['scenario']:25s}] n={res['n_questions']} noise={noise} tie={tie_rate}")
        print(f"    acc = {res['accuracy']:.4f}  ρ = {res['spearman']:.4f}  τ = {res['kendall']:.4f}")

    # 与 paper 对比
    print("\n=== 与 Paper Table 4 对比 ===")
    print("| Method | acc | ρ | τ |")
    print("|---|---|---|---|")
    print("| Paper RSLIR (best) | 0.7796 | 0.7071 | 0.5592 |")
    print("| Paper SCUNLP (2nd) | 0.6883 | 0.5197 | 0.3827 |")
    print("| Paper GLM-4.7 baseline | 0.7413 | 0.6177 | 0.4830 |")
    for r in results:
        print(f"| 模拟 {r['scenario']:20s} | {r['accuracy']:.4f} | {r['spearman']:.4f} | {r['kendall']:.4f} |")

    out_path = out_dir / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"scenarios": results, "paper_baseline": {
            "RSLIR": {"accuracy": 0.7796, "spearman": 0.7071, "kendall": 0.5592},
            "SCUNLP": {"accuracy": 0.6883, "spearman": 0.5197, "kendall": 0.3827},
        }}, f, indent=2, ensure_ascii=False)
    print(f"\n结果已写入 {out_path}  (用时 {time.time()-t0:.1f}s)")


if __name__ == "__main__":
    main()
