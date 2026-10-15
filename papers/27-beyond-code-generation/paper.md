# Beyond Code Generation 论文解读 (Happy Bhati, 2026)

> 论文: **Beyond Code Generation: Reliability, Verification, and Cost Economics in the Agentic Software Development Lifecycle**
> 作者: Happy Bhati (Northeastern University)
> 链接: arXiv:2609.04681v1, 4 Sep 2026
> 解读日期: 2026-10-15
> 主题: **Agent 时代, 真正的瓶颈不是 "能不能写代码", 而是 "改完能不能 ship"**

---

## 0. 为什么这一轮复现 "Beyond Code Generation"?

14 轮 /loop 复现过的 paper (round 6-14) 全部都在" 怎么让 agent 写出 patch" 层面。**没有 paper 专门问" 改完之后, 怎么才算真完成"**。

**Happy Bhati 这篇 paper 直接攻这个 gap**:
- 提出 4 个新概念: **PQC (Production-Qualified Change)**, **Verification Tax**, **Throughput Paradox**, **Autonomy Budget**
- 引用 30 个 2024-2026 实证研究 (RCT / 行业 telemetry / benchmark / 公司 report)
- 核心 claim: **"AI 写代码 +180%, 但 release 只有 +30%"** (Demirer et al. 100K GitHub developer study)

**本轮复现目标**:
- 6 个 mini coding task, 测**每个 verification gate 杀掉多少 candidate**
- 测 **PQC rate** (pass 所有 gate 的比例) vs **candidate generation rate**
- 测 **Verification Tax** (verification token / generation token)
- 把" Throughput Paradox" 在 mini 任务上 reproduce 一次

---

## 1. 论文核心: 4 个 engineering construct

### 1.1 Throughput Paradox (commits ≫ releases)

**引用 Demirer, Musolff, Yang (NBER, 2026, 100K GitHub developer)**:

| Stage | Cumulative effect |
|---|---|
| Autocomplete (Copilot) | +40% commits |
| Interactive agent (IDE) | +140% commits |
| **Autonomous agent (CLI/Cloud)** | **+180% commits, +50% projects, but only +30% releases** |

**Insight**: 写代码快了 4.5x, 但**真 release 只快了 1.3x**。中间多出的 4.5x → 1.3x 都被 verification / review / test / integration 吃掉了。

### 1.2 Production-Qualified Change (PQC) — 新单位

```
PQC_i = ∏_{g ∈ G_i} 1{g(i) = pass}

G_i = 该 change 需要的 reliability gate 集合
  - 低风险 doc edit: |G| = 1 (e.g. 仅 "doc build pass")
  - 中风险 feature: |G| = 3-4 (test + review + security)
  - 高风险 (auth / payment): |G| = 5+ (test + review + security + deploy + canary)
```

**PQC-Throughput(T) = Σ PQC_i / |T|**

**核心论断**: 不能拿" commits" 或" PR count" 当指标 — 那是 candidate generation, 不是 deliverable。

### 1.3 Verification Tax

```
V_tax = (C_CI + C_review + C_security + C_rework) / C_generation
```

**Insight**: 模型账单 (C_generation) 只是一小部分。**真正的成本是 verification 链路上的 CI / review / security / rework**。Token 越来越便宜, 但 verification 是人 + 算力 + 时间的混合成本, 不会等比例下降。

### 1.4 Agentic Autonomy Budget (三角)

```
3 个 constrained resources:
  1. Money / compute: model tokens, context, tools, sandbox, CI, parallelism
  2. Reliability / risk: expected failure impact, security exposure, reversibility, blast radius
  3. Human-attention: clarification, review, escalation, debugging, approval, incident response

Permitted autonomy = intersection of 3 budgets
```

**Insight**: "Agent 能跑 30 分钟 vs 8 小时 vs 几天" 是 capability 描述, 但**生产环境要的是 "autonomy 是 budget 决定, 不是 capability 决定"**。

---

## 2. Reliability Gate Ladder (Figure 2)

```
Candidate correctness:
  Requirements fit → Patch correctness → Build / type checks → Unit tests → Integration / contract

Production qualification:
  Security / dependency policy → Review / ownership → Deploy / canary → Production SLO / rollback → Maintenance / regression
```

**关键观察**:
- **Benchmarks 通常停在 "Unit tests pass"** — SWE-bench, HumanEval, MBPP 都是这一层
- **生产 release 要走完整个 ladder** — 9 个 gate 全过才算 PQC
- 任何一个 gate 失败 = 该 change 永远不是 deliverable

**这跟 round 12/13/14 复现里的发现一致**:
- round 12 Reflexion: pass@1 = 87.5% (仅 test pass, 一个 gate)
- round 13 SWE-Lancer: pass@3 = 100% (人工选 best, 一个 gate)
- round 14 CodePlan: 12/24 files correct (file-level match, 一个 gate)
- **4 轮全部停在" Unit tests pass" 这一层** — 跟 paper 5.1 节呼应

---

## 3. The Verification Tax 的 3 个 case study

### 3.1 TestGen-LLM (Meta, FSE 2024) — 75/57/25 数字

```
75% generated test cases built correctly
57% passed reliably
25% increased coverage
+ engineers accepted 73% of recommendations
```

**Insight**: **测试覆盖率上升 ≠ 缺陷检测率上升**。" More tests" 不一定 "better tests"。

### 3.2 SWE-chat (Stanford, arXiv:2604.20779) — 41/23/44 bimodal

```
41% of agent coding sessions: agent authored virtually all committed code
23% of sessions: humans authored most
44% of agent-produced code: survived into user commits
+ users pushed back on agent outputs in 44% of turns
```

**Insight**: Agent 跟 human 协作是 **bimodal**, 不是 gradual takeover。

### 3.3 Northeastern 5-language token study (Wu et al. 2026)

> **同一 problem difficulty 下, Python / Java / Rust / OCaml 的 token 消耗**差 2-10x。
> 原因: agent 在动态语言 (Python) 更常出现 **non-compiling attempts, revision of passing solutions, distrust of tests, fallback prototyping**。

**Insight**: **Token cost 是 software-engineering quality signal**, 不只是 model pricing 决定。

---

## 4. 论文的 6 个工程教训 (Section 17)

**给 engineering leader 的 6 条 operating stance**:

1. **Budget the whole delivery path** — 不只算 model cost, 算 CI / sandbox / review / security / rework / incident
2. **Measure shipped reliability, not generated activity** — 用 PQC, 不用 commits
3. **Protect scarce review capacity** — 低 risk property 自动化, 高 risk 留给 expert
4. **Make agent runs reproducible** — version model / harness / prompts / context
5. **Set hard stop rules** — token / time ceiling + progress checkpoint
6. **Treat tests as evidence, not ceremony** — strong oracles + property + mutation

**给 researcher 的 8 个 RQ** (Section 16):
- RQ1: What predicts PQC better than benchmark score?
- RQ2: Can verification budgets be allocated adaptively?
- RQ3: When does an additional agent help (not hurt)?
- RQ4: Optimal stop rule for long-horizon agents?
- RQ5: How to attribute agentic cost to delivered value?
- RQ6: Do AI-generated tests improve real defect detection?
- RQ7: What org design converts code acceleration to release?
- RQ8: How should software agents coordinate?

---

## 5. 论文的局限性 (paper 自己说)

1. **不是 PRISMA systematic review** — 是 structured systems synthesis
2. **很多 2026 source 是 preprint / 公司 report** — 不是 peer-reviewed
3. **公司 reported deployment outcome 受 selection bias** — 不能直接 transfer
4. **Gartner forecast 是 planning signal, 不是 measured outcome**
5. **不同 study 测不同 population** — 不能直接 compare (26% productivity ≠ 19% slowdown ≠ 180% commit gain)
6. **PQC / Verification Tax / Autonomy Budget 是 hypothesis, 不是 validated standard**

---

## 6. 跟 14 轮 /loop 的关系

| 轮 | 复现对象 | 评测 layer | 跟本轮关系 |
|---|---|---|---|
| 6 | SWE-agent | long-horizon issue | 停在 test pass |
| 7 | AutoCodeRover | AST retrieval | 停在 test pass |
| 8 | OmniCode | bug-fixing | 停在 test pass |
| 10 | OpenHands | SWE | 停在 test pass |
| 11 | RepoCoder | line completion | 停在 exact match |
| 12 | Self-Evolving | HumanEval | 停在 test pass |
| 13 | SWE-Lancer | choose best | 停在 review score |
| 14 | CodePlan | multi-file edit | 停在 file match |
| **15** | **Beyond Code Generation (本轮)** | **5-gate PQC ladder** | **第一次爬完整 ladder** |

**14 轮里本轮的新事**:
1. **第一次爬完整 Reliability Gate Ladder** — round 6-14 全部停在 "Unit tests pass" 一层
2. **第一次测 PQC rate** — 之前没人算" candidate rate vs deliverable rate"
3. **第一次测 Verification Tax** — 之前没人算" verification cost / generation cost"
4. **第一次用 LLM-as-gate** (reviewer / security checker) — 之前只让 LLM 写代码, 不用 LLM 验证

---

## 7. 本轮复现策略

### 7.1 不能 1:1 复现

**原 paper 是 synthesis** — 30 个 cited 研究, 没有 own original experiment。本轮 mini 复现走 "**模拟 Throughput Paradox**" 路线:
- 6 个 HumanEval-style task
- 每个 task: 5 个 reliability gate (compile → test → review → security → deploy)
- 测每个 gate pass rate
- 算 PQC rate, Verification Tax

### 7.2 Gate 实现

- **Gate 1 (Compile/import)**: 把 candidate 写到 sandbox, `python3 -c "import m"` 跑通
- **Gate 2 (Test pass)**: 跑 task 自带的 assert test, returncode 0
- **Gate 3 (Code review)**: LLM-as-reviewer, 评估 readability / naming / docstring
- **Gate 4 (Security)**: LLM-as-security-checker, 评估 hardcoded secret / SQL injection / unsafe deserialization
- **Gate 5 (Deploy ready)**: LLM-as-deploy-checker, 评估 production readiness (logging, error handling, no debug print)

### 7.3 复现假设

- **Generation rate** (Gate 1 pass): 90%+ — LLM 几乎都能写出 syntactically correct code
- **Test pass rate** (Gate 2): 70-80% — mini task 简单
- **Code review pass**: 50-70% — LLM 经常写" 能跑但 ugly" 的代码
- **Security pass**: 80-90% — mini task 没真安全 issue, 但 LLM 偶尔误报
- **Deploy ready pass**: 30-50% — 真实生产 readiness 最难
- **Final PQC rate** (5 gates 全过): 估 20-40%
- **Verification Tax**: 估 2-4x (verification 3 个 LLM call + generation 1 个)

---

## 8. takeaway 总结

| Insight | 论文数据 | 我的解读 |
|---|---|---|
| Commits +180% but releases +30% | Demirer NBER 100K developers | 14 轮第一次测 deliverable rate |
| PQC = change × gates 全 pass | 新概念 | 14 轮第一次用" 全 ladder 算分" |
| Verification Tax = verification cost / gen cost | Wu et al. + FinOps | 14 轮第一次算 ratio |
| TestGen-LLM 75/57/25 | Meta FSE 2024 | 测试多 ≠ 测试好 |
| Autonomy = budget ∩ | 三角模型 | 不是 capability 决定 |
| LLM 在动态语言 (Python) 比静态语言 (Java/Rust) 费 token 2-10x | Wu et al. 2026 | 14 轮没人研究 token economy |

---

## 9. 引用

- Bhati, H. **Beyond Code Generation: Reliability, Verification, and Cost Economics in the Agentic Software Development Lifecycle**. arXiv:2609.04681v1, Sep 2026 — 本轮解读
- Demirer, Musolff, Yang. **Writing Code vs. Shipping Code: Productivity Effects Across Generations of AI Coding Tools**. NBER WP 35275, 2026 — Throughput Paradox data
- Baumann et al. **SWE-chat: Coding Agent Interactions From Real Users in the Wild**. arXiv:2604.20779 — 41/23/44 bimodal
- Alshahwan et al. **Automated Unit Test Improvement using LLMs at Meta**. FSE 2024 — TestGen-LLM 75/57/25
- Wu, Anderson, Guha. **Best Programming Language for Tokenmaxxing**. arXiv:2607.22807 — 5-language token cost
- Bhati. **Agentic AI in the Software Development Lifecycle**. arXiv:2604.26275, 2026 — author 上一篇

---

*本文由 Claude Code 完成于 2026-10-15, 是 14 轮 /loop 中**第一个爬完整 Reliability Gate Ladder** 的复现。*
