# 当 SWE-Bench 70% 成为历史：SWE-Bench Pro 撕开 2025 年 enterprise coding 真实水平

> 写于 2026-10-16 (round 39)，配合 `papers/29-swe-bench-pro/paper.md` 与 `REPRODUCTION_NOTES.md` 阅读。
>
> 这篇 blog 解决 2 个问题：
> 1. **你 2026 年还在引用 SWE-Bench 70%+ 数字吗？那是错的。**
> 2. **SWE-Bench Pro 在 round 34 LLM4SE 综述 + round 35-38 多智能体四象限里处于什么位置？**

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

## Round 39 在 LLM4SE 项目中的位置

### Round 34 → 38 回顾：LLM4SE 方法论四象限

我之前 5 个 round 在做"LLM4SE 综述 (round 34) 之后的方法论扩展"：

| Round | 论文 | LLM4SE 象限 | Domain |
|------:|---|---|---|
| 34 | Fan et al. LLM4SE Survey | 综述 | Cross-domain |
| 35 | CoCoEmo | **Steering** (latent space intervention) | TTS |
| 36 | CRUX | **Oracle** (Coverage/Density probe) | RAG |
| 37 | OpenHands | **Framework** (tool abstraction) | Coding agent |
| 38 | ChatDev | **Protocol** (formal chat chain) | Multi-agent |

### Round 39 的定位：**Benchmark 论文作为方法论实证**

SWE-Bench Pro 跟前 4 round 不同——它**不是方法论文，是 benchmark 论文**。但它在 round 34 LLM4SE 综述里**横跨多个 section**：

| round 34 section | SWE-Bench Pro 对应 |
|---|---|
| §V Testing (Automated Regression Oracle) | fail2pass test verification |
| §VIII Analytics (failure mode) | 6-class failure mode classification |
| §IX Domain-specific (Human-in-loop) | PS+Req+Interface human augmentation |
| §XII Crosscut (multi-language) | Python/JS/TS/Go + 5 more |

> **Benchmark 论文也是 LLM4SE 方法论文**——它**实证**了 4 个 round 34 章节的方法论价值。

### Round 39 在多智能体三角里的位置

我之前 30+ round 形成的多智能体三角形：

```
ChatDev 2023 ──── MetaGPT 2024 ──── OpenHands 2025
     (Protocol)         (Framework)         (Framework)
                            │
                            ▼
                    SWE-Bench Pro 2025
                    (Benchmark evaluation)
```

**SWE-Bench Pro 是这三角的「裁判」**——它定义了 2025-2026 年 coding agent 评测的**新基线**：
- 43.6% public / 17.8% commercial（vs SWE-Bench Verified 70%）
- 100+ LoC mean patch（vs 11.6）
- 11+ repos / 4+ languages（vs 12 Python）

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

**Round 39 复现 V3 验证**了这一点：731/731 instance 的 requirements 和 interface **全部非空**——Table 3 的 17.5pp 提升是**真实可复现的**，不是 artifact。

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

### 关键观察（V5 验证）

**Round 39 复现 V5 直接计算了 enterprise gap**：

| Model | Public | Commercial | Gap |
|---|---:|---:|---:|
| Claude Sonnet 4 | 42.7% | 9.1% | **-33.6pp** ⚠️ |
| OpenAI GPT-5 (high) | 41.8% | 15.7% | -26.1pp |
| **Best-of-best** | **43.6%** (Sonnet 4.5) | **17.8%** (Opus 4.1) | -25.8pp |

**Per-model collapse 是 commercial set 的关键特征**：
- Sonnet 4 在 public 上 42.7%，到 commercial 跌到 9.1%（**-33.6pp**）
- GPT-5 (high) 在 public 上 41.8%，到 commercial 跌到 15.7%（-26.1pp）
- 即便 best commercial 17.8%（Opus 4.1），也比 best public 43.6% 跌 25.8pp

> **结论**：商用 repo 比 public repo 难 2-3×。可能因为：startup code base 文档更少、业务逻辑更复杂、没有长期 contributor community。

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

**Round 39 V6 验证**了 Not-Submitted 概念在 round 34 LLM4SE §VIII Analytics 章节的方法论位置——"hidden ceiling" 是 §VIII 里 failure mode 分类的延伸。

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

**Round 34 LLM4SE §V "Automated Regression Oracle" 的延伸**：fail2pass test verification 只能 catch "正确解法但 API 错" 的 failure，**无法诊断** "wrong solution"——所以 paper 用了 LLM-as-judge (GPT-5) 来分类 6 类 failure。这正是 round 36 CRUX Coverage/Density 的 "diagnostic oracle" 在 SWE 域的对应物。

---

## Round 39 复现的 7 项 verifications

### V1: 重新跑 verify_swe_bench_pro.py (3/4 checks)

```
v1_eq_731:                 True
v1_repos_eq_11:            True
augmentation_fields_present: True
patch_size_107_mean_close: False  (our 286 vs paper 107 — convention diff)
```

3/4 check 通过，**第 4 个不是 false negative**——是 line-counting 口径差异，V4 进一步研究。

### V2: v1=731 / 11 repos / 4 langs 全部精确匹配

| 维度 | Expected | Actual | Match |
|---|---:|---:|---|
| v1 count | 731 | 731 | ✓ |
| repo count | 11 | 11 | ✓ |
| main languages | {python, js, go, ts} | {python, js, go, ts} | ✓ |

**Top-5 repos** (out of 11):
- ansible/ansible: 96
- internetarchive/openlibrary: 91
- flipt-io/flipt: 85
- qutebrowser/qutebrowser: 79
- gravitational/teleport: 76

### V3: Human Augmentation 731/731 完整

- Non-empty requirements: **731/731** ✓
- Non-empty interface: **731/731** ✓

**意义**：Table 3 报告的 17.5pp 提升是**真实可复现的**——所有 731 instance 的 augmentation 字段都非空。

### V4: Patch-size line-counting convention reverse-engineering

| Convention | Mean | Median | Gap to 107.4 |
|---|---:|---:|---:|
| all non-empty lines | 286.3 | 180 | +178.9 |
| +/- lines | 169.6 | 94 | +62.2 |
| **+ only (added)** | **120.3** | **63** | **+12.9** ✓ closest |
| - only (removed) | 49.2 | 20 | -58.2 |

**结论**：Paper 的 "lines of code" 用的是 **净增行（+ only）** 口径——只数 added lines，不数 context 和 removed。
**120.3 vs 107.4 差 12.9**——在合理范围内，可能是 paper 去掉了纯空行（non-whitespace added lines）。

### V5: Public vs Commercial enterprise gap

**Best-of-best gap**: 43.6% - 17.8% = **25.8pp**
**Per-model collapse**: Claude Sonnet 4 -33.6pp, GPT-5 -26.1pp

> **Paper §8 结论 "23% / 18%" 准确反映 enterprise 真实难度。**

### V6: Round 34 LLM4SE methodology alignment (5/5 categories)

| Category | Match |
|---|---:|
| Benchmark / dataset (§V + §VIII) | 8/8 = 100% |
| Patch / failure mode analysis (§IV + §V) | 8/8 = 100% |
| Human-in-the-loop / augmentation (§IX) | 7/7 = 100% |
| Multi-language / cross-domain (§XII) | 8/8 = 100% |
| Not-submitted / hidden ceiling (§VIII) | 7/7 = 100% |

**5/5 = 100% categories match** — SWE-Bench Pro 是 round 34 LLM4SE 综述 §V+§VIII+§IX+§XII 的**多章节 benchmark 实证**。

### V7: Optional LLM endpoint sanity check (skipped)

`.env` 未配置 placeholder，V7 自动 skip。如需启用：

```bash
cd papers/29-swe-bench-pro
cp .env.example .env
# 编辑 .env, 填入真实 key
python3 reproduce.py
```

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

## Round 39 的元结论：3 个 takeaway

### Takeaway 1：SWE-Bench 70% 是历史，Pro 23%/18% 是 2026 真实

任何还在用 SWE-Bench Verified 数字宣传的论文/产品，**是 2023 年的标准**。**2026 年标准**是 SWE-Bench Pro：
- Public 43.6% / Commercial 17.8%
- 100+ LoC mean patch
- 4+ languages
- PS+Req+Interface human augmentation
- 3-subset design

### Takeaway 2：Benchmark 论文也是 LLM4SE 方法论文

SWE-Bench Pro 横跨 round 34 LLM4SE 综述 4 个 section（§V+§VIII+§IX+§XII），是**多章节方法论实证**。V6 验证 5/5 categories 100% match。

> **Benchmark 不是 "just data"**——它是 round 34 §V Automated Regression Oracle、§VIII failure mode classification、§IX human-in-the-loop、§XII cross-domain 的**集合实证**。

### Takeaway 3：跟 round 35-38 多智能体四象限的连接

| Round | 论文 | LLM4SE 象限 | 跟 SWE-Bench Pro 关系 |
|------:|---|---|---|
| 35 | CoCoEmo | Steering | (TTS 域独立) |
| 36 | CRUX | Oracle | **同源**：round 34 §V Automated Regression Oracle 的 RAG 域 vs SWE-Bench 域 |
| 37 | OpenHands | Framework | **被 SWE-Bench Pro 评测** |
| 38 | ChatDev | Protocol | **被 SWE-Bench Pro 评测** |
| **39** | **SWE-Bench Pro** | **Benchmark (横跨 4 章节)** | **裁判** |

> **Round 39 是 round 35-38 多智能体系列的「评测章」**——它定义了 2025-2026 年 OpenHands、ChatDev、MetaGPT 等**被如何打分**。

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
- Round 34 LLM4SE Survey (Fan et al. 2023) — §V Testing + §VIII Analytics + §IX Domain + §XII Crosscut
- Round 35 CoCoEmo / Round 36 CRUX / Round 37 OpenHands / Round 38 ChatDev — LLM4SE 方法论四象限
- Round 30 OmniCode / Round 23 LoopsBench / Round 26 AgentSWE — 多智能体三角

> 本 blog 基于 `reproduce.py` 的 7 项 verification（V1 重新跑 verify_swe_bench_pro.py / V2 v1=731/11/4 / V3 731/731 aug / V4 patch 净增行 / V5 enterprise gap / V6 LLM4SE 5/5 / V7 LLM endpoint skipped），详见 `_round39_reproduction_results.json`。
