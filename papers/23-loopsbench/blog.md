# 当 Coding Agent 进入「长程时代」：LoopsBench 给出的冷启动数据

> 写于 2026-10-14，配合 `papers/23-loopsbench/paper.md` 与 `REPRODUCTION_NOTES.md` 阅读。
> 一篇 paper 同时讲清楚 LoopsBench 做了什么、能复现什么、以及**为什么 25% 才是真实的 2026 年 Coding Agent 上限**。

---

## 引子：你以为的 SWE-Bench 不再代表 Coding Agent

2024 年起，几乎所有 Coding Agent 评测都在围着 SWE-Bench 转。
但 SWE-Bench 实际上是个**单步问题**：

> 给你一个 issue，你输出一个 patch，patch 让单测全过就算赢。

它不关心：
- Agent 提交 patch 前**试了几次**
- 中间是否**保留前序工作**
- 如果 agent 自己修过头，**回头是不是真的把历史也破坏了**

而 2026 年的 Coding Agent 早就不止做 patch 了——它们在**持续地改一个仓库**：
- Codex goal mode 跑 24 小时不关机
- Claude Code dynamic workflows 自己 fork 多个 worker
- Karpathy 的 AutoResearch 写「**我的工作就是写 loop**」

这种**长程循环**机制不是 SWE-Bench 能测的。

**LoopsBench** 是第一个正面回应这件事的公开基准。
它来自 Microsoft + 南京大学 + UCL + SJTU（Han Li, Zhemin Fang 等），2026 年 8 月放 arXiv。

---

## LoopsBench 的设计哲学

### 三个关键判断

1. **评测对象从 patch 升级到 loop**：不是「这次 patch 对不对」，而是「这个循环机制能不能持续推进」。
2. **用 DAG 而非 issue**：每个任务是一个**有向无环图**，节点是原子开发单元（PR / commit / Lab step / 论文迭代），边是 4 种被 admit 的依赖关系（sequential PR chains、structural module reuse、functional producer/consumer API edges、compositional layering）。
3. **流感知运行时**：测试**不是一把全跑**——只在前沿（ready frontier）节点上验证，且已完成的节点**保留为永久回归义务**。这意味着 agent 不能「修了 A 破坏 B」。

### 论文的核心数字

> **Opus-4.7 + Claude Code + outer continuation = 25.00% Resolve Rate**

这意味着，2026 年 8 月最强的 agent 组合，在 112 个长程任务里**有 75% 干不完**。

这跟 SWE-Bench 上动辄 60–80% 的数字形成强烈对比——不是 agent 退步了，而是 LoopsBench 暴露了一个完全不同的能力维度。

### Loop Trace Metrics：过程可见性

论文另一个贡献是提出**3 类 loop trace 指标**：
- **Planning Fidelity**：replay 的计划与原始 DAG 的 Edge F1、Layer ρ
- **Implementation**：PatchLen、Jaccard 相似度
- **Testing**：TPR（Test Pass Rate）、F2P（Fail to Pass）、**Reg↓（Regression）**

特别值得注意的是 **Regression Rate**：所有评测配置里，agent 都会引入 regression（破坏先前通过的测试）。
论文 RQ3 的实测：**Claude Code dynamic workflows 跑 97.96 个 context-budget round**，但 Resolve Rate 只有 17.65%——单纯加 round 数不是解药。

---

## 我做的复现验证（结果不漂亮，但很真实）

我没跑 agent——那需要 Docker + LLM API + 200+ 小时，**机器条件不允许**。
我只做了**数据集层级的结构性 sanity check**。

### 实测 vs 论文声称

| 论文声称 | 实测 | 评价 |
|---|---|---|
| 112 tasks | 112 tasks | ✅ 一致 |
| 5,300+ development units | 201,017（按 unit_count 求和） | ❌ **38 倍差异** |
| 9 domains | 12 categories | ❌ 数量不符 |
| 8 languages | 12 categories 含细分 | ❌ 数量不符 |
| 29 PR + 57 Lab + 26 Research source split | 数据集无 source 字段 | ❌ 不可直接复现 |
| DAG 结构（dependency graph） | 存在（每个 task 有 module_node/edge/layer 字段） | ✅ 一致 |
| median dependency depth 6 | median layers=4, nodes=11 | ⚠️ 量级相近，口径不同 |

### 这意味着什么？

1. **HF 数据集已演化**：论文与最新 HF 版本不同步——5,300+ 可能是 v1 采样，HF v2 把它扩成 201k module-level units。
2. **9 domains 口径模糊**：实测 12 类，论文没列具体名字。跑 Agent 前需要**重做 mapping**。
3. **source split 在元数据中不显式**：必须读 GitHub task 目录或 tags 才能区分 29/57/26。

### 我的诚实结论

> **HF 数据集可加载、112 任务真实存在、DAG 抽象成立，但论文里 5,300+ / 9 domains / 29+57+26 这些数字不能照搬。** 这是研究复现里非常常见的「论文 v.s. artifact 不同步」问题。下游若用 LoopsBench 做实验，需要**以 HF 列为基准重新算**。

---

## 对 2026 Coding Agent 研究的实际意义

### 1. Harness 已经到顶

SWE-Bench 类基准的提升空间被 harness 吃掉。模型升级的边际收益趋平。
**真正能拉开差距的是 loop 工程**——触发、停机、状态持久、回归义务、验证子 agent。

### 2. 25% 不是 agent 弱，是评测变了

这跟 SWE-Bench 上 70–80% 不矛盾——那是**不同能力**。
「**修一个 issue**」和「**持续修一个 repo 的多个 issue 且不破坏旧工作**」是两种工程。

### 3. Regression 才是 loop 的硬骨头

所有配置都引入 regression，**没有任何 agent 真正实现「持续绿」**。
这是 loop 工程必须正面解决的——不是多轮对话，而是「**已工作的不能崩**」。

### 4. Loop trace 指标是新维度

Edge F1、Reg↓、Rounds 这些**过程指标**比 Resolve Rate 更有信息量。
研究者应同时报告：
- **结果**：Resolve Rate、TPR、F2P
- **过程**：Rounds、Edge F1、Regression Rate、PatchLen
- **结构**：frontier 演化、discard 率

---

## 如果你今天要搭一个 LoopsBench 评测

1. **先看 Docker build**：Course Labs 主要是 C/C++，构建链重。
2. **回归测试是核心**：不要只看最终 pass，要画 Reg↓ 曲线。
3. **把 frontier 当一阶对象**：观测 ready frontier 大小、regression 次数、discard 数。
4. **不要用单测覆盖率作为唯一信号**：LoopsBench 提供 TPR/F2P/Reg 三件套。
5. **以 HF 数据集为基准重新计算**：5,300+、9 domains、29/57/26 这些论文数字不能直接用。

---

## 我给 LoopsBench 的 3 个改进建议

1. **论文与 HF 数据集版本对齐**：在 dataset README 中显式标记 unit_count 含义 + source 标签。
2. **9 domains 的具体名字**：把 category→domain 的映射写在论文里，12 个 category 怎么 fold 成 9 个。
3. **公开一份 reference agent 实现**：哪怕是「无脑调用 Claude Code 每次 frontier 都重测」也能给社区一个 baseline 数字。

---

## 结语

LoopsBench 的真正贡献不是又**一个** coding agent benchmark，而是**承认了一件事**：

> **Coding Agent 已经进入长程时代，而我们还在用 SWE-Bench 量它。**

如果你 2026 年还在用单测 pass 率评估 agent 的工程能力，你评估的是 harness，不是 loop。

而 loop 才是真正的产品差异点。

---

## 参考

- 论文：Han Li et al. *LoopsBench: From Harness Engineering to Loop Engineering in Coding Agent Evaluation*. arXiv:2608.00267, 2026.
- 论文 PDF：`papers/23-loopsbench/2608.00267.pdf`
- 数据集：`LoopsBench/LoopsBench` on HuggingFace
- 代码：`github.com/microsoft/Loopsbench`
- 项目页：`loopsbench.ai`

> 本博客基于结构性复现（不跑 Agent），HF 数据集已加载但与论文数字不完全对齐，详见 `REPRODUCTION_NOTES.md`。
