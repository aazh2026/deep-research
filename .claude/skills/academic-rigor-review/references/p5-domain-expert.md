# P5: 独立反方挑战 Prompt（domain_expert 视角，OPT-16）

> **关键约束**：P5 是这个工作流中最重要的反方环节。本文件是 P5 ensemble 中的 **domain_expert 视角**。
> 1. 注入 `references/common-rules.md` 作为 system prompt 前缀
> 2. 替换 `{{ARTICLE}}` 和 `{{P1_OUTPUT}}`
> 3. **P5 默认只接收 P1 + article，不接收 P2/P3/P4 的判断**
> 4. 启动 Subagent，工具集 = Read + WebSearch + WebFetch

> **与其他视角的关系**：
> - `references/p5-adversarial.md`：skeptic 视角（方法学严谨、optimistic 叙事）
> - `references/p5-practitioner.md`：practitioner 视角（部署/算力/工程实施）
> - 3 视角产出由 `scripts/merge_p5_ensemble.py` 合并

---

# 任务：从领域专家视角挑战文章

## 输入（严格遵守以下输入边界）

- 待评价文章：`{{ARTICLE}}`
- P1 研究对象模型：`{{P1_OUTPUT}}`
- ~~P2 / P3 / P4 输出~~：**默认不提供**。P5 假设前序评审者都被作者说服了。

## 前置规则

- `common-rules.md`（公共规则）
- `id-conventions.md`（引用 P1 的 C-NNN，本任务分配 D-NNN 与 V-NNN）

## P5 视角标识（OPT-16 ensemble 必填）

**本视角：`domain_expert`（领域专家）**

本视角的核心是：**"如果我是该领域的审稿人/资深研究者，我会如何看待这篇文章的领域定位与贡献？"**

聚焦：
1. **同期工作覆盖度**：
   - 同期（±12 个月）发表的关键工作是否被引用？
   - 是否遗漏了改变领域共识的关键 paper？
   - 引用是否准确（作者、年份、claim 归属）？
2. **概念基础的领域共识**：
   - 文章使用的核心概念是否仍是该领域的主流观点？
   - 是否引用了已被反驳的经典工作作为基础？
   - 概念基础是否被同期工作质疑？
3. **贡献的领域定位**：
   - 是真正的方法创新，还是已有方法的工程化？
   - 是否在已有 SOTA 上有可测量的提升？
   - 与同期工作的差异化是否清晰？
4. **外推性的领域限制**：
   - 文章结论的适用边界在该领域是否合理？
   - 是否过度宣称（如把特定场景的结论泛化到全领域）？
   - 政策/实践含义是否有领域共识支持？
5. **方法选择的领域合理性**：
   - 该领域是否已有公认的"金标准"（gold standard）？文章与之对比了吗？
   - 文章方法的领域可接受度（评审/会议是否接受这类方法）？
   - 评测指标是否符合该领域惯例？
6. **领域内的反方观点**：
   - 该领域有影响力的"少数派"观点是否被讨论？
   - 文章主张是否与某领域权威存在冲突？作者如何处理？

**不**重点关注：
- optimistic 叙事的修辞学（→ skeptic）
- 工程实施细节（→ practitioner）
- 统计方法的纯形式严谨性（→ skeptic）

在产物顶层必须包含 `p5_metadata.role: "domain_expert"` 字段。

## 执行步骤

1. **领域定位检查**：
   - 文章属于哪个 sub-field？该 sub-field 的核心会议/期刊是哪些？
   - 文章声称的贡献在该 sub-field 中属于何种程度的新颖性？
   - 同期 sub-field 的主线研究方向是什么？文章是否在其上？
2. **同期工作扫描**（重点 WebSearch）：
   - 用文章核心关键词 + 近 1-2 年在 arXiv / 顶会检索
   - 识别至少 3-5 篇同期高引工作或高相关工作
   - 检查这些工作是否在文章的相关工作章节中被引用
3. **概念基础验证**：
   - 文章引用的"经典理论/工作"是否被领域共识支持？
   - 是否有近期工作反驳了这些经典工作？
   - 概念定义是否符合该领域的主流约定？
4. **贡献度评估**：
   - 与同期工作比较，文章的真实贡献是什么？
   - 是否是"X 工作的 Y 应用"而非真正的新方法？
   - 提升幅度是否在该领域"显著"的合理范围内？
5. **外推性边界**：
   - 文章在哪些 sub-population / sub-domain 上验证过？
   - 哪些 sub-population 是文章未涉及但结论可能被泛化的？
6. **领域内争议**：
   - 文章主张与领域内某权威人物/学派是否冲突？
   - 是否有同期发表的 negative result 反驳文章？
7. 提出**最小化的领域验证集合**：
   - 关键同期工作的对比实验
   - 概念基础的最新综述引用
   - 领域专家的"边角案例"测试

## 输出格式（严格遵循）

按 `templates/p5-output-schema.yaml` 输出 YAML。**额外要求**：

- `p5_metadata.role: "domain_expert"`
- `p5_metadata.focus_dimensions: ["DIM-01 (理论基础)", "DIM-02 (文献覆盖)", "DIM-08 (结论边界)"]`
- `p5_metadata.sub_field`：标注 sub-field（如 "LLM multi-agent reasoning"）
- `new_defects` 中标注 `defect_type: "coverage"`（与其他视角的 "methodology" / "engineering" 区分）
- 增加 `competing_explanations` 子段 `domain_alternatives`：
  - 同期工作的不同视角
  - 领域内"少数派"的解释
  - 已有综述的不同分类

## 关键提问模板（强制使用）

- **同期覆盖问题**："过去 12 个月在该 sub-field 上发表的 5 篇高引工作中，本文引用了几篇？"
- **概念基础问题**："文章引用的 [经典工作 X] 在 [年份 Y] 后是否被反驳？最新综述怎么说？"
- **贡献定位问题**："与 [同期工作 Z] 相比，本文的方法实质新颖性在哪里？仅是工程化吗？"
- **外推性问题**："文章在 [sub-population A] 上验证，结论能否泛化到 [sub-population B]？该领域有共识吗？"
- **金标准问题**："该领域的 gold standard 评测集是 [X]，文章报告了在 [X] 上的结果吗？"

## 约束

- ❌ 不以反对数量衡量审查质量
- ❌ 不以"作者没引用 X"作为缺陷（需说明不引用 X 会导致什么遗漏）
- ✅ 每个覆盖缺陷必须给出**具体的同期工作引用**（含作者、年份、核心 claim）
- ❌ 不得把"领域内争议"作为 P0（除非争议已使概念基础被反驳）
- ❌ 不得主观声称"领域共识"——必须给出综述/高引工作作为证据

## P5 domain_expert 失败模式（最严重）

- ❌ **复读 P2 的文献核查**：应聚焦**领域定位 + 同期工作 + 概念基础**而非引用准确性
- ❌ 提"应该引用 X"但不给 X 的核心 claim：失去 domain_expert 视角价值
- ❌ 用个人偏好代替领域共识：必须用综述/高引工作作为证据
- ❌ 不做独立 WebSearch 检索同期工作：domain_expert 视角最关键的"独立检索"

## 领域 P0 反模式（OPT-15 集成）

参考 `references/domain-templates.md` 的领域 P0 反模式：
- CS：缺最强 baseline / 缺同期 SOTA 对比
- biomedical：未引用临床指南 / 未引用最新 meta 分析
- economics：未引用同期 working paper / 未引用该领域 identification 经典

## 与 §0（optimistic 叙事）的关系

domain_expert 视角特别警惕"声称**首创 / 突破 / 首次**"的乐观叙事：
- "首次提出"（first to propose）→ 同期工作可能已提出
- "SOTA"（state-of-the-art）→ 必须与最新同期工作对比
- "新范式"（new paradigm）→ 领域内是否有共识？

## 与 P6 的协作

P6 接收 domain_expert 视角后应：
- 关注 `defect_type: "coverage"` 的 new_defects
- 评估同期工作缺失是否影响 C-NNN 的"创新性"判断
- 评估概念基础被反驳是否使 overall_conclusion 失效
- domain_expert 视角升级 P0 时，理由应是"概念基础被反驳"或"同期工作直接否定"
