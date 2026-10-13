"""InfographicVQA 盲 baseline 评测脚本。

用法：
    .venv/bin/python scripts/run_experiment.py
    .venv/bin/python scripts/run_experiment.py --max 500
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import load_split, stats_summary
from src.baselines import (
    compute_majority_answer, majority_predict,
    compute_random_pool, random_predict,
    compute_type_majority, type_majority_predict,
    compute_numeric_stats, numeric_median_predict, numeric_mode_predict,
    evaluate_baseline,
)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--max", type=int, default=None,
                   help="最多评测几题（默认全 2801）")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output", default="outputs/results.json")
    args = p.parse_args()

    out_dir = Path(__file__).parent.parent / "outputs"
    out_dir.mkdir(exist_ok=True)

    # 加载数据
    qs = load_split("validation", max_questions=args.max)
    stats = stats_summary(qs)
    print("\n[stats]", json.dumps(stats, ensure_ascii=False, indent=2))

    # 计算 6 个 baseline 的"字典"
    majority = compute_majority_answer(qs)
    pool = compute_random_pool(qs)
    type_majority = compute_type_majority(qs)
    num_stats = compute_numeric_stats(qs)

    print(f"\n[majority] 全体最常答案: {majority!r}")
    print(f"[type-majority] numeric={type_majority.get('numeric')!r}, "
          f"open={type_majority.get('open')!r}, yes_no={type_majority.get('yes_no')!r}")
    print(f"[numeric] median={num_stats['median']}, mode={num_stats['mode']!r}")

    # 跑 6 个 baseline
    results: dict[str, dict] = {}

    preds_majority = majority_predict(qs, majority)
    results["majority"] = evaluate_baseline(qs, preds_majority)

    preds_random = random_predict(qs, pool, seed=args.seed)
    results["random"] = evaluate_baseline(qs, preds_random)

    preds_type_majority = type_majority_predict(qs, type_majority)
    results["type_majority"] = evaluate_baseline(qs, preds_type_majority)

    # numeric-only 类的 baseline 仍要跑全题，非 numeric 填 "0"
    preds_num_median = numeric_median_predict(qs, num_stats["median"])
    results["numeric_median"] = evaluate_baseline(qs, preds_num_median)

    preds_num_mode = numeric_mode_predict(qs, num_stats["mode"])
    results["numeric_mode"] = evaluate_baseline(qs, preds_num_mode)

    # 按 question_type 分桶随机抽样
    def type_random_predict(qs, type_pool, seed):
        import random as _r
        rng = _r.Random(seed)
        out = []
        for q in qs:
            items = type_pool.get(q.question_type)
            if not items:
                out.append("")
                continue
            answers = [a for a, _ in items]
            weights = [w for _, w in items]
            out.append(rng.choices(answers, weights=weights, k=1)[0])
        return out

    type_pool = {}
    from collections import defaultdict, Counter
    by_type = defaultdict(Counter)
    for q in qs:
        for a in q.answers:
            by_type[q.question_type][a] += 1
    for t, c in by_type.items():
        total = sum(c.values())
        type_pool[t] = [(a, n / total) for a, n in c.items()]
    preds_type_random = type_random_predict(qs, type_pool, args.seed)
    results["type_random"] = evaluate_baseline(qs, preds_type_random)

    print("\n" + "=" * 60)
    print("ANLS results (validation split)")
    print("=" * 60)
    for name, r in results.items():
        print(f"  {name:18s}  ANLS = {r['anls']:.4f}   (n={r['n']})")
    print("=" * 60)

    # 按 question_type 分桶分析（majority 在各 type 上的表现）
    print("\n[per-type ANLS] (using majority predictions)")
    from collections import defaultdict
    type_scores: dict[str, list[float]] = defaultdict(list)
    from src.metrics import anls_score
    for q, pred in zip(qs, preds_majority):
        s = anls_score(pred, q.answers)
        type_scores[q.question_type].append(s)
    for t, ss in sorted(type_scores.items()):
        avg = sum(ss) / len(ss) if ss else 0
        print(f"  {t:10s}  ANLS = {avg:.4f}   (n={len(ss)})")

    # 写 JSON
    out_path = Path(__file__).parent.parent / args.output
    out_path.parent.mkdir(exist_ok=True, parents=True)
    payload = {
        "split": "validation",
        "stats": stats,
        "results": {k: {"anls": v["anls"], "n": v["n"]} for k, v in results.items()},
        "per_type_majority": {
            t: {"anls": sum(ss) / len(ss), "n": len(ss)}
            for t, ss in type_scores.items()
        },
        "predictions": {
            "majority": preds_majority,
            "type_majority": preds_type_majority,
            "numeric_median": preds_num_median,
            "numeric_mode": preds_num_mode,
        },
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n[OK] wrote {out_path}")


if __name__ == "__main__":
    main()
