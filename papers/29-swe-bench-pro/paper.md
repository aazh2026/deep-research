# SWE-Bench Pro 论文中文解读

> Paper: Xiang Deng, Jeff Da, et al. (21 authors, Scale AI). **"SWE-Bench Pro: Can AI Agents Solve Long-Horizon Software Engineering Tasks?"** (arXiv: 2509.16941v2, 2025-09)
> Data: https://huggingface.co/datasets/ScaleAI/SWE-bench_Pro
> Code: https://github.com/scaleapi/SWE-bench_Pro-os
> 解读日期: 2026-10-14

---

## 一句话定位

> Scale AI 在 2025-09 放出的 **SWE-Bench 续作**——把 12 个 Python repo（500 个 trivial patch）扩成 **41 个 repo / 9 语言 / 1865 个 multi-file 任务**，并通过**许可证策略**（GPL only）和**商业 repo 采购**做到 contamination-resistant。
>
> 核心结论：top agent 在 public set 上 ~23% resolve rate，**比 SWE-Bench Verified 的 70% 跌 3 倍**——这才是 2026 年 enterprise software engineering 的真实水平。

---

## 1. 为什么需要 SWE-Bench Pro

### 1.1 SWE-Bench 的三个根本问题

论文 §1 列出当代 coding benchmark 的三个局限：

1. **Data contamination** — 来自 permissive license（MIT/Apache/BSD）的 repo 在 LLM 训练语料里很容易出现。Constructing benchmark from public GitHub 本身就跟 training set 边界模糊。
2. **Task complexity too low** — SWE-Bench Verified 里 161/500 (32%) 只需要改 1-2 行代码。**Industrial software engineering** 是 multi-file 几百行改。
3. **Single-language bias** — SWE-Bench 几乎全是 Python。Multi-SWE-bench (Zan 2024) 加了 JS/TS/Java/Go/Rust/C++，但样本量小。

### 1.2 SWE-Bench Pro 的三个对应解法

| 问题 | SWE-Bench Pro 解法 |
|---|---|
| Contamination | 1) **严格 GPL/copyleft only** + 2) **从 startup 采购 commercial repo** |
| Task complexity | 每个 problem 平均 107 行 patch（vs SWE-Bench Verified 11.6 行）|
| Single-language | 9 种语言（Python/JS/TS/Go 等）|

> **核心创新是「contamination-resistant by design」**——不是事后检测，而是**构造阶段就用许可证策略把 training set 排除掉**。

---

## 2. 数据集结构

### 2.1 三个 subset（防 overfit 双重保险）

| Subset | Size | 来源 | 可见性 | 用途 |
|---|---|---|---|---|
| **Public** | 731 | GPL/copyleft GitHub repo | 公开在 HF | 社区评测 |
| **Commercial** | 276 | 从 startup 采购 | 私有，**只公开结果** | 反映 enterprise 真实 |
| **Held-Out** | 858 | 类似 public 结构的私有 repo | 私有 | 未来 overfit 检测 |
| **总计** | **1865** | | | |

**关键设计**：
- **Public 公开** → 任何人都可以跑，可以检测 contamination
- **Commercial 只公开结果** → 防止「训练时直接爬 commercial repo」
- **Held-Out 私有** → 即使 public 已被 contamination，未来还有 overfit detection 手段

> **这是 2025 年 benchmark 设计的新范式**——**只公开结果不公开数据**。SWE-Bench 当时全公开，导致 training set 边界模糊。

### 2.2 41 个 repo 的分布（§3.1, Figure 1）

- 11 个 public GPL repo → 731 个 public instances
- 18 个 startup 商业 repo → 276 commercial instances
- 12 个 private held-out repo → 858 instances
- 每 repo 限制 50–100 instances，最多 100（避免单 repo 主导）

### 2.3 9 种语言（Figure 3 right）

论文只强调 Python/JS/TS/Go 四种主力，**承认** Java/C++/Rust 不足（§7.1 limitation）。

### 2.4 任务复杂度对比（Figure 1）

| | SWE-Bench Verified | SWE-Bench Pro |
|---|---|---|
| Patch lines (mean) | 11.6 | **107.4** |
| Patch lines (median) | 4.5 | 55.0 |
| Files per task | 1.x | 1–19+（含 10+ 约 100+ instance）|
| Trivial 1-line task | 161/500 (32%) | **0**（明确排除）|

> 100× 复杂度差——这就是 top agent 从 70% 跌到 23% 的根本原因。

---

## 3. 数据集构造流程

### 3.1 4 步（§4）

**Step 1: Sourcing Problems**
- 用 commit history 找 consecutive commit pairs
- Older commit = base，newer = instance
- Test patch = 测试相关 diff（verify 修复）
- Gold patch = 其余 diff（agent 应当产出）

**Step 2: Creating Task Descriptions**
- **人类补充** task description（commit message 不够用）
- 三件套：
  - **Problem statement**（动机）
  - **Requirements**（具体行为约束，避免 ambiguity）
  - **Interface**（API 签名、class/method names 防 false negative）

**Step 3: Creating Environments**
- Docker images，**包含完整 dependency resolution**
- Python：isolated venv
- JS/TS/Go：Node.js + npm/yarn + GOPATH
- 每个 task 一个 docker image

**Step 4: Test Verification**
- 人类 verify **所有 test 都是 fail2pass**（issue 没修时 fail，修完后 pass）
- 任何 test 修不修都过 → 删
- 任何 test 跟 issue 无关 → 删
- 任何 test run-to-run 不稳定 → 删

> **Test hygiene 比 dataset size 更重要**——一个 flaky test 就能让 benchmark 数字失真。

### 3.2 Human Augmentation 的影响（Table 3）

| Model | With Aug (PS+Req+Interface) | Without Aug (PS only) | 差异 |
|---|---:|---:|---:|
| OpenAI GPT-5 (high) | 25.9% | 8.40% | **-17.5pp** |
| Claude Opus 4.1 | 22.7% | 8.20% | **-14.5pp** |

**没有 human augmentation，top agent 也会跌到 8%**。

> **核心洞察**：SWE-Bench 类 benchmark 的「input design」对结果影响**比模型升级还大**。把 PS+Req+Interface 三个组件都提供时，GPT-5 高出**17.5 个百分点**。

论文 §6.2 解释：unit test 是「narrow verifier」——只 accept 特定 API 形式。Human augmentation 显式告诉 agent 该用什么 API，避免了「正确解决但 test fail」的 false negative。

---

## 4. 评测结果（Table 1 + Table 2）

### 4.1 Public set (N=731) — Table 1

| Model | Resolve (%) |
|---|---:|
| Claude Sonnet 4.5 | **43.6** |
| Claude Sonnet 4 | 42.7 |
| OpenAI GPT-5 (high) | 41.8 |
| Claude Haiku 4.5 | 39.5 |
| Kimi K2 Instruct | 27.7 |
| OpenAI GPT-OSS 120B | 16.2 |

### 4.2 Commercial set (N=276) — Table 2

| Model | Resolve (%) |
|---|---:|
| Claude Opus 4.1 | **17.8** |
| OpenAI GPT-5 (high) | 15.7 |
| OpenAI GPT-5 (medium) | 14.9 |
| Gemini 2.5 Pro Preview | 10.1 |
| Claude Sonnet 4 | 9.1 |
| OpenAI GPT-4o | 3.6 |

### 4.3 关键观察

1. **Public vs Commercial 巨大 gap**
   - Claude Opus 4.1: 22.7% (public) vs 17.8% (commercial) — **-5pp**
   - Claude Sonnet 4: 42.7% (public) vs 9.1% (commercial) — **-33.6pp ⚠️**
   - GPT-5 (high): 41.8% (public) vs 15.7% (commercial) — **-26.1pp ⚠️**
   - GPT-4o: 27.7%? (public) vs 3.6% (commercial) — **-24pp** (note: public is 27.7 for Kimi, GPT-4o not in Table 1)

2. **商用 repo 比 public repo 难得多**——可能因为：
   - startup code base 文档更少
   - 业务逻辑更复杂
   - 没有长期 contributor community

3. **结论 §8 数字**：top model 在 SWE-Bench Pro 上 23%，在 SWE-Bench Verified 上 70%+。
   - 实际是 public 23%，commercial 更低
   - **3× 差距** —— 是「真实 enterprise software engineering」vs「toy Python issue」的距离

### 4.4 跨语言与跨 repo 表现（Figure 3）

- **JS/TS/Go/Python** 是 4 种主要语言
- Python 普遍最强（model-specific，~30%+）
- JS/TS 表现极不均匀（某些 repo < 10%，某些 > 30%）
- 10+ files 任务：frontier models 仍 > 10%，open-source 接近 0
- 500+ LoC 任务：最难的 bin，frontier models 仍能 ~12%

---

## 5. Trajectory Failure Modes（Table 4）

论文用 **LLM-as-a-judge (GPT-5)** 把 6 个模型的失败 trajectory 分类。6 类 failure：

| Failure | Claude Opus 4.1 | GPT-5 (high) | Sonnet 4 | Gemini 2.5 Pro | GPT-4o | Qwen3 32B |
|---|---:|---:|---:|---:|---:|---:|
| **Wrong solution** | 50.3% | 39.5% | 25.5% | 35.0% | 45.2% | 25.0% |
| **Syntax error** | 31.3% | 29.3% | 7.7% | **56.5%** | 36.7% | 48.7% |
| **Incorrect file** | 4.9% | 8.8% | 2.1% | 4.0% | 11.2% | 19.7% |
| **Instruction following** | 2.7% | 4.8% | 2.1% | 1.9% | 6.2% | 1.6% |
| **Edge case** | 0.8% | 0.0% | 0.0% | 0.0% | 0.0% | 0.7% |
| **Tool-Use** | 10.0% | 17.3% | 62.6% | 2.7% | 0.7% | 4.3% |
| **Not-submitted rate** | 25.8% | 72.8% | 55.9% | 47.1% | 27.9% | 52.7% |

### 5.1 关键观察

1. **Sonnet 4 的 62.6% Tool-Use failure 是异常**——可能 Sonnet 4 跟 SWE-Agent scaffold 兼容性差
2. **Not-submitted 比例惊人**
   - GPT-5: **72.8%** 没提交任何 patch
   - Sonnet 4: 55.9% 没提交
   - Qwen3: 52.7% 没提交
   - Opus 4.1: 25.8% 没提交（最低）
   - **frontier model 有 25–73% 的概率直接放弃任务**——这是 hidden dimension
3. **Long-context 失败是 Sonnet 4 的核心问题**：57.4% 死在长 context 上
4. **Tool-Use 失败**是 frontier model 的相对优势（Opus 4.1 仅 10%，Sonnet 4 高达 62.6%）

### 5.2 关键洞察

> **「Not-Submitted」率是隐藏的 hard ceiling**——如果你连 patch 都不交，Resolve Rate 自然 0。
> 
> SWE-Bench Pro 揭示了 2025 年的真实状况：top model **有 1/4 到 3/4 概率根本没尝试**。

---

## 6. 与 SWE-Bench (Verified) 的关系

| 维度 | SWE-Bench Verified | SWE-Bench Pro Public | SWE-Bench Pro Commercial |
|---|---|---|---|
| N | 500 | 731 | 276 |
| Repos | 12 Python | 11 GPL | 18 startup |
| Languages | 1 (Python) | 4+ (Python/JS/TS/Go) | 4+ |
| Patch mean | 11.6 lines | 107.4 lines | ? |
| Trivial 1-line | 161 (32%) | 0 | 0 |
| Best Resolve | 70%+ (2025) | **43.6%** (Sonnet 4.5) | **17.8%** (Opus 4.1) |
| Contamination | High (permissive) | Low (GPL only) | Very Low (purchased private) |
| Human Aug | No | **Yes (PS+Req+Interface)** | Yes |
| Public data | Yes (HF) | Yes (HF) | No |

> **SWE-Bench Pro 不是替换 SWE-Bench**——而是**重新校准**它。SWE-Bench 70% 的数字让公众高估了 agent 能力，SWE-Bench Pro 23% 才是 2025 年真实 enterprise software engineering 难度。

---

## 7. 评测方法学细节（§5）

### 7.1 Scaffold
- **SWE-Agent** 作为主 scaffold（论文来自 SWE-Agent 团队）
- 也试了 **Agentless**——但 multi-file 表现差，弃用
- max 50 turns
- Open-source LLM 用 vLLM host，single node 8× H100

### 7.2 Issue Ambiguity 设置
- "without ambiguity"：给 model 完整 PS+Req+Interface
- 这是默认设置——测的是**「修一个具体问题」**的能力，不是**「理解模糊需求」**的能力

### 7.3 Pass@1
- Single run per problem
- 不取 best-of-N

### 7.4 评测协议限制
- **依赖 test suite**（fail2pass + pass2pass）——限论文 §7.1
- 真实任务可能有多种正确解法，original test 只能 accept 一种

---

## 8. 与本系列其他论文的关系

| 论文 | 测什么 | 与 SWE-Bench Pro 关系 |
|---|---|---|
| **LoopsBench** (2608.00267) | 长程 loop engineering | 测的是**「持续在 repo 上工作」**——SWE-Bench Pro 是**「一次性修一个 issue」** |
| **Agentic Coding in the Wild** (2608.00101) | Production telemetry 形状 | 反映**生产里** agent 是什么 workload；SWE-Bench Pro 是**评测** |
| **AgentSWE** (2610.13361) | 受托 agent 是否实现 requirement | 测**「agent 造 agent」**；SWE-Bench Pro 是**「agent 修代码」** |
| **SWE-Bench Pro** (2509.16941) | Long-horizon software engineering | **直接挑战 SWE-Bench 的天花板** |

> 4 篇合起来：
> - **SWE-Bench Pro**：评测——单次多文件任务上限
> - **LoopsBench**：评测——长程 loop 持续工作
> - **AgentSWE**：评测——受托造 agent
> - **Agentic Coding**：实证——生产里实际什么形状

**SWE-Bench Pro 跟 AgentSWE 不冲突**——前者测 **修一个 100 行 patch**，后者测 **造一个能用的 agent**。但两者都揭示了**「SWE-bench 70% 是错觉」**。

---

## 9. 论文方法学评价

### 优点
1. **污染抵抗设计**——GPL only + commercial 采购 + held-out 私有，**三层保险**
2. **任务复杂度升级明显**——107 行 mean patch vs 11.6
3. **公开 human augmentation 数据**——揭示「input design 比模型升级更关键」
4. **Failure mode 分类可信**——LLM-as-judge with 87% alignment (cite Yang 2024)
5. **Cross-set 验证**——public vs commercial 差异自然暴露 enterprise 难度

### 局限（论文自承）
1. ❌ **语言覆盖不全**——Java/C++/Rust 不足
2. ❌ **依赖 test suite**——只能 accept 特定解法（pass@1 限制）
3. ❌ **Not-submitted 率高**——frontier model 25-73% 放弃——这本身说明 task 难度超过 agent 能力
4. ❌ **没有分析 budget**——50 turn 是任意的
5. ❌ **未测 model 升级的 marginal effect**——只有 single-run 数字

### 关键风险（论文未充分讨论）
- ⚠️ **Commercial 276 instance 太少**——CI bound 宽，17.8% 的真实置信区间可能 [12%, 24%]
- ⚠️ **GPL only 仍可能 contamination**——某些 large GPL repo 在 training set 里出现
- ⚠️ **Failure mode 分类是 GPT-5 judge**——可能 GPT-5 bias 自家 model
- ⚠️ **没有 prompt variation 报告**——单 prompt 结果
- ⚠️ **「23%」结论过度简化**——public 23% vs commercial 17.8% 是不同难度

### 论文没说但有意义的
- **2025-09 的 SWE-Agent scaffold 在 2026 年已不是 frontier**——Sonnet 4.5、GPT-5 之后还有 Claude Code、Codex 等
- **Held-Out 858 没用上**——留着防 overfit 是个 nice 想法，但目前没有任何人 published 验证
- **Pass@5 / Pass@10 没测**——multi-sample 是 2026 年的常见做法

---

## 10. 落地建议（如果你在做 coding agent）

### 如果你要在 SWE-Bench Pro 上做 leaderboard 排名

1. **永远要 PS+Req+Interface 三件套**——单 PS 会跌 17.5pp
2. **Not-submitted 率是 hidden ceiling**——优化 first-submit rate
3. **Tool-Use 失败是 Sonnet 4 的绊脚石**——但 GPT-5/Opus 4.1 很低
4. **10+ files 任务是 frontier vs open-source 的分水岭**
5. **商用 set 比 public 难 2-3×**——别只用 public 数字

### 如果你是 benchmark designer

1. **许可证策略是 contamination-resistant 的最简方法**——但仅限 public 数据
2. **采购 commercial repo** 才能测 enterprise 真实难度
3. **Human augmentation 比 model 升级影响更大**——Table 3 的 17.5pp 是 design lesson
4. **Failure mode 分类比单一 Resolve Rate 信息量大**
5. **留出 held-out 留出未来**——即使你现在不用

### 如果你是 user

1. **别信 SWE-Bench 70% 数字**——那不是 enterprise 真实水平
2. **真实 enterprise 难度是 20% 量级**——top agent 能解 1/5
3. **multi-file 任务 + 复杂业务逻辑 + 文档不全**——这是 80% 真实任务形态
4. **agent 经常「不提交」**——你需要 scaffold 鼓励「先交一版」

---

## 11. 核心 takeaway（一句话）

> **SWE-Bench Pro 撕开了 2025-2026 年 coding agent 评测的真相**：top agent 在 100 行 multi-file 任务上 23%，在商业 enterprise 任务上 18%——**比 SWE-Bench Verified 70% 低 3-4 倍**。任何还在用 SWE-Bench 数字说「agent 已经能自动化软件工程」的人，都没看到 enterprise 真实。
