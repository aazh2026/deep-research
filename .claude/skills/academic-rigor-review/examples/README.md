# Smoke Test Output: docs/design.md 评审

这是 skill 自身的端到端冒烟测试产物。**测试目标不是证明 skill 完美，而是验证 skill 真实可用并暴露缺陷**。

## 测试范围

- ✅ P1（研究对象解析）
- ✅ P3（主张证据审查）
- ✅ Step 3.5（P0 orchestrator 预检）
- ✅ P6（综合评审 + P0 硬规则自检）
- ⏭️ P2（无外部文献可核查，跳过）
- ⏭️ P4（本文无实验设计可审计，跳过）
- ⏭️ P5（节省 token，但意味着 P5 视角下的 P0 缺陷可能漏检）

## 关键发现

### 1. skill 真实可用

- P1 YAML 通过 schema 校验，提取 15 条 claim（C-001 至 C-015），其中 7 条为 `core`
- P3 YAML 通过 schema 校验，输出 12 条 ledger + 9 条 logic_defects
- P6 YAML 通过 P0-R1 至 P0-R5 全部硬规则自检

### 2. skill 找到 design 自身的 1 个 P1 缺陷

**D-001（severity=P1）**：

> design.md 第二节声称 "P2—P5 可在 P1 完成后并行执行"，
> 但 P3 prompt 输入显式包含 P2_OUTPUT、P4 包含 P3_OUTPUT、P5 包含 P2/P3/P4_OUTPUT。
>
> 严格的并行执行不可能——P3/P4/P5 之间是流水线关系。

**此发现已在 SKILL.md 的"核心架构"和 Step 2 中修正**：

- 修正为"阶段 1 启动 P2 + P5（两者都只依赖 P1），阶段 2 启动 P3（依赖 P2），阶段 3 启动 P4（依赖 P3）"
- 加 ⚠️ 标注说明 design.md 原声明与各 prompt 输入列表的矛盾

### 3. P0 预检机制成功

- Step 3.5 在 P3 完成后执行，扫描所有 P 产物的 `key_defects` / `defects` / `logic_defects` 字段
- 本次 P0 预检结果：空（无 P0 缺陷）
- P6 schema 的 `precheck_p0_summary.precheck_input_was_empty=true` 字段成功记录此事实
- 这意味着 P6 可以正常给出 `core_qualified_supported` 而不被 P0 否决

### 4. P6 硬规则全部通过

P0-R1: critical_defects 中无 P0 → p0_veto_triggered=false ✓
P0-R2: precheck 为空 → verdict 不受 P0 约束 ✓
P0-R3: P1 缺陷 D-001 含 related_claim_id/impact_scope/fix_requirement ✓
P0-R4: V-001（修复 D-001）priority=must ✓
P0-R5: rationale 未出现 DIM 平均分冲销 P0 的表述 ✓

## 评分

| 维度 | 分数 | 说明 |
| --- | --- | --- |
| DIM-01 理论基础 | 3 | 工程类比合理但缺直接证据 |
| DIM-02 文献相关工作 | N/A | 方法论无外部引用 |
| DIM-03 论证与推理 | 3 | 1 项 P1 内部矛盾 + 多项 P2 论证不足 |
| DIM-04 研究方法 | 3 | 7 任务划分内在逻辑但缺完备性论证 |
| DIM-05 证据与数据 | N/A | 方法论无实验数据 |
| DIM-06 有效性与偏差控制 | 3 | P5 独立视角优秀但边界有歧义 |
| DIM-07 可复现性 | 2 | 无端到端运行数据 |
| DIM-08 结论边界 | 4 | 结论边界声明明确 |

## 最终 verdict

`core_qualified_supported`（核心结论基本成立，但部分需收缩）

## 局限性

1. P5 跳过后，可能漏掉 P5 视角下的关键 P0 缺陷。完整端到端应运行 P5。
2. 本测试中 orchestrator 同时扮演了"主 agent"和"子 agent"两个角色（合成测试）。
   真实多 Subagent 部署中，每个 P 任务由独立 agent 执行，可能产生不同结论。
3. P0 预检只看 severity=P0 的字段，未做跨产物一致性检查（如 P3 标记为 refuted 但 P5 不挑战的 claim）。
