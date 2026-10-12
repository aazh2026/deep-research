# P3: 主张、证据与逻辑推理审查 Prompt

> 本文件是 P3 Subagent 的 prompt 模板。调用时：
> 1. 注入 `references/common-rules.md` 作为 system prompt 前缀
> 2. 替换 `{{ARTICLE}}`、`{{P1_OUTPUT}}`、`{{P2_OUTPUT}}`
> 3. **P2_OUTPUT 可选**（若不可用，使用 `{{P2_OUTPUT_PLACEHOLDER}}` 标记并启用"初稿模式"——见 §0）
> 4. 启动 Subagent，工具集 = Read

---

## §0 P2 输出占位机制（R6 引入）

P3 的输入 `{{P2_OUTPUT}}` 在两种模式下行为不同：

### 模式 A：完整模式（P2_OUTPUT 完整可用）

- 正常使用 P2 提供的 E-NNN 证据清单
- P3 直接消费 P2 报告的"待验证"标记
- P3 输出中的 `evidence_status.evidence_source` 标记为 `P2`

### 模式 B：初稿模式（P2_OUTPUT 不可用 / 部分可用 / 超时）

**触发条件**（任一）：
- `{{P2_OUTPUT_PLACEHOLDER}}` 替换为 `PENDING` 或 `<unavailable>`
- P2 运行超时（默认 30 min），orchestrator 选择不等
- P2 WebSearch 失败率 > 50%

**P3 行为变化**：
1. **不等待 P2**：P3 用 P1 + article 独立做逻辑分析
2. **强制声明不确定性**：每条 claim 的 `evidence_status` 必须含 `evidence_source: P1_ONLY` 和 `p2_dependency: BLOCKED` 字段
3. **重点关注"不依赖 P2 也能发现的缺陷"**：循环论证、概念偷换、隐含假设等
4. **P2 完成后增量更新**：当 P2_OUTPUT 到达，**只对 P2 影响范围内的 claim 重跑**：
   - 受 P2 新增 E-NNN 直接影响的 claim
   - 之前标记为 `p2_dependency: BLOCKED` 的 claim
   - 不重跑已经完整分析过的 claim（避免重复工作）

**P3 输出标记**：
```yaml
p3_metadata:
  mode: draft | complete       # 当前运行模式
  p2_status: available | pending | partial
  p2_received_at: <ISO 8601>  # 仅 complete 模式填写
  affected_claim_ids: [...]    # 仅增量更新时填写
```

**下游影响**：
- P4 应感知 P3 的 mode，若为 draft 则延后启动 P4 等待 P2 增量更新
- P6 应在 `evaluation_limitations` 中显式声明"P3 在 P2 未完成时初稿运行，结论时效性受 P2 增量影响"

### 反模式（明确禁止）

- ❌ P2 不可用时 P3 仍假装"全部已分析"（必须显式 `p2_dependency: BLOCKED`）
- ❌ P2 到达后 P3 全量重跑（应只重跑 affected_claim_ids）
- ❌ orchestrator 在 P2 长时间不可用时不告知 P3，直接报"上游失败"（应先报"使用初稿模式"再决定是否延后）

---

# 任务：审查文章的主张、证据链与推理有效性

## 输入

- 待评价文章：`{{ARTICLE}}`
- P1 研究对象模型：`{{P1_OUTPUT}}`
- P2 理论与文献核查报告：`{{P2_OUTPUT}}`（不可用时替换为 `{{P2_OUTPUT_PLACEHOLDER}}=PENDING`）`

## 前置规则

- `common-rules.md`（公共规则）
- `id-conventions.md`（引用 P1 的 C-NNN、P2 的 E-NNN，本任务分配 D-NNN）

## 目标

逐项检查文章的关键主张是否得到充分支持，证据与主张之间的推理是否有效，是否存在逻辑跳跃、概念偷换、隐含假设或结论过度延伸。

## 执行步骤

1. 对每个核心主张建立独立的论证链：主张、支持证据、推理规则、隐含假设、适用边界。
2. 检查证据的相关性、真实性、充分性与代表性。区分直接证据、间接证据、类比依据和作者观点。
3. 检查从证据到结论的推理是否有效，识别：
   - 因果与相关混淆
   - 以偏概全
   - 循环论证
   - 选择性证据
   - 错误类比
   - 概念偷换
   - 未经证明的前提
4. 检查中间推论是否成立，避免只审查文章的最终结论。
5. 对比较性主张，检查比较对象、评价维度和适用条件是否一致。
6. 对因果性主张，检查是否存在混杂因素、反向因果或其他合理解释。
7. 检查证据是否存在相互依赖或重复计数。
8. 评估证据能够支持的最强结论，并与作者实际表述比较。
9. 识别缺少必要前提、需要补充证据或需要收缩表述的主张。
10. 对存在争议的判断，给出支持该判断的理由及其不确定性。

## 输出格式（严格遵循）

按 `templates/p3-output-schema.yaml` 输出 YAML。

### A. claim_evidence_ledger（必填）

每条 claim 的台账：

- `claim_id`（C-NNN）
- `claim_text` + `position`
- `claim_type`
- `supporting_evidence_ids`（E-NNN 列表）
- `opposing_evidence_ids`（E-NNN 列表）
- `reasoning_rule`
- `implicit_assumptions`
- `evidence_sufficiency`（充分 / 部分 / 不足）
- `reasoning_validity`（有效 / 部分 / 无效）
- `scope_boundary`
- `status`（已支持 / 部分支持 / 待验证 / 被反驳）
- `judgment_basis`

### B. logic_defects（必填）

每条缺陷：

- `id`（D-NNN）
- `related_claim_id`（C-NNN）
- `defect_type`（causal_confusion / overgeneralization / circular / selective / analogy / concept_swap / unproven_premise 等）
- `textual_evidence`（原文位置 + 引用）
- `why_problematic`
- `downstream_impact`
- `severity`（P0 / P1 / P2 / P3）
- `suggested_fix`

### C. conclusion_strength_review（必填）

每个核心结论：

- `author_claim`
- `evidence_supported_claim`
- `gap`
- `suggested_more_cautious_wording`

### D. dependency_analysis（必填）

- `claim_dependencies`：哪些 claim 依赖其他 claim（如 `C-005 depends on [C-001, C-003]`）
- `critical_premise_failures`：哪些前提失效后哪些结论需要重新评估

## 约束

- ❌ 不得将缺少证据直接判定为结论错误
- ❌ 不得仅凭表达不清认定推理错误
- ✅ 必须指出具体的推理环节和缺失条件
- ✅ 对无法确认的问题标记为"待验证"

## P3 失败模式

- ❌ 把"作者没说清楚"等同于"推理错误"（前者是表达问题，后者是逻辑问题）
- ❌ 对每条 claim 都机械给"待验证"（应用既有证据给出真实判断）
- ❌ 忽略 P2 已经核实为"被反驳"的引用，直接接受作者论述
