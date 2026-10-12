# P1: 研究对象解析 Prompt

> 本文件是 P1 Subagent 的 prompt 模板。调用时：
> 1. 注入 `references/common-rules.md` 作为 system prompt 前缀
> 2. 把 `{{ARTICLE}}` 替换为 article 内容
> 3. 启动 Subagent（agent_type=general-purpose）

---

# 任务：解析文章的研究对象与论证结构

## 输入

- 待评价文章：`{{ARTICLE}}`
- 研究背景或研究领域（可选）：`{{RESEARCH_CONTEXT}}`
- 作者声明的研究目标或创新点（可选）：`{{AUTHOR_CLAIMS}}`

## 前置规则

在执行本任务前，请先阅读并遵守：

- `common-rules.md`（学术严谨性评价公共规则）
- `id-conventions.md`（统一 ID 规则，特别是 C-NNN 分配规则）

## 目标

在不提前判断文章质量的前提下，重建文章的研究结构，为后续理论核查、论证审查、方法学审查和反方挑战提供统一输入。

## 执行步骤

1. 识别文章类型：理论研究、实证研究、实验对比、文献综述、工程方法论、观点评论或混合类型。
2. 提取研究问题、研究动机、目标对象、核心概念及其定义。
3. 提取作者明确声明的创新点，并区分新概念、新方法、新证据、新结论和新应用。
4. 将文章的主要结论拆解为**原子化主张**。每个主张应表达一个可独立检查的判断，避免将多个结论合并为一个主张。
5. 标注每个主张的类型：事实、理论、因果、比较、规范性或预测性。
6. 重建文章的论证结构：研究问题 → 理论或假设 → 研究方法 → 证据或结果 → 结论。
7. 识别作者明确声明和隐含依赖的关键假设。
8. 识别文章的适用范围、研究对象、限制条件和作者自述的局限。
9. 标注文章中尚无法确定含义、存在歧义或缺少定义的内容。

## 输出格式（严格遵循）

按 `templates/p1-output-schema.yaml` 输出 YAML，**不要输出 Markdown 报告**，所有结构化字段必须用 YAML 列表/对象表达。报告性说明可放在末尾的 `narrative_summary` 字段。

### A. research_object_overview（必填）

- `article_type`：单选
- `research_questions`：研究问题列表
- `research_goals`：研究目标列表
- `core_concepts`：核心概念列表（每个含 `name`, `definition`）
- `research_method`：研究方法
- `declared_contributions`：作者声明的贡献列表

### B. claims（必填）

每条 claim 必须包含：

- `id`：`C-NNN`（P1 负责分配，P1 范围内从 C-001 开始）
- `text`：原文或准确转述
- `position`：原文位置（章节 / 段落 / 句子标识）
- `type`：fact / theory / causal / comparative / normative / predictive
- `importance`：core / important / minor
- `author_support`：作者提供的支持依据
- `implicit_assumptions`：隐含假设列表
- `intended_scope`：预期适用范围

### C. argument_structure（必填）

描述主要 claim 之间的依赖关系。从研究问题到最终结论的推导路径，用 `dependencies` 字段表达（每条 claim 引用它的前提 claim 的 ID）。

### D. uncertainties（必填）

记录存在歧义、缺少定义、无法提取或尚需外部核查的内容。

### E. downstream_inputs（必填）

输出供 P2、P3、P4、P5 使用的结构化研究对象模型摘要。

## 约束

- 本任务只负责**解析**，不提前评定文章是否严谨
- 不擅自补充作者没有提出的主张
- 不将作者自述的创新直接认定为真实创新
- 每条 claim 必填 `id`、`text`、`position`，缺一即视为 P1 失败
- 输出的 YAML 必须能被任何标准 YAML 解析器解析

## 失败模式（应主动避免）

- ❌ 把"作者认为本文的创新点"直接列为"已确认的创新"（这是声明，不是事实）
- ❌ 多个 claim 合并为一条（如"该方法既高效又鲁棒"应拆为两条）
- ❌ 把推断当原文转述
- ❌ 跳过 position 字段（后续 P 任务无法定位）
