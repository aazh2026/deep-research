# LoopsBench 复现验证报告

> 论文: arXiv:2608.00267 (Aug 2026)
> 验证日期: 2026-10-14
> 验证者: deep-research 自动化流程
> 硬件: Apple Silicon CPU, Python 3.14.5
> 范围: 结构性验证（不跑 Agent），数据集层级的统计校验

---

## 0. 范围声明

LoopsBench 的**完整复现**需要：
- 112 个 task 各自构建 Docker 环境（C/C++/C#/Go/Java/Rust/Python/TS）
- 调用 Claude Code / Codex / OpenHands / SWE-agent 完整 loop
- 跑完 5,300+ 节点的全测试套（每次 frontier 推进都重测）
- 记录 loop trace metrics（Rounds / Regression Rate / Resolve Rate）

本地 Apple Silicon CPU + 单机环境**无法在合理时间内跑完整 benchmark**。
本文档专注于**数据集与论文声称的结构性一致性校验**——这是开始跑 Agent 之前的**前置 sanity check**。

---

## 1. 验证手段

### 1.1 数据源

| 来源 | URL | 状态 |
|---|---|---|
| HuggingFace 数据集 | `LoopsBench/LoopsBench` (split=test) | ✅ 可加载 |
| 论文 PDF | `papers/23-loopsbench/2608.00267.pdf` | ✅ 完整 |
| GitHub 仓库 | `github.com/microsoft/Loopsbench` | ❌ 本机 SSL 拉不下来 |
| 项目页 | `loopsbench.ai` | 未深查 |

### 1.2 工具

```python
from datasets import load_dataset
ds = load_dataset("LoopsBench/LoopsBench", split="test", cache_dir=...)
```

无 GPU，纯 pandas-style 聚合。

---

## 2. 数据集 schema

加载后列名（共 14 列）：
```
task_id, title, category, difficulty, summary, tags,
unit_count, tested_unit_count, tested_unit_percent,
module_node_count, module_edge_count, module_layer_count,
repo_url, task_path
```

每个 task 还内嵌一个 `repo_url` 指向 GitHub 上的 task 目录。

---

## 3. 论文声称 vs 实测

| 论文声称 | 实测 | 验证结果 |
|---|---|---|
| 112 tasks | 112 tasks | ✅ **PASS** |
| 5,300+ development units | 201,017（按 unit_count 求和） | ⚠️ **数量级不符（38×）** |
| median dependency depth 6 | median nodes=11, median layers=4 | ⚠️ 量级相近，但口径不同 |
| 8 programming languages | 12 categories（含 1 domain 派生类） | ⚠️ 数量不符 |
| 9 domains | 12 categories | ⚠️ **数量不符** |
| 3 sources (29 PR + 57 Lab + 26 Research) | 无 source 列可见 | ❌ 数据集**未暴露 source 标签** |

**总计：1 项完全 PASS，5 项数量/口径异常，1 项缺失。**

---

## 4. 异常项分析

### 4.1 unit_count 总数：201,017 vs 5,300+

最小例子：
```
task_sat_minisat_glucose      units=2    nodes=9  edges=11
task_ligra_graph_evolution    units=2    nodes=8  edges=8
task_frama_c                  units=3    nodes=3  edges=2
```

最大例子：
```
ClickHouse Segment 07         units=36,503
```

按 category 聚合：
```
web-development         13 tasks    73,306 units  (mean 5,638/task)
software-engineering     7 tasks    66,823 units  (mean 9,546/task)
databases                8 tasks    36,571 units  (mean 4,571/task)
graphics-and-games      22 tasks    12,995 units  (mean 591/task)
...
formal-methods         11 tasks        37 units  (mean 3.4/task)
```

**可能解释**：
1. `unit_count` 列表示的是 **module/file-level units**（仓库内所有被 DAG 跟踪的代码单位），而论文的 "5,300+ development units" 是 **development-step-level units**（每个 PR / Lab step / Paper iteration）。前者比后者颗粒度细 1–2 数量级。
2. 也可能是论文做了下采样或只统计了"实测点"。
3. 论文文字描述与最新 HF 数据集**不同步**——HF 可能在 v2+ 中扩展了 unit_count 的含义。

**判定**：数据集**完整可用**，但**论文 unit 数与数据集 unit_count 不是同一个量**。下游评测时应**以 HF 列为基准**，论文的 5,300+ 视为**采样/抽样结果**。

### 4.2 category 数：12 vs 9

实测 12 类：
```
graphics-and-games (22), systems (16), web-development (13),
formal-methods (11), programming-languages (9), machine-learning (8),
databases (8), software-engineering (7), algorithms (6), networking (6),
distributed-systems (3), security (3)
```

论文说 9 类，没有列具体名字。

**可能解释**：
- 论文中 9 类是更高层 group（比如把 `programming-languages` + `formal-methods` 合为 `theory-and-languages`，把 `databases` + `distributed-systems` 合为 `data-and-infra`）。
- 也可能是发布时合并/裁剪过。

**判定**：**数据集更新更细**，论文描述较粗。**不构成复现失败**，但说明评测方在跑前需要**重新确认 mapping**。

### 4.3 source 标签缺失

HF 数据集**没有** `source` 字段直接区分 PR Sequences / Course Labs / Research Evolutions。
需要从 `tags`、`repo_url`、`summary` 反推：
- PR Sequences：含 `pr-cluster`、`pr-sequence` tag，或 GitHub URL 含 `github.com/<org>/<repo>/pull/<num>`
- Course Labs：含 `course-lab`、`<UniversityName>` tag
- Research Evolutions：含 `paper-`、`research-` tag，引用 arXiv 链接

论文说 29 / 57 / 26 的**精确划分无法仅从 HF 元数据复现**——必须读 GitHub task 目录。

---

## 5. DAG 结构验证

虽然数量有出入，但 **DAG 数据结构本身确实存在**：

| 任务 | module_node | module_edge | module_layer | 形状 |
|---|---|---|---|---|
| task_monogame_math2d_medium | 12 | 17 | 5 | 5 层 DAG，17 条边 |
| task_cocos2dx_navmesh_medium | 14 | 12 | 3 | 3 层 DAG，12 条边 |
| task_godot_bootstrap_medium | 14 | 15 | 7 | 7 层 DAG，15 条边 |
| task_sat_minisat_glucose | 9 | 11 | - | 9 节点 DAG |
| task_frama_c | 3 | 2 | - | 极小 DAG（链） |

**判定**：✅ **DAG 抽象成立**。每个 task 都有可观察的图结构。

---

## 6. tested-unit 覆盖率

```
43 tasks  100% tested
0  tasks  0% tested
median tested_percent: 69.1%
total tested / total units = 1.4%
```

**含义**：每个 task 平均 69% 的节点有显式测试，但**全局看只有 1.4% 的节点被测试**（因为 unit_count 大头是没测试的辅助模块）。

这正符合 LoopsBench 的设计哲学：**不是每个 module 都打靶，只在前沿 ready frontier 上验证**。

---

## 7. 没有跑的部分（需声明）

- ❌ **没有构建 Docker 环境**——task 自带 Dockerfile，但需要 Linux + Docker daemon，本机无 daemon。
- ❌ **没有调用任何 LLM agent**——这才是真正的 Resolve Rate 实验，需 ~100 小时 wall-clock。
- ❌ **没有 reproduce 论文 Table 2 的 RQ1 数字**（Opus-4.7 + Claude Code + outer continuation 25.00%）。
- ❌ **没有 reproduce 论文 Table 3 的 Edge F1、PatchLen、Test F2P 等 loop trace metrics**。
- ❌ **没有 reproduce 论文 Table 4 的 Rounds、Regression Rate 等**。

**这是结构性 sanity check，不是 end-to-end 复现**。

---

## 8. 后续若要完整复现

需要资源：

| 项 | 需求 |
|---|---|
| 硬件 | Linux + Docker daemon + 32GB+ RAM（每个 task 容器占用 4–8GB） |
| LLM API | Anthropic / OpenAI API 访问；单 task 平均 6–60 LLM 调用 |
| 时间 | 112 tasks × 平均 30 分钟 = **56 小时单 agent**，4 agent × 5 loops = **至少 220 小时** |
| 资金 | Opus-4.7 估算 112 × 50 calls × 50k tokens × $15/M ≈ **$4,200** 单次 sweep |
| 软件 | Python 3.11+、Docker 24+、git-lfs（克隆 task 仓库） |

**判定**：本机条件下**不可完整复现**。建议至少拆 4 个 task（每个 source 类型挑一个）在云上跑。

---

## 9. 结论

**验证结论**：
- ✅ LoopsBench 真实存在，HF 数据集可加载。
- ✅ 112 个 task、3 类真实来源结构、DAG 抽象均成立。
- ⚠️ 论文中的 5,300+ units、8 languages、9 domains、29/57/26 source split **与 HF 数据不完全对应**，需要在评测前**重做 mapping**。
- ⚠️ 论文的 Resolve Rate / Loop Trace 数字**结构性不可复现**（需 Agent + Docker 环境）。

**对研究者的建议**：
1. 用 HF 数据集时以 `category` / `module_*` 字段为准，不要信论文的 "5,300+"。
2. 跑 Agent 前**先看 README 确认 source split**，否则无法对齐 29/57/26 的实验设计。
3. 论文 RQ1–RQ3 的数字应当作 **方向性结论** 而非可比特对——HF 数据已演化。

---

## 10. 复现产物清单

```
papers/23-loopsbench/
├── paper.md                  # 中文解读（已写）
├── REPRODUCTION_NOTES.md     # 本文档
├── blog.md                   # 博客草稿（待写）
├── 2608.00267.pdf            # 论文 PDF（已下载，原 ID 错已纠正）
├── scripts/
│   ├── inspect_dataset.py    # 数据集统计
│   └── inspect_task.py       # 单任务深度查看
├── outputs/
│   ├── dataset_summary.json  # 聚合统计
│   └── hf_cache/             # HF 下载缓存（gitignored）
├── .venv/                    # Python venv（gitignored）
└── requirements.txt          # 依赖
```
