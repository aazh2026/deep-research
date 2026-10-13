"""Inspect 4 个 ablation 的 wiki + skill 状态。"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main():
    out_dir = Path(__file__).parent.parent / "outputs"
    summary = json.loads((out_dir / "ablation_summary.json").read_text())

    print("=" * 70)
    print("WikiSkill Ablation Inspect")
    print("=" * 70)

    for name, data in summary.items():
        print(f"\n## {name}")
        print(f"  config: {data['config']}")
        print(f"  final R_best: {data['final_R_best']:.3f}")
        print(f"  wiki size: {data['final_wiki_size']}")
        print(f"  n_commits / n_rollbacks: {data['n_commits']} / {data['n_rollbacks']}")
        print(f"  final skills ({len(data['final_skills'])}):")
        for s in data["final_skills"][:3]:
            print(f"    - {s[:100]}")
        print(f"  wiki first 5:")
        for w in data["wiki_first_5"]:
            print(f"    - {w[:80]}")
        print(f"  val_per_iter:")
        for v in data["val_per_iter"]:
            tag = "baseline" if v["iter"] == 0 else (
                "ACCEPT" if v.get("accepted") else "REJECT"
            )
            print(f"    iter {v['iter']}: R={v['R']:.3f} [{tag}]")

    print("\n" + "=" * 70)
    print("Skill body 差异（核心 ablation claim）：")
    print("=" * 70)
    for name in ["no_wiki", "full"]:
        data = summary[name]
        skills = data["final_skills"]
        print(f"\n[{name}] final skill bodies:")
        if not skills:
            print("  (no skills committed)")
        for s in skills:
            print(f"  - {s[:100]}")
    no_wiki = summary["no_wiki"]["final_skills"]
    full = summary["full"]["final_skills"]
    print(f"\nSet diff (no_wiki vs full):")
    print(f"  no_wiki only: {set(no_wiki) - set(full)}")
    print(f"  full only:    {set(full) - set(no_wiki)}")


if __name__ == "__main__":
    main()
