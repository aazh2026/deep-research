"""
LoopsBench partial verification - inspect dataset structure.

Paper claims:
  - 112 tasks spanning 8 languages, 9 domains
  - 5,300+ development units, median dependency depth 6
  - 29 PR Sequences, 57 Course Labs, 26 Research Evolutions

We verify structural claims without running an agent:
  1. Total task count = 112
  2. Sum of unit_count matches 5,300+
  3. Distribution by category and difficulty
  4. Tested-unit percentage distribution
  5. Module node/edge/layer stats
"""
import os, json, sys
from collections import Counter, defaultdict
from statistics import median, mean

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{ROOT}/outputs"
os.makedirs(OUT, exist_ok=True)

from datasets import load_dataset

print(">> Loading LoopsBench/LoopsBench (split=test)...")
ds = load_dataset("LoopsBench/LoopsBench", split="test", cache_dir=f"{OUT}/hf_cache")

print(f">> Rows: {len(ds)}")
print(f">> Columns ({len(ds.column_names)}): {ds.column_names}")

# Aggregation
n_tasks = len(ds)
by_category = Counter()
by_difficulty = Counter()
total_units = 0
total_tested = 0
unit_counts = []
node_counts = []
edge_counts = []
layer_counts = []
tested_pcts = []

for row in ds:
    by_category[row["category"]] += 1
    by_difficulty[row["difficulty"]] += 1
    uc = row["unit_count"]
    tc = row["tested_unit_count"]
    pct = row["tested_unit_percent"]
    total_units += uc
    total_tested += tc
    unit_counts.append(uc)
    node_counts.append(row["module_node_count"])
    edge_counts.append(row["module_edge_count"])
    layer_counts.append(row["module_layer_count"])
    tested_pcts.append(pct)

# === Verify paper claims ===
print("\n=== Paper claim verification ===")
print(f"Claim: 112 tasks       | Actual: {n_tasks} tasks  -> {'PASS' if n_tasks == 112 else 'MISMATCH'}")
print(f"Claim: 5,300+ units    | Actual: {total_units} units  -> {'PASS' if total_units >= 5300 else 'MISMATCH'}")
print(f"Claim: median depth 6  | Actual: median nodes/task = {median(node_counts)}, median layers = {median(layer_counts)}")

print("\n=== Category distribution (9 domains expected) ===")
for k, v in sorted(by_category.items(), key=lambda x: -x[1]):
    print(f"  {k:30s}  {v:4d}  ({100*v/n_tasks:.1f}%)")

print(f"\nUnique categories: {len(by_category)} (paper claims 9)")

print("\n=== Difficulty distribution ===")
for k, v in sorted(by_difficulty.items()):
    print(f"  {k:15s}  {v:4d}  ({100*v/n_tasks:.1f}%)")

print("\n=== Unit count stats ===")
print(f"  total_units       = {total_units}")
print(f"  total_tested      = {total_tested}")
print(f"  tested_percent    = {100 * total_tested / total_units:.1f}% of all units have tests")
print(f"  units/task median = {median(unit_counts)}")
print(f"  units/task mean   = {mean(unit_counts):.1f}")
print(f"  units/task max    = {max(unit_counts)}  (in: {ds[unit_counts.index(max(unit_counts))]['title']})")

print("\n=== Module graph stats (DAG structure proxy) ===")
print(f"  nodes/task median = {median(node_counts)}  mean = {mean(node_counts):.1f}")
print(f"  edges/task median = {median(edge_counts)}  mean = {mean(edge_counts):.1f}")
print(f"  layers/task median= {median(layer_counts)} mean = {mean(layer_counts):.1f}")

print("\n=== Tested-unit coverage ===")
print(f"  100% tested: {sum(1 for p in tested_pcts if p == 100)}")
print(f"  0% tested:   {sum(1 for p in tested_pcts if p == 0)}")
print(f"  median tested_percent: {median(tested_pcts):.1f}%")

# Paper's source split (29 / 57 / 26) - check if category maps to source
print("\n=== Source mapping hypothesis ===")
print("Paper says 29 PR Sequences + 57 Course Labs + 26 Research Evolutions = 112")
print("Try mapping categories to sources:")
# Research Evolutions likely: papers/research tagged
research_count = sum(1 for r in ds if "research" in r["tags"] or "paper" in r["tags"] or "research" in r["category"])
print(f"  research-tagged: {research_count}")
course_count = sum(1 for r in ds if "course" in r["category"] or "course-lab" in r["tags"] or "labs" in r["category"])
print(f"  course-lab-tagged: {course_count}")
pr_count = sum(1 for r in ds if "pr-cluster" in r["tags"] or "pr-sequence" in r["tags"] or "github" in r["tags"])
print(f"  pr-sequence-tagged: {pr_count}")

# Persist summary
with open(f"{OUT}/dataset_summary.json", "w") as f:
    json.dump({
        "n_tasks": n_tasks,
        "total_units": total_units,
        "total_tested_units": total_tested,
        "tested_percent": 100 * total_tested / total_units,
        "by_category": dict(by_category),
        "by_difficulty": dict(by_difficulty),
        "unique_categories": len(by_category),
        "units_per_task": {
            "median": median(unit_counts),
            "mean": mean(unit_counts),
            "max": max(unit_counts),
        },
        "module_stats": {
            "nodes_median": median(node_counts),
            "edges_median": median(edge_counts),
            "layers_median": median(layer_counts),
        },
        "all_task_ids": [r["task_id"] for r in ds],
        "categories_list": list(by_category.keys()),
    }, f, indent=2, ensure_ascii=False)

print(f"\n>> Saved summary to outputs/dataset_summary.json")
