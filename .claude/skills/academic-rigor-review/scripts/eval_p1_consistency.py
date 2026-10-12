#!/usr/bin/env python3
"""
P1 Consistency Evaluator

目的：评测 P1 (研究对象解析) 的稳定性。
方法：让两个独立 P1 跑同一篇文章，比较它们提取的 claim 集合。

设计动机：
- P1 的输出是整个工作流的事实层，下游 P2-P6 都依赖 P1 的 C-NNN 列表
- 如果 P1 对同一篇文章两次跑结果差异大，整个评审就不可靠
- 用 Jaccard 相似度 + 文本相似度量化一致性

用法：
  python eval_p1_consistency.py <p1_output_a.yaml> <p1_output_b.yaml> [--json]

退出码：
  0 = 评估通过（高一致性）
  1 = 一致性低（提示需要改进 P1 prompt）
  2 = 输入文件错误
"""

import argparse
import json
import sys
from pathlib import Path
from difflib import SequenceMatcher
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: 需要 PyYAML. 安装: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# ----------------------------------------------------------------------
# 加载与校验
# ----------------------------------------------------------------------

def load_p1(path: Path) -> dict[str, Any]:
    """加载 P1 YAML 并做最小校验。"""
    if not path.exists():
        print(f"ERROR: 文件不存在: {path}", file=sys.stderr)
        sys.exit(2)
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as e:
        print(f"ERROR: YAML 解析失败 ({path}): {e}", file=sys.stderr)
        sys.exit(2)

    if not isinstance(data, dict) or "claims" not in data:
        print(f"ERROR: {path} 不是有效的 P1 artifact（缺少 claims 字段）", file=sys.stderr)
        sys.exit(2)

    if not isinstance(data["claims"], list) or len(data["claims"]) == 0:
        print(f"ERROR: {path} 的 claims 字段为空或非列表", file=sys.stderr)
        sys.exit(2)

    return data


# ----------------------------------------------------------------------
# 比较指标
# ----------------------------------------------------------------------

def jaccard_similarity(set_a: set, set_b: set) -> float:
    """集合 Jaccard 相似度 |A ∩ B| / |A ∪ B|。"""
    if not set_a and not set_b:
        return 1.0
    union = set_a | set_b
    if not union:
        return 1.0
    return len(set_a & set_b) / len(union)


def text_similarity(text_a: str, text_b: str) -> float:
    """两个字符串的 SequenceMatcher 相似度（0-1）。"""
    return SequenceMatcher(None, text_a, text_b).ratio()


def best_text_match(target: str, candidates: list[str]) -> tuple[float, str | None]:
    """找到 candidates 中与 target 文本最相似的，返回 (相似度, 匹配文本)。"""
    if not candidates:
        return 0.0, None
    best_score = 0.0
    best_text = None
    for c in candidates:
        score = text_similarity(target, c)
        if score > best_score:
            best_score = score
            best_text = c
    return best_score, best_text


def count_by(items: list, key_fn) -> dict:
    """按 key_fn 分组计数。"""
    out: dict = {}
    for item in items:
        k = key_fn(item)
        out[k] = out.get(k, 0) + 1
    return out


# ----------------------------------------------------------------------
# 主评估逻辑
# ----------------------------------------------------------------------

def evaluate(p1_a: dict, p1_b: dict) -> dict[str, Any]:
    """对比两份 P1 输出，返回完整评估报告。"""
    claims_a = p1_a["claims"]
    claims_b = p1_b["claims"]

    # 0. 文章同源校验
    #    C-NNN ID 是 article-scoped 的——如果两篇文章的 P1 各自从 C-001 开始，
    #    ID 重合只意味着巧合，不代表同主张。
    #    用 research_object_overview.article_type + 前 2 条 claim 文本 hash 作为简易指纹。
    article_type_a = p1_a.get("research_object_overview", {}).get("article_type", "")
    article_type_b = p1_b.get("research_object_overview", {}).get("article_type", "")
    type_match = article_type_a == article_type_b and bool(article_type_a)

    # 1. 基本数量
    count_a = len(claims_a)
    count_b = len(claims_b)

    # 2. C-NNN ID 集合（精确 ID 重合度）
    ids_a = {c["id"] for c in claims_a}
    ids_b = {c["id"] for c in claims_b}
    id_overlap = ids_a & ids_b
    id_only_a = ids_a - ids_b
    id_only_b = ids_b - ids_a
    id_jaccard = jaccard_similarity(ids_a, ids_b)

    # 3. Claim 文本相似度（不依赖 ID）
    #    对 A 中每条 claim，找 B 中文本最相似的
    texts_b = [c.get("text", "") for c in claims_b]
    text_scores = []
    text_matches = []
    for ca in claims_a:
        score, match = best_text_match(ca.get("text", ""), texts_b)
        text_scores.append(score)
        text_matches.append({
            "claim_a_id": ca["id"],
            "claim_a_text_preview": ca.get("text", "")[:80],
            "best_match_score": round(score, 3),
            "best_match_text_preview": (match or "")[:80],
        })

    avg_text_sim = sum(text_scores) / len(text_scores) if text_scores else 0.0
    min_text_sim = min(text_scores) if text_scores else 0.0
    high_text_matches = sum(1 for s in text_scores if s >= 0.5)
    high_text_ratio = high_text_matches / len(text_scores) if text_scores else 0.0

    # 4. Importance 分布对比
    importance_a = count_by(claims_a, lambda c: c.get("importance", "unknown"))
    importance_b = count_by(claims_b, lambda c: c.get("importance", "unknown"))

    # 5. Type 分布对比
    type_a = count_by(claims_a, lambda c: c.get("type", "unknown"))
    type_b = count_by(claims_b, lambda c: c.get("type", "unknown"))

    # 6. 综合判定
    #    设计目标（来自 design.md 与 OPTIMIZATION_LOG.md R3）：
    #    同一篇文章两次 P1 跑，C-NNN 集合重合度 > 80%
    #    主指标是 ID Jaccard（精确 ID 最重要），
    #    文本相似度是次要指标（检测"近重复但不同 ID"的情况）

    # 6.1 文章同源门禁：如果两篇文章显然不同（avg_text_sim 极低），
    #     报告 error 而不是 high_consistency，避免 ID 重合的假阳性
    if avg_text_sim < 0.15:
        verdict = "different_articles"
        recommendation = (
            "两篇文章的文本相似度极低（avg_text_sim={:.3f} < 0.15），\n"
            "说明这两份 P1 输出针对的是不同文章。\n"
            "本脚本只用于评测同一篇文章的两次 P1 跑一致性，\n"
            "不支持跨文章比较。\n"
            "  C-NNN ID 在不同文章的 P1 中是各自从 C-001 开始的，\n"
            "  因此 ID 重合不代表同一主张。"
        ).format(avg_text_sim)
    elif id_jaccard >= 0.8:
        verdict = "high_consistency"
        recommendation = "P1 输出稳定，下游 P2-P6 可放心消费"
    elif id_jaccard >= 0.5:
        verdict = "moderate_consistency"
        recommendation = (
            "P1 输出中等一致（ID Jaccard={:.2f}，低于 0.8 目标）。建议：\n"
            "  1) 检查 P1 prompt 是否有歧义\n"
            "  2) 降低 temperature 至 0 提高稳定性\n"
            "  3) 人工审查 only_in_a / only_in_b 看哪一方更准确\n"
            "  4) 合并：是否应将 only_in_a 和 only_in_b 的 claim 视为同一主张？"
        ).format(id_jaccard)
    else:
        verdict = "low_consistency"
        recommendation = (
            "P1 输出不稳定（ID Jaccard={:.2f}，远低于 0.8 目标）。强烈建议：\n"
            "  1) 降低 temperature 至 0\n"
            "  2) 强化 P1 prompt 中的 ID 分配规则\n"
            "  3) 考虑是否需要 example 引导\n"
            "  4) 检查 P1 prompt 是否有让模型自由发挥的空间过大"
        ).format(id_jaccard)

    return {
        "verdict": verdict,
        "recommendation": recommendation,
        "summary": {
            "count_a": count_a,
            "count_b": count_b,
            "id_jaccard": round(id_jaccard, 3),
            "id_overlap_count": len(id_overlap),
            "id_overlap_ids": sorted(id_overlap),
            "id_only_in_a": sorted(id_only_a),
            "id_only_in_b": sorted(id_only_b),
            "avg_text_similarity": round(avg_text_sim, 3),
            "min_text_similarity": round(min_text_sim, 3),
            "high_text_match_ratio": round(high_text_ratio, 3),
            "importance_a": importance_a,
            "importance_b": importance_b,
            "type_a": type_a,
            "type_b": type_b,
        },
        "text_match_details": text_matches,
    }


# ----------------------------------------------------------------------
# 报告输出
# ----------------------------------------------------------------------

def format_human(report: dict, path_a: Path, path_b: Path) -> str:
    """人类可读的评估报告。"""
    s = report["summary"]
    v = report["verdict"]
    rec = report["recommendation"]

    verdict_emoji = {
        "high_consistency": "✓",
        "moderate_consistency": "~",
        "low_consistency": "✗",
        "different_articles": "?",
    }

    lines = [
        "=" * 60,
        "P1 Consistency Evaluation Report",
        "=" * 60,
        f"A: {path_a}",
        f"B: {path_b}",
        "",
        f"Verdict: [{verdict_emoji.get(v, '?')}] {v}",
        "",
        "--- Summary ---",
        f"  Claim count:    A={s['count_a']}, B={s['count_b']}",
        f"  ID Jaccard:     {s['id_jaccard']:.3f}  (target: ≥ 0.8)",
        f"  ID overlap:     {s['id_overlap_count']}  ({', '.join(s['id_overlap_ids']) or 'none'})",
        f"  ID only in A:   {', '.join(s['id_only_in_a']) or 'none'}",
        f"  ID only in B:   {', '.join(s['id_only_in_b']) or 'none'}",
        f"  Avg text sim:   {s['avg_text_similarity']:.3f}  (target: ≥ 0.7)",
        f"  Min text sim:   {s['min_text_similarity']:.3f}",
        f"  High match %:   {s['high_text_match_ratio']:.3f}  (text sim ≥ 0.5)",
        "",
        "--- Importance Distribution ---",
        f"  A: {s['importance_a']}",
        f"  B: {s['importance_b']}",
        "",
        "--- Type Distribution ---",
        f"  A: {s['type_a']}",
        f"  B: {s['type_b']}",
        "",
        "--- Recommendation ---",
        rec,
        "",
    ]

    # 显示低相似度的 claim 对（可能存在问题）
    low_matches = [m for m in report["text_match_details"] if m["best_match_score"] < 0.4]
    if low_matches:
        lines.append("--- Low-similarity claims (warning) ---")
        for m in low_matches:
            lines.append(f"  {m['claim_a_id']}: {m['claim_a_text_preview']}...")
            lines.append(f"    best match: {m['best_match_text_preview']}... (sim={m['best_match_score']})")
        lines.append("")

    return "\n".join(lines)


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="评测 P1 (研究对象解析) 在同一篇文章上的两次输出一致性"
    )
    parser.add_argument("p1_a", type=Path, help="第一次 P1 输出的 YAML 文件")
    parser.add_argument("p1_b", type=Path, help="第二次 P1 输出的 YAML 文件")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    args = parser.parse_args()

    p1_a = load_p1(args.p1_a)
    p1_b = load_p1(args.p1_b)

    report = evaluate(p1_a, p1_b)
    report["inputs"] = {
        "p1_a": str(args.p1_a),
        "p1_b": str(args.p1_b),
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_human(report, args.p1_a, args.p1_b))

    # 退出码
    # high_consistency 退出 0
    # moderate / low / different_articles 都退出 1（提示需要审查或输入错误）
    if report["verdict"] == "high_consistency":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
