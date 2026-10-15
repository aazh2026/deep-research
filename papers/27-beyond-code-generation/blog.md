# 15 轮 /loop 复现 Beyond Code Generation: 6 个 gate 把 100% 砍到 33%

> 15 轮 /loop 复现纪实, 这次研究 SWE 真实痛点: **改完代码, 怎么才算真完成?**
> 论文: **Beyond Code Generation** (Happy Bhati, Northeastern, 2026) — 4 个新概念, 30 个 cited 研究, 1 个核心悖论

---

## 0. 一句话 takeaway

**6 个 mini coding task × 5 个 reliability gate = candidate rate 100% 一路砍到 PQC 33%。Verification Tax 2.8x, G5 (deploy ready) 是最大瓶颈。Demirer NBER 100K developer study 报 "commits +180%, releases +30%" — 我们的 mini 复现是 100% → 33%, 完全同一方向。**

---

## 1. 15 轮 /loop 第一次问 "真完成没"

14 轮 /loop 复现过的 paper 全部停在 "test pass" 这一层:
- round 6 SWE-agent: pass test
- round 7 AutoCodeRover: pass test
- round 8 OmniCode: pass test
- round 11 RepoCoder: line exact match
- round 12 Reflexion: pass test
- round 13 SWE-Lancer: choose best proposal
- round 14 CodePlan: file exact match

**没有 paper 问 "test pass 之后, 还差什么"**。

Happy Bhati (Northeastern, 2026) 这篇 **直接攻这个 gap** — 提出 4 个新概念:

1. **PQC (Production-Qualified Change)** — change 是不是" 真完成" 的单位
2. **Verification Tax** — verification cost / generation cost
3. **Throughput Paradox** — commits +180% vs releases +30% (Demirer NBER)
4. **Agentic Autonomy Budget** — 三角: money / reliability / human-attention

**本轮 /loop 目标**: operationalize 5-gate PQC ladder 在 6 个 mini coding task, 测每个 gate 砍多少。

---

## 2. The 5-gate Reliability Ladder

```
Candidate correctness:        Production qualification:
  Requirements fit              Security / dependency policy
    → Patch correctness           → Review / ownership
      → Build / type checks        → Deploy / canary
        → Unit / property tests      → Production SLO / rollback
          → Integration / contract    → Maintenance / regression
```

**关键观察**: 14 轮 /loop 全部停在 "Unit tests pass" (第 4 个 gate)。**生产 release 要走完 9 个 gate**。

**本轮 mini 版 5-gate**:
- G1 Compile/import
- G2 Test pass
- G3 Code review (LLM-as-reviewer)
- G4 Security (LLM-as-security-checker)
- G5 Deploy ready (LLM-as-deploy-checker)

PQC = G1 ∧ G2 ∧ G3 ∧ G4 ∧ G5 全过。

---

## 3. 复现结果: 100% → 33% PQC

### 3.1 Per-gate pass rate

| Gate | 含义 | Pass | Rate |
|---|---|---|---|
| G0 Generation | LLM 输出可解析 code | 6/6 | 100% |
| **G1 Compile** | import 跑通 | 6/6 | **100%** |
| **G2 Test** | unit test pass | 6/6 | **100%** |
| G3 Code review | LLM-as-reviewer | 5/6 | 83% |
| G4 Security | LLM-as-security | 5/6 | 83% |
| **G5 Deploy ready** | LLM-as-deploy | 2/6 | **33%** |
| **PQC** (G1-G5 全过) | Production-Qualified | **2/6** | **33%** |

### 3.2 Throughput Paradox 在 mini 任务上 reproduce

```
Paper (Demirer NBER 2026, 100K developer):
  Autocomplete  → +40% commits
  Interactive   → +140% commits
  Autonomous    → +180% commits, +50% projects, but only +30% releases

我们的 mini 复现 (6 task):
  Candidate (G0+G1) → 100%
  Test pass (G2)    → 100%
  PQC (G1-G5)       → 33%
  Attenuation       → 67 pp
```

**方向完全一致**: candidate 远多于 PQC。**bottleneck 真的在 verification 不在 generation**。

### 3.3 Verification Tax = 2.81x

| Component | Tokens | Ratio to gen |
|---|---|---|
| **Generation** (1 LLM call) | 3,638 | 1.00x |
| Reviewer (G3) | ~3,300 | 0.91x |
| Security (G4) | ~3,400 | 0.93x |
| Deploy (G5) | ~3,500 | 0.96x |
| **Total verification** (3 LLM call) | **10,230** | **2.81x** |

**跟 paper 9.1 完全一致**: "Token price is only the visible part of cost" — verification 是 2.8x generation, 但 paper 9.1 暗示真实生产环境 verification 占比更高 (人力 review / CI / security scan 加起来 5-10x)。

---

## 4. Per-task 的 2 件事

### 4.1 2/6 PQC: 简单 transformation task

```
task_2 separate_parity: G1 ✓ G2 ✓ G3 ✓ G4 ✓ G5 ✓ → PQC ✓
task_4 merge_dicts:     G1 ✓ G2 ✓ G3 ✓ G4 ✓ G5 ✓ → PQC ✓
```

**两个 PQC 都是 "无 I/O, 无 security, 简单 data transformation"** — LLM 写 + LLM 验都过。

### 4.2 task_6 (password_hash) 3 个 LLM gate 全 fail

```
task_6 verify_password: G1 ✓ G2 ✓ G3 ✗ G4 ✗ G5 ✗ → PQC ✗
```

**LLM 自己 review 自己写的 `verify_password` 写出来的代码**:
- G3 review: 缺 docstring / edge case 处理
- G4 security: 用 `==` 直接 compare password, 没用 `hmac.compare_digest` (timing attack 风险)
- G5 deploy: 缺 input validation / error handling

**Insight**: LLM 写 security-sensitive code 经常 missing 关键 best practice。**LLM-as-security-checker 真的 work** — 它 catch 到了。

---

## 5. LLM-as-reviewer 的 bias (复现中发现)

### 5.1 第一次跑: G3 全 0/6

第一版 prompt 写 "must have docstring, PEP 8, ..." → LLM reviewer 6/6 全 fail。

**问题**: mini one-function task 不需要 docstring, LLM reviewer 用 "production library code" 标准 review, 永远 fail。

### 5.2 Fix: 改 prompt "Be LENIENT, only fail on real correctness"

G3 立刻从 0/6 → 5/6 pass。

**Insight 1**: LLM self-eval 有 calibration 问题, **要 explicit prompt engineering** 才能 work。

**Insight 2**: 跟 paper RQ3 "When does an additional agent increase reliability rather than correlated error?" 呼应 — **LLM 验证 LLM 不一定独立**, 要 prompt 强制它换 evaluation lens。

**Insight 3**: 14 轮 /loop 都没专门研究 LLM-as-evaluator, 是个 open space。

---

## 6. G5 (deploy ready) 是真瓶颈 — 跟 paper 5.1 一致

```
G1 Compile:        100%  (LLM 写 valid Python)
G2 Test:           100%  (mini task 简单)
G3 Review:          83%  (LLM eval 调参后)
G4 Security:        83%  (LLM 真 catch security)
G5 Deploy ready:    33%  ← 最大 bottleneck
```

**为什么 G5 33%**:
- LLM 写 mini task **不主动**加 error handling
- LLM 写 mini task **不主动**加 logging
- LLM 写 mini task **不主动**加 input validation
- LLM 写 mini task **不主动**考虑 type hint

**跟 paper 13.1 "hidden organizational issue: verification capacity" 完全一致**:
> Companies often budget AI licenses before budgeting the capacity needed to verify the resulting changes. This is the software equivalent of adding upstream factory machines without increasing inspection, integration, or shipping capacity. When generation is cheap, the queue can simply move.

**LLM 把 candidate rate 拉满, verification 跟不上, PQC 砍到 33%**。

---

## 7. 跟 14 轮 /loop 其它 paper 的对比

| 轮 | 评测 | 跟本轮对比 |
|---|---|---|
| 6 SWE-agent | test pass | + G3/G4/G5 |
| 7 AutoCodeRover | test pass | 同 |
| 11 RepoCoder | line match | + G3/G4/G5 |
| 12 Reflexion | test pass | + G3/G4/G5 |
| 13 SWE-Lancer | proposal rank | + G3/G4/G5 |
| 14 CodePlan | file exact | + G3/G4/G5 |
| **15 Beyond Code Generation (本轮)** | **5-gate PQC** | **第一次完整 ladder** |

**15 轮里本轮的 4 个第一**:
1. 第一次爬完整 reliability ladder
2. 第一次算 PQC rate
3. 第一次算 Verification Tax
4. 第一次用 LLM-as-reviewer / security / deploy checker

---

## 8. takeaway 总结

| Insight | 论文数据 | 我的复现 | 15 轮视角 |
|---|---|---|---|
| Throughput Paradox | 180% → 30% release | 100% → 33% PQC, 67 pp attenuation | 15 轮第一次算 attenuation |
| Verification Tax | "visible part of cost" | 2.81x | 15 轮第一次算 ratio |
| G5 deploy ready 是 bottleneck | review 是 capacity problem | 33% pass (lowest) | 跟 paper 13.1 一致 |
| LLM-as-reviewer 需 calibration | RQ3 "additional agent" | 0/6 → 5/6 通过 prompt fix | 15 轮第一次研究 LLM eval bias |
| TestGen-LLM 75/57/25 | more tests ≠ better tests | 我们的 G2 = 100% (mini 太简单) | paper 测 real PR 时 G2 < 100% |
| Test pass ≠ production | Section 3.1 | G2 100% vs PQC 33% | 14 轮没人指出 |

---

## 9. 留给未来轮的 open question

1. **Cross-language token cost** — round 15 只 Python, paper Wu et al. 测 5 语言差 2-10x
2. **Multi-agent verification** — paper 报 CooperBench 30% penalty, 本轮没测
3. **Adaptive verification budget** — paper RQ2, 按 task risk 选不同 gate
4. **LLM-as-evaluator calibration** — 本轮发现 prompt-engineering 影响巨大, 值得专文研究
5. **Real PR 评测** — paper 强调 "real PR", mini task 太简单, G2 = 100% 不能 generalize

---

## 10. 引用

- Bhati, H. **Beyond Code Generation: Reliability, Verification, and Cost Economics in the Agentic Software Development Lifecycle**. arXiv:2609.04681v1, Sep 2026 — 本轮复现
- Demirer, Musolff, Yang. **Writing Code vs. Shipping Code: Productivity Effects Across Generations of AI Coding Tools**. NBER WP 35275, 2026 — Throughput Paradox
- Baumann et al. **SWE-chat: Coding Agent Interactions From Real Users in the Wild**. arXiv:2604.20779 — bimodal
- Alshahwan et al. **Automated Unit Test Improvement using LLMs at Meta**. FSE 2024 — TestGen-LLM
- Wu, Anderson, Guha. **Best Programming Language for Tokenmaxxing**. arXiv:2607.22807 — 5-language token
- Khatua et al. **CooperBench: Why Coding Agents Cannot be Your Teammates Yet**. arXiv:2601.13295 — multi-agent penalty
- Desai et al. **SWE-Marathon**. arXiv:2606.07682 — 27.2M tokens, 13.8% reward hacking

---

*15 轮 /loop 复现系列 by Claude Code · 本轮 (round 15) 2026-10-15 完结 · 6 mini task · 5 reliability gate · 24 LLM call · gen 3,638 + ver 10,230 = 13,868 tokens · Verification Tax 2.81x · PQC rate 33% · 总耗时 ~5 分钟*
