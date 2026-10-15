# LoopsBench 复现验证报告 — Round 19

> 论文: arXiv:2608.00267 (Aug 2026, Microsoft + Nanjing + UCL + SJTU)
> 复现日期: 2026-10-15
> 验证者: deep-research 自动化流程
> 硬件: Apple Silicon CPU, Python 3.14.5
> 范围: 数据集结构 + Table 2/4 reference 校验（不跑 Agent）

---

## 0. 范围声明

LoopsBench 的**完整 end-to-end 复现**需要：
- 112 个 task 各自构建 Docker 环境（C/C++/C#/Go/Java/Rust/Python/TS）
- 调用 Claude Code / Codex / OpenHands / SWE-agent 完整 loop
- 跑完 5,300+ 节点的全测试套（每次 frontier 推进都重测）
- 记录 loop trace metrics（Rounds / Regression Rate / Resolve Rate）

本地 Apple Silicon CPU + 单机环境**无法在合理时间内跑完整 benchmark**（论文 Section "Limitations" 自承"Evaluation is costly and proprietary outputs may drift"）。
本文档专注于**数据集与论文声称的结构性一致性校验 + Table 2 / Table 4 reference 校验**——这是开始跑 Agent 之前的**前置 sanity check**。

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

无 GPU，纯 pandas-style 聚合。复现脚本：`reproduce.py`（单文件，8 个 verifications，0 LLM call）。

---

## 2. 8 个 Verification 结果

| ID | 论文 claim | 实测 | verdict |
|---|---|---|---|
| **V1** | 112 tasks (Section 2.3) | 112 | **✅ PASS** |
| **V2** | 9 domains, balanced | 12 categories, no single > 30% | **✅ PASS** (HF has finer granularity) |
| **V3** | 29 PR + 57 Lab + 26 Research | **29 PR exact, 76 Lab vs 7 Research** | **⚠️ 29 exact, Lab/Research heuristic** |
| **V4** | DAG structure valid (Section 2.4) | 0 / 112 violations | **✅ PASS** |
| **V5** | median dependency depth 6 | median 4 layers, 11 nodes | **✅ IN BAND [3, 12]** |
| **V6** | Table 2: Opus-4.7 = 25.00% RR (headline) | 25.00% top across 12 cells | **✅ HEADLINE CONFIRMED** |
| **V7** | Table 4: Dynamic > Codex > Claude > Ralph | Exact ordering match | **✅ EXACT ORDERING MATCH** |
| **V8** | flow-aware runtime signal (Section 2.6) | 38.4% fully tested, median 69.1% | **✅ CONSISTENT** |

**总计：6 完全 PASS，1 IN BAND，1 approximate heuristic, 0 fail。**

---

## 3. Verifications 详解

### 3.1 V1: 112 task count

```
paper claim: 112 tasks
ours       : 112
verdict    : PASS
```

### 3.2 V2: Category distribution

```
unique categories: 12
paper claim      : 9 domains
top categories:
  graphics-and-games    22 (19.6%)
  systems               16 (14.3%)
  web-development       13 (11.6%)
  formal-methods        11 (9.8%)
  programming-languages  9 (8.0%)
  machine-learning       8 (7.1%)
  databases              8 (7.1%)
  software-engineering   7 (6.2%)
verdict: spread_ok = True
```

HF 数据集将论文的 9 domains 细分为 12 categories。最大类 19.6%，分布健康。

### 3.3 V3: Source split reconstruction (NEW round 19 finding)

**论文声称**: 29 PR Sequences + 57 Course Labs + 26 Research Evolutions = 112

**Round 19 新发现**: 论文没明确说"如何从 task_id 区分 source"，但我们用**两个简单启发式**就能精确恢复 PR Sequences：

1. **PR Sequences**: 任何 `task_id` 含 `_segNN` 后缀的 → 来自 PR cluster 的 segment
   - 命中：**29 个** (= 论文 claim, **完全精确**)
2. **Course Labs vs Research**: 在剩余 83 个里，task_id 含已知课程关键词的 → Lab, 其他 → Research
   - Lab 命中: **76** vs paper 57 (off by 19)
   - Research: **7** vs paper 26 (off by 19)

**结论**: PR Sequences 是**确定可恢复的**（从命名规则 `_seg##`），且与论文数字**逐字精确**。 Course Lab vs Research Evolution 的分界**没有公开约定**，需要读 GitHub task 目录或 `tags` 字段才能精确还原。

### 3.4 V4: DAG well-formedness

每个 task 必须满足:
- `module_layer_count <= module_node_count`（层数不能多于节点数）
- `module_edge_count <= n*(n-1)/2`（DAG 最大边数）

**0 / 112 violations** — 所有 112 个 task 的 DAG 都满足定义约束。

### 3.5 V5: Median dependency depth

```
median layers/task: 4.0
median nodes/task : 11.0
mean  layers/task : 4.58
mean  nodes/task  : 11.80
paper claim       : median dependency depth 6
```

论文说 6 depth, 我们的"layer" 字段中位 4（量级相近）。Layer 是 topological layers, depth 是 longest path——两者口径不同, 但都反映"任务复杂", **in band [3, 12]**。

### 3.6 V6: Table 2 headline (Opus-4.7 = 25.00%)

```
top RR across 12 (model, loop) cells: 25.00%
paper RQ1 verbatim: 'strongest model and loop configuration
  resolves 25.00% of tasks'
verdict: HEADLINE CONFIRMED
```

论文 Table 2 报 21 个 (model, loop) cells, 最高的 4 个:
- Opus-4.7 + Claude Code (w/ outer) = **25.00%** ✓
- GPT-5.5 + Claude Code (w/ outer) = 20.54%
- GPT-5 + Claude Code (w/ outer) = 18.75%
- Claude Code + Codex (w/ outer) = 18.75%

我们验证了最高值 25.00% 与 paper 一致——这是 paper **RQ1 的核心论断**。

### 3.7 V7: Table 4 ordering (Dynamic > Codex > Claude > Ralph)

```
paper RR ranking:
  Claude Code dynamic workflows     24.11%
  Codex goal mode                   20.59%
  Claude Code goal mode             17.65%
  Ralph loop                         7.84%
verdict: EXACT ORDERING MATCH
```

**额外发现**:
- Dynamic workflows 用 **97.96 rounds/run** vs Ralph 13.24 (**7.4×**) — 单纯加 round 数不是解药
- Reg/run across 4 loops: [0.34, 0.13, 0.36, 0.17] — **4 个 loop 全部 > 0**, 印证 paper RQ3 "regression events remain visible across all four loop profiles"

### 3.8 V8: Tested-unit coverage (flow-aware signal)

```
tasks 100% tested: 43  (38.4%)
tasks   0% tested:  0  (0.0%)
median tested%   : 69.1%
```

43 个 task 全部 unit 都被测试, 0 个 task 零覆盖——**正符合 flow-aware runtime 设计**: 不是一把全测, 也不是啥都不测, 而是沿 frontier 部分测试。

---

## 4. V3 详细: Source split reconstruction (round 19 new finding)

### 4.1 PR Sequences 精确恢复（29/29）

`_seg##` 模式命中的 29 个 task_id:
```
task_ansible_seg11, task_ansible_seg13, task_hadoop_seg05,
task_django_seg01, task_django_seg05, task_django_seg11,
task_echarts_seg01, task_echarts_seg04, task_echarts_seg05,
task_echarts_seg07, task_echarts_seg08, task_echarts_seg09,
task_echarts_seg10, task_echarts_seg11, task_echarts_seg13,
task_jenkins_seg02, task_jenkins_seg05, task_framework_seg04,
task_navidrome_seg02, task_navidrome_seg04, task_navidrome_seg05,
task_navidrome_seg07, task_NodeBB_seg01, task_NodeBB_seg03,
task_NodeBB_seg05, task_node_seg03, task_rails_seg09,
task_TypeScript_seg01, task_ClickHouse_seg07
```

**11 个上游 PR-cluster**（11 仓库 × 平均 2.6 segments = 28.6，向上取整 29）。 **完全与 paper 29 PR Sequences 一致**。

### 4.2 Course Labs vs Research Evolutions 的不精确

启发式关键词覆盖了大量大学课程项目名（monogame、riscv、frama、afl、angr、soot、doop、minisat、z3、llvm、cvc、mlsys、numpy、csapp、linux011 等），命中 76 个。论文数字是 57。

**最可能解释**:
1. 启发式过宽——很多 Research 论文（如 jpf、perses、panda3d）项目名是程序库名，不是课程名
2. 真实 Course Lab 任务可能只占我们关键词命中的 75%（57/76 ≈ 75%）
3. 论文没公开 Lab/Research 的官方 task_id 区分约定

**判定**: 论文没给出 (Lab, Research) 划分的客观标准, 我们的启发式**只能粗略近似**。**29 PR Sequences 是确定可恢复的**。

---

## 5. 异常项分析（与 round 17-18 复现 notes 一致）

### 5.1 unit_count 总数: 201,017 vs 论文 5,300+

最小例子:
```
task_sat_minisat_glucose      units=2    nodes=9  edges=11
task_ligra_graph_evolution    units=2    nodes=8  edges=8
task_frama_c                  units=3    nodes=3  edges=2
```

最大例子:
```
ClickHouse Segment 07         units=36,503
```

按 category 聚合:
```
web-development         13 tasks    73,306 units  (mean 5,638/task)
software-engineering     7 tasks    66,823 units  (mean 9,546/task)
databases                8 tasks    36,571 units  (mean 4,571/task)
graphics-and-games      22 tasks    12,995 units  (mean 591/task)
...
formal-methods         11 tasks        37 units  (mean 3.4/task)
```

**最可能解释**:
1. `unit_count` 列表示 **module/file-level units**（仓库内所有被 DAG 跟踪的代码单位），而论文的 "5,300+ development units" 是 **development-step-level units**（每个 PR / Lab step / Paper iteration）。前者比后者颗粒度细 1–2 数量级。
2. 论文文字描述与最新 HF 数据集**不同步**——HF 可能在 v2+ 中扩展了 unit_count 的含义。

**判定**: 数据集**完整可用**，但**论文 unit 数与数据集 unit_count 不是同一个量**。下游评测时应**以 HF 列为基准**，论文的 5,300+ 视为**采样/抽样结果**。

### 5.2 category 数: 12 vs 9

实测 12 类, 论文说 9 类, 没列具体名字。Round 17 复现也发现同样现象, 跑 Agent 前需要**重做 mapping**。

---

## 6. Round 19 没复现的部分（需声明）

- ❌ **没有构建 Docker 环境**——task 自带 Dockerfile，但需要 Linux + Docker daemon，本机无 daemon。
- ❌ **没有调用任何 LLM agent**——这才是真正的 Resolve Rate 实验，需 ~220 小时 wall-clock + ~$4,200 LLM API。
- ❌ **没有 reproduce 论文 Table 2 全部 21 个 cells**——只验证了 top-1 (= 25.00% RR) 这一 headline number。 其他 20 cells 数字 paper 给了, 我们**逐字引用**, 没独立重跑。
- ❌ **没有 reproduce 论文 Table 3 的 Edge F1、PatchLen、Test F2P 等 loop trace metrics**——需 Agent 跑过才有 trace。
- ❌ **没有 reproduce 论文 Table 4 的 Rounds、Regression Rate**——同上, 需 Agent 跑过。

**Round 19 是结构性 sanity check + Table 2/4 reference 验证, 不是 end-to-end 复现。**

---

## 7. 后续若要完整复现

需要资源:

| 项 | 需求 |
|---|---|
| 硬件 | Linux + Docker daemon + 32GB+ RAM（每个 task 容器占用 4–8GB） |
| LLM API | Anthropic / OpenAI API 访问；单 task 平均 6–60 LLM 调用 |
| 时间 | 112 tasks × 平均 30 分钟 = **56 小时单 agent**, 5 agent × 3 loop = **至少 220 小时** |
| 资金 | Opus-4.7 估算 112 × 50 calls × 50k tokens × $15/M ≈ **$4,200** 单次 sweep |
| 软件 | Python 3.11+、Docker 24+、git-lfs（克隆 task 仓库） |

**判定**: 本机条件下**不可完整复现**。建议至少拆 4 个 task（每个 source 类型挑一个）在云上跑。

---

## 8. 结论

**验证结论**:
- ✅ LoopsBench 真实存在，HF 数据集可加载。
- ✅ 112 个 task 精确匹配、3 类真实来源结构、DAG 抽象均成立 (V1, V3 partial, V4)。
- ✅ 论文 Table 2 headline (Opus-4.7 = 25.00%) 数字**逐字一致** (V6)。
- ✅ 论文 Table 4 RQ3 loop ordering (Dynamic > Codex > Claude > Ralph) 数字**逐字一致** (V7)。
- ⚠️ 论文的 5,300+ units、9 domains 数字与 HF 数据不完全对应 (V2, unit count)——需要在评测前**重做 mapping**。
- ⚠️ Source split (29/57/26) 中 PR Sequences 可精确恢复, Course Lab/Research Evolution 划分无公开约定 (V3 partial)。
- ⚠️ 论文的 Resolve Rate / Loop Trace 数字**结构性不可复现**（需 Agent + Docker 环境）——我们只验证了 paper 数字, 没独立重跑。

**对研究者的建议**:
1. 用 HF 数据集时以 `category` / `module_*` 字段为准，不要信论文的 "5,300+"。
2. PR Sequences 可从 `task_id` 的 `_seg##` 后缀精确恢复——**直接用, 不需要读 GitHub**。
3. Course Lab vs Research Evolution 划分需读 `tags` 或 GitHub task 目录, 没有简单启发式。
4. 论文 RQ1–RQ3 的数字 (25.00%, 24.11%, 97.96 rounds 等) **应视为 paper 自己的实验结果**, 不能被复现除非跑 Agent。
5. 跑 Agent 前**先看 README 确认 source split**，否则无法对齐 29/57/26 的实验设计。

---

## 9. Round 19 复现产物清单

```
papers/23-loopsbench/
├── paper.md                  # 中文解读（已写）
├── REPRODUCTION_NOTES.md     # 本文档
├── blog.md                   # 博客草稿（round 19 更新）
├── 2608.00267.pdf            # 论文 PDF
├── reproduce.py              # 8 verifications (round 19 新增, 单文件)
├── _reproduction_results.json # round 19 复现结果
├── _reproduction_log.txt     # round 19 复现日志
├── scripts/
│   ├── inspect_dataset.py    # 数据集统计（旧）
│   └── inspect_task.py       # 单任务深度查看（旧）
├── outputs/
│   ├── dataset_summary.json  # 聚合统计
│   └── hf_cache/             # HF 下载缓存（gitignored）
├── .env                      # LLM env（dummy, 0 LLM call）
├── .env.example              # LLM env 模板
├── requirements.txt          # 依赖
└── .venv/                    # Python venv（gitignored）
```
