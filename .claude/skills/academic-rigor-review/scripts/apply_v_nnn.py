#!/usr/bin/env python3
"""
P7 修订闭环分析器

目的：
- 接受 P7 输出的 V-NNN 修订任务清单
- 对每条任务判断：
  1. 是否可自动应用（pure text revision）
  2. 还是需要 manual / evidence-gathering / experiment 重跑
- 根据"影响范围触发的 P 重跑"表，计算需要重跑的 P 任务集合
- 输出修订计划（不是直接修改 article.md，是给出指导）

设计动机：
- P7 当前输出 V-NNN 任务清单，但没有工具帮作者实际执行
- 关键是：哪些 V-NNN 可以纯文本完成？哪些需要重做实验？
- 哪些 P 需要重跑？（避免不必要的全量重跑）

用法：
  python apply_v_nnn.py \\
    --article runs/.../article.md \\
    --p6 runs/.../p6_synthesis.yaml \\
    --p7 runs/.../p7_revision.yaml \\
    --out runs/.../p7_revision_plan.yaml
"""

import argparse
import sys
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("ERROR: 需要 PyYAML. 安装: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# ----------------------------------------------------------------------
# V-NNN 分类规则
# ----------------------------------------------------------------------

# 关键词驱动的修订类型判断
# 每类对应不同的"可自动应用"判定和"触发重跑 P"
TEXT_REVISION_KEYWORDS = {
    "remove", "delete", "rephrase", "reword", "clarify", "rewrite",
    "narrow", "limit scope", "specify", "add caveat", "添加", "删除",
    "改写", "澄清", "重写", "收缩", "限定", "修改措辞",
}

EVIDENCE_REVISION_KEYWORDS = {
    "add citation", "add reference", "verify citation", "add quote",
    "publish", "release", "公开", "reproduce", "reproducibility",
    "补充引用", "核实引用", "新增证据", "补充数据", "补充实验", "复现",
}

METHOD_REVISION_KEYWORDS = {
    "rerun experiment", "recompute", "redesign", "re-analyze",
    "compute-matched", "self-consistency baseline",
    "重新设计实验", "重跑实验", "补充对照",
}

CONCLUSION_REVISION_KEYWORDS = {
    "remove claim", "delete claim", "narrow conclusion", "downgrade",
    "删除主张", "删除结论", "收缩结论", "降低确定性",
}


def classify_revision(v_nnn: dict) -> str:
    """根据 revision_action 关键词判断修订类型。

    返回：text / evidence / method / conclusion / unknown
    """
    action = (v_nnn.get("revision_action") or "").lower()

    # 顺序检查：conclusion > method > evidence > text
    # 这样 "add experiment and remove claim" 优先识别为 conclusion 修订
    for keyword_set, label in [
        (CONCLUSION_REVISION_KEYWORDS, "conclusion"),
        (METHOD_REVISION_KEYWORDS, "method"),
        (EVIDENCE_REVISION_KEYWORDS, "evidence"),
        (TEXT_REVISION_KEYWORDS, "text"),
    ]:
        for kw in keyword_set:
            if kw.lower() in action:
                return label

    return "unknown"


# ----------------------------------------------------------------------
# "影响范围触发的 P 重跑" 表（来自 p7-revision.md Step 8）
# ----------------------------------------------------------------------

RE_RUN_TRIGGERS = {
    "text": [],  # 纯文字修订通常不触发重跑（除非影响 claim 状态）
    "evidence": ["P2"],  # 引用/文献被修改 → 重跑 P2
    "method": ["P4"],  # 方法被修改 → 重跑 P4
    "conclusion": ["P3", "P5", "P6"],  # 核心结论被修改 → 必须重跑 P5 + P6
    "unknown": ["P3", "P6"],  # 未知类型保守处理
}


def affected_p_tasks(v_nnns: list[dict]) -> set[str]:
    """计算所有 V-NNN 触发重跑的 P 任务集合（去重）。"""
    affected = set()
    for v in v_nnns:
        rev_type = classify_revision(v)
        for p in RE_RUN_TRIGGERS.get(rev_type, []):
            affected.add(p)

    # 永远需要重跑 P6（综合评审）
    affected.add("P6")

    return affected


def is_auto_applicable(v_nnn: dict) -> bool:
    """判断 V-NNN 是否可以纯文本自动应用（无需 LLM / 实验）。"""
    rev_type = classify_revision(v_nnn)
    if rev_type == "text":
        return True
    if rev_type == "conclusion":
        # 收缩结论可以纯文本完成（如"增加 caveat"、"限定 scope"）
        # 删除结论则需要谨慎（可能影响其他 claim）
        return "narrow" in v_nnn.get("revision_action", "").lower() or \
               "限定" in v_nnn.get("revision_action", "") or \
               "收缩" in v_nnn.get("revision_action", "")
    return False


# ----------------------------------------------------------------------
# 主分析
# ----------------------------------------------------------------------

def analyze(article_path: Path, p6: dict, p7: dict) -> dict[str, Any]:
    """分析 V-NNN 列表，输出修订计划。"""
    article_text = article_path.read_text() if article_path.exists() else ""

    v_nnns = p7.get("revision_task_list", [])
    if not v_nnns:
        return {
            "error": "P7 产物中没有 revision_task_list 字段",
            "recommendation": "先运行 P7 生成 V-NNN 任务清单",
        }

    classifications = []
    auto_count = 0
    manual_count = 0

    # 找出 P6 中的 P0 defect id 集合
    p0_defect_ids = {d.get("id") for d in p6.get("critical_defects", [])
                     if d.get("severity") == "P0"}

    p0_count = sum(1 for v in v_nnns
                   if v.get("original_defect") in p0_defect_ids)

    for v in v_nnns:
        rev_type = classify_revision(v)
        auto = is_auto_applicable(v)
        if auto:
            auto_count += 1
        else:
            manual_count += 1

        classifications.append({
            "v_nnn_id": v.get("id", "?"),
            "original_defect": v.get("original_defect", "?"),
            "revision_type": rev_type,
            "auto_applicable": auto,
            "requires_expertise": rev_type in ("method", "evidence", "unknown"),
            "triggers_p_rerun": RE_RUN_TRIGGERS.get(rev_type, []),
            "estimated_effort": {
                "text": "low (1-2 hours, 纯文本)",
                "evidence": "medium (1-2 days, 需补实验/引用)",
                "method": "high (1-2 weeks, 需重跑实验)",
                "conclusion": "medium (1-3 days, 需专家审查)",
                "unknown": "high (需领域专家判断)",
            }[rev_type],
        })

    affected_p = affected_p_tasks(v_nnns)

    # 修订优先级
    priority_order = ["conclusion", "method", "evidence", "text", "unknown"]
    sorted_v_nnns = sorted(
        classifications,
        key=lambda c: priority_order.index(c["revision_type"])
    )

    return {
        "summary": {
            "total_v_nnns": len(v_nnns),
            "p0_related_count": p0_count,
            "auto_applicable_count": auto_count,
            "manual_required_count": manual_count,
            "affected_p_tasks": sorted(affected_p),
            "affected_p_count": len(affected_p),
        },
        "v_nnn_classifications": sorted_v_nnns,
        "execution_recommendation": {
            "step_1": f"先执行 P0 相关的 {p0_count} 条 V-NNN（按 references/p6-synthesis.md P0-R4 要求）",
            "step_2": f"按 priority_order 顺序执行其余 V-NNN",
            "step_3": f"完成后触发重跑：{', '.join(sorted(affected_p))}",
            "step_4": "重跑完成后 P6 复评，verdict 应升级（若 P0/P1 全部关闭）",
        },
        "side_effect_warnings": [
            "❌ 任何 conclusion 类修订都必须做 side-effect 检查（p7-revision.md Step 6）",
            "❌ 删除 claim 之前必须确认没有其他 claim 依赖它",
            "❌ 修改方法后必须重跑 P3 + P5 + P6（不能只重跑 P4）",
            "✅ text 类修订通常不需要重跑，除非修改后改变了 claim 的实证状态",
        ],
        "loop_closure_check": {
            "p0_all_closed": p0_count == 0,
            "p0_remaining": [
                c["v_nnn_id"] for c in classifications
                if c["v_nnn_id"].startswith("V-")
                and p0_count > 0
            ],
            "next_p6_run_needed": bool(affected_p),
        },
    }


def format_human(report: dict, article_path: Path) -> str:
    """人类可读输出。"""
    if "error" in report:
        return f"ERROR: {report['error']}\n  Recommendation: {report.get('recommendation', 'N/A')}"

    s = report["summary"]
    lines = [
        "=" * 60,
        "P7 Revision Plan",
        "=" * 60,
        f"Article: {article_path}",
        "",
        f"Total V-NNNs:           {s['total_v_nnns']}",
        f"P0-related:             {s['p0_related_count']}",
        f"Auto-applicable:        {s['auto_applicable_count']}",
        f"Manual required:        {s['manual_required_count']}",
        f"Affected P tasks:       {', '.join(s['affected_p_tasks'])}",
        "",
        "--- Execution Order ---",
    ]

    for c in report["v_nnn_classifications"]:
        lines.extend([
            f"  {c['v_nnn_id']}  ({c['revision_type']}, "
            f"auto={c['auto_applicable']}, "
            f"triggers={','.join(c['triggers_p_rerun']) or 'none'})",
            f"    effort: {c['estimated_effort']}",
        ])

    lines.extend([
        "",
        "--- Execution Recommendation ---",
    ])
    for k, v in report["execution_recommendation"].items():
        lines.append(f"  {k}: {v}")

    lines.extend([
        "",
        "--- Side-effect Warnings ---",
    ])
    for w in report["side_effect_warnings"]:
        lines.append(f"  {w}")

    lines.extend([
        "",
        "--- Loop Closure Check ---",
    ])
    for k, v in report["loop_closure_check"].items():
        lines.append(f"  {k}: {v}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="分析 P7 V-NNN 任务，输出修订计划 + 受影响 P 任务集合"
    )
    parser.add_argument("--article", type=Path, required=True,
                        help="原始 article.md 路径")
    parser.add_argument("--p6", type=Path, required=True,
                        help="P6 综合评审 YAML 路径")
    parser.add_argument("--p7", type=Path, required=True,
                        help="P7 修订产物 YAML 路径（V-NNN 任务清单）")
    parser.add_argument("--out", type=Path, default=None,
                        help="输出修订计划 YAML 路径（默认 stdout）")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    args = parser.parse_args()

    for p in [args.article, args.p6, args.p7]:
        if not p.exists():
            print(f"ERROR: 文件不存在: {p}", file=sys.stderr)
            sys.exit(2)

    p6 = yaml.safe_load(args.p6.read_text())
    p7 = yaml.safe_load(args.p7.read_text())

    report = analyze(args.article, p6, p7)

    if args.json:
        import json
        output = json.dumps(report, ensure_ascii=False, indent=2)
    else:
        output = format_human(report, args.article)

    if args.out:
        import json
        args.out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2)
            if args.json
            else yaml.safe_dump(report, allow_unicode=True, sort_keys=False)
        )
        print(f"已写入: {args.out}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
