"""
Inspect a single task's full content - verify DAG structure exists in raw data.
"""
import os, json
from datasets import load_dataset

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f"{ROOT}/outputs"

ds = load_dataset("LoopsBench/LoopsBench", split="test", cache_dir=f"{OUT}/hf_cache")

# Pick the smallest task to dump full content
sample = ds[0]
print(f"Task 0: {sample['task_id']}")
print(f"  unit_count: {sample['unit_count']}")
print(f"  module nodes/edges/layers: {sample['module_node_count']}/{sample['module_edge_count']}/{sample['module_layer_count']}")
print(f"  repo_url: {sample['repo_url']}")
print()
print(f"summary (first 500): {sample['summary'][:500]}")
print()
print(f"tags: {sample['tags']}")

# Find a small-PR-cluster task
small = sorted(ds, key=lambda r: r["unit_count"])[:5]
print("\n=== 5 smallest tasks ===")
for r in small:
    print(f"  {r['task_id']:50s}  units={r['unit_count']:4d}  nodes={r['module_node_count']:3d}  edges={r['module_edge_count']:3d}  cat={r['category']}")

# Distribution stats
print(f"\n=== Per-category unit totals ===")
from collections import defaultdict
cat_units = defaultdict(lambda: [0, 0])
for r in ds:
    cat_units[r["category"]][0] += r["unit_count"]
    cat_units[r["category"]][1] += 1
for cat, (u, n) in sorted(cat_units.items(), key=lambda x: -x[1][0]):
    print(f"  {cat:30s}  {n:3d} tasks  {u:7d} units  (mean {u/n:.1f})")
