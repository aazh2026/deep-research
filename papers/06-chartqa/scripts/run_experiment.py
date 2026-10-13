"""ChartQA 主实验。

复现目标（受 CPU 限制）：

1. 加载 train/val 三个 split（test 无 gold，论文说用于 leaderboard）
2. **实现 ChartQA 官方 relaxed/strict Acc 指标**（Section 4.1）
3. **Majority baseline**：在 train 上统计最常见答案
4. **Random baseline**：random numeric guess + 简单文本词典
5. 按 human vs machine split 切分算 Acc，**验证 paper claim**：
   - 「人工问题比模板问题**显著更难**」
6. 写 JSON 报告

不跑：
- 任何 VLM（GPT-4V、Qwen-VL 等）
- 任何 T5/UniChart 等 fine-tune 方法
- 任何 OCR 流水线
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict

# 让脚本能 import src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.baselines import (
    compute_majority_predictor,
    majority_predict,
    random_predict,
)
from src.data_loader import ChartQAQuestion, load_split, stats_summary
from src.metrics import is_correct


def evaluate(predictions: list[dict], gold_qs: list[dict], mode: str = "relaxed") -> dict:
    """对一组 prediction 算整体 + 按 human/machine × answer_type 的 Acc。"""
    # 用 uid 对齐 predictions 和 gold
    gold_by_uid = {q["uid"]: q for q in gold_qs}

    n_correct_strict = 0
    n_correct_relaxed = 0
    n_total = 0

    by_source_relaxed = defaultdict(lambda: {"n": 0, "n_correct": 0})
    by_type_relaxed = defaultdict(lambda: {"n": 0, "n_correct": 0})
    by_source_type_relaxed = defaultdict(lambda: {"n": 0, "n_correct": 0})

    for pred in predictions:
        q = gold_by_uid[pred["uid"]]
        gold_labels = q["label"]
        is_human = q["human_or_machine"] == 0
        src = "human" if is_human else "machine"
        atype = q["answer_type"]

        n_total += 1
        ok_strict = is_correct(pred["prediction"], gold_labels, mode="strict")
        ok_relaxed = is_correct(pred["prediction"], gold_labels, mode="relaxed")
        if ok_strict:
            n_correct_strict += 1
        if ok_relaxed:
            n_correct_relaxed += 1
        by_source_relaxed[src]["n"] += 1
        if ok_relaxed:
            by_source_relaxed[src]["n_correct"] += 1
        by_type_relaxed[atype]["n"] += 1
        if ok_relaxed:
            by_type_relaxed[atype]["n_correct"] += 1
        by_source_type_relaxed[f"{src}_{atype}"]["n"] += 1
        if ok_relaxed:
            by_source_type_relaxed[f"{src}_{atype}"]["n_correct"] += 1

    return {
        "n_total": n_total,
        "strict_acc": n_correct_strict / n_total if n_total else 0.0,
        "relaxed_acc": n_correct_relaxed / n_total if n_total else 0.0,
        "by_source": {
            k: {
                "n": v["n"],
                "n_correct": v["n_correct"],
                "acc": v["n_correct"] / v["n"] if v["n"] else 0.0,
            }
            for k, v in by_source_relaxed.items()
        },
        "by_answer_type": {
            k: {
                "n": v["n"],
                "n_correct": v["n_correct"],
                "acc": v["n_correct"] / v["n"] if v["n"] else 0.0,
            }
            for k, v in by_type_relaxed.items()
        },
        "by_source_x_type": {
            k: {
                "n": v["n"],
                "n_correct": v["n_correct"],
                "acc": v["n_correct"] / v["n"] if v["n"] else 0.0,
            }
            for k, v in by_source_type_relaxed.items()
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--splits", nargs="+", default=["val"],
                        help="要评测的 split")
    parser.add_argument("--text_vocab_size", type=int, default=50,
                        help="Random baseline 文本词表大小（train 最高频前 K）")
    parser.add_argument("--output", type=str, default="./outputs/results.json")
    parser.add_argument("--cache_dir", type=str, default="./cache")
    args = parser.parse_args()

    t0 = time.time()

    # 1) 加载数据
    print(f"\n[exp] 加载 splits: {args.splits}")
    splits: dict[str, list[ChartQAQuestion]] = {}
    for s in args.splits:
        splits[s] = load_split(s, args.cache_dir)
    train_qs = load_split("train", args.cache_dir)
    print(f"\n[exp] 数据集概况:")
    for s, qs in splits.items():
        st = stats_summary(qs)
        print(f"  {s}: total={st['total']}  by_source={st['by_source']}  by_type={st['by_answer_type']}")

    # 2) Majority baseline predictor（基于 train）
    print("\n[exp] === 计算 Majority predictor (from train) ===")
    num_pred, text_pred = compute_majority_predictor(train_qs)
    print(f"  numeric majority: {num_pred}")
    print(f"  text majority: {text_pred!r}")

    # 3) Random baseline 文本词表
    from collections import Counter
    text_counter: Counter[str] = Counter()
    for q in train_qs:
        for lbl in q.label:
            lbl = lbl.strip()
            if lbl and not is_correct_text_numeric(lbl):
                text_counter[lbl.lower()] += 1
    text_vocab = [w for w, _ in text_counter.most_common(args.text_vocab_size)]
    if not text_vocab:
        text_vocab = ["yes", "no"]

    # 4) 在每个 split 上跑 baseline
    report = {
        "config": {
            "splits": args.splits,
            "text_vocab_size": args.text_vocab_size,
            "elapsed_sec": time.time() - t0,
        },
        "majority_predictor": {"numeric": num_pred, "text": text_pred},
    }

    for split_name, qs in splits.items():
        print(f"\n[exp] === Split: {split_name} ({len(qs)} 题) ===")
        # gold dict 形式（供 evaluate 对齐 uid）
        gold_dicts = [
            {
                "uid": q.uid,
                "label": q.label,
                "human_or_machine": q.human_or_machine,
                "answer_type": q.answer_type,
            }
            for q in qs
        ]
        # Majority
        maj_preds = majority_predict(qs, num_pred, text_pred)
        maj_metrics = evaluate(maj_preds, gold_dicts)
        print(f"  Majority: strict={maj_metrics['strict_acc']:.3f}  relaxed={maj_metrics['relaxed_acc']:.3f}")
        print(f"    by source (relaxed): {maj_metrics['by_source']}")
        print(f"    by type (relaxed):   {maj_metrics['by_answer_type']}")
        # Random
        rnd_preds = random_predict(qs, text_vocab=text_vocab, seed=42)
        rnd_metrics = evaluate(rnd_preds, gold_dicts)
        print(f"  Random:   strict={rnd_metrics['strict_acc']:.3f}  relaxed={rnd_metrics['relaxed_acc']:.3f}")
        print(f"    by source (relaxed): {rnd_metrics['by_source']}")
        print(f"    by type (relaxed):   {rnd_metrics['by_answer_type']}")

        report[f"{split_name}_results"] = {
            "majority": maj_metrics,
            "random": rnd_metrics,
        }

    # 5) 关键 paper claim 验证
    print("\n[exp] === Paper Claim 验证：human vs machine split 难度差 ===")
    claim_results = {}
    for split_name, qs in splits.items():
        m = report[f"{split_name}_results"]
        # 期望：machine_acc > human_acc（baseline 报告在两类上的差距）
        for baseline_name in ["majority", "random"]:
            b = m[baseline_name]
            human_acc = b["by_source"].get("human", {}).get("acc", 0.0)
            machine_acc = b["by_source"].get("machine", {}).get("acc", 0.0)
            gap = machine_acc - human_acc
            print(f"  [{split_name}] {baseline_name}: machine_acc={machine_acc:.3f}  human_acc={human_acc:.3f}  gap={gap:+.3f}")
            claim_results[f"{split_name}_{baseline_name}_gap"] = {
                "human_acc": human_acc,
                "machine_acc": machine_acc,
                "gap": gap,
            }
    report["paper_claim_validation"] = claim_results

    # 6) 写报告
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n[exp] → {args.output}")


def is_correct_text_numeric(s: str) -> bool:
    from src.metrics import is_numeric
    return is_numeric(s)


if __name__ == "__main__":
    main()
