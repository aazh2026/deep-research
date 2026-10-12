#!/usr/bin/env python3
"""
P2 文献核查缓存机制

目的：
- 同领域多篇论文评估时，P2 的引用核查结果可缓存复用
- 避免对同一引用（如 LLM 领域的 CAMEL / ToT / ReAct）重复 WebSearch/WebFetch
- 显著降低 token 消耗与时间

设计动机：
- R2 LLM Harmony 测试中 P2 跑了 5+ 次 WebSearch 验证 CAMEL baseline
- 若再评估其他 LLM multi-agent 文章，P2 又会重复相同工作
- 缓存后第二次起只需读 cache

用法：
  # 添加核查记录
  python cache_p2.py add \\
    --title "CAMEL: Communicative Agents for ..." \\
    --authors "Li et al." \\
    --year 2023 \\
    --venue "NeurIPS" \\
    --verified true \\
    --source-url "https://arxiv.org/abs/2303.17760" \\
    --credibility high \\
    --quote "..." \\
    --finding "..."

  # 查询
  python cache_p2.py query --title "CAMEL: ..." --authors "Li et al." --year 2023

  # 合并 P2_OUTPUT（自动用 cache 补全未核查的引用）
  python cache_p2.py merge --p2 runs/.../p2_literature_audit.yaml --out runs/.../p2_merged.yaml

  # 统计
  python cache_p2.py stats

存储：.claude/skills/academic-rigor-review/cache/p2_cache.json
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    print("ERROR: 需要 PyYAML. 安装: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# ----------------------------------------------------------------------
# 缓存位置与持久化
# ----------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
CACHE_DIR = SKILL_DIR / "cache"
CACHE_FILE = CACHE_DIR / "p2_cache.json"


def load_cache() -> dict[str, Any]:
    """加载缓存文件，缺失则创建。"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if not CACHE_FILE.exists():
        return {"_meta": {"version": "1.0", "created_at": now_iso()}, "entries": {}}
    return json.loads(CACHE_FILE.read_text())


def save_cache(cache: dict[str, Any]) -> None:
    """保存缓存。"""
    CACHE_FILE.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2)
    )


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


# ----------------------------------------------------------------------
# 缓存 key
# ----------------------------------------------------------------------

def normalize(s: str) -> str:
    """规范化字符串（小写、合并空白、移除标点）。"""
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def citation_key(title: str, authors: str, year: int | str) -> str:
    """根据引用信息生成稳定 hash key。

    使用 (title + first_author + year) 的规范化组合 + SHA256。
    不依赖 venue（venue 字段在不同引用格式中差异大）。
    """
    # 提取 first_author（取第一个逗号或 "et al." 之前）
    first_author = re.split(r"[,;]|et al\.?", authors, maxsplit=1)[0].strip()
    normalized = f"{normalize(title)}|{normalize(first_author)}|{str(year).strip()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


# ----------------------------------------------------------------------
# 子命令实现
# ----------------------------------------------------------------------

def cmd_add(args) -> int:
    """添加一条核查记录到缓存。"""
    cache = load_cache()
    key = citation_key(args.title, args.authors, args.year)
    now = now_iso()

    # 如果已存在，更新
    if key in cache["entries"]:
        entry = cache["entries"][key]
        entry["evaluation"] = {
            "verified": args.verified,
            "source_url": args.source_url,
            "source_credibility": args.credibility,
            "quote": args.quote,
            "key_finding": args.finding,
        }
        entry["last_used_at"] = now
        entry["hit_count"] = entry.get("hit_count", 1)
        action = "updated"
    else:
        cache["entries"][key] = {
            "citation": {
                "title": args.title,
                "authors": args.authors,
                "year": int(args.year) if str(args.year).isdigit() else args.year,
                "venue": args.venue,
                "raw_text": args.raw_text or f"{args.authors} ({args.year}). {args.title}.",
            },
            "evaluation": {
                "verified": args.verified,
                "source_url": args.source_url,
                "source_credibility": args.credibility,
                "quote": args.quote,
                "key_finding": args.finding,
            },
            "first_checked_at": now,
            "last_used_at": now,
            "hit_count": 1,
        }
        action = "added"

    save_cache(cache)
    print(f"  [{action}] {key}: {args.title} ({args.year})")
    return 0


def cmd_query(args) -> int:
    """查询缓存中是否已有某引用的核查结果。"""
    cache = load_cache()
    key = citation_key(args.title, args.authors, args.year)
    entry = cache["entries"].get(key)
    if entry is None:
        print(f"  [miss] {key}: {args.title} ({args.year})")
        return 1

    # 命中：更新 last_used_at 与 hit_count
    entry["last_used_at"] = now_iso()
    entry["hit_count"] = entry.get("hit_count", 0) + 1
    save_cache(cache)

    print(f"  [hit ] {key}: {args.title} ({args.year})")
    print(f"        verified: {entry['evaluation']['verified']}")
    print(f"        source:   {entry['evaluation']['source_url']}")
    print(f"        credibility: {entry['evaluation']['source_credibility']}")
    print(f"        hit_count: {entry['hit_count']}")
    return 0


def cmd_merge(args) -> int:
    """合并 P2_OUTPUT 与 cache：cache 命中的引用直接补全到 P2_OUTPUT。

    P2_OUTPUT 中每个引用的结构（来自 templates/p2-output-schema.yaml）：
      - cited_as: 引用文本
      - original_citation: 原始引用
      - verification_status: verified / refuted / unverified
      - source_url
      - source_credibility
      - quote
      - 等等

    合并策略：
      1. 遍历 P2_OUTPUT 中的每条引用
      2. 尝试用 (title, authors, year) 在 cache 中查找
      3. 命中：填充 verification_status / source_url / quote 等字段
      4. 未命中：保留原值
    """
    cache = load_cache()
    p2 = yaml.safe_load(args.p2.read_text())

    # 兼容不同的字段名（不同版本可能用 cited_paper 或 citation）
    references = p2.get("citation_audit", []) or p2.get("references", []) or []
    if not references:
        print("WARN: P2_OUTPUT 中未找到 citation_audit / references 字段", file=sys.stderr)

    hits = 0
    misses = 0
    enriched = []

    for ref in references:
        title = ref.get("title") or ref.get("cited_paper_title", "")
        authors = ref.get("authors") or ref.get("cited_authors", "")
        year = ref.get("year") or ref.get("cited_year", "")

        if not title or not authors:
            enriched.append(ref)
            continue

        key = citation_key(title, authors, year)
        entry = cache["entries"].get(key)

        if entry is None:
            misses += 1
            enriched.append(ref)
            continue

        # 命中：用 cache 的 evaluation 字段补全
        hits += 1
        new_ref = dict(ref)
        ev = entry["evaluation"]

        # verification_status：仅当原值是 pending/unverified 时覆盖
        # 避免覆盖人工 verified 状态（信任本地结论）
        current_status = ref.get("verification_status", "pending")
        if current_status in ("pending", "unverified", None, ""):
            new_ref["verification_status"] = (
                "verified" if ev.get("verified") else "refuted"
            )
            new_ref["_status_overridden_by_cache"] = True

        new_ref.setdefault("source_url", ev.get("source_url"))
        new_ref.setdefault("source_credibility", ev.get("source_credibility"))
        new_ref.setdefault("quote", ev.get("quote"))
        new_ref["_cache_hit"] = {
            "key": key,
            "first_checked_at": entry.get("first_checked_at"),
            "hit_count": entry.get("hit_count", 0),
        }
        enriched.append(new_ref)

        # 更新 last_used_at
        entry["last_used_at"] = now_iso()
        entry["hit_count"] = entry.get("hit_count", 0) + 1

    # 写回 P2 产物
    p2["citation_audit"] = enriched
    p2.setdefault("p2_cache_metadata", {})
    p2["p2_cache_metadata"] = {
        "merge_time": now_iso(),
        "total_references": len(references),
        "cache_hits": hits,
        "cache_misses": misses,
        "hit_rate": round(hits / len(references), 3) if references else 0,
    }

    save_cache(cache)

    if args.out:
        args.out.write_text(
            yaml.safe_dump(p2, allow_unicode=True, sort_keys=False)
        )
        print(f"已写入: {args.out}", file=sys.stderr)
    else:
        print(yaml.safe_dump(p2, allow_unicode=True, sort_keys=False))

    print(f"\n  cache hits:   {hits} / {len(references)}", file=sys.stderr)
    print(f"  hit rate:     {p2['p2_cache_metadata']['hit_rate']}", file=sys.stderr)
    return 0 if hits > 0 else 1


def cmd_stats(args) -> int:
    """显示缓存统计。"""
    cache = load_cache()
    entries = cache.get("entries", {})
    total = len(entries)
    if total == 0:
        print("  缓存为空")
        return 0

    total_hits = sum(e.get("hit_count", 0) for e in entries.values())
    verified = sum(1 for e in entries.values() if e["evaluation"].get("verified"))
    refuted = sum(1 for e in entries.values() if not e["evaluation"].get("verified"))

    print(f"  Total entries:        {total}")
    print(f"  Total hits:           {total_hits}")
    print(f"  Avg hits/entry:       {total_hits / total:.2f}")
    print(f"  Verified citations:   {verified}")
    print(f"  Refuted citations:    {refuted}")

    # 显示 top 5 高频引用
    by_hits = sorted(entries.items(), key=lambda kv: -kv[1].get("hit_count", 0))
    print("\n  Top 5 by hit_count:")
    for key, entry in by_hits[:5]:
        cit = entry["citation"]
        print(f"    {key}  ({entry.get('hit_count', 0)} hits): {cit.get('title', '?')[:60]} ({cit.get('year', '?')})")
    return 0


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="P2 文献核查缓存：add / query / merge / stats"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # add
    p_add = sub.add_parser("add", help="添加一条核查记录到缓存")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--authors", required=True)
    p_add.add_argument("--year", required=True)
    p_add.add_argument("--venue", default="")
    p_add.add_argument("--raw-text", default="")
    p_add.add_argument("--verified", type=lambda v: v.lower() == "true", required=True)
    p_add.add_argument("--source-url", default="")
    p_add.add_argument("--credibility", default="medium",
                       choices=["high", "medium", "low"])
    p_add.add_argument("--quote", default="")
    p_add.add_argument("--finding", default="")

    # query
    p_query = sub.add_parser("query", help="查询缓存中是否有某引用的核查")
    p_query.add_argument("--title", required=True)
    p_query.add_argument("--authors", required=True)
    p_query.add_argument("--year", required=True)

    # merge
    p_merge = sub.add_parser("merge", help="合并 P2_OUTPUT 与缓存（自动补全命中引用）")
    p_merge.add_argument("--p2", type=Path, required=True)
    p_merge.add_argument("--out", type=Path, default=None)

    # stats
    sub.add_parser("stats", help="显示缓存统计")

    args = parser.parse_args()
    if args.cmd == "add":
        sys.exit(cmd_add(args))
    elif args.cmd == "query":
        sys.exit(cmd_query(args))
    elif args.cmd == "merge":
        sys.exit(cmd_merge(args))
    elif args.cmd == "stats":
        sys.exit(cmd_stats(args))


if __name__ == "__main__":
    main()
