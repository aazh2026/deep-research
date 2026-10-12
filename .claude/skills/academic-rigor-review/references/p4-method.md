# P4: 研究方法与有效性审查 Prompt

> 本文件是 P4 Subagent 的 prompt 模板。调用时：
> 1. 注入 `references/common-rules.md` 作为 system prompt 前缀
> 2. 替换 `{{ARTICLE}}`、`{{P1_OUTPUT}}`、`{{P3_OUTPUT}}`、`{{SUPPLEMENTARY_MATERIALS}}`
> 3. 启动 Subagent，工具集 = Read + Bash + WebFetch（用于复现性检查）

---

# 任务：审查文章的研究方法、证据质量与有效性威胁

## 输入

- 待评价文章：`{{ARTICLE}}`
- P1 研究对象模型：`{{P1_OUTPUT}}`
- P3 主张证据台账：`{{P3_OUTPUT}}`
- 研究材料、数据、代码或实验记录（可选）：`{{SUPPLEMENTARY_MATERIALS}}`

## 前置规则

- `common-rules.md`（公共规则）
- `id-conventions.md`（引用 P1/P3 的 ID，本任务分配 D-NNN 与 V-NNN）

## 目标

判断研究方法是否适合回答研究问题，研究设计是否可靠，测量与比较是否合理，以及研究结果能否支撑作者声称的结论。

## 执行步骤

1. **根据文章类型选择相应的审查标准**。对于没有实验设计的理论文章，不得机械要求提供实验数据。
2. 检查研究问题、研究方法、评价指标和最终结论之间是否一致。
3. 对实证研究检查：样本选择、样本量依据、测量方法、数据质量、缺失数据处理、统计分析、结果报告。
4. 对对比实验检查：基线选择、实现质量、模型和版本、提示词、上下文、工具权限、计算预算、重复次数及其他影响结果的变量。
5. 对定性研究检查：案例选择、分析程序、编码规则、研究者偏差、解释的可追溯性。
6. 对理论研究检查：定义是否明确、假设是否合理、推导是否完整、结论是否依赖未声明的条件。
7. 对文献综述检查：检索范围、来源选择、纳入排除标准、综合方法、潜在发表偏差。
8. 对工程方法论检查：机制设计依据、适用场景、实际案例、失败案例、实施条件、效果验证。
9. 检查内部有效性、外部有效性、构念效度、统计结论有效性等风险；不适用的类别应说明原因。
10. 检查可复现性所需的信息是否充分：数据、代码、配置、实验步骤、环境说明。
11. 区分已经证实的缺陷、潜在风险和因资料不足而无法判断的问题。
12. **提出能够区分不同解释的补充实验或分析**，而不只是泛泛要求"增加实验"。

## 输出格式（严格遵循）

按 `templates/p4-output-schema.yaml` 输出 YAML。

### A. method_question_fit（必填）

每条核心 claim：

- `claim_id`（C-NNN）
- `method_appropriate`（是 / 部分 / 否 / 不适用）
- `reasoning`

### B. claim_evidence_ledger（必填，R8 新增）

> **R8 引入**：与 P3 的 `claim_evidence_ledger` 对齐。P3 评估"逻辑证据"，P4 评估"方法学证据"，
> 两者合并形成完整的 per-claim evidence ledger。

每条重要性 = core 的 C-NNN 必填：

- `claim_id`（C-NNN）
- `supporting_evidence_ids`（E-NNN 列表，方法学维度支持该 claim 的证据）
- `opposing_evidence_ids`（E-NNN 列表，方法学维度反对该 claim 的证据）
- `supporting_method_findings`（P4 自己发现的方法学支持点，文字描述）
- `opposing_method_findings`（P4 自己发现的方法学反对点，文字描述）
- `cross_reference_to_p3`（引用 P3 同一 claim 的 ledger 条目，说明方法学层面新增/修正；
  若无新增写"无新增，P3 评估已充分覆盖"）

### C. research_design_audit（必填）

每条审查项：

- `item`
- `article_description`
- `verification_evidence_ids`（E-NNN 列表，R8 升级：原 `verification_evidence` string → list）
- `issue_found`
- `impact`
- `status`（已确认 / 潜在 / 资料不足）

### D. validity_threats（必填）

分别分析：

- `internal_validity`
- `external_validity`
- `construct_validity`
- `statistical_conclusion_validity`
- `reproducibility`

每项列出威胁清单。每条 threat 含：

- `threat`（威胁描述）
- `related_claim_id`（C-NNN）
- `evidence_ids`（E-NNN 列表，R8 升级：原 `evidence_id` string → list）
- `severity`（P0 / P1 / P2 / P3）

### E. key_defects（必填）

按 P0–P3 分级，每条：

- `id`（D-NNN）
- `severity`
- `related_claim_id`（C-NNN）
- `evidence_ids`（E-NNN 列表，R8 升级：原 `evidence_id` string → list）
- `impact_category`（data_credibility / measurement / causal_inference / comparison_fairness / generalization）
- `description`

### F. supplementary_verification_plan（必填）

每条验证：

- `id`（V-NNN）
- `question_to_verify`
- `competing_explanations`
- `recommended_experiment`
- `controls_needed`
- `observation_metrics`
- `decision_rule`（不同结果如何影响结论）

### G. method_overall_judgment（必填）

- `method_appropriateness`
- `evidence_quality`
- `comparison_fairness`
- `validity`
- `reproducibility`

每项 1–5 分 + 评分锚点 + **`key_evidence_ids`**（E/D-NNN 列表，R8 升级：原 `key_evidence` → `key_evidence_ids`）。

## 约束

- ❌ 不得仅因论文没有公开代码就直接判定其结论无效
- ❌ 不得将作者未报告某项控制措施直接等同于确定没有控制
- ✅ 区分"未报告"、"已确认缺失"、"已确认错误"
- ✅ 验证方案必须能区分竞争性解释（不只是"加实验"）

## P4 失败模式

- ❌ 对理论文章要求"补充实验数据"（理论文章不适用）
- ❌ 把"未公开代码"升级为 P0（应区分"作者未提供"与"代码实际有误"）
- ❌ 验证方案写成"建议增加更多实验"（必须给出可操作的实验设计）
