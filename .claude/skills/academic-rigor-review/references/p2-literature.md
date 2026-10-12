# P2: 理论基础与文献核查 Prompt

> 本文件是 P2 Subagent 的 prompt 模板。调用时：
> 1. 注入 `references/common-rules.md` 作为 system prompt 前缀
> 2. 替换 `{{ARTICLE}}`、`{{P1_OUTPUT}}`、`{{RESEARCH_SOURCES}}`
> 3. 启动 Subagent，**必须给 WebSearch + WebFetch 工具**

---

# 任务：核查文章的理论基础、相关工作与创新性

## 输入

- 待评价文章：`{{ARTICLE}}`
- P1 研究对象模型：`{{P1_OUTPUT}}`
- 可用文献检索能力或文献资料：`{{RESEARCH_SOURCES}}`

## 前置规则

- `common-rules.md`（公共规则）
- `id-conventions.md`（E-NNN 证据 ID、D-NNN 缺陷 ID 由本任务分配）

## 目标

判断文章的理论依据是否可靠，核心概念是否有清晰来源，相关工作是否覆盖关键成果，创新性主张是否有充分依据。

## 执行步骤

1. 提取核心概念、理论、模型、原则和关键事实陈述。
2. 对关键引用进行核查：确认来源是否真实可访问、原文是否支持作者引用的观点，以及引用语境是否被准确保留。
3. 对理论性主张，检查概念定义、适用前提、理论推导和引用依据。
4. 检查相关工作是否覆盖直接相关的代表性研究、重要替代方案、反对观点及必要的基础研究。
5. 区分文献缺失与研究缺陷：只有当遗漏影响理论依据、创新判断或结论可靠性时，才认定为实质性问题。
6. 对作者的创新主张逐项开展已有成果对照，区分真正的新贡献、已有方法的重新组合、术语重命名和应用迁移。
7. 对无法核实的文献或理论来源明确标记，不得虚构补全。
8. 判断理论依据是否足以支撑文章后续的研究设计和结论。

## 输出格式（严格遵循）

按 `templates/p2-output-schema.yaml` 输出 YAML。

### A. theory_concept_audit（必填）

每条核查项字段：

- `concept_or_theory`
- `meaning_in_article`
- `position`（原文位置）
- `source`（声称来源）
- `verification_result`（已核实 / 部分核实 / 待验证 / 无法核实）
- `evidence_id`（E-NNN）
- `role_in_research`

### B. citation_audit（必填）

每条引用：

- `citation_entry`
- `source_exists`（是 / 否 / 部分）
- `supports_claim`（是 / 否 / 部分 / 语境被扭曲）
- `context_accurate`（是 / 否）
- `evidence_id`（E-NNN）
- `verification_status`（已支持 / 部分支持 / 待验证 / 被反驳）

### C. related_work_coverage（必填）

- `covered_areas`
- `missing_critical_areas`
- `opposing_views`（缺失/存在/不适用）
- `impact_on_article`

### D. innovation_review（必填）

对每条 `declared_contributions`（来自 P1）输出：

- `claim_id`（C-NNN）
- `innovation_category`：substantive / needs_more_check / recombination / renaming / application_transfer / insufficient_evidence / overlaps_with_known
- `evidence_id`（E-NNN）
- `justification`

### E. defects（必填）

每条缺陷：

- `id`（D-NNN）
- `related_claim_id`（C-NNN）
- `evidence_id`（E-NNN）
- `problem`
- `severity`（P0 / P1 / P2 / P3）
- `impact_on_core_conclusion`
- `suggested_remediation`

### F. overall_judgment（必填）

- `theory_reliability`
- `literature_coverage`
- `citation_accuracy`
- `innovation_evidence_sufficiency`

每个字段 1–5 分 + 评分锚点 + 关键证据。

## 约束

- ❌ 不将搜索不到等同于不存在
- ❌ 不将引用数量等同于理论充分性
- ✅ 只有实际查阅并核实的来源才能标记为"已核实"
- ✅ 区分"尚未找到相关研究"与"确认不存在相关研究"
- ❌ 不得编造引用、文献、作者、出版信息

## P2 失败模式

- ❌ 把"Google 搜不到"等同于"该引用不存在"（应改为"待核实"）
- ❌ 把相关工作的"未覆盖"全部升级为 P0（应根据"是否影响理论/创新/结论"分级）
- ❌ 对 P1 给出的每条 claim 都套一遍模板，忽略哪些 claim 真的涉及理论/文献
