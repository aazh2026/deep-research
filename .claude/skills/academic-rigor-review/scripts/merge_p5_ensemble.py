#!/usr/bin/env python3
"""
P5 Ensemble 合并脚本（OPT-16）

目的：
- 接受 3 个视角的 P5 输出（skeptic / practitioner / domain_expert）
- 按共识强度（1/2/3 roles）合并 new_defects / competing_explanations
- 对共识 ≥ 2 的缺陷，**强烈建议升级 P0**（写到 ensemble_metadata.p0_recommendations）
- 输出去重 + 共识标注 + 共识升级建议的 merged YAML

设计动机：
- 单次 P5 LLM 调用易漏报（LLM Harmony 测试已验证）
- 3 视角独立 prompt + 独立 LLM 调用 → 漏报率显著下降
- 共识是更强的信号：2+ 视角独立识别同一缺陷 → 高置信度
- 1 视角独有 → 需 P6 单独验证（不直接升级 P0）

用法：
  python merge_p5_ensemble.py \\
    --skeptic p5_skeptic.yaml \\
    --practitioner p5_practitioner.yaml \\
    --domain-expert p5_domain_expert.yaml \\
    --out p5_ensemble_merged.yaml
"""

import argparse
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: 需要 PyYAML. 安装: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# ----------------------------------------------------------------------
# 共识升级规则
# ----------------------------------------------------------------------

# 共识强度 → P0 升级建议
CONSENSUS_P0_RULES = {
    3: "strong_recommend",   # 3 视角都识别 → 强烈建议 P0
    2: "recommend",          # 2 视角独立识别 → 建议升级 P0
    1: "needs_verification",  # 仅 1 视角 → 需 P6 单独验证
}


def normalize_defect_key(d: dict) -> tuple[str, str]:
    """生成去重 key（近似）：(related_claim_id, description 前 20 字符)。

    后续由 _find_matching_key 用 SequenceMatcher 模糊匹配。
    """
    claim = (d.get("related_claim_id") or "").lower().strip()
    desc = (d.get("description") or "")[:20].lower().strip()
    return (claim, desc)


def _key_terms(s: str) -> set[str]:
    """提取关键术语：英文 / 数字 token + 中文 2+ 字符片段。

    中文不分词（避免 jieba 依赖），但通过滑动窗口 + 标点切分得到候选 2-4 字术语。
    """
    import re
    s = s.lower()
    terms = set()

    # 英文 / 数字 token
    for m in re.finditer(r"[a-z0-9]+", s):
        if len(m.group()) >= 2:
            terms.add(m.group())

    # 中文字符切 2-gram（用 unigram + bigram）
    chinese = re.findall(r"[一-鿿]+", s)
    for chunk in chinese:
        # 单字
        for c in chunk:
            terms.add(c)
        # 双字
        for i in range(len(chunk) - 1):
            terms.add(chunk[i:i + 2])

    return terms


def _shared_terms(a: set, b: set) -> int:
    return len(a & b)


def _find_matching_key(defect_map: dict, new_key: tuple[str, str],
                        new_desc: str,
                        seq_threshold: float = 0.40,
                        min_shared_terms: int = 3) -> str | None:
    """在已有 defect_map 中找与 new_key/new_desc 模糊匹配的 key。

    匹配条件（**同时满足**——AND 逻辑，避免假阳性）：
    1. related_claim_id 相同
    2. SequenceMatcher ratio >= seq_threshold
    3. 共享关键术语数 >= min_shared_terms

    返回匹配的现有 key；未找到返回 None。
    """
    if not defect_map:
        return None
    claim, _ = new_key
    new_terms = _key_terms(new_desc)
    for existing_key, entry in defect_map.items():
        existing_claim, _ = existing_key
        if existing_claim != claim:
            continue
        existing_desc = entry.get("description") or ""
        ratio = SequenceMatcher(None, existing_desc, new_desc).ratio()
        if ratio < seq_threshold:
            continue
        existing_terms = _key_terms(existing_desc)
        if _shared_terms(existing_terms, new_terms) < min_shared_terms:
            continue
        return existing_key
    return None


def merge_defects(p5_outputs: dict[str, dict]) -> list[dict]:
    """合并 new_defects，用 SequenceMatcher 模糊匹配去重。

    返回每条 defect 包含 consensus（哪几个 role 识别）字段。
    """
    defect_map: dict[tuple[str, str], dict] = {}

    for role, p5 in p5_outputs.items():
        defects = p5.get("new_defects", [])
        for d in defects:
            key = normalize_defect_key(d)
            desc = d.get("description", "")
            existing_key = _find_matching_key(defect_map, key, desc)

            if existing_key is None:
                # 新建条目
                defect_map[key] = {
                    "id": d.get("id", "?"),
                    "related_claim_id": d.get("related_claim_id"),
                    "evidence_id": d.get("evidence_id"),
                    "textual_position": d.get("textual_position"),
                    "description": d.get("description"),
                    "severity": d.get("severity"),
                    "defect_type": d.get("defect_type"),
                    "why_previous_reviewers_missed": d.get("why_previous_reviewers_missed"),
                    "consensus": [],
                    "consensus_strength": 0,
                    "consensus_roles_detail": [],
                }
                existing_key = key

            entry = defect_map[existing_key]
            if role not in entry["consensus"]:
                entry["consensus"].append(role)
            entry["consensus_strength"] = len(entry["consensus"])
            entry["consensus_roles_detail"].append({
                "role": role,
                "severity": d.get("severity"),
                "defect_type": d.get("defect_type"),
                "evidence_id": d.get("evidence_id"),
                "why_missed": d.get("why_previous_reviewers_missed"),
            })

    # 共识升级：若 ≥ 2 roles 独立识别为 P1，自动建议升级 P0
    for entry in defect_map.values():
        if entry["consensus_strength"] >= 2:
            max_severity = max(
                (d.get("severity", "P3") for d in entry["consensus_roles_detail"]),
                key=lambda s: {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(s, 4),
            )
            entry["max_severity_across_roles"] = max_severity
            entry["consensus_p0_recommendation"] = CONSENSUS_P0_RULES[entry["consensus_strength"]]
        else:
            entry["consensus_p0_recommendation"] = CONSENSUS_P0_RULES[1]

    return list(defect_map.values())


def merge_claim_challenges(p5_outputs: dict[str, dict]) -> list[dict]:
    """合并 core_claim_challenges：按 claim_id + challenge_strength 收集。"""
    challenge_map: dict[str, dict] = {}

    for role, p5 in p5_outputs.items():
        challenges = p5.get("core_claim_challenges", [])
        for c in challenges:
            claim_id = c.get("claim_id", "?")
            if claim_id not in challenge_map:
                challenge_map[claim_id] = {
                    "claim_id": claim_id,
                    "original_claim": c.get("original_claim"),
                    "challenges_by_role": {},
                    "consensus_strength": 0,
                }
            entry = challenge_map[claim_id]
            entry["challenges_by_role"][role] = {
                "strongest_counter_argument": c.get("strongest_counter_argument"),
                "challenge_strength": c.get("challenge_strength"),
                "could_change_conclusion": c.get("could_change_conclusion"),
            }
            entry["consensus_strength"] = len(entry["challenges_by_role"])

    return list(challenge_map.values())


def collect_p0_recommendations(merged_defects: list[dict]) -> list[dict]:
    """从合并的 defects 中提取共识升级 P0 建议。"""
    recs = []
    for d in merged_defects:
        if d.get("consensus_p0_recommendation") in ("strong_recommend", "recommend"):
            recs.append({
                "defect_id": d["id"],
                "related_claim_id": d.get("related_claim_id"),
                "consensus_strength": d["consensus_strength"],
                "consensus_roles": d["consensus"],
                "max_severity_across_roles": d.get("max_severity_across_roles"),
                "recommendation": d["consensus_p0_recommendation"],
                "rationale": _build_p0_rationale(d),
            })
    return recs


def _build_p0_rationale(d: dict) -> str:
    """根据共识生成 P0 升级理由。"""
    n = d["consensus_strength"]
    roles = " + ".join(d["consensus"])
    if n == 3:
        return (
            f"3 个独立视角（{roles}）均识别该缺陷。"
            f"高置信度 P0 缺陷，建议 P6 优先纳入 critical_defects 并触发 verdict 降级。"
        )
    if n == 2:
        return (
            f"2 个独立视角（{roles}）识别该缺陷。"
            f"中等置信度 P0 升级建议，P6 应基于 evidence_id 验证后决策。"
        )
    return f"仅 1 视角识别，需 P6 单独验证。"


def compute_value_stats(p5_outputs: dict[str, dict]) -> dict:
    """汇总 3 视角的 value_self_assessment。"""
    stats = {"by_role": {}, "average_total": 0, "high_value_total": 0}
    totals = []
    for role, p5 in p5_outputs.items():
        vs = p5.get("p5_metadata", {}).get("value_self_assessment", {})
        if vs:
            stats["by_role"][role] = vs
            totals.append(vs.get("total", 0))
            stats["high_value_total"] += vs.get("high_value_count", 0)
    stats["average_total"] = round(sum(totals) / len(totals), 2) if totals else 0
    return stats


def merge(p5_files: dict[str, Path]) -> dict[str, Any]:
    """合并 3 个 P5 输出。"""
    p5_outputs = {}
    for role, path in p5_files.items():
        if not path.exists():
            print(f"WARN: {role} 文件不存在: {path}", file=sys.stderr)
            continue
        p5_outputs[role] = yaml.safe_load(path.read_text())

    if not p5_outputs:
        return {"error": "没有有效的 P5 输出"}

    if len(p5_outputs) < 3:
        print(f"WARN: 只有 {len(p5_outputs)}/3 个视角（{list(p5_outputs.keys())}）",
              file=sys.stderr)

    merged_defects = merge_defects(p5_outputs)
    merged_challenges = merge_claim_challenges(p5_outputs)
    p0_recs = collect_p0_recommendations(merged_defects)
    value_stats = compute_value_stats(p5_outputs)

    return {
        "artifact_type": "p5_ensemble_merged",
        "version": "1.0",
        "ensemble_metadata": {
            "roles_merged": list(p5_outputs.keys()),
            "merge_time": _now_iso(),
            "total_input_defects": sum(
                len(p5.get("new_defects", [])) for p5 in p5_outputs.values()
            ),
            "total_unique_defects": len(merged_defects),
            "consensus_distribution": {
                "3_roles": sum(1 for d in merged_defects if d["consensus_strength"] == 3),
                "2_roles": sum(1 for d in merged_defects if d["consensus_strength"] == 2),
                "1_role": sum(1 for d in merged_defects if d["consensus_strength"] == 1),
            },
            "p0_recommendations_count": len(p0_recs),
        },
        "p5_metadata_merged": {
            "value_stats": value_stats,
            "focus_dimensions_covered": _union_focus_dimensions(p5_outputs),
        },
        "merged_new_defects": merged_defects,
        "merged_claim_challenges": merged_challenges,
        "p0_recommendations": p0_recs,
        "remaining_individual_outputs": p5_outputs,  # 保留原始以便追溯
    }


def _union_focus_dimensions(p5_outputs: dict[str, dict]) -> list[str]:
    """汇总所有视角的 focus_dimensions。"""
    dims = set()
    for p5 in p5_outputs.values():
        for d in p5.get("p5_metadata", {}).get("focus_dimensions", []):
            dims.add(d)
    return sorted(dims)


def _now_iso() -> str:
    from datetime import datetime
    return datetime.now().isoformat(timespec="seconds")


def format_human(report: dict) -> str:
    """人类可读输出。"""
    if "error" in report:
        return f"ERROR: {report['error']}"

    em = report["ensemble_metadata"]
    lines = [
        "=" * 60,
        "P5 Ensemble 合并报告",
        "=" * 60,
        f"Roles merged: {', '.join(em['roles_merged'])}",
        "",
        f"Total input defects:    {em['total_input_defects']}",
        f"Total unique defects:   {em['total_unique_defects']}",
        "",
        "Consensus distribution:",
        f"  3 roles agree:   {em['consensus_distribution']['3_roles']}",
        f"  2 roles agree:   {em['consensus_distribution']['2_roles']}",
        f"  1 role only:     {em['consensus_distribution']['1_role']}",
        "",
        f"P0 recommendations:     {em['p0_recommendations_count']}",
    ]

    if report["p0_recommendations"]:
        lines.append("")
        lines.append("--- P0 Upgrade Recommendations ---")
        for r in report["p0_recommendations"]:
            lines.append(f"  {r['defect_id']} ({r['consensus_strength']} roles: {', '.join(r['consensus_roles'])})")
            lines.append(f"    → {r['recommendation']}")
            lines.append(f"    {r['rationale']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="P5 Ensemble 合并：3 视角 → 共识标注 + P0 升级建议"
    )
    parser.add_argument("--skeptic", type=Path, required=True,
                        help="skeptic 视角 P5 输出")
    parser.add_argument("--practitioner", type=Path, required=True,
                        help="practitioner 视角 P5 输出")
    parser.add_argument("--domain-expert", type=Path, required=True,
                        help="domain_expert 视角 P5 输出")
    parser.add_argument("--out", type=Path, default=None,
                        help="输出 merged YAML 路径")
    args = parser.parse_args()

    p5_files = {
        "skeptic": args.skeptic,
        "practitioner": args.practitioner,
        "domain_expert": args.domain_expert,
    }

    report = merge(p5_files)

    if args.out:
        args.out.write_text(
            yaml.safe_dump(report, allow_unicode=True, sort_keys=False)
        )
        print(f"已写入: {args.out}", file=sys.stderr)
        print(format_human(report))
    else:
        print(yaml.safe_dump(report, allow_unicode=True, sort_keys=False))

    sys.exit(0 if report.get("p0_recommendations") is not None else 1)


if __name__ == "__main__":
    main()
