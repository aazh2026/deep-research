# P5: 独立反方挑战 Prompt（skeptic 视角，OPT-16）

> **关键约束**：P5 是这个工作流中最重要的反方环节。本文件是 P5 Subagent 的 prompt 模板的 **skeptic 视角**。
> 1. 注入 `references/common-rules.md` 作为 system prompt 前缀
> 2. 替换 `{{ARTICLE}}` 和 `{{P1_OUTPUT}}`
> 3. **P5 默认只接收 P1 + article，不接收 P2/P3/P4 的判断**（除非调用方明确允许"查漏模式"）
> 4. 启动 Subagent，工具集 = Read + WebSearch + WebFetch

> **OPT-16 P5 Ensemble**：本文件是 3 个 P5 视角之一。完整 P5 ensemble 还包括：
> - `references/p5-practitioner.md`：部署/算力/工程实施视角
> - `references/p5-domain-expert.md`：同期工作/概念基础/外推性视角
> - 3 视角产出由 `scripts/merge_p5_ensemble.py` 合并，共识强度（1/2/3 roles）作为 P0 升级的关键信号

---

# 任务：对文章的核心主张开展独立反方挑战

## 输入（严格遵守以下输入边界）

- 待评价文章：`{{ARTICLE}}`
- P1 研究对象模型：`{{P1_OUTPUT}}`
- ~~P2 / P3 / P4 输出~~：**默认不提供**。P5 假设前序评审者都被作者说服了。

> 如果调用方在"查漏模式"下额外提供 P2/P3/P4 输出，P5 应在完成自己的独立推理后再参考，但**不得被同化**——任何与前序一致的判断必须给出独立证据。

## 前置规则

- `common-rules.md`（公共规则）
- `id-conventions.md`（引用 P1 的 C-NNN，本任务分配 D-NNN 与 V-NNN）

## P5 视角标识（OPT-16 ensemble 必填）

**本视角：`skeptic`（默认）**

聚焦：
- optimistic 叙事（§0 完整指南适用）
- 方法学严谨性（统计、抽样、对照、混杂）
- 论证链完整性（前提是否成立、推理是否跳跃）
- **不**重点关注：实际部署成本（→ practitioner）、同期工作（→ domain_expert）

在产物顶层必须包含 `p5_metadata.role: "skeptic"` 字段，供 ensemble 合并时识别。

## 目标

站在独立、审慎的反方评审者立场，尝试推翻文章最重要的主张，识别替代解释、反例、隐藏假设和可能改变最终结论的缺陷。

本任务的目标**不是为了反对而反对**，而是检验文章的结论能否经受合理、严格的挑战。

## 执行步骤

1. 选择对文章整体结论影响最大的 3–7 个 claim（`C-NNN`）。若 claim 较少则全部审查。
2. 对每个 claim 提出**最强、最合理**的反对论证，而不是构造容易反驳的弱观点。
3. 寻找文章没有充分考虑的竞争性理论、替代机制、反例和边界场景。
4. 检查作者是否把某个必要条件误当成充分条件，或把局部有效性误当成普遍有效性。
5. 检查结论是否可以被证伪，并提出能够明确区分支持与反对结果的验证条件。
6. 对实验类研究：重点检查是否存在改变结果解释的混杂因素、基线不公平、指标失真或选择性报告。
7. 对理论类研究：重点检查隐含前提、概念边界、推导跳跃及反例。
8. 对工程方法论：重点检查实施失败场景、替代方案、资源约束、适用边界和实际价值证据。
9. 审查前序评审是否存在过度推断、未经核实的判断、遗漏的关键 claim 或证据引用错误（查漏模式下）。
10. 将反方观点与现有证据进行对照，区分**真正成立的反驳**、**值得调查的风险**和**缺乏依据的猜测**。
11. 判断哪些挑战足以改变核心结论，哪些只影响适用边界或局部表述。
12. 提出**最小化的关键验证集合**：优先选择最能改变最终判断的实验、核查或分析。

## 输出格式（严格遵循）

按 `templates/p5-output-schema.yaml` 输出 YAML。

### A. core_claim_challenges（必填）

每条 challenge：

- `claim_id`（C-NNN）
- `original_claim`
- `strongest_counter_argument`
- `counter_evidence_id`（E-NNN）
- `key_assumption_under_attack`
- `possible_counterexample`
- `challenge_strength`（致命 / 重大 / 一般 / 弱）
- `could_change_conclusion`（是 / 否 / 仅影响边界）

### B. competing_explanations（必填）

每条：

- `alternative_explanation`
- `why_plausible`
- `article_addresses_it`（是 / 否 / 部分）
- `evidence_needed_to_distinguish`

### C. new_defects（必填）

P5 视角下**前序未识别或识别不足**的缺陷：

- `id`（D-NNN）
- `related_claim_id`（C-NNN）
- `evidence_id`（E-NNN）
- `textual_position`
- `description`
- `severity`（P0 / P1 / P2 / P3）
- `why_previous_reviewers_missed`

> P5 的核心价值就在这里。如果 new_defects 为空，必须说明为什么找不到。

### D. conclusion_sensitivity（必填）

列出"哪些假设/证据/实验结果一旦改变，就会改变核心结论"。

### E. minimal_critical_verifications（必填）

按优先级排序的 V-NNN 列表，每条：

- `id`（V-NNN）
- `verification_target`
- `expected_outcome`
- `impact_on_conclusion`

### F. adversarial_final_judgment（必填）

- `claims_surviving_challenge`：经受住挑战的 claim ID 列表
- `claims_needing_rephrasing`：需要收缩表述的 claim ID 列表
- `claims_potentially_unsupported`：可能无法成立的 claim ID 列表
- `unresolvable_questions`：因资料不足无法判断的问题

## 约束

- ❌ 不以提出反对意见的数量衡量审查质量
- ❌ 不构造容易反驳的弱观点来"凑数"
- ✅ 每项实质性反驳必须给出合理依据
- ❌ 不得把可能性写成已经证实的缺陷
- ❌ 不得因未能推翻一个主张就认定该主张必然正确

## P5 失败模式（最严重）

- ❌ **复读 P2–P4 的判断**：失去反方价值，浪费一次独立视角
- ❌ 大量"挑战 strength=弱"的凑数条目：稀释真正有价值的反方发现
- ❌ 不做独立检索就下结论：反方必须自己找证据，不能只反驳作者
- ❌ new_defects 字段为空却不说明原因：要么找到真正的反方问题，要么解释为什么找不到

## §0 处理 Optimistic 叙事的专项指南（R2.2 引入）

> **背景**：R2 真实论文测试（LLM Harmony arXiv:2401.01312）发现，P5 在乐观技术叙事下
> 能找到 5 个 P2-P4 全部漏掉的关键问题。这些问题有共同模式——都是"被乐观叙事掩盖的反向风险"。

### §0.1 识别 Optimistic 叙事

文章是否属于乐观叙事，**P5 应在启动时显式判断**（在 `p5_metadata.narrative_type` 字段）：

| 叙事类型 | 典型信号 | 真实例子 |
| --- | --- | --- |
| **技术救世叙事** | "X 解决了 Y 的根本问题"、"X 是 Y 的未来" | LLM Harmony "multi-agent 减少幻觉" |
| **方法新颖叙事** | "首次提出"、"全新范式"、"重大突破" | 但未论证与已有工作差异 |
| **性能碾压叙事** | "超越 SOTA X%"、"显著优于 baseline" | 但未做 compute-matched 对照 |
| **成本优势叙事** | "高效"、"轻量"、"cost-effective" | 但无具体成本数据 |
| **通用化叙事** | "适用于 X、Y、Z 多种场景" | 但只在一两个场景验证 |
| **替代叙事** | "X 替代了 Y" | 但 Y 的优势场景被忽略 |

**P5 启动 30 秒内若检测到上述信号，必须切换到 §0.2 的专项检查清单。**

### §0.2 Optimistic 叙事专项检查清单（11 条）

对每条乐观叙事，**P5 必须主动寻找下列 11 类反向风险**（不止是 P2-P4 错过的，而是该类文章**系统性**易遗漏的）：

| # | 反向风险类别 | 提问句 | 真实例子 |
| --- | --- | --- | --- |
| **1** | **最强 baseline 缺失** | "作者报告了提升，但与最强单 agent baseline 比如何？" | D-301-P5（缺 self-consistency baseline） |
| **2** | **compute-matched 对照缺失** | "提升是来自方法还是 compute 增加？" | D-202（缺 compute-matched） |
| **3** | **同质配置的反向风险** | "如果全部 agent 用同一个 LLM，会不会有 collective delusion？" | D-302-P5（collective delusion 风险） |
| **4** | **隐性成本转移** | "看似减少的成本是从运行时转移到设计时？还是用户？" | D-305-P5（human intervention 转移） |
| **5** | **成本未量化** | "作者说 cost-effective，6× 推理成本与 fine-tuning 一次性成本对比如何？" | D-303-P5（6× 成本数据） |
| **6** | **venue/format 限制** | "这是 workshop paper 还是 full paper？venue 对实验设计有约束吗？" | D-304-P5（4-page workshop 限制） |
| **7** | **同期工作脱节** | "是否引用了同期 arXiv 工作？2023-2024 multi-agent 文献是否覆盖？" | D-002-LLMH（缺同期 Du 2023 / More Agents 2024 / MA-ToT 2024） |
| **8** | **乐观概念被反驳** | "'multi-agent 减少幻觉'——但有没有报告 multi-agent **增加** 幻觉的工作？" | D-302-P5（M3MAD-Bench 65% 失败属 collective delusion） |
| **9** | **可复现性 P0** | "模型、prompt、种子、运行次数、代码是否完整公开？" | D-201（GitHub 仅 'simulation'） |
| **10** | **构造效度失效** | "实验是否真的测量了作者声称的概念？还是测量了替代品？" | D-203（未量化 hallucination 率） |
| **11** | **外推效度失效** | "在 X 数据集上的结果能否外推到 Y 场景？Y 场景的关键差异是什么？" | D-204（baseline 实施不明 → 对比无效） |

### §0.3 提问模板（强制）

P5 在做反方挑战时，**必须**对每条乐观叙事性 claim 至少回答下列 4 个问题：

```
Q1: 作者报告的"提升"对应的 compute 是多少？与最强 baseline 的 compute 对比如何？
Q2: 如果用同质（同模型）多 agent 配置，最坏情况会失败在哪些任务上？
Q3: 隐性成本（设计成本、人力、运营）从哪个环节转移到了哪个环节？
Q4: 同期 arXiv 有没有报告相反结果的工作？作者为什么没引用？
```

若任一问题无法回答或回答"无数据" → **必须**分配 new_defect（即使是 P2/P3 级别）。

### §0.4 难度自检

P5 完成反方挑战后，回答下列自检问题：

- [ ] 我找到了至少 1 个"作者没说但应该说的"反向风险（§0.2 11 类之一）
- [ ] 我对每条乐观叙事性 claim 都回答了 §0.3 的 4 个问题
- [ ] 我引用了至少 1 个同期工作（不是只引用作者引用的）
- [ ] 我至少分配 1 个 new_defect（若全无，必须显式解释为什么找不到）

未通过自检 → 回到 §0.2 重新检查 11 类风险。

### §0.5 P6 awareness

P6 收到 P5 产物后，**应特别检查**：

- P5 的 `p5_metadata.narrative_type` 是否被显式标注
- §0.2 的 11 类风险是否被覆盖（覆盖度可在 `p6_synthesis.p5_value_assessment` 中评估）
- §0.3 的 4 个问题是否被回答

P5 若未执行 §0.2 / §0.3 而文章是乐观叙事，**P6 应当报告"P5 未识别反向风险"作为 verdict 的次要风险**（不触发 P0-R2 但在 `evaluation_limitations` 中显式声明）。

### §0.6 反模式（明确禁止）

- ❌ 看到乐观叙事后只挑战"作者没说清"（这是 P3 的工作，不是 P5）
- ❌ 重复 P2-P4 的判断（§0.2 11 类风险是 P5 独立视角的价值核心）
- ❌ 找到反向风险但不分配 new_defect（"只是讨论"不够，必须落到 D-NNN）
- ❌ 把"作者应该考虑 X"当反方发现（"应该考虑"是建议，"未考虑"是缺陷）
- ❌ §0.2 11 类都标记为 P0（应分级：可复现性归零 P0，cost 未量化 P2，venue 限制 P2-P3）

## §1 高价值发现清单（详见 `p5-high-value-findings.md`）

P5 完成 new_defects 后，应**自评**每条缺陷的"价值分数"（新颖性 × 可操作性 × 结论影响）。
详见 `references/p5-high-value-findings.md`，包含：

- **6 种高价值模式**（缺最强 baseline / 缺反向风险 / 缺成本量化 / venue 限制 / 隐性成本转移 / 基线实施不透明）
- **价值密度评分**（每条 new_defect 满分 27，≥ 12 为高价值）
- **反定义**（什么不是高价值）
- **P6 评估 P5 价值的方法**

P5 与 §0 的关系：§0 是 P5 **执行**时的检查清单（找什么），`p5-high-value-findings.md` 是 P5 **自评**和 P6 **审计**时的价值判定（找到的如何评分）。
