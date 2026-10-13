"""DocVQA Challenge 2020 复现主实验。

Task 1: VQA on Document Images (ANLS 评价)
- 加载 nielsr/docvqa_1200_examples（与 03-docvqa 同源）
- 跑 4 个 baseline：majority / random / lexical / span_exact
- 输出 ANLS

Task 2: VQA on Document Image Collection (MAP 评价)
- paper 用 14,362 图像 + 20 queries，本地无 DocCVQA 镜像
- 实施：toy 合成数据验证 MAP 实现正确性
- 与 paper Table 2 (DQA 0.8090, DOCR 0.7915) 的真实数字比较
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data_loader import load_task1
from src.baselines import (
    compute_majority_answer, majority_predict,
    compute_random_pool, random_predict,
    lexical_predict, span_exact_predict,
    evaluate_task1,
)
from src.metrics import (
    average_precision, mean_average_precision,
    precision_at_k, recall_at_k,
)


def split_qs(qs, train_ratio=0.66, dev_ratio=0.17, test_ratio=0.17, seed=42):
    import random
    rng = random.Random(seed)
    indices = list(range(len(qs)))
    rng.shuffle(indices)
    n = len(qs)
    n_train = int(n * train_ratio)
    n_dev = int(n * dev_ratio)
    return (
        [qs[i] for i in indices[:n_train]],
        [qs[i] for i in indices[n_train:n_train + n_dev]],
        [qs[i] for i in indices[n_train + n_dev:]],
    )


def task2_simulation():
    """Task 2 toy 验证：用合成数据测 MAP 实现。

    paper 报 DQA 0.8090, DOCR 0.7915。我们没有 DocCVQA 数据集，
    但能验证：
    1. MAP 在完美 retrieval 下 = 1.0
    2. MAP 对部分命中的敏感性
    3. P@k / R@k 在 14K 文档场景下的下界
    """
    print("\n=== Task 2: VQA on Document Image Collection (MAP 模拟) ===")
    print("注：本地无 DocCVQA 14,362 图像数据集，仅 toy 验证 MAP 实现")
    print()

    # 场景 A：完美 retrieval
    n_queries = 20  # paper 的 query 数
    n_relevant_per_q = 3
    preds_perfect = [[f"d{i}_{j}" for j in range(n_relevant_per_q)]
                     for i in range(n_queries)]
    gold_perfect = [{f"d{i}_{j}" for j in range(n_relevant_per_q)}
                    for i in range(n_queries)]
    res = mean_average_precision(preds_perfect, gold_perfect)
    print(f"  完美 retrieval:  MAP = {res['map']:.4f}  (理论 1.0)")

    # 场景 B：BM25-like 弱 retrieval（每 query 检索 100 文档，命中 1-2 个）
    import random
    rng = random.Random(42)
    preds_weak = []
    gold_weak = []
    for i in range(n_queries):
        relevant = {f"d{i}_{j}" for j in range(n_relevant_per_q)}
        retrieved = list(relevant) + [f"noise_{i}_{k}" for k in range(100)]
        rng.shuffle(retrieved)
        # relevant 排在中间
        retrieved = retrieved[:50] + list(relevant) + retrieved[50:]
        preds_weak.append(retrieved)
        gold_weak.append(relevant)
    res_weak = mean_average_precision(preds_weak, gold_weak)
    print(f"  弱 retrieval:    MAP = {res_weak['map']:.4f}  (paper 冠军 0.8090)")

    # P@10 / R@10 / P@100 / R@100 报告
    p10, r10 = [], []
    for p, g in zip(preds_weak, gold_weak):
        p10.append(precision_at_k(p, g, 10))
        r10.append(recall_at_k(p, g, 10))
    print(f"  P@10 = {sum(p10)/len(p10):.4f}  R@10 = {sum(r10)/len(r10):.4f}")

    return {
        "perfect_map": res["map"],
        "weak_map": res_weak["map"],
        "p_at_10_weak": sum(p10) / len(p10),
        "r_at_10_weak": sum(r10) / len(r10),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cache", default="./cache")
    p.add_argument("--output", default="./outputs")
    p.add_argument("--max_questions", type=int, default=1000)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ---- Task 1 ----
    print("=== Task 1: VQA on Document Images (ANLS) ===")
    t0 = time.time()
    all_qs = load_task1("train", cache_dir=args.cache)
    if args.max_questions and args.max_questions < len(all_qs):
        all_qs = all_qs[:args.max_questions]
    print(f"[main] 加载用时 {time.time()-t0:.1f}s，{len(all_qs)} 题")

    train_qs, dev_qs, test_qs = split_qs(all_qs, seed=args.seed)
    print(f"[main] 切分: train={len(train_qs)} dev={len(dev_qs)} test={len(test_qs)}")

    majority = compute_majority_answer(train_qs)
    pool = compute_random_pool(train_qs)
    print(f"[main] 多数答案: '{majority}', random pool: {len(pool)} 不同答案")

    results = {
        "task1": {
            "config": {
                "max_questions": args.max_questions,
                "n_train": len(train_qs),
                "n_dev": len(dev_qs),
                "n_test": len(test_qs),
            },
            "split_results": {},
        },
        "task2_simulation": None,
    }

    for split_name, s_qs in [("train", train_qs), ("dev", dev_qs), ("test", test_qs)]:
        # 4 个 baseline
        preds_maj = majority_predict(s_qs, majority)
        preds_rnd = random_predict(s_qs, pool, seed=args.seed)
        preds_lex = [lexical_predict(q) for q in s_qs]
        preds_se = [span_exact_predict(q) for q in s_qs]

        res_maj = evaluate_task1(s_qs, preds_maj)
        res_rnd = evaluate_task1(s_qs, preds_rnd)
        res_lex = evaluate_task1(s_qs, preds_lex)
        res_se = evaluate_task1(s_qs, preds_se)

        results["task1"]["split_results"][split_name] = {
            "majority": res_maj,
            "random": res_rnd,
            "lexical": res_lex,
            "span_exact": res_se,
        }

        print(f"\n[{split_name}] (n={len(s_qs)})")
        print(f"  majority:    ANLS = {res_maj['anls']:.4f}")
        print(f"  random:      ANLS = {res_rnd['anls']:.4f}")
        print(f"  lexical:     ANLS = {res_lex['anls']:.4f}")
        print(f"  span_exact:  ANLS = {res_se['anls']:.4f}  (≈ Plain BERT QA)")

    # ---- Task 2 (toy) ----
    results["task2_simulation"] = task2_simulation()

    # ---- 写报告 ----
    out_path = out_dir / "results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n[main] 结果已写入 {out_path}")


if __name__ == "__main__":
    main()
