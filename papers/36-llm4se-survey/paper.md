# LLM4SE 综述解读：LLM 在软件工程中的全景

> Paper: Angela Fan, Beliz Gokkaya, Mark Harman, Mitya Lyubarskiy, Shubho Sengupta, Shin Yoo, Jie M. Zhang. **"Large Language Models for Software Engineering: Survey and Open Problems"**
> arXiv:2310.03533v4 [cs.SE] (Submitted 5 Oct 2023, v4 11 Nov 2023)
> 7 作者, 跨 Meta (Generative AI / PyTorch / FAIR / Developer Infra) + KAIST + King's College London
> 解读日期: 2026-10-16
> 论文类型: 短文 / 立场文章 (3 页), 实质为 13-section 分类法 + open problems

---

## 一句话定位

> 2023 年 10 月, 由 7 位跨 Meta / KAIST / KCL 作者联合发布的 LLM4SE 短综述, 提出了 **13-section LLM4SE 分类法** (从需求到教育) 与 **"Automated Regression Oracle"** 概念 (用既有软件行为作为 oracle), 论证了 **"hybrid techniques (传统 SE + LLM)"** 是部署 LLM-based SE 的关键路径。

论文虽然只有 3 页, 但在结构上承载了 12 个章节的内容骨架 (II-XII), 是 2023 年 LLM4SE 领域的一份高密度位置定义。

---

## 1. 论文要解决的 3 个根本问题

### 1.1 LLM-based SE 作为新子学科的边界

论文把 LLM4SE 定位为 SE 的 **新子学科** (而非临时趋势), 因此需要一个 **统一分类法** 来让 200+ 后续 LLM 论文可以自我归位。

### 1.2 LLM 的 emergent properties 是双刃剑

- **正面**: novelty + creativity → 跨任务 (编码、设计、需求、修复、重构、性能、文档、分析) 通用
- **负面**: hallucination → 错误的工程产物可能看着像对的 (尤其会引入 bug)

### 1.3 Oracle Problem 在 LLM 时代的特殊性

- **传统 SE**: Oracle Problem 是老大难 (怎么判断输出对不对)
- **LLM 时代**: 多数 SE 任务有 **automatable ground truth** (代码可执行), 这是 LLM 时代 SE 比其他 LLM 应用幸运的根本原因
- **关键创新**: 提出 **Automated Regression Oracle** —— 用既有系统行为做 oracle (适合重构、性能优化等不改变语义的场景)

---

## 2. 论文核心贡献 (5 项)

### 2.1 Table I: arXiv 增长趋势的实证

| Year | |A| (all CS) | |L| (w/ LLM) | |L ∩ S| (LLM4SE) | %L/A | %L∩S/L |
|------|----|----|----|---|---|
| 2019 | 55,325 | 36 | 0 | 0.00 | 0.00 |
| 2020 | 71,431 | 99 | 5 | 0.00 | 5.05 |
| 2021 | 77,520 | 192 | 13 | 0.25 | 6.77 |
| 2022 | 81,964 | 434 | 45 | 0.53 | 10.36 |
| **2023** (Jul only) | 52,547 | 1,665 | 181 | 3.17 | 10.87 |

**Key finding**: LLM 论文中 **10.87%** 是 LLM4SE 论文 (2023), 还在快速增长。**注意**: 数据只到 2023-07-27, 2024-2026 的曲线留给我们去测。

### 2.2 13-section 分类法 (图 1 隐含, 章节明示)

按软件开发活动 + 研究领域双重维度划分:
- **III**: Requirement Engineering & Design
- **IV**: Code Generation & Completion (含 Prompt Eng. for Code / Hybrid / Scientific Eval / Code Gen Models)
- **V**: Software Testing (含 New Tests / Adequacy / Minimisation / Output Prediction / Flakiness)
- **VI**: Maintenance, Evolution, Deployment (含 Debugging & Repair / Performance / Clone Detection / Refactoring)
- **VII**: Documentation Generation
- **VIII**: Software Analytics and Repository Mining
- **IX**: Human-Computer Interaction
- **X**: Software Engineering Process
- **XI**: Software Engineering Education
- **XII**: Crosscutting Open Research Topics

这是论文最重要的可验证成果 —— **后续 LLM4SE 论文可按这个分类法自检**。

### 2.3 Automated Regression Oracle 概念

```
传统 Oracle Problem: 怎么判断程序对不对?
Automated Regression Oracle: 用既有系统行为做基准
                             (仅适合不改变语义的场景: 重构、性能优化)
```

这一概念后续被 Genetic Improvement / Refactoring / LLM4Test 等子领域引用。

### 2.4 SBSE ↔ LLM4SE 的方法论桥梁

论文用整段论证 **Search-Based Software Engineering (SBSE)** 和 **LLM4SE** 在评估方法论上的同构性:
- 都面临 noisy / non-deterministic / incomplete 结果
- 都依赖 robust statistical inference
- SBSE 二十年的经验可直接迁移到 LLM4SE

这是论文的第二个重要概念贡献 —— **不是"LLM 取代传统 SE", 而是"LLM 借用传统 SE 的方法论脚手架"**。

### 2.5 13 个具体 Open Problems

每一节末尾都列出 Open Problems, 涵盖:
- Code generation: oracle, fine-tuning cost
- Testing: 4.8% Claude 2 / 1.7% GPT-4 on coding, prompt engineering, mutation testing
- Maintenance: APR, performance, clone detection, refactoring
- Crosscutting: hallucination, nondeterminism, evaluation science, explainability

---

## 3. 论文的论证薄弱处 (诚实指出)

### 3.1 数据时效性问题

Table I 数据截至 2023-07-27, 2024-2026 的趋势未覆盖。论文作者也承认 *"numbers for 2023 are underestimated"*。

### 3.2 关键数字的"3 页论文"局限

论文援引的关键数字很多 (4.8% Claude 2、1.7% GPT-4、46% Copilot、62% Java Copilot、72% / 160% repair improvement、21% Defects4J-Nl2fix Top-1) 都是引用他人工作, **论文本身没有做新实验**, 因此其结论的"实证"力度取决于二手引用质量。

### 3.3 "Survey" 的范围坦白

论文第 1 节明确: *"any survey of such a rapidly expanding area can neither aspire nor claim to be comprehensive"*。因此 **本文应被视为"早期 LLM4SE 地图", 而非"穷尽式综述"**。

### 3.4 缺乏可复现的 benchmark

论文没有像 SWE-bench / HumanEval 那样提供自己的 benchmark 任务, 后续社区需要为每节 (V/VI/VII 等) 单独建立 benchmark, 这也是为何后续 2024-2025 出现了 SWE-bench Verified、SWE-bench Pro、HumanEval+、LiveCodeBench 等多个领域 benchmark。

---

## 4. 在 deep-research 项目的位置

本仓库现有 28 篇论文 (03-42 编号), 其中 SWE / coding agent / SE 类别约 16 篇, 大致可对应本综述的分类法:

| 论文 (仓库) | 综述对应 section |
|---|---|
| 22-wikiskill | IV (Code Generation) |
| 23-loopsbench | IV (Code Generation Models / Eval) |
| 24-loop-engineering-blocks | IV (Code Generation Models) |
| 25-self-evolving-coding-agents | IV + X (Process) |
| 26-agentswe | IV (Training Data) |
| 27-beyond-code-generation | X (Process) + IV |
| 29-swe-bench-pro | IV (Eval) |
| 30-omnicode | IV (Code Gen) |
| 31-ai-coding-agents-pull-requests | VIII (Repo Mining) |
| 32-agentic-coding-in-the-wild | IV + VIII (Real-world) |
| 33-swe-agent | IV + VI (Repair) |
| 34-swe-bench | IV (Eval) |
| 35-swe-lancer | IV (Eval) |
| 37-autocoderover | VI (Repair) |
| 38-openhands | IV + X (Process) |
| 39-codeplan | IV (Code Gen, multi-file) |
| 40-chatdev | X (Process, multi-agent) |
| 41-metagpt | X (Process, multi-agent) |
| 42-repocoder | IV (Code Gen) |

**观察**: 16/19 = 84% 集中在 **IV (Code Gen) + X (Process)** 两个 section, **V (Testing) / VII (Doc) / IX (HCI) / XI (Education)** 在本仓库几乎空白。这与论文预判一致: 2023-2026 LLM4SE 实际发展失衡, **测试与教育是被低估的子领域**。

---

## 5. 论文未提到但本仓库覆盖的盲点

1. **Long-horizon task**: 论文没预见到 SWE-bench Pro 这种 731×100+ 行 patch 的 enterprise 任务复杂度
2. **Contamination**: 论文强调 Oracle Problem, 但未提 SWE-bench Pro §1 指出的 **License-based contamination** 风险
3. **Agentic multi-step**: 论文谈 "ReAct" 模式, 但未涉及 SWE-agent / OpenHands 这种 **多步 agent 循环** 的轨迹分析
4. **Real-world telemetry**: 论文没有 32-agentic-coding-in-the-wild 这种 27 模型 × 45 工具 × 626K calls/pair 的真实工业 telemetry

---

## 6. 给后续 round 的提示

如果再做一次 LLM4SE 综述 (基于 2024-2026 数据), 应该:
1. 用 arXiv API 实测 2024-2026 的 %L∩S/L 曲线 (论文只到 2023-07)
2. 把第 V (Testing) / VII (Doc) / IX (HCI) / XI (Education) 单独拎出来各做一个 deep-dive
3. 加 1 节: **Multi-Agent SE Process** (本仓库 38/40/41 都属于此)
4. 加 1 节: **Long-Horizon + Contamination-Resistant Eval** (29 / 35 属于此)

---

## 参考文献 (论文内引用了 200+ 篇, 这里只列对本解读关键的)

- Table I 数据源: Cornell-University/arxiv (Kaggle, accessed 2023-07-27)
- CodeX: Chen et al. 2021 (OpenAI Codex)
- AlphaCode: Li et al. 2022 (DeepMind)
- CODAMOSA: Lemieux et al. 2023 (SBST + LLM hybrid)
- ChatRepair: Xia et al. 2023 ($0.42/bug)
- AlphaRepair: Xia et al. 2023 (Cloze-style APR)
- Libro: Kang et al. 2023 (Bug report → test)
- ReAct: Yao et al. 2022 (交互式推理框架)
- Genetic Improvement: Harman et al. (Oracle 思想源头)
- 完整 200+ 引用见 arXiv 原文

---

*本解读为 deep-research 项目 round 34 产物, 配合 REPRODUCTION_NOTES.md 与 blog.md 阅读。*
