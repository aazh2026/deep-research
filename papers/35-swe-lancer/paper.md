# SWE-Lancer 论文解读 (OpenAI, ICML 2025)

> 论文: **SWE-Lancer: Can Frontier LLMs Earn $1 Million from Real-World Freelance Software Engineering?**
> 作者: Samuel Miserendino, Michele Wang, Tejal Patwardhan, Johannes Heidecke (OpenAI)
> 链接: arXiv:2502.12115v4, 29 May 2025, ICML 2025 (PMLR 267)
> 解读日期: 2026-10-15
> 主题: **$1M 真实外包任务 benchmark, 把 LLM 编码能力映射成"赚多少钱"**

---

## 0. 为什么这一轮复现 SWE-Lancer?

13 轮 /loop 复现过的 paper (SWE-agent, AutoCodeRover, OpenHands, RepoCoder, Reflexion...) 都有一个共同点: **benchmark 来自 GitHub issue 或合成 task**。

**SWE-Lancer 是第一个把"真实人类支付"做 benchmark 的 paper**:
- 1,488 个 task 来自 **Expensify Upwork 公开仓库** (Expensify 把它 12 年真实外包任务全部公开放)
- 总价 **$1,000,000 USD** (按 Upwork 真实 freelancer 收到的金额)
- IC SWE (代码) + SWE Manager (选 best proposal) 双轨评测
- End-to-end Playwright test (不是 unit test)

**本轮复现目标**: 
- **SWE Manager 子集** — 让 LLM 从 3 个候选 proposal 里选 best (最容易, 不需要 Docker 跑 Playwright)
- 5-8 个 mini 任务, 测 "**LLM 选 best proposal 跟 paper 报 44.9% pass@1 一致吗?**"

---

## 1. 论文核心问题

### 1.1 SWE-bench / HumanEval 的局限

现有 benchmark 都是:
- 来自 GitHub issue (Jimenez 2024, Chowdhery 2024) — **只有 open-source repo, 缺商业**
- 用 unit test 评分 (Jimenez 2024) — **容易 grader hacking (见 paper Appendix A7)**
- 没有 "$ 价值" 概念 — **SWE-bench 全 pass 跟 SWE-bench 0% pass 对经济没意义**

**SWE-Lancer 的承诺**:
- 真实商业 codebase (Expensify)
- 真实 freelancer payout ($50 - $32,000/task)
- End-to-end Playwright test (避免 grader hacking)
- 直接报 "$ 多少"

### 1.2 1,488 个 task 的结构

| 类别 | 数量 | 总价 | 评估方式 |
|---|---|---|---|
| **IC SWE** (代码生成) | 764 | $414,775 | End-to-end Playwright test, all pass 才算 pass |
| **SWE Manager** (选 best proposal) | 724 | $585,225 | LLM 选出的 proposal 跟 ground-truth freelancer 一致才 pass |
| **Diamond** (高价值子集) | 5,508 USD / task 中位 | $500,800 | 全部 1,488 task 的 50% subset |
| **Full** | 全部 | $1,000,000 | 全部 |

**SWE Manager 比 IC SWE 更 "managerial"**:
- 给出 2-5 个 freelancer proposal
- LLM 浏览 codebase 后选 best
- 选对 = pass, 选错 = fail
- "**99% agreement** between LLM chosen and human manager" (paper §2)

### 1.3 模型 baseline 结果 (Figure 5, 6)

```
                       Full        Diamond
GPT-4o:               $303,525    16.5% IC / 38.7% SWE Mgr
o1:                   $380,350    20.2% IC / 41.3% SWE Mgr
Claude 3.5 Sonnet:    $403,325    26.2% IC / 44.9% SWE Mgr  ← best
```

**Claude 3.5 Sonnet 最强**, 拿到 **$400K / $1M** = 40% 货币化捕获率。

---

## 2. SWE Manager 任务的形式 (本轮复现对象)

### 2.1 Task 形式 (Figure 2)

```
[Input]
  1. 原始 issue (Upwork 上 1:1 拷过来, 包括价格 $X,XXX)
  2. codebase snapshot (pre-fix state, 但本轮不提供真实 repo)
  3. 2-5 个 freelancer proposal (历史真实记录)
     - Proposal 1: UserSmith — "Align comment handling with backend, including markdown parsing and CSS rendering"
     - Proposal 2: UserJohn — "Overcomplicated the scope... incomplete"
     - Proposal 3: UserPatel — "Please issue until markdown parsing PR..."
     - Proposal 4: UserSmith — "Correct bold styling..."
     - ...

[Output]
  选一个 proposal (a/b/c/d/...)

[Evaluation]
  选中的 proposal == human manager 当时选的 == ground truth
```

### 2.2 Task 难度来源

- 88% IC SWE 是 bug fix, 12% 是新 feature
- SWE Manager task 平均要 model 在 **4-5 个 proposal** 里选
- $32,000 task 比 $50 task 难 100x (longer PR, 多人提交, 多轮迭代)

---

## 3. 关键发现 (Section 3)

### 3.1 Pass@k 增长极陡 (Figure 7)

```
o1 on Diamond IC SWE:
  pass@1 = 16.5%
  pass@3 = 24.9%   +8.4 pp
  pass@5 = 35.9%   +11.0 pp
  pass@7 = 48.5%   +12.6 pp
```

**6 次额外尝试让 pass rate 接近 3 倍** — 跟 round 12 Reflexion 一致, "**LLM 多 sample 收益极大**"。

### 3.2 Test-time compute 提升 (Figure 8)

```
o1 IC SWE Diamond pass@1:
  Low reasoning effort:    9.3%
  Medium reasoning effort: 13.1%
  High reasoning effort:   16.5%   (+7.2 pp)
  
对应 earn rate: $16K → $29K
```

**"think more" 在 harder 任务 ($1K+) 收益更大** — $32K+ 任务从 7.7% → 15.4% (+7.7 pp)。

### 3.3 User tool 的边际效果 (Figure 9)

```
GPT-4o:  8.0% (no tool) → 8.0% (with tool)   0 pp
o1:     13.1% (no tool) → 16.5% (with tool) +3.4 pp
```

**Playwright user tool 对 o1 有 +3.4 pp, 对 GPT-4o 是 0** — 强 reasoning model 才能"用工具"。

### 3.4 Manager 任务比 IC 任务简单 (Figure 6)

```
IC SWE Diamond:    GPT-4o 8.0%,  o1 16.5%,  Claude 26.2%
SWE Manager Full:  GPT-4o 37.6%, o1 41.3%,  Claude 44.9%
```

**SWE Manager pass rate ~2x IC SWE** — 因为 "**4 选 1**" 比 "**从 0 写代码**" 容易。

---

## 4. paper 的 4 个关键 insight (我读完后)

### 4.1 "$1M 是 1,488 个 task 总和, 不是单一 model 能拿全"

- Claude 3.5 Sonnet 拿 **$403K / $1M** = 40%
- 60% task 没人能解 (即使 frontier)
- **"$1M" 是 marketing**, 真实捕获率 ~40%

### 4.2 "Manager 任务比 IC 任务简单" 反直觉

直觉说 "选 best" 难, 因为要" 懂所有 proposal 才能选对"。但 paper 报 **44.9% (Manager) > 26.2% (IC)**。

**原因**: 4 选 1 随机就是 25%, manager 任务 44.9% 说明 model **比随机好 20 pp** — 不是 "容易", 是 "**比 IC 任务的 0.1% 起步好很多**"。

### 4.3 "Reasoning model 一定要开 user tool"

- GPT-4o 不用 tool / 用 tool: 0 pp 差
- o1 不用 tool / 用 tool: **+3.4 pp**
- **强 reasoning model 知道 "什么时候调 Playwright", 弱 model 调了也不看**

### 4.4 "$500K 的 task 比 $50 task 难 100x, 但 frontier 不会 100x 好"

- $32K+ task: Claude 3.5 Sonnet 估计 5-10% pass
- $50-500 task: Claude 估计 40-50% pass
- **frontier model 跟新手 freelancer 在高价值 task 上差距缩小** — 因为这些 task 需要 domain knowledge (e.g. Expensify 内部 API)

---

## 5. paper 的局限性 (paper 自己说)

1. **单 codebase** — 只有 Expensify, 推广到其他 codebase 未必
2. **历史任务** — Expensify 在 2024 年 freeze, 没有 2025+ 新任务
3. **Playwright grader hacking** — 一些 task 是用 Playwright 模拟用户, 可以被 game (paper Appendix A7 警告)
4. **Manager 任务有 99% agreement 但 1% 灰色 case** — paper 没深入分析

---

## 6. 跟 12 轮 /loop 的关系

| 轮 | 复现对象 | Benchmark 来源 | 评测方式 |
|---|---|---|---|
| 6 | SWE-agent | GitHub issue | unit test |
| 7 | AutoCodeRover | GitHub issue | unit test |
| 8 | OmniCode | GitHub issue | unit test |
| 9 | AIDev | 工业 PR | descriptive |
| 10 | OpenHands | 自构 mini task | unit test |
| 11 | RepoCoder | RepoEval 公开 | unit test |
| 12 | Self-Evolving + Reflexion | 合成 mini HumanEval | unit test |
| **13** | **SWE-Lancer (本轮)** | **真实 Upwork $1M** | **Playwright / LLM 选 best** |

**13 轮里 3 件新事**:
1. **第一个 $ 计价 benchmark** (前面 12 轮都是 "pass rate" 抽象数字)
2. **第一个 Manager-style 任务** (前面都是 "代码生成", 这里是 "选 best")
3. **第一次 report "earn rate"** (frontier model 拿 $403K / $1M)

---

## 7. 本轮复现策略

### 7.1 不能 1:1 复现

**原 paper 复现** = 跑 1,488 个 task, 用 Claude 3.5 Sonnet 跟 o1, 总 cost 数万美元 + Docker 启动。

**本轮 mini 复现**:
- 5-8 个 **synthetic SWE Manager 任务**
- 任务设计: 简单 Python bug, 给 3 个 proposal (一个正确, 2 个错)
- 测 "**LLM 选 best 跟 paper 报 44.9% 一致吗?**"
- 用 M3.1 (我们自己的 LLM), 不是 Claude 3.5 Sonnet

### 7.2 复现假设

- 如果 "4 选 1 随机 25%" → M3.1 拿 50% = 跟 Claude 3.5 Sonnet 的 44.9% 接近
- 如果 "M3.1 拿 80%" → 比 Claude 3.5 Sonnet 强 (这是 "弱 LLM + 简单 task" 的 headroom)
- 如果 "M3.1 拿 25%" → 等于随机, paper 数据要谨慎相信

### 7.3 任务示例

```
[Task: "Add input validation to calc.divide()"]
Issue: divide(5, 0) 返回 None, 但应该 raise ZeroDivisionError
Payout: $500

[Proposal A: UserSmith] 
  "Add raise ZeroDivisionError('b == 0') at function start"
  ✓ Correct
  
[Proposal B: UserJohn]
  "Wrap in try/except, return 'error' string on ZeroDivisionError"
  ✗ Silently swallows error
  
[Proposal C: UserPatel]
  "Change return type to Optional[float], return None on b==0"
  ✗ Loses type safety
```

LLM 选 A = pass, 选 B/C = fail。

---

## 8. takeaway 总结

| Insight | 论文数据 | 我的解读 |
|---|---|---|
| Claude 3.5 Sonnet 拿 $400K / $1M | 40% 货币化捕获率 | frontier model 远没"$1M" 那么神 |
| Manager 44.9% > IC 26.2% | 4 选 1 比 0 写简单 | benchmark 难度阶梯比想象陡 |
| pass@7 = 48.5% ≈ 3x pass@1 | 6 次额外尝试 | LLM multi-sample 收益极陡 |
| Reasoning + user tool = +3.4 pp | o1 8% → 16.5% | 强 model 才能"用 tool" |
| 60% task 无解 | $1M 是 marketing | frontier ceiling 远低 |

---

## 9. 引用

- Miserendino et al. **SWE-Lancer: Can Frontier LLMs Earn $1 Million from Real-World Freelance Software Engineering?**. ICML 2025 (arXiv:2502.12115v4) — 本轮解读
- Jimenez et al. **SWE-bench: Can Language Models Resolve Real-World GitHub Issues?**. ICLR 2024 — 同领域前置
- Shinn et al. **Reflexion**. NeurIPS 2023 — Round 12, multi-attempt 的范式鼻祖
- OpenAI. **o1 System Card**. 2024 — 强 reasoning model 的代表
- Anthropic. **Claude 3.5 Sonnet Model Card**. 2024 — paper best model

---

*本文由 Claude Code 完成于 2026-10-15, 是 13 轮 /loop 中**第一个 $ 计价 + 真实外包 task 的 paper 复现**。*
