"""主实验：CRUX 评估 BM25 vs Oracle vs Random。

步骤：
1. 加载 50 个 Multi-News 样本
2. 每个样本：构造 sub-questions + 贪心 oracle
3. 跑三种 retriever：BM25、Random、Oracle
4. 计算 Cov(Z) / Den(Z) for each
5. 计算 RAG proxy 质量：concat(retrieved) vs summary 的 token F1
6. 计算 Cov/Den 与 RAG 质量的 Kendall τ
7. 输出 JSON 报告
"""

from __future__ import annotations

import json
import math
import os
import sys
import time

# 让脚本可以 import src/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.coverage import compute_coverage
from src.data_loader import load_crux_samples
from src.density import build_oracle, compute_density, token_count_of_passages
from src.grader import (
    generate_subquestions,
    grade_passage,
)
from src.retrievers import (
    bm25_retrieve_per_query,
    oracle_retrieve,
    random_retrieve,
)


def rag_quality_proxy(retrieved_Z: list[str], summary: str) -> float:
    """RAG 质量代理：concat(Z) 与 summary 的 content-token F1。

    论文里用 Llama 生成质量作为 RAG 指标；本地用 lexical overlap 代理。
    F1 范围 [0, 1]。
    """
    from src.grader import content_tokens

    concat = " ".join(retrieved_Z)
    p_toks = content_tokens(concat)
    g_toks = content_tokens(summary)
    if not p_toks or not g_toks:
        return 0.0
    common = sum((p_toks & g_toks).values())
    if common == 0:
        return 0.0
    p_sum = sum(p_toks.values())
    g_sum = sum(g_toks.values())
    prec = common / p_sum
    rec = common / g_sum
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)


def kendall_tau(x: list[float], y: list[float]) -> float | None:
    """Kendall's τ 等级相关。

    tau = (concordant - discordant) / (n*(n-1)/2)
    """
    n = len(x)
    if n < 2:
        return None
    concordant = 0
    discordant = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            if dx == 0 or dy == 0:
                continue  # tie
            if (dx > 0 and dy > 0) or (dx < 0 and dy < 0):
                concordant += 1
            else:
                discordant += 1
    denom = concordant + discordant
    if denom == 0:
        return 0.0
    return (concordant - discordant) / denom


def run_experiment(
    n_queries: int = 50,
    top_k: int = 20,
    n_subquestions: int = 5,
    eta: int = 3,
    w: float = 0.5,
    output_path: str = "./outputs/results.json",
) -> dict:
    """主实验入口。"""
    t0 = time.time()

    # 1) 加载数据
    samples = load_crux_samples(n_queries=n_queries)
    if not samples:
        print("[exp] 没有加载到样本，退出")
        return {}

    # 2) 对每个样本：构造 sub-questions + oracle
    per_sample_data: list[dict] = []
    for s in samples:
        Q = generate_subquestions(
            s.summary, n_questions=n_subquestions, gold_info=s.gold_info
        )
        if len(Q) < 2:
            continue
        Z_star = oracle_retrieve(s.passages, Q, grade_passage, eta=eta)
        if not Z_star:
            continue
        per_sample_data.append(
            {
                "uid": s.uid,
                "summary": s.summary,
                "n_passages": len(s.passages),
                "n_queries": len(Q),
                "queries": Q,
                "Z_star": Z_star,
                "n_oracle_passages": len(Z_star),
            }
        )
    print(
        f"[exp] 有效样本 {len(per_sample_data)} / {len(samples)}（oracle 至少 1 个 passage）"
    )

    # 3) 跑三种 retriever
    results_by_method: dict[str, list[dict]] = {
        "BM25": [],
        "Random": [],
        "Oracle": [],
    }
    rag_quality: dict[str, list[float]] = {"BM25": [], "Random": [], "Oracle": []}

    for sd in per_sample_data:
        Q = sd["queries"]
        Z_star = sd["Z_star"]
        summary = sd["summary"]
        for method in ["BM25", "Random", "Oracle"]:
            if method == "BM25":
                Z = bm25_retrieve_per_query(Q, sd_passages(sd), top_k=top_k)
            elif method == "Random":
                Z = random_retrieve(sd_passages(sd), top_k=top_k, seed=hash(sd["uid"]) & 0xFFFF)
            else:  # Oracle
                Z = Z_star
            cov = compute_coverage(Z, Q, grade_passage, eta=eta)
            den = compute_density(
                Z, Z_star, Q, grade_passage, cov_Z=cov, eta=eta, w=w
            )
            rq = rag_quality_proxy(Z, summary)
            results_by_method[method].append(
                {
                    "uid": sd["uid"],
                    "n_retrieved": len(Z),
                    "token_Z": token_count_of_passages(Z),
                    "cov": cov,
                    "den": den,
                    "rag_quality": rq,
                }
            )
            rag_quality[method].append(rq)

    # 4) 聚合指标
    summary_per_method: dict[str, dict] = {}
    for method, rows in results_by_method.items():
        if not rows:
            continue
        mean_cov = sum(r["cov"] for r in rows) / len(rows)
        mean_den = sum(r["den"] for r in rows) / len(rows)
        mean_rq = sum(r["rag_quality"] for r in rows) / len(rows)
        mean_n = sum(r["n_retrieved"] for r in rows) / len(rows)
        mean_tok = sum(r["token_Z"] for r in rows) / len(rows)
        summary_per_method[method] = {
            "n_samples": len(rows),
            "mean_n_retrieved": mean_n,
            "mean_token_Z": mean_tok,
            "mean_coverage": mean_cov,
            "mean_density": mean_den,
            "mean_rag_quality_proxy": mean_rq,
        }

    # 5) Kendall τ：BM25 的 Cov/Den 与 RAG quality proxy 的相关性
    bm25_rows = results_by_method["BM25"]
    bm25_cov = [r["cov"] for r in bm25_rows]
    bm25_den = [r["den"] for r in bm25_rows]
    bm25_rq = [r["rag_quality"] for r in bm25_rows]
    # ROUGE-style token F1 不在 BM25 自己里看 — 用所有方法混合
    all_rq: list[float] = []
    all_cov: list[float] = []
    all_den: list[float] = []
    for method in ["BM25", "Random", "Oracle"]:
        for r in results_by_method[method]:
            all_rq.append(r["rag_quality"])
            all_cov.append(r["cov"])
            all_den.append(r["den"])
    tau_cov_vs_rq = kendall_tau(all_cov, all_rq)
    tau_den_vs_rq = kendall_tau(all_den, all_rq)
    # 仅 BM25 内部
    tau_bm25_cov_vs_rq = kendall_tau(bm25_cov, bm25_rq)
    tau_bm25_den_vs_rq = kendall_tau(bm25_den, bm25_rq)

    elapsed = time.time() - t0
    report = {
        "config": {
            "n_queries_target": n_queries,
            "n_valid_samples": len(per_sample_data),
            "top_k": top_k,
            "n_subquestions": n_subquestions,
            "eta": eta,
            "w": w,
            "elapsed_sec": elapsed,
        },
        "per_method_summary": summary_per_method,
        "kendall_tau": {
            "all_methods_cov_vs_rag_quality": tau_cov_vs_rq,
            "all_methods_den_vs_rag_quality": tau_den_vs_rq,
            "bm25_only_cov_vs_rag_quality": tau_bm25_cov_vs_rq,
            "bm25_only_den_vs_rag_quality": tau_bm25_den_vs_rq,
        },
    }
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # 打印
    print(f"\n[exp] === CRUX 复现结果 ===")
    print(f"  有效样本：{len(per_sample_data)}, 耗时 {elapsed:.1f}s")
    for m, s in summary_per_method.items():
        print(
            f"  {m:7s}: Cov={s['mean_coverage']:.3f} Den={s['mean_density']:.3f} "
            f"RQ={s['mean_rag_quality_proxy']:.3f}  n={s['mean_n_retrieved']:.1f} tok={s['mean_token_Z']:.0f}"
        )
    print(f"  Kendall τ (all methods):")
    print(f"    Cov vs RQ: {tau_cov_vs_rq}")
    print(f"    Den vs RQ: {tau_den_vs_rq}")
    print(f"  Kendall τ (BM25 only):")
    print(f"    Cov vs RQ: {tau_bm25_cov_vs_rq}")
    print(f"    Den vs RQ: {tau_bm25_den_vs_rq}")
    print(f"\n[exp] → {output_path}")
    return report


# Helper to recover passages from a stored sample
_PASSAGE_CACHE: dict[str, list[str]] = {}


def sd_passages(sd: dict) -> list[str]:
    """从 per_sample_data 字典里取 passages（带缓存）。"""
    if sd["uid"] not in _PASSAGE_CACHE:
        # 重新加载（牺牲一点效率换取代码简洁）
        from src.data_loader import load_crux_samples
        samples = {s.uid: s for s in load_crux_samples(n_queries=1000)}
        _PASSAGE_CACHE.update(samples)
    return _PASSAGE_CACHE[sd["uid"]].passages


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--n_queries", type=int, default=50)
    parser.add_argument("--top_k", type=int, default=20)
    parser.add_argument("--n_subquestions", type=int, default=5)
    parser.add_argument("--eta", type=int, default=3)
    parser.add_argument("--w", type=float, default=0.5)
    parser.add_argument("--output", type=str, default="./outputs/results.json")
    args = parser.parse_args()

    run_experiment(
        n_queries=args.n_queries,
        top_k=args.top_k,
        n_subquestions=args.n_subquestions,
        eta=args.eta,
        w=args.w,
        output_path=args.output,
    )
