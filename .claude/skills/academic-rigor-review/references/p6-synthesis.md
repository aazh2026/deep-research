# P6: 综合评审与学术严谨性评分 Prompt

> 本文件是 P6 Subagent 的 prompt 模板。P6 是**整个工作流中唯一看全局的决策节点**。
> 1. 注入 `references/common-rules.md` 作为 system prompt 前缀
> 2. 替换所有 `{{...}}` 变量
> 3. 启动 Subagent，工具集 = Read

---

# 任务：综合评价文章的学术严谨性

## 输入

- 待评价文章：`{{ARTICLE}}`
- P1 研究对象模型：`{{P1_OUTPUT}}`
- P2 理论与文献核查报告：`{{P2_OUTPUT}}`
- P3 主张证据台账：`{{P3_OUTPUT}}`
- P4 方法学审查报告：`{{P4_OUTPUT}}`
- P5 反方挑战报告：`{{P5_OUTPUT}}`
- 评价标准版本：`{{EVALUATION_PROTOCOL_VERSION}}`
- **Orchestrator 预检的 P0 缺陷清单**：`{{PRECHECK_P0_DEFECTS}}`（由 orchestrator 在 P5 完成后扫描 P2–P5 产物生成，见 SKILL.md Step 3.5）

## 前置规则

- `common-rules.md`（公共规则）
- `id-conventions.md`（八个 DIM 维度的标准定义）

## 目标

综合已有审查证据，评价文章的学术严谨性，形成**可复核**的评分、关键缺陷、核心主张可信程度及改进建议。

> **本任务不应该重新凭印象评价全文**，而是综合前面各项任务的可追溯产物，形成有证据支撑的最终判断。

## 执行步骤

### 1. 检查评审材料完整性

- 检查输入产物是否完整、相互一致、证据是否可追溯
- 识别不同任务之间的矛盾
- 对缺少原始依据、无法核实或存在明显错误的评审结论进行降级处理
- 不得将上游 Subagent 的判断自动视为事实

### 1.5 P0 缺陷硬规则（违反任一条则 P6 视为失败）

P6 必须严格遵守以下五条硬规则。这些规则**任何其他维度分数都不能抵消**。

#### 规则 P0-R1：P0 缺陷必须显式处理

`{{PRECHECK_P0_DEFECTS}}` 中列出的每条 P0 缺陷，必须在 `final_verdict.p0_veto_triggered` 中体现为 `true`，并在 `critical_defects` 中完整列出。

如果 P6 不知道 `{{PRECHECK_P0_DEFECTS}}`（该字段缺失或为空），但其他上游产物中存在 `severity=P0` 的 D-NNN，视为 orchestrator 错误，**P6 应当拒绝综合并报告"上游 P0 缺陷未预检"**。

#### 规则 P0-R2：verdict 强制降级

若 `{{PRECHECK_P0_DEFECTS}}` 非空（≥1 条 P0）：

- `final_verdict.verdict` **只能是** `core_falsified_by_critical_defects` 或 `insufficient_evidence`
- 即便其他七个维度都打 5 分，verdict 也**不允许**为 `core_fully_supported`
- 即便作者提供了补救方案，verdict **也必须在 P0 关闭后才能升级**

#### 规则 P0-R3：P0 影响范围必须可追溯

每条 P0 缺陷在 `critical_defects` 中必须给出：

- `affected_claims`：列出该 P0 缺陷影响的所有 C-NNN
- `impact_scope`：说明这些 claim 失效后哪些下游结论需要重新评估
- `fix_requirement`：修复所需的最低验收标准（不是"修改措辞"，必须能改变 C-NNN 的 status）

#### 规则 P0-R4：P0 修复优先级为 must

`improvement_task_list` 中每条 P0 缺陷的修复任务必须 `priority=must`，且必须在 `evaluation_limitations` 中显式声明："本次 verdict 受到 P0 缺陷影响，需在 P0 全部关闭后重跑 P6"。

#### 规则 P0-R5：维度评分与 verdict 分离

DIM 评分反映**当前可见证据下**各维度的严谨程度；`final_verdict` 反映**文章能否被接受**。两者独立：

- DIM 平均 4.0 + 存在 P0 → verdict 仍必须是 5 或 6
- DIM 平均 2.5 但无 P0 → verdict 可能是 3 或 4（取决于 P1 缺陷）

P6 不得用 DIM 高分"冲销"P0 的影响，也不得用 verdict 严苛"惩罚"其他维度。

### 2. 评价八个维度

分别评价：

1. `DIM-01` 理论基础
2. `DIM-02` 文献与相关工作
3. `DIM-03` 论证与推理
4. `DIM-04` 研究方法
5. `DIM-05` 证据与数据
6. `DIM-06` 有效性与偏差控制
7. `DIM-07` 可复现性与可证伪性
8. `DIM-08` 结论边界与研究贡献

每个维度使用 1–5 分：

- `1` 严重不足
- `2` 较弱
- `3` 基本成立
- `4` 严谨
- `5` 高度严谨

**评分必须遵循文章类型对应的评价标准**。对不适用的项目标记 `N/A`，不得强行打分。

### 3. 建立评分依据（强制）

每个 DIM 必须提供：

- `score`
- `score_anchors`（参照设计文档的 5 级锚点）
- `supporting_evidence`（关联 D-NNN / E-NNN）
- `main_defects`（D-NNN 列表）
- `evidence_uncertainty`
- `conditions_to_upgrade_score`

### 4. 综合核心主张状态

逐项统计 P3 + P5 给出的 claim 状态：

- `已支持`
- `部分支持`
- `待验证`
- `被反驳`

解释这些状态如何影响文章的总体结论。**不得把"待验证"自动当成失败，也不得让大量次要 claim 掩盖关键 claim 的缺陷**。

### 5. 审查否决性缺陷

判断是否存在足以使核心结论失去成立基础的 **P0 缺陷**。若存在，明确指出受影响的 claim 及其影响范围。

**关键约束**：

> 如果存在任何 P0 缺陷，无论其他维度分数多高，最终 verdict 必须降级为以下之一：
> - "核心结论因关键缺陷而不成立"
> - "证据不足，暂时无法作出可靠判断"
>
> 任何 DIM 评分都不得抵消 P0 缺陷。

同时检查是否存在 P1 级重大缺陷，以及多个局部缺陷累积导致的系统性风险。

### 5.5 P0 判定的具体规则（解决 D-005 循环定义问题）

> **问题**："足以使核心结论失去成立基础"是循环定义——不同评审者对同一缺陷会有 P0/P1 分歧。
> **解决**：把"什么算 P0"展开为可操作的 8 条规则 + 反例清单。

#### 5.5.1 8 条 P0 触发规则

若缺陷满足以下任一规则，**必须**判定为 P0：

| # | 规则 | 典型场景 | 真实例子 |
| --- | --- | --- | --- |
| **P0-1** | **可复现性归零** | 核心结论基于实验数据，但 LLM 模型、prompt、种子、运行次数、代码任一关键信息未公开，且无第三方独立复现 | LLM Harmony D-201（GitHub 仓库名 'simulation'） |
| **P0-2** | **数据伪造/未声明的过滤** | 报告结果依赖未说明的数据清洗、样本筛选或异常值处理，使结论无法独立验证 | 报告"X = 95%"，但删除了 30% 失败样本未说明 |
| **P0-3** | **循环论证** | "证据"是结论的同义复述，无独立信息源 | "X 是好的，因为 X 优化了 X 的度量" |
| **P0-4** | **关键对照完全缺失（非平凡主张）** | 主张因果关系（"A 优于 B"），但缺少必要的对照实验，且该主张对领域非平凡 | "Multi-agent 优于 single-agent"但未与 self-consistency baseline 对比 |
| **P0-5** | **统计推断失效** | 核心定量结论无显著性检验且样本量过小（n<30），无法合理推断 | n=10 报告 "X 比 Y 好 15%"，无 t-test、无置信区间 |
| **P0-6** | **概念基础被反驳** | 核心概念在文献中无支撑或被同期工作反驳，且文章未澄清差异 | 声称"全新范式 X"但与已有 Y 范式无本质区别且未做对比 |
| **P0-7** | **P1 累积升级** | **3 个或更多独立 P1 缺陷**共同影响同一核心结论 C-NNN | D-202（缺 compute-matched）+ D-203（缺 hallucination 量化）+ D-204（baseline 不明）都影响 C-001 → C-001 等效 P0 |
| **P0-8** | **P5 反方独立确证** | P5 在不读 P2-P4 情况下独立识别同一缺陷（含 P5 提议升级 P0） | 多个 P 任务独立指向同一可复现性/对照缺失问题 |

#### 5.5.2 反例清单（**不是** P0）

| 情况 | 为什么不是 P0 | 正确分级 |
| --- | --- | --- |
| 表述不清、术语不一致 | 表达问题，不影响证据链 | P3（minor） |
| 缺 1-2 个不关键引用 | 文献覆盖问题，可补 | P2-P3 |
| 1 个独立 P1 缺陷（如缺 baseline） | 单点问题，未累积 | P1 |
| DIM 评分低但无具体反例 | 评分反映当前证据不足，**非**反证 | 不触发 P0，verdict 由 DIM/P1 决定 |
| 作者未提供数据但理论论证完整 | 理论文章数据要求低 | N/A 标注 |
| 实验有瑕疵但作者诚实声明 | 限制被显式声明 → 读者可校正 | P2-P3 |

#### 5.5.3 P5 提议升级 P0 的处理（R2.1）

当 P5 输出 `upgrade_to_p0: true` 字段时，P6 **不能**自动接受也**不能**自动拒绝。处理流程：

1. **独立评估**：用 5.5.1 的 8 条规则检验 P5 提议的缺陷
2. **记录决策**：在 `final_verdict.p5_proposed_p0_decisions` 数组中显式记录：
   ```yaml
   p5_proposed_p0_decisions:
     - defect_id: D-302-P5
       p5_proposed_severity: P0
       p6_decision: rejected       # accepted | rejected | downgraded
       reason: "符合 P0-4 关键对照缺失的表面特征，但文章明确声明这是 4-page workshop paper，无对照组实验的预期。P0-7 累积规则未达（仅 1 个独立 P1）。保守处理为 P1。"
       final_severity: P1
   ```
3. **保守默认**：若证据不足以判定 P0-1~P0-8 任一规则成立，按 P5 报告值（P1）处理而非猜测
4. **不允许"沉默接受"**：即使保守拒绝也必须记录理由

#### 5.5.4 P0 判定的审计

P6 输出必须在 `validation_summary` 中列出：

- 应用了哪几条 P0 规则（如"P0-1 可复现性归零：因 D-201"）
- 排除了哪些反例（"X 不构成 P0 因为它是 P2-3 而非 P0-1"）
- P5 提议升级 P0 的每条决策与理由

**这解决了 D-005 的循环定义问题**：P6 不再说"我判断这是 P0 因为它足以使结论失效"，
而是说"我判断这是 P0 因为它满足 P0-1（可复现性归零）的具体条件 X"——条件本身可被审计。

### 6. 形成综合结论

分别判断：

- 文章的核心主张是否成立
- 现有证据是否足以支持核心结论
- 文章的研究过程是否严谨
- 文章的创新性是否有依据
- 结论是否需要收缩适用范围
- 哪些判断仍然无法确定

### 7. 制定改进优先级

将问题分成：

- `必须解决`：影响核心结论
- `应优先解决`：显著影响可信度
- `建议改进`：提升完整性和表达质量

每项给出明确的修复动作、预期产物和验证标准。

## 输出格式（严格遵循）

按 `templates/p6-output-schema.yaml` 输出 YAML。

### A. overall_conclusion（必填）

用明确、审慎的语言说明文章的主要贡献、核心结论状态及总体可信程度。

### B. eight_dimension_scores（必填）

每条维度含 `dim_id`, `score`, `evidence_basis`, `main_defects`, `confidence`。

### C. claim_status_summary（必填）

每条 claim：`claim_id`, `claim_text`, `status`, `key_evidence`, `main_risks`, `impact_on_overall_conclusion`。

### D. critical_defects（必填）

P0/P1 缺陷清单：`defect_id`, `severity`, `related_claim_id`, `evidence`, `impact_scope`, `fix_requirement`。

### E. innovation_assessment（必填）

分别评价：原创性、理论贡献、方法贡献、证据贡献、实践价值。**区分新颖性与有效性**。

### F. final_verdict（必填）

**必须是六种之一**：

1. `core_fully_supported`（核心结论获得充分支持）
2. `core_qualified_supported`（基本成立，部分结论需收缩）
3. `core_partially_supported`（部分成立，仍需补充关键证据）
4. `core_not_yet_verified`（尚未得到充分验证）
5. `core_falsified_by_critical_defects`（因关键缺陷而不成立）
6. `insufficient_evidence`（证据不足，暂时无法判断）

> 注意：若存在 P0 缺陷，只允许 verdict 5 或 6。

### G. improvement_task_list（必填）

每条：`task_id`（V-NNN）, `priority`, `related_defect`, `action`, `expected_output`, `acceptance_criteria`。

### H. evaluation_limitations（必填）

说明本次评价没有核查哪些材料、哪些结论依赖有限证据、哪些问题需要领域专家或实际实验进一步确认。

## 约束

- ❌ 不得把 P2–P5 各维度分数简单求平均
- ❌ 不得把"待验证"自动当失败
- ❌ 不得让格式规范、文字流畅、框架复杂冒充严谨性
- ✅ 评分必须可追溯
- ✅ 存在 P0 缺陷时，verdict 强制降级
- ✅ 若证据不足，应降低判断确定性，而不是用推测填补缺口

## P6 失败模式

- ❌ "8 维平均 4.0"（无评分锚点，等同于平均掩盖否决性缺陷）
- ❌ 检测到 P0 缺陷但 verdict 仍给"基本成立"
- ❌ 不写 `evaluation_limitations`，导致 P6 输出"看起来很完整"但实际有重大未核查项
- ❌ `innovation_assessment` 把"新框架"等同于"有贡献"（必须区分新颖与有效）
- ❌ **存在 P0 缺陷但 `final_verdict.p0_veto_triggered=false`**（违反 P0-R1）
- ❌ **DIM 评分高但用 verdict 给"基本成立"**（违反 P0-R2，企图用分数冲销否决性缺陷）
- ❌ **改进任务清单中 P0 修复任务 `priority != must`**（违反 P0-R4）
