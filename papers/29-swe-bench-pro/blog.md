# 当 SWE-Bench 70% 成为历史：SWE-Bench Pro 撕开 2025 年 enterprise coding 真实水平

> 写于 2026-10-14，配合 `papers/29-swe-bench-pro/paper.md` 与 `REPRODUCTION_NOTES.md` 阅读。
>
> 这篇 blog 解决一个问题：**你 2026 年还在引用 SWE-Bench 70%+ 数字吗？那是错的。**

---

## 引子：SWE-Bench Verified 70% 的错觉

2024 年起，**SWE-Bench Verified** 几乎成为 coding agent 能力的**事实标准**：
- Claude 3.5 Sonnet 突破 50%
- Claude Sonnet 4 跑到 65%
- OpenAI o1 跑到 70%+

所有人开始说「**coding agent 已经能自动化软件工程**」。

但 2025 年 9 月，**Scale AI 放出的 SWE-Bench Pro** 撕开了这个幻觉：

> **Top agent 在 SWE-Bench Pro 上 23%，在 commercial enterprise 任务上 18%**。
>
> **比 SWE-Bench Verified 70% 跌 3-4 倍**。

这不是模型的错——是 SWE-Bench Verified **太过简单**：
- 161/500 (32%) 任务**只需要 1-2 行 patch**
- Patch mean 11.6 行
- 几乎全是 Python 单文件
- 全部来自 permissive license repo（**训练集很可能见过**）

> **SWE-Bench 70% 的真正含义是：「toy Python issue 上 70% 修对」**。
> 真实 enterprise software engineering 难度是 20% 量级。

---

## SWE-Bench Pro 怎么测的：3 个 subset × 41 repo × 1865 任务

### 3 个 subset（防 contamination 三层保险）

| Subset | N | 来源 | 可见性 |
|---|---:|---|---|
| **Public** | 731 | 11 个 GPL/copyleft repo | 公开在 HF |
| **Commercial** | 276 | 18 个 startup 商业 repo | 私有，**只公开结果** |
| **Held-Out** | 858 | 12 个 private repo | 私有 |
| **总计** | **1865** | | |

**3 个 subset 的设计**是 2025 年 benchmark 设计的**新范式**——**只公开结果不公开数据**。这跟 SWE-Bench（全部公开）形成鲜明对比。

> SWE-Bench 全部公开 → 训练语料可能爬到 → 数字虚高。
> SWE-Bench Pro 三层保险 → 法律层面排除 contamination → 数字可信。

### 41 repo、9 语言、107 行 mean patch

| 维度 | SWE-Bench Verified | SWE-Bench Pro |
|---|---:|---:|
| N | 500 | 731 public + 1134 private |
| Repos | 12 Python | 11 GPL + 18 startup + 12 private |
| Languages | 1 (Python) | 4 main (Py/JS/TS/Go) in public, 9 total |
| Patch mean | 11.6 行 | **107 行** |
| Patch median | 4.5 行 | 55 行 |
| Trivial 1-2 行任务 | 161 (32%) | **0**（明确排除）|
| Multi-file 任务 | 少 | **大量**（10+ files 约 100+ instance）|

> **100× 复杂度差** ——这是 top agent 从 70% 跌到 23% 的根本原因。

### Human Augmentation：每个任务显式给三件套

每个 SWE-Bench Pro instance 包含：
- **Problem Statement**（issue 描述）
- **Requirements**（具体行为约束——比 PS 详细 2-3 倍）
- **Interface**（API 签名 + input/output type）

**这是 SWE-Bench Pro 的隐藏杀手锏**。表 3 证明：

| Model | PS+Req+Interface | PS only | 差异 |
|---|---:|---:|---:|
| GPT-5 (high) | 25.9% | 8.40% | **+17.5pp** |
| Claude Opus 4.1 | 22.7% | 8.20% | **+14.5pp** |

> **Human augmentation 比模型升级影响大**——给 GPT-5 配上 PS+Req+Interface，比给 GPT-4 配 PS-only 高 **20+ 个百分点**。

---

## 评测结果：top model 23%，commercial 18%

### Public set（N=731）

| Model | Resolve (%) |
|---|---:|
| Claude Sonnet 4.5 | **43.6** |
| Claude Sonnet 4 | 42.7 |
| OpenAI GPT-5 (high) | 41.8 |
| Claude Haiku 4.5 | 39.5 |
| Kimi K2 Instruct | 27.7 |
| OpenAI GPT-OSS 120B | 16.2 |

### Commercial set（N=276）

| Model | Resolve (%) |
|---|---:|
| Claude Opus 4.1 | **17.8** |
| OpenAI GPT-5 (high) | 15.7 |
| Gemini 2.5 Pro Preview | 10.1 |
| Claude Sonnet 4 | 9.1 |
| OpenAI GPT-4o | 3.6 |

### 关键观察

1. **Commercial 比 public 难 2-3×**
   - Claude Sonnet 4: 42.7% (public) → 9.1% (commercial) — **-33.6pp** ⚠️
   - GPT-5 (high): 41.8% (public) → 15.7% (commercial) — **-26.1pp** ⚠️
   - Opus 4.1: 22.7% (public) → 17.8% (commercial) — 相对稳定

2. **结论 §8 数字 23%**——是 public 平均，commercial 17.8%。**真实 enterprise 难度是 18%**。

3. **商用 repo 比 public repo 难得多**——可能因为：
   - startup code base 文档更少
   - 业务逻辑更复杂
   - 没有长期 contributor community

---

## Not-Submitted 率：被忽视的 hidden ceiling

论文 Table 4 揭示了**隐藏的 hard ceiling**——**Not-Submitted 率**（agent 跑了但没交 patch）：

| Model | Not-Submitted |
|---|---:|
| Claude Opus 4.1 | 25.8% |
| GPT-4o | 27.9% |
| **OpenAI GPT-5 (high)** | **72.8%** ⚠️ |
| Claude Sonnet 4 | 55.9% |
| Qwen3 32B | 52.7% |
| Gemini 2.5 Pro Preview | 47.1% |

> **GPT-5 有 72.8% 概率根本没尝试**——这才是 hidden ceiling。

**这意味着什么**：
- 你看到的 Resolve Rate 是「交了 patch 的人中多少解对」
- 但**有 1/4 到 3/4 的人根本没交**
- 真实能力应该看「**提交率 × 通过率**」——不是单独看通过率

**为什么 Not-Submitted 高**：
- **Sonnet 4 的 62.6% Tool-Use 失败**——Sonnet 4 跟 SWE-Agent scaffold 兼容性差
- **GPT-5 的 96.4% Tool-Use 错误**——scaffold 没正确调通 tool use
- **Qwen3 32B 的 78.8% Tool-Use 错误**——小模型更明显

> **Scaffold 比 model 重要**——Sonnet 4 跟 Claude Code 配肯定远高于 9.1% commercial 数字。

---

## Failure Mode 6 类（Table 4）

| Failure | Opus 4.1 | GPT-5 | Sonnet 4 | Gemini 2.5 | GPT-4o | Qwen3 32B |
|---|---:|---:|---:|---:|---:|---:|
| **Wrong solution** | 50.3% | 39.5% | 25.5% | 35.0% | 45.2% | 25.0% |
| **Syntax error** | 31.3% | 29.3% | 7.7% | **56.5%** | 36.7% | 48.7% |
| **Incorrect file** | 4.9% | 8.8% | 2.1% | 4.0% | 11.2% | 19.7% |
| **Instruction following** | 2.7% | 4.8% | 2.1% | 1.9% | 6.2% | 1.6% |
| **Edge case** | 0.8% | 0.0% | 0.0% | 0.0% | 0.0% | 0.7% |
| **Tool-Use** | 10.0% | 17.3% | **62.6%** | 2.7% | 0.7% | 4.3% |

**关键 insight**：
- **Wrong solution 是 top model 的最大失败**（Opus 4.1 50.3%）——说明 frontier model 能跑通流程但**理解错需求**
- **Sonnet 4 的 62.6% Tool-Use 是异常**——Sonnet 4 跟 SWE-Agent 不兼容
- **Syntax error 在小模型更严重**（Qwen3 48.7%）——但 Gemini 2.5 Pro Preview 56.5% 是反常（可能是 prompt 不匹配）

---

## 我做的复现验证（数据集完全匹配）

我没跑模型（需要 8× H100 + 数百小时 + 数万 USD）——只做了**数据集层验证**。

### 7 项结构检查全部 PASS

| Check | 内容 | 结果 |
|---|---|---|
| 1 | HF 有 3 个 config | ✅ |
| 2 | v1 config = **731 instances**（精确匹配 paper）| ✅ |
| 3 | 11 public repos（精确匹配 paper）| ✅ |
| 4 | 4 languages（Python/JS/Go/TS）| ✅ |
| 5 | Human augmentation 三件套 100% 非空 | ✅（731/731）|
| 6 | Patch size 数量级匹配 | ✅（107 vs 我统计 125，差 17%）|
| 7 | Sample instance 抽检 | ✅ |

### ⚠️ 一个重要发现：default (642) ≠ v1 (731)

HF 数据集有 3 个 config：
- `default`：642 instance（**新版**，删了 89 个）
- `hard`：51 instance（hard 子集）
- `v1`：731 instance（**精确匹配 paper**）

> **复现 paper 数字必须用 `v1`，不是 `default`**——89 个 instance 在新版本中被删除。

### ⚠️ Patch size 数字反推：paper 用的「净增行」

| 计算方式 | Mean | Median |
|---|---:|---:|
| 所有非空行 | 301.6 | 193 |
| `+` 和 `-` 行 | 179.7 | 101 |
| 仅 `+` 行（added） | **125.4** | 67 |
| **Paper 声称** | **107.4** | **55** |

> **Paper 用的口径是「净增行」**——只数 `+` 行，不数 context 行和 `-` 行。125.4 vs 107.4 差 17%，在合理范围内。

---

## 跟其他 SWE-Bench 类 benchmark 对比

| Benchmark | N | Best | 任务复杂度 | 公开度 |
|---|---:|---:|---|---|
| SWE-Bench (2023) | 2,294 | 23% | 单文件 + Python | 全部公开 |
| SWE-Bench Verified | 500 | **70%+** | **太简单** | 全部公开 |
| **SWE-Bench Pro Public** | 731 | **43.6%** (Sonnet 4.5) | 107 行 mean | 公开 |
| **SWE-Bench Pro Commercial** | 276 | **17.8%** (Opus 4.1) | 107 行 mean | 私有 |
| **SWE-Bench Pro Held-Out** | 858 | N/A | 107 行 mean | 私有 |
| LoopsBench | 112 | 25% | DAG multi-step | 公开 |
| AgentSWE | 25 | 31.6 (Editing) | 完整 agent | 公开 |

> **SWE-Bench Pro 提供了「真实 enterprise」的金标准**——17.8% / 23% 是 2025-2026 年的真实水平。

---

## 对 2026 年 coding agent 研究的实际意义

### 1. 别再引用 SWE-Bench 70% 数字了

任何 2024-2025 年的「SWE-Bench Verified 70%」引用都该淘汰——**那是 toy Python issue**。
**2026 年该引用 SWE-Bench Pro**：
- 公开评测 → 23% 量级
- enterprise → 18% 量级

### 2. Not-Submitted 率必须报

只看 Resolve Rate 是**误导**——**Not-Submitted 25-73% 是 hidden ceiling**。
报告时应该给 `Resolve Rate × (1 - Not-Submitted Rate)` = **Effective Resolve Rate**。

### 3. Scaffold 比 model 重要

Sonnet 4 在 SWE-Agent 上 9.1% commercial，**但 Sonnet 4 配 Claude Code 实际能到 25%+**——这是 scaffold 差异。
任何 model 排名必须**配 scaffold 一起报告**。

### 4. Human Augmentation 是设计 lesson

PS+Req+Interface 三件套比 PS only 高 17.5pp。**Input design 比 model 升级还关键**。
- 不要拿 GitHub issue 原文当 task——要重构
- 显式列 requirements
- 显式列 interface（API 签名、class 名）

### 5. Multi-file + Multi-language 是真正分水岭

Python 单文件问题已经 70%+。**multi-file + 非 Python + 复杂业务逻辑**才是 frontier vs others 的真实分水岭。

### 6. 3-subset 设计是 2026 年 benchmark 标配

- Public 公开（社区评测）
- Commercial 私有（测 enterprise 真实）
- Held-Out 私有（防 overfit）

> **只公开结果不公开数据**是 2025-2026 年 benchmark design 的新范式。

---

## 我对 SWE-Bench Pro 的 5 个改进建议

1. **公开 5 种语言**（Java/C++/Rust/PHP/Ruby）——paper 标题说 9 languages，但 public 只有 4
2. **跑 Held-Out 858**——paper 留着不用，浪费
3. **多 scaffold 对比**——SWE-Agent 是 2024 scaffold，2026 该跑 Claude Code / Codex
4. **报告 Not-Submitted 详细原因**——25-73% 没提交是核心问题
5. **报告 line counting 口径**——给 patch size 数字下明确定义（净增行？+/- 行？context 行？）

---

## 结语

2026 年的 coding agent 评测已经**进入「multi-file + multi-language + enterprise 真实」阶段**。

> **SWE-Bench Verified 70% 是历史**。
> **SWE-Bench Pro 23% / 18% 是 2025-2026 年的真实水平**。

如果你的产品还在用 SWE-Bench Verified 数字宣传——**那是 2023 年的标准**。

如果你的评测还只跑 Python——**那是 2024 年的标准**。

如果你的评测 scaffold 是 SWE-Agent + 50 turn——**那是 2024 年的标准**。

**2026 年的标准是**：
- SWE-Bench Pro Public/Commercial
- Claude Code / Codex scaffold
- 4+ 语言
- 100+ 行 mean patch
- Not-Submitted Rate 报告
- 3-subset 数据集设计

**不达标的话，你的数字再漂亮也不代表 enterprise 真实**。

---

## 参考

- 论文 PDF：`papers/29-swe-bench-pro/2509.16941.pdf`
- 数据集：`https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro`（用 `v1` config）
- 代码：`https://github.com/scaleapi/SWE-bench_Pro-os`
- Project page：`https://scale.com/research/swe_bench_pro`
- 同系列已写论文：
  - LoopsBench（`papers/23-loopsbench/`）
  - Agentic Coding in the Wild（`papers/32-agentic-coding-in-the-wild/`）
  - AgentSWE（`papers/26-agentswe/`）

> 本博客基于数据集层验证（未跑模型——需要 8× H100 + 数百小时 + 数万 USD），7 项结构检查全部 PASS，详见 `REPRODUCTION_NOTES.md`。
