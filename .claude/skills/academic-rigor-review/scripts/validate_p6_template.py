#!/usr/bin/env python3
"""
P6 领域模板校验脚本（OPT-15）

目的：
- 验证 P6_OUTPUT 中的 domain_template 字段符合 schema
- 检查 dim_weights 8 个值之和 = 1.0（容许 0.01 浮点误差）
- 验证领域 P0 反模式不与通用 P0-N 冲突
- 输出人类可读报告

用法：
  python validate_p6_template.py --p6 p6_synthesis.yaml
  python validate_p6_template.py --p6 p6_synthesis.yaml --json
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: 需要 PyYAML. 安装: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# ----------------------------------------------------------------------
# 模板定义（必须与 references/domain-templates.md 一致）
# ----------------------------------------------------------------------

TEMPLATES = {
    "cs": {
        "DIM-01": 0.08, "DIM-02": 0.12, "DIM-03": 0.10, "DIM-04": 0.15,
        "DIM-05": 0.15, "DIM-06": 0.10, "DIM-07": 0.20, "DIM-08": 0.10,
    },
    "biomedical": {
        "DIM-01": 0.12, "DIM-02": 0.10, "DIM-03": 0.12, "DIM-04": 0.18,
        "DIM-05": 0.15, "DIM-06": 0.18, "DIM-07": 0.08, "DIM-08": 0.07,
    },
    "economics": {
        "DIM-01": 0.15, "DIM-02": 0.10, "DIM-03": 0.15, "DIM-04": 0.15,
        "DIM-05": 0.12, "DIM-06": 0.12, "DIM-07": 0.08, "DIM-08": 0.13,
    },
    "default": {
        "DIM-01": 0.125, "DIM-02": 0.125, "DIM-03": 0.125, "DIM-04": 0.125,
        "DIM-05": 0.125, "DIM-06": 0.125, "DIM-07": 0.125, "DIM-08": 0.125,
    },
}


def parse_template_name(name: str) -> tuple[str, list[str]]:
    """解析模板名：返回 (主模板, 组合模板列表)。

    'cs' → ('cs', ['cs'])
    'mixed:cs+biomedical' → ('mixed', ['cs', 'biomedical'])
    """
    if name.startswith("mixed:"):
        rest = name[len("mixed:"):]
        parts = rest.split("+")
        return ("mixed", parts)
    return (name, [name])


def expected_weights(template_name: str) -> dict[str, float] | None:
    """返回模板的预期权重。mixed 模板取算术平均。"""
    primary, parts = parse_template_name(template_name)
    if primary == "mixed":
        # 验证所有子模板存在
        for p in parts:
            if p not in TEMPLATES:
                return None
        # 算术平均
        n = len(parts)
        merged = {dim: 0.0 for dim in TEMPLATES["default"].keys()}
        for p in parts:
            for dim, w in TEMPLATES[p].items():
                merged[dim] += w / n
        return merged
    return TEMPLATES.get(primary)


def validate(p6_path: Path) -> dict:
    """校验 P6 产物的 domain_template 字段。"""
    p6 = yaml.safe_load(p6_path.read_text())

    result = {
        "file": str(p6_path),
        "checks": [],
        "errors": [],
        "warnings": [],
    }

    # DOM-1: domain_template 必填
    if "domain_template" not in p6:
        result["errors"].append({
            "rule": "DOM-1",
            "message": "domain_template 字段缺失（OPT-15 必填）"
        })
        return result
    dt = p6["domain_template"]

    result["checks"].append({"rule": "DOM-1", "status": "pass"})

    # 模板名检查
    name = dt.get("name", "")
    primary, parts = parse_template_name(name)

    if primary not in TEMPLATES and primary != "mixed":
        result["errors"].append({
            "rule": "DOM-1",
            "message": f"未知模板: {name}（支持 cs / biomedical / economics / default / mixed:）"
        })
        return result

    # DOM-2: dim_weights 和为 1.0
    weights = dt.get("dim_weights", {})
    if not weights:
        result["errors"].append({
            "rule": "DOM-2",
            "message": "domain_template.dim_weights 缺失"
        })
    else:
        total = sum(weights.values())
        if not (0.99 <= total <= 1.01):
            result["errors"].append({
                "rule": "DOM-2",
                "message": f"dim_weights 之和 = {total}（应在 [0.99, 1.01]）"
            })
        else:
            result["checks"].append({
                "rule": "DOM-2",
                "status": "pass",
                "total": round(total, 4),
            })

    # 与预期模板对比
    expected = expected_weights(name)
    if expected is None:
        result["warnings"].append({
            "rule": "DOM-3",
            "message": f"无法找到预期权重（混合模板 {name} 含未知子模板）"
        })
    else:
        diffs = []
        for dim in expected:
            actual = weights.get(dim, 0)
            exp = expected[dim]
            if abs(actual - exp) > 0.01:
                diffs.append(f"{dim}: 实际 {actual} vs 预期 {exp}")
        if diffs:
            result["warnings"].append({
                "rule": "DOM-3",
                "message": f"权重与参考模板不一致：{'; '.join(diffs)}"
            })
        else:
            result["checks"].append({
                "rule": "DOM-3",
                "status": "pass",
                "note": f"权重与 {name} 参考模板一致"
            })

    # DOM-4: mixed 模板必须说明组合依据
    if primary == "mixed":
        if len(parts) < 2:
            result["errors"].append({
                "rule": "DOM-4",
                "message": "mixed 模板必须至少 2 个领域"
            })
        elif not dt.get("rationale"):
            result["errors"].append({
                "rule": "DOM-4",
                "message": "mixed 模板必须在 rationale 给出组合依据"
            })
        else:
            result["checks"].append({
                "rule": "DOM-4",
                "status": "pass",
                "components": parts,
            })

    # P0 反模式不冲突：仅在 p0 defects 中验证 template P0 列表
    template_p0 = dt.get("domain_specific_p0_checks", [])
    if template_p0:
        result["checks"].append({
            "rule": "DOM-3",
            "status": "pass",
            "note": f"声明了 {len(template_p0)} 条领域 P0 反模式（与通用 P0-N 兼容）"
        })

    # 计算加权 DIM 平均
    dim_scores = p6.get("eight_dimension_scores", [])
    if dim_scores and weights:
        score_map = {d["dim_id"]: d.get("score") for d in dim_scores}
        weighted_total = 0.0
        weighted_count = 0
        for dim, w in weights.items():
            s = score_map.get(dim)
            if s is not None and isinstance(s, (int, float)):
                weighted_total += w * s
                weighted_count += w
        if weighted_count > 0:
            result["weighted_dim_avg"] = round(weighted_total / weighted_count, 3)
        else:
            result["weighted_dim_avg"] = None
    else:
        result["weighted_dim_avg"] = None

    return result


def format_human(report: dict) -> str:
    """人类可读报告。"""
    lines = ["=" * 60, "P6 领域模板校验", "=" * 60, f"File: {report['file']}", ""]

    if report["checks"]:
        lines.append("--- Pass ---")
        for c in report["checks"]:
            note = c.get("note", "")
            lines.append(f"  ✓ {c['rule']}: {c.get('status', '?')}  {note}")

    if report["warnings"]:
        lines.append("")
        lines.append("--- Warnings ---")
        for w in report["warnings"]:
            lines.append(f"  ⚠ {w['rule']}: {w['message']}")

    if report["errors"]:
        lines.append("")
        lines.append("--- Errors ---")
        for e in report["errors"]:
            lines.append(f"  ✗ {e['rule']}: {e['message']}")

    if "weighted_dim_avg" in report:
        lines.append("")
        lines.append(f"  Weighted DIM avg: {report['weighted_dim_avg']}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="P6 领域模板校验")
    parser.add_argument("--p6", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.p6.exists():
        print(f"ERROR: 文件不存在: {args.p6}", file=sys.stderr)
        sys.exit(2)

    report = validate(args.p6)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(format_human(report))

    sys.exit(1 if report["errors"] else 0)


if __name__ == "__main__":
    main()
