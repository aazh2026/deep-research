# MetaGPT 论文解读 (DeepWisdom + KAUST, ICLR 2024)

> 论文: **MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework**
> 作者: Sirui Hong, Mingchen Zhuge, Jonathan Chen, Xiawu Zheng, Yuheng Cheng, Ceyao Zhang, Jinlin Wang, Zili Wang, Steven Ka Shing Yau, Zijuan Lin, Liyang Zhou, Chenyu Ran, Lingfeng Xiao, Chenglin Wu, Jürgen Schmidhuber
> 链接: arXiv:2308.00352v7, ICLR 2024 (Nov 2023)
> 解读日期: 2026-10-15
> 主题: **用 SOP (Standardized Operating Procedures) 编排 multi-agent, 解决 LLM 协作的" 鸡尾酒会 "问题**

---

## 0. 为什么这一轮复现 MetaGPT?

15 轮 /loop 复现过的 paper:
- round 6-14: 全部单 agent / multi-turn / 一次性 LLM 改
- round 15: 5-gate PQC ladder — 但还是 **single LLM call 写, 多个 gate 验**

**没有 paper 专门研究 "**多个 LLM agent 怎么协作才能真 work**"**。MetaGPT 是**第一个** 真正工业级 multi-agent SOP framework, 报了一个 SOTA 数字:
- **Pass@1 85.9% on HumanEval** (vs GPT-4 67.0%)
- **Pass@1 87.7% on MBPP** (vs GPT-4 67.0%, +5.4% absolute over MetaGPT w/o feedback)
- **3.75/4 executability on SoftwareDev** (vs ChatDev 2.25/4)

**本轮复现目标**:
- 6 个 mini HumanEval task, **ablation 4 个 setting**:
  1. Baseline: 单 LLM call, 无 SOP
  2. MetaGPT-lite: 1 agent (Engineer only)
  3. MetaGPT-lite: 3 agents (Product + Architect + Engineer)
  4. MetaGPT-lite: 3 agents + executable feedback (test-driven retry)
- 测 "**SOP 真 work 吗**" / "**feedback 真 +5% 吗**" / "**更多 role 更好吗**"

---

## 1. 论文核心问题

### 1.1 LLM multi-agent 的" 鸡尾酒会 "问题

```
传统 LLM multi-agent 协作 (如 ChatDev / AgentVerse):
  A: "Hi, how are you?"
  B: "Great! Have you had lunch?"
  C: "Hello..."
  → 经过 5 轮 "social chatter" 后, 原始 task 已经被稀释
  → 真正 work 的代码 / 内容比例低
```

**MetaGPT 的观察**: 人类社会解决这个问题的办法是 **SOP (Standardized Operating Procedures)** — 工厂流水线、医生会诊、code review 都有 SOP。**LLM agent 也应该有 SOP**。

### 1.2 MetaGPT 的 3 大设计

1. **Role Specialization** — 5 个固定 role: Product Manager / Architect / Project Manager / Engineer / QA Engineer
2. **SOP Workflow** — 流水线: PM 写 PRD → Architect 写 design → PM 拆 task → Engineer 写 code → QA Engineer 写 test
3. **Structured Communication** — 不用 free-form dialogue, 用 structured output (JSON / Message Pool + Subscribe)

---

## 2. MetaGPT 架构 (Figure 1-3)

### 2.1 5 个 Role

| Role | 输出 | Profile |
|---|---|---|
| **Product Manager** | PRD (User Stories + Requirement Pool + Competitive Analysis) | "Goal: maximize product value" |
| **Architect** | System Design (File List + Data Structures + Interface APIs) | "Goal: ensure design is feasible" |
| **Project Manager** | Task List (Logic Analysis + Task Allocation) | "Goal: optimize resource use" |
| **Engineer** | Code (Class + Function + Comments) | "Goal: write elegant, readable, extensible, efficient code" |
| **QA Engineer** | Test cases (Unit Test + Edge cases) | "Goal: ensure code is correct" |

### 2.2 Assembly Line Paradigm

```
User: "Make the 2048 sliding tile number puzzle game"
   ↓
[PM]    → PRD: "Web-based 2048 game, user-friendly"
   ↓
[Arch]  → Design: pygame + main.py + game.py + test_game.py
   ↓
[PM]    → Tasks: "main loop / game over / input"
   ↓
[Eng]   → Code: game.py with self.size / self.score / etc.
   ↓
[QA]    → Tests: test_game.py with assert statements
   ↓
Acceptance Check → Output
```

### 2.3 Structured Communication

- **Shared Message Pool** — 所有 agent publish structured message, 不是 dialogue
- **Subscribe Mechanism** — agent 只订阅跟自己 role 相关的 message
- **Action-Output Standardization** — 每个 action 有 schema, 强制 LLM 输出 structured data

---

## 3. Executable Feedback (Section 3.3) — 跟 round 12/15 串起来

```
Engineer 写完 code → 写 test → 跑 test
  if test fail:
    Error message → Engineer 改 code
  if test pass:
    QA Engineer 进一步 review
```

**跟 round 12 (Reflexion) 几乎一样**:
- Reflexion: 写 → 跑 test → 失败反思 → 再写
- MetaGPT executable feedback: 写 → 写 test → 跑 → 失败 debug → 再写

**不同**: MetaGPT 有 SOP, 每个 agent 有 specific role; Reflexion 是 single agent 反思。

**paper 数据**: 4.2% (HumanEval) / 5.4% (MBPP) improvement 来自 executable feedback。

---

## 4. 关键实验结果 (Section 4)

### 4.1 Pass@1 on HumanEval / MBPP (Figure 4)

```
                            HumanEval    MBPP
AlphaCode (1.1B)             17.1%        -
Incoder (6.7B)               15.2%       17.6%
CodeGeeX (13B)               18.9%       26.9%
CodeGen-Mono (16.1B)         32.9%       38.6%
PaLM Coder (64B)             36.0%       47.0%
Codex (175B)                 47.0%       58.1%
Codex + CodeT                65.8%       67.0%
GPT-4                        67.0%         - 
─────────────────────────────────────────────
MetaGPT (w/o feedback)       81.7%       82.3%
MetaGPT                      85.9%       87.7%  ← SOTA
```

**5.4% absolute gain on MBPP from executable feedback** (82.3 → 87.7).

### 4.2 Statistical Analysis on SoftwareDev (Table 1)

| Index | ChatDev | MetaGPT w/o Feedback | MetaGPT |
|---|---|---|---|
| **(A) Executability (1-4)** | 2.25 | 3.67 | **3.75** |
| **(B) Cost#1: Time (s)** | 762 | 541 | 503 |
| **(B) Cost#2: Token Usage** | 19,292 | 24,613 | 31,255 |
| **(C) Code Files** | 1.9 | 4.6 | 5.1 |
| **(C) Lines per File** | 40.8 | 42.3 | 49.3 |
| **(C) Total Code Lines** | 77.5 | 194.6 | 251.4 |
| **(D) Productivity (tok/line)** | 248.9 | 126.5 | 124.3 |
| **(E) Human Revision Cost** | 2.5 | 2.25 | **0.83** |

**3 个关键 finding**:
- **MetaGPT 3.75/4 executability vs ChatDev 2.25** — SOP 真 work, **+1.5 档**
- **MetaGPT 0.83 human revision cost vs ChatDev 2.5** — 3x 少改, **structured communication 真省 review**
- **MetaGPT 503s vs ChatDev 762s** — 33% 快, **assembly line 比分 role-chat 高效**

### 4.3 Ablation on Roles (Table 3)

| Roles | # Agents | Lines | Expense | Revisions | Executability |
|---|---|---|---|---|---|
| Eng | 1 | 83.0 | **$0.915** | 10 | 1.0 |
| Eng + Product | 2 | 112.0 | $1.059 | 6.5 | 2.0 |
| Eng + Product + Arch | 3 | 143.0 | $1.204 | 4.0 | 2.5 |
| Eng + Product + Arch + Proj | 3 | 205.0 | $1.251 | 3.5 | 2.0 |
| **All 4** | **4** | **191.0** | $1.385 | **2.5** | **4.0** |

**关键**:
- **Roles 越多 → revisions 越少 (10 → 2.5)** — 多 SOP 减少 rework
- **Roles 越多 → executability 越高 (1.0 → 4.0)** — 多 review 提升质量
- **Expense 上升但 productivity 也上升** — $0.92 → $1.39, 4x executability, 单位 quality 成本下降

### 4.4 Capabilities Comparison (Table 2)

| Capability | AutoGPT | LangChain | AgentVerse | ChatDev | MetaGPT |
|---|---|---|---|---|---|
| PRD generation | ✗ | ✗ | ✗ | ✗ | ✓ |
| Technical design | ✗ | ✗ | ✗ | ✗ | ✓ |
| API interface | ✗ | ✗ | ✗ | ✗ | ✓ |
| Code generation | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Precompilation exec** | ✗ | ✗ | ✗ | ✗ | ✓ |
| **Role-based task mgmt** | ✗ | ✗ | ✗ | ✓ | ✓ |
| **Code review** | ✗ | ✗ | ✗ | ✓ | ✓ |

**MetaGPT 唯一一个有" Precompilation execution"** (executable feedback, Section 3.3)。

---

## 5. 跟 15 轮 /loop 的关系

| 轮 | 复现对象 | 跟本轮关系 |
|---|---|---|
| 6 SWE-agent | single agent long-horizon | 本轮 multi-agent |
| 7 AutoCodeRover | AST retrieval | 本轮 SOP-based |
| 11 RepoCoder | line completion | 本轮 multi-agent |
| 12 Reflexion | self-evolution (single agent) | 本轮 structured SOP |
| 13 SWE-Lancer | choose best proposal | 本轮 PM-as-coordinator 类似 |
| 14 CodePlan | multi-file edit | 本轮 multi-role orchestration |
| 15 Beyond Code Gen | 5-gate PQC | 本轮 SOP-based PQC |
| **16 MetaGPT (本轮)** | **multi-agent SOP** | **本轮** |

**15 轮里本轮的 5 个新事**:
1. **第一个 multi-agent SOP framework 复现** — round 6-15 全是单 agent
2. **第一个 ablation 1/2/3/4 agent** — round 6-15 没人测" 多 agent vs 少 agent"
3. **第一个 executable feedback 对比** — round 12 Reflexion 单独, 本轮对照
4. **第一个测 "structured output 减少 revision cost"** — Table 1 0.83 vs 2.5
5. **第一个报" Pass@1 85.9% vs 67.0% (GPT-4)"** — round 6-15 没人用 GPT-4 baseline

---

## 6. 复现策略

### 6.1 不能 1:1 复现

**原 MetaGPT**:
- 164 HumanEval + 427 MBPP + 70 SoftwareDev task
- 5 个 role (PM, Arch, PM, Eng, QA), 各自一个 GPT-3.5/GPT-4 call
- 跑 assembly line: 5+ LLM call / task
- Project Manager 跟 Engineer 之间有 Message Pool + Subscribe

**本轮 mini 复现**:
- 6 mini HumanEval task (跟 round 12/15 类似)
- 4 setting: Baseline / 1-agent / 3-agent / 3-agent + feedback
- "SOP" 简化为**给每个 agent 一个 distinct system prompt + structured output 要求**
- "Message Pool" 简化为**前一个 agent 的 output 作为下一个 agent 的 input**

### 6.2 4 个 setting 设计

```
Setting 1: Baseline
  - 1 LLM call, prompt = "write this function"
  - 不分 role, 不分 step, 直接出 code

Setting 2: 1-agent (Engineer only)
  - 1 LLM call, system prompt = "You are a Python engineer, write code"
  - 跟 Setting 1 几乎一样, 只是 system prompt 不同

Setting 3: 3-agent (Product + Architect + Engineer)
  - Agent 1 (Product): prompt → PRD-style output (用 description + acceptance criteria)
  - Agent 2 (Architect): PRD → design (function signature + edge cases)
  - Agent 3 (Engineer): design → code
  - 3 LLM call, structured chain

Setting 4: 3-agent + Executable feedback
  - 跟 Setting 3 一样, 但 Engineer 写完后, 跑 test, 失败把 error 喂回去再写
  - 最多 3 retry
  - 3-9 LLM call
```

### 6.3 评测指标

- **Pass@1**: pass test 的比例
- **# LLM calls per task**: SOP 的 token cost
- **Token cost per task**: 实测的 token
- **Code structure score**: 0-2 (docstring + type hint + edge case handling)
- **Executable feedback gain**: Setting 3 vs 4 的差距
- **Role ablation gain**: Setting 1/2/3 的差距

---

## 7. 复现假设

| Setting | 估 Pass@1 | 估 LLM call | 估 token |
|---|---|---|---|
| Baseline (1 call) | 80-90% | 1 | 500 |
| 1-agent (Eng) | 80-90% | 1 | 500 |
| 3-agent SOP | 85-95% | 3 | 1500 |
| 3-agent + feedback | 90-100% | 3-9 | 2500 |

**期望**:
- 3-agent > 1-agent (SOP 真 work)
- 3-agent + feedback > 3-agent (feedback 加分)
- 但 token cost 3-agent + feedback 是 baseline 5x

---

## 8. takeaway 总结

| Insight | 论文数据 | 我的解读 |
|---|---|---|
| Pass@1 85.9% HumanEval | vs GPT-4 67% | SOP 真 work |
| Pass@1 87.7% MBPP | +5.4% from feedback | executable feedback 重要 |
| 3.75/4 executability on SoftwareDev | vs ChatDev 2.25 | assembly line 优于 chat |
| 4 role ablation: 1.0 → 4.0 | 增加 role 提升质量 | 但 cost 也涨 |
| 0.83 human revision cost | vs ChatDev 2.5 | structured output 省 review |
| Precompilation execution | MetaGPT 独有 | 跟 round 12 Reflexion 类似 |

---

## 9. 引用

- Hong et al. **MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework**. arXiv:2308.00352v7, ICLR 2024 — 本轮解读
- Qian et al. **ChatDev: Communicative Agents for Software Development**. 2023 — Round 16 baseline
- Chen et al. **AgentVerse: Fostering Multi-Agent Collaboration**. 2023 — Round 16 baseline
- Shinn et al. **Reflexion**. NeurIPS 2023 — Round 12, executable feedback 思路
- Wei et al. **Chain-of-Thought Prompting**. 2022 — round 16 ablation base
- Chen et al. **Evaluating Large Language Models Trained on Code**. 2021 — HumanEval

---

*本文由 Claude Code 完成于 2026-10-15, 是 15 轮 /loop 中**第一个复现 multi-agent SOP framework** 的论文。*
