"""轻量级 text-only QA baseline + 评估。

我们没本地 LLM 推理能力（CPU），所以 text-only baseline 走两条路：

1. **Oracle / substring baseline**：直接在 PDF 文本里搜 gold answer 的关键
   数字/短语，看是否出现。已在 pdf_text.find_answer_in_text 实现
2. **Random baseline**：对数值类问题（chart_reading）随机猜；文本生成类
   （complex/cross_modal）当作 ACC = 0
3. **Heuristic baseline**：基于关键词/数字长度的简单判断（未来扩展）

ACC 评估（论文 Eq. 1）：ACC(f_θ) = (1/|Q_valid|) * Σ 1[J(â, q) ≥ τ]
其中 τ=6（GPT-5 评分 ≥6 算对）。本地没有 GPT-5，我们用：
- text_hit_score: 0-1 之间的「文本证据强度」
- 阈值 0.5：>0.5 视为文本-only 能答出

这只是「text-only 能力上限」代理指标。
"""

from __future__ import annotations

import os
import random
from collections import Counter
from typing import Optional

from src.data_loader import SDBQuestion, load_subset
from src.pdf_text import (
    download_pdf,
    extract_pdf_pages,
    find_answer_in_text,
)


# Heuristic 评分：综合 substring / number / phrase hit
def text_evidence_score(hit_info: dict, mode: str = "lenient") -> float:
    """把 pdf_text.find_answer_in_text 的输出转成 [0,1] 分数。

    模式：
    - "lenient"：substring + num + phrase 综合（早期版本，phrase 太宽松）
    - "strict"：仅 substring + num（phrase 不计入）
    - "number_only"：只信 num_hits == num_total（最严）
    """
    if mode == "lenient":
        if hit_info["substring_hit"]:
            return 1.0
        s = 0.0
        if hit_info["num_total"] > 0:
            s += 0.5 * (hit_info["num_hits"] / hit_info["num_total"])
        if hit_info["phrase_total"] > 0:
            s += 0.5 * (hit_info["phrase_hits"] / hit_info["phrase_total"])
        return min(1.0, s)
    if mode == "strict":
        if hit_info["substring_hit"]:
            return 1.0
        if hit_info["num_total"] > 0:
            return hit_info["num_hits"] / hit_info["num_total"]
        # 没数字就没信号
        return 0.0
    if mode == "number_only":
        if hit_info["substring_hit"]:
            return 1.0
        if hit_info["num_total"] == 0:
            return 0.0
        return 1.0 if hit_info["num_hits"] == hit_info["num_total"] else 0.0
    if mode == "conservative":
        # 「text-only 答得出」的唯一判据：gold answer 整句出现在 PDF 文本里
        # 这正是 paper claim "chart 答案只在视觉里" 的核心指标
        # 即使 num_hits == num_total，只要句子不出现就视作 text-only 不可答
        return 1.0 if hit_info["substring_hit"] else 0.0
    if mode == "high_bar":
        # 折中：要求 ≥80% 的数字都出现，或者整句出现
        if hit_info["substring_hit"]:
            return 1.0
        if hit_info["num_total"] > 0 and (
            hit_info["num_hits"] / hit_info["num_total"] >= 0.8
        ):
            return 1.0
        return 0.0
    raise ValueError(f"Unknown mode: {mode}")


def text_only_evaluate(
    qs: list[SDBQuestion],
    pdf_dir: str = "./data/pdfs",
    cache_dir: str = "./cache",
    skip_missing_pdfs: bool = True,
    score_mode: str = "strict",
) -> list[dict]:
    """对每个 question 跑 text-only 评估，返回每题结果列表。

    score_mode: lenient | strict | number_only
    """
    from tqdm import tqdm

    out: list[dict] = []
    # 先把所有需要的 PDF 下载下来
    pdf_paths: dict[str, str] = {}
    needed_pdfs = {q.pdf_filename for q in qs}
    print(f"[eval] 需要 {len(needed_pdfs)} 个不同 PDF ...")
    for fn in tqdm(needed_pdfs, desc="下载 PDF"):
        try:
            pdf_paths[fn] = download_pdf(fn, save_dir=pdf_dir, cache_dir=cache_dir)
        except Exception as e:
            print(f"[eval]  下载失败 {fn[:60]}: {e}")
    print(f"[eval] 成功下载 {len(pdf_paths)} / {len(needed_pdfs)} 个 PDF")

    for q in tqdm(qs, desc="text-only 评估"):
        path = pdf_paths.get(q.pdf_filename)
        if path is None:
            if skip_missing_pdfs:
                out.append({"uid": q.uid, "subset": q.subset, "difficulty": q.difficulty,
                            "skipped": True, "score": 0.0})
                continue
            else:
                raise FileNotFoundError(q.pdf_filename)
        try:
            pages = extract_pdf_pages(path)
            text = "\n".join(pages)
            hit = find_answer_in_text(q.answer, text, pages)
            score = text_evidence_score(hit, mode=score_mode)
        except Exception as e:
            print(f"[eval] {q.uid} 失败: {e}")
            hit = {"any_hit": False, "substring_hit": False, "num_hits": 0,
                   "num_total": 0, "phrase_hits": 0, "phrase_total": 0,
                   "evidence_page": None}
            score = 0.0
        out.append({
            "uid": q.uid,
            "subset": q.subset,
            "difficulty": q.difficulty,
            "skipped": False,
            "score": score,
            "substring_hit": hit["substring_hit"],
            "num_hits": hit["num_hits"],
            "num_total": hit["num_total"],
            "phrase_hits": hit["phrase_hits"],
            "phrase_total": hit["phrase_total"],
            "evidence_page": hit["evidence_page"],
        })
    return out


def random_evaluate(
    qs: list[SDBQuestion],
    seed: int = 42,
) -> list[dict]:
    """Random baseline：随机给每个 question 一个 [0, 1] 分数。

    期望 ACC ≈ mean(score_threshold)，用来对照 text-only 的真实信号。
    """
    rng = random.Random(seed)
    out = []
    for q in qs:
        out.append({
            "uid": q.uid,
            "subset": q.subset,
            "difficulty": q.difficulty,
            "skipped": False,
            "score": rng.random(),
            "substring_hit": False,
            "num_hits": 0,
            "num_total": 0,
            "phrase_hits": 0,
            "phrase_total": 0,
            "evidence_page": None,
        })
    return out


def aggregate_acc(
    results: list[dict],
    threshold: float = 0.5,
) -> dict:
    """计算 ACC(τ) — 论文 Eq. 1。

    ACC = mean(1[score >= τ]) over valid (non-skipped) questions.
    """
    valid = [r for r in results if not r.get("skipped", False)]
    if not valid:
        return {"n_valid": 0, "acc": 0.0}
    n_correct = sum(1 for r in valid if r["score"] >= threshold)
    return {
        "n_valid": len(valid),
        "n_correct": n_correct,
        "acc": n_correct / len(valid),
        "threshold": threshold,
    }


def aggregate_by_subset(
    results: list[dict],
    threshold: float = 0.5,
) -> dict[str, dict]:
    """按 subset 分别算 ACC。"""
    by_subset: dict[str, list[dict]] = {}
    for r in results:
        if r.get("skipped", False):
            continue
        by_subset.setdefault(r["subset"], []).append(r)
    return {k: aggregate_acc(v, threshold) for k, v in by_subset.items()}


def aggregate_by_difficulty(
    results: list[dict],
    threshold: float = 0.5,
) -> dict[int, dict]:
    """按 difficulty L1-L5 分别算 ACC。"""
    by_diff: dict[int, list[dict]] = {}
    for r in results:
        if r.get("skipped", False):
            continue
        by_diff.setdefault(r["difficulty"], []).append(r)
    return {k: aggregate_acc(v, threshold) for k, v in sorted(by_diff.items())}
