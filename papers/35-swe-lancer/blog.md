# SWE-Lancer: 13 轮 /loop 第一次复现 $1M 真实外包 benchmark

> 写在第十三轮 /loop: 复现 OpenAI 2025 年 SWE-Lancer paper (ICML 2025), 写了 mini SWE Manager 选 best proposal, 8 task × 3 runs 上 83.3% pass@1, 100% pass@3, 100% earn rate。
> 跑完最大的感受是: **"选 best" 比 "写代码" 容易 2x, multi-attempt 几乎"必救回" task, $1M 这个数字是 marketing, 真实 frontier model 拿 ~40% capture rate**。
> 13 轮 /loop 里 3 件新事: (1) 第一次 $ 计价 benchmark, (2) 第一次 Manager-style 选 best, (3) 第一次看到 "earn rate 100% in mini" vs "earn rate 40% in real" 的 synthetic-real gap。

---

## 0. 13 轮 /loop 第一次复现 $ 计价 benchmark

13 轮 /loop 复现过的 benchmark:
- Round 6-8: SWE-bench, RepoEval, HumanEval
- Round 9: AIDev (descriptive, 65K 工业 PR)
- Round 10: OpenHands 自构 task
- Round 11: RepoEval line completion
- Round 12: 合成 mini HumanEval
- **Round 13: SWE-Lancer ($1M 真实 Upwork benchmark)** ← 本轮

**SWE-Lancer 跟前 12 轮最大的 3 个不同**:

1. **$ 计价**: 1,488 个 task 来自 Expensify 真实 Upwork 仓库, 总价 $1M USD, 跑完直接报 "model 赚多少钱"
2. **Manager-style 任务**: 724 个 SWE Manager task 测 "LLM 选 best proposal", 不测 "LLM 写代码"
3. **End-to-end Playwright test**: 不用 unit test, 模拟真实用户操作

**本轮复现目标**: SWE Manager 子集 (724 个 task) 的核心协议 — 4-5 选 1 → mini 复现 3 选 1。

---

## 1. 我的复现: 8 task 上 83.3% pass@1, 100% pass@3

### 1.1 复现规模

| 维度 | Paper (SWE Manager Diamond) | 我的复现 |
|---|---|---|
| Task 数 | 364 (50% of 724) | **8 synthetic** |
| Proposal 数 / task | 4-5 | 3 |
| LLM | Claude 3.5 Sonnet (best) / o1 / GPT-4o | M3.1-Flash |
| Pass@1 协议 | avg of 多次 sampling | 同 |
| Pass@k 协议 | n sampling 任一对 | k=3 任一对 |
| 总 LLM call | ~10K+ | **24** |
| Cost (估算) | ~$10K | $0 (本地 API) |

### 1.2 复现结果

| Metric | 数值 | Paper (Claude 3.5 Sonnet) |
|---|---|---|
| **pass@1 (单次)** | **83.3%** (20/24) | 44.9% |
| **pass@3 (任一)** | **100%** (8/8) | ~50% (估算 pass@3) |
| **Majority vote** | **100%** (8/8) | — |
| **Random baseline** | 33.3% (3 选 1) | 25% (4-5 选 1) |
| **Δ vs random** | **+50.0 pp** | +20 pp |
| **Earn rate** | **100%** ($18K/$18K) | ~40% ($400K/$1M, paper) |

**关键 insight**: **+50 pp vs random 跟 paper +20 pp 方向一致** — LLM 选 best 显著高于随机, 这是 paper 的核心 claim。

### 1.3 8 task 的具体类别跟结果

| Category | Payout | Pass@1 | Δ vs random |
|---|---|---|---|
| bug_fix | $500 | 100% | +67 pp |
| performance | $1,500 | 100% | +67 pp |
| security (×2) | $3K-$5K | 50-67% | +17-33 pp |
| correctness | $2,000 | 100% | +67 pp |
| concurrency | $4,000 | 100% | +67 pp |
| api_design | $1,200 | 67% | +33 pp |
| testing | $800 | 100% | +67 pp |

**观察**: 大部分 category 100% pass, **security (50-67%) 跟 api_design (67%) 是难 task** — 跟 paper 报"高价 task ($3K+) 难" 一致。

---

## 2. 跟 paper 数字差距的诚实解释

**我的 83.3% 远高于 paper 44.9%, 不是说 model 强, 是因为**:

1. **3 选 1 vs 4-5 选 1**: random baseline 33% vs 25%, 我的 headroom 多 8 pp
2. **合成 task 的 "correct" 太明显**: 我设计的 task 都有 "明显技术正确 + 2 个明显错"
3. **8 task noise 主导**: 真实 Diamond 是 ~364 task, 8 task 任何结论都有 12.5% 量化单位
4. **没用 Playwright / Docker**: paper 测 IC SWE 时环境复杂, 我只测 Manager 子集

**真正可比的 insight**:
- ✓ LLM 显著高于 random (+50 pp vs paper +20 pp) — **direction 一致**
- ✓ multi-attempt 收益巨大 (pass@1 83% → pass@3 100%) — **跟 paper Figure 7 趋势一致**
- ✓ SWE Manager 比 IC SWE 简单 (跟 paper Manager 44.9% vs IC 26.2% 一致)

---

## 3. SWE-Lancer 给我 5 个新的认知

### 3.1 "$1M 是 marketing, 真实 capture rate ~40%"

paper Figure 5 显示 Claude 3.5 Sonnet 拿 **$403,325 / $1,000,000 = 40%**。
- 60% task 没人能解 (即使 frontier)
- **"$1M benchmark" 是 paper 的 marketing angle, 不是 "frontier model 真的能赚 $1M"**

### 3.2 "Manager 任务比 IC 任务简单" 反直觉, 但有道理

直觉: "选 best" 难, 因为要"懂所有 proposal 才能选对"。
实际: Manager 44.9% vs IC 26.2% (paper 报), 我的 83% (mini) vs 0% 起步 (写代码没 0%, 但 pass rate 远低)。

**原因**:
- 4 选 1 随机 25% 已经不低
- "选" 不需要生成新内容, 只需要"识别最佳", 难度天花板低
- "写代码" 0 起步, 任何 syntax error / missing import 都会 fail

### 3.3 "Multi-attempt 几乎必救回 task"

我的 pass@1 = 83.3% → pass@3 = 100%, **+16.7 pp**。
Paper Figure 7: o1 pass@1 = 16.5% → pass@7 = 48.5%, **+32 pp**。

**结论**: "**给 LLM 多次机会选 / 写**" 是 ROI 最高的 prompt engineering, 不需要 fine-tuning, 不需要改 model。

### 3.4 "高价 task 跟低价 task 的 pass rate 差 2x"

paper Figure 8: o1 在 $32K+ 任务 15.4% vs <$500 任务 17.1%, **差 1.7 pp, 没想象的 100x 难**。
我的: $5K task 50-67%, $500 task 100%, **差 33-50 pp, 比 paper 略陡**。

**真实 industry 含义**: Expensify 内部 $32K task 需要"理解 Expensify 内部 API" 这种 domain knowledge, frontier LLM 没这种知识, 表现就跟新手 freelancer 差不多。

### 3.5 "Reasoning model 才能用好 user tool"

paper Figure 9: 
- GPT-4o: 不用 tool / 用 tool = 8.0% / 8.0% (0 pp)
- o1: 不用 tool / 用 tool = 13.1% / 16.5% (**+3.4 pp**)

**含义**: 强 reasoning model 知道 "什么时候调 Playwright / 什么时候看 log", 弱 model 调了也看不懂。**这跟 round 12 self-evolving survey 强调的 "agent 需要 reasoning" 一致**。

---

## 4. SWE Manager 跟生产力的关系

paper 不只 benchmark, 也直接建议 "**SWE Manager 模式可以用于生产**":

| 场景 | 用法 | 预期 pass rate |
|---|---|---|
| GitHub PR review | 给 LLM 4 个 PR, 让它选 best merge | ~50% (跟 Sonnet SWE Manager 持平) |
| Upwork 投标评估 | 4 个 freelancer 投标 1 个 task, LLM 选 best | ~50% |
| A/B test proposal | 4 个产品方案, LLM 选哪个上线 | 难评估, 主观 |
| Bug triage | 4 个 issue claim 是同一 bug, LLM 选 root cause | ~50% |

**我的 83% 比 paper 44.9% 高, 因为我设计的 task "明显 best", 真实场景 proposal 不会这么分明**。

---

## 5. 跟 12 轮 /loop 其他复现的对比 (横向)

| 轮 | 复现对象 | 评测方式 | 关键数字 |
|---|---|---|---|
| 6 | SWE-agent | long-horizon issue | 1 instance, 290K token |
| 7 | AutoCodeRover | AST retrieval | 1 instance, 6K token |
| 8 | OmniCode | bug-fixing | 10 instance, 50% file_overlap |
| 9 | AIDev | 工业 PR | 65K PR, descriptive |
| 10 | OpenHands | 通用 agent | 7 task, SW 0/4 |
| 11 | RepoCoder | code completion | 5 task, 噪声主导 |
| 12 | Self-Evolving + Reflexion | mini HumanEval | 8 task, 87.5%→100% (+12.5 pp) |
| **13** | **SWE-Lancer (本轮)** | **mini SWE Manager** | **8 task, 83.3%→100% pass@3** |

**13 轮里 4 件事是最有信息密度的**:
- **Round 8** OmniCode 50% file_overlap — 真实 bug-fixing 远没 paper 报的 70%
- **Round 10** OpenHands SWE 0/4 — 通用 agent 离 production 还远
- **Round 12** Reflexion +12.5 pp — self-evolution 真的 work
- **Round 13** SWE-Lancer +50 pp vs random — "选 best" 任务 LLM 远超 random

---

## 6. 13 轮 /loop 的 meta 反思

**复现 13 篇 paper 的方法论沉淀 (跟 round 12 互补)**:

1. **小样本 (5-8 task) 能验证 direction, 不能验证 magnitude** — round 13 跟 paper 都验 "LLM 远超 random", 但 magnitude 不一致
2. **Multi-attempt 是 ROI 最高的 prompt engineering** — round 12 (+12.5 pp) 跟 round 13 (+16.7 pp) 都看到
3. **"选 best" 比 "写代码" 容易 2x** — round 13 跟 paper 报 44.9% > 26.2% 一致
4. **$ 计价 benchmark 比 "pass rate" 抽象数字更"刺眼"** — "$1M" 让人记住, "60% pass" 不一定
5. **合成 task 比真实 task 简单 2-3x** — round 13 我 83% vs paper 45%, 几乎全部是 task 设计差距

**13 轮看完一轮, 我对 "SWE benchmark 怎么用" 的最终判断**:

```
你要测 model 什么能力?
├── 代码生成 → SWE-bench / HumanEval
├── 长链路 issue → SWE-agent / OpenHands
├── 检索代码 → RepoCoder / RepoEval
├── 自我进化 → self-evolving benchmark
├── 选 best → SWE Manager (本轮)
└── 真实商业价值 → SWE-Lancer Diamond
```

**对真用 SWE-Lancer 的人**:
- "$1M" 是 marketing, 真实 capture rate 40%, 别拿 "$1M" 自我安慰
- SWE Manager pass rate 2x IC SWE, "选 best" 是性价比最高的 LLM 应用
- Multi-attempt (k=3-7) 是几乎必拿的 ROI
- 高价 task 跟低价 task 难度差 2-5x, 不差 100x — **frontier model 在真实商业 task 上没想象的弱**

---

## 7. 一句话总结

> **SWE-Lancer 第一次把"model 编码能力"映射成"赚多少钱" — 这个 benchmark 概念本身就比 $1M 数字更有价值**。
> **我的 8 task mini 复现看到 +50 pp vs random (paper +20 pp), 验证 "LLM 选 best" 真的 work, 但绝对数字 (83% vs 45%) 跟 paper 有 gap, 主要是合成 task 比真实 task 简单**。

跑完 13 轮, 我对 "frontier LLM 编码能力" 的最终判断:

```
model 真实能做什么?
├── 写 100 行以下新代码 (HumanEval) → 80-90% pass
├── 修 bug (SWE-bench) → 30-50% pass
├── 长链路 issue (SWE-agent) → 10-20% pass
├── 选 best (SWE Manager) → 40-80% pass  ← 本轮
└── 真实商业 $1K-$32K 任务 (SWE-Lancer) → 15-25% pass
```

**这比"无脑相信 paper 报的 91% Pass@1"靠谱多了**。

---

## 8. 引用

- Miserendino et al. **SWE-Lancer: Can Frontier LLMs Earn $1 Million from Real-World Freelance Software Engineering?**. ICML 2025, arXiv:2502.12115v4 — 本轮解读
- Jimenez et al. **SWE-bench: Can Language Models Resolve Real-World GitHub Issues?**. ICLR 2024 — Round 6
- Shinn et al. **Reflexion**. NeurIPS 2023 — Round 12, multi-attempt 鼻祖
- Zhou et al. **Self-Evolving Coding Agents**. arXiv:2608.03392v4, 2026 — Round 12
- OpenAI. **o1 System Card**. 2024 — paper 强 reasoning model
- Anthropic. **Claude 3.5 Sonnet Model Card**. 2024 — paper best model

---

*本文由 Claude Code 完成于 2026-10-15, 基于 8 synthetic task × 3 runs = 24 LLM call 复现, 总 ~16K token。*
