# P2.5: 文献补查 Prompt（针对 P3 标记的"待验证"项）

> 本文件是 P2.5 Subagent 的 prompt 模板。P2.5 是 P2 的**补充**而非替代：
> - P2：全量文献核查（覆盖文章所有 C-NNN 的引用与背景）
> - P2.5：**针对性补查**（只针对 P3 标识的"待验证"claim）
>
> 调用时：
> 1. 注入 `references/common-rules.md` 作为 system prompt 前缀
> 2. 替换 `{{ARTICLE}}`、`{{P1_OUTPUT}}`、`{{P2_OUTPUT}}`、`{{P3_PENDING_CLAIMS}}`
> 3. 启动 Subagent，**必须给 WebSearch + WebFetch 工具**
> 4. 通常 P2.5 比 P2 快 5-10x（只做针对性搜索）

---

## §0 与 P2 的关系

| 维度 | P2 | P2.5 |
| --- | --- | --- |
| **触发** | P1 完成后 | P3 完成后 + P3 标识"待验证" claim |
| **输入** | 全部 C-NNN | 仅 P3 标记的 `status=pending` claim |
| **范围** | 全量核查（概念 / 引用 / 同期工作 / 创新性） | 仅补 P2 未覆盖或 P3 额外需要的证据 |
| **输出** | 完整 E-NNN 清单 + 关键缺陷 D-NNN | 仅新增的 E-NNN + 必要的 D-NNN |
| **时间** | 5-30 min | 1-5 min |
| **失败容忍** | 中（重跑成本高） | 高（可再跑 P2 全量） |

**P2.5 不替代 P2**。如果 P2 整体失败，应优先修复 P2 而非用 P2.5 代替。

---

# 任务：针对 P3 标记的"待验证"claim 做定向文献补查

## 输入

- 待评价文章：`{{ARTICLE}}`
- P1 研究对象模型：`{{P1_OUTPUT}}`（仅参考 claim 文本与位置）
- P2 已有文献核查：`{{P2_OUTPUT}}`（避免重复检索）
- **P3 标记的"待验证"claim 清单**：`{{P3_PENDING_CLAIMS}}`（每条含 `claim_id`, `claim_text`, `pending_reason`, `p2_evidence_status`）

## 前置规则

- `common-rules.md`（公共规则）
- `id-conventions.md`（E-NNN 沿用 P2 命名空间，从 E-500 起；D-NNN 用 D-5XX-2.5 后缀避免冲突）

## 目标

为 P3 标记的"待验证"claim 找到**决定性证据**（支持、反驳、或确认"无证据"），使 P3 能更新这些 claim 的 status。

> **关键约束**：P2.5 是"找证据"任务，不是"找缺陷"任务。
> - 若找到支持证据 → 输出 E-NNN 标记 claim 为 `supported`
> - 若找到反驳证据 → 输出 E-NNN + 必要时 D-NNN（高严重度）标记 claim 为 `refuted`
> - 若搜索后确认无证据 → 输出 E-NNN（类型=negative_finding）标记 claim 为 `pending_insufficient_evidence`
> - **不得**通过"未找到"自动升级严重度（这是 P3 / P5 的工作）

## 执行步骤

### 1. 分析待验证清单

对每条 `{{P3_PENDING_CLAIMS}}` 中的 claim：

- 读 `pending_reason` 理解 P3 卡在哪
- 读 `p2_evidence_status` 知道 P2 已有/缺什么
- 决定本轮搜索的具体目标（如"找 X 方法的原始论文"、"找 X 数据集的标准结果"）

### 2. 避免重复检索

- 读 `{{P2_OUTPUT}}` 中所有 E-NNN，跳过 P2 已查过的引用与论点
- 重点是 P2 **没查到**或 P2 报告"无外部可查"但 P3 仍认为关键的项

### 3. 针对性搜索（每个 claim 1-3 次 WebSearch）

搜索策略（按需选用）：

- **原始来源**："[作者/方法名] original paper [year]"
- **同期工作**："[topic] benchmark [year-1] to [year+1]"
- **反驳证据**："[claim 关键词] refuted" / "limitations of [method]"
- **标准结果**："[dataset] state-of-the-art [year]" / "[model] on [benchmark]"

**搜索原则**：
- 优先权威源（arXiv、ACL/NeurIPS 论文、官方文档）
- 1 个 claim 最多 3 次搜索，超过则停止（避免无限循环）
- 每次搜索记录 query 字符串以便复盘

### 4. 评估找到的证据

对每条找到的证据：

| 证据类型 | 输出 E-NNN 类型 | claim 状态更新建议 |
| --- | --- | --- |
| 直接支持 | `direct_support` | `pending` → `supported` |
| 间接支持 | `indirect_support` | `pending` → `partial` |
| 反向证据 | `counter_evidence` | `pending` → `refuted`，并触发 D-NNN |
| 仅否定性发现 | `negative_finding` | `pending` → `pending_insufficient_evidence`（不升级） |
| 不可访问 / 来源失效 | `source_unavailable` | `pending` → `pending_source_unavailable` |

### 5. 输出结果

按 `templates/p2_5-output-schema.yaml` 输出 YAML。

### A. supplement_summary（必填）

- `total_pending_claims`: 本次处理的待验证 claim 总数
- `resolved_to_supported`: 升级为 supported 的数量
- `resolved_to_refuted`: 升级为 refuted 的数量
- `still_pending`: 仍未找到决定性证据的数量
- `new_e_count`: 新增 E-NNN 总数
- `new_d_count`: 新增 D-NNN 总数
- `avg_searches_per_claim`: 平均每条 claim 搜索次数（健康度指标）

### B. per_claim_results（必填）

每条 claim 一条记录：

```yaml
- claim_id: C-007
  pending_reason: "P2 报告 'cost-effective' 但未量化；P3 需要具体数字"
  p2_evidence_status: partial   # 来自 P3 输入
  search_queries:
    - "GPT-4 inference cost per token 2024"
    - "fine-tuning cost vs inference cost multi-agent"
  found_evidence:
    - evidence_id: E-501
      type: counter_evidence
      source: "OpenAI pricing page 2024-09"
      quote: "GPT-4 input $30/M tokens, output $60/M tokens"
      verdict: 推理成本比 fine-tuning 一次性成本高 6-10× for typical workload
  final_status: refuted
  new_defects:
    - defect_id: D-501-2.5
      severity: P1
      related_claim_id: C-007
      brief_problem: "cost-effective 主张与公开 API 定价数据反向"
```

### C. unresolved_claims（必填）

对仍未找到决定性证据的 claim：

```yaml
- claim_id: C-XXX
  reason_unresolved: "搜索 3 次未找到相关文献"
  recommended_next_step: "需要领域专家咨询 / 重新评估 claim 是否需要外部证据"
  downgrade_acceptable: true   # 若是 marginal claim，可降级为 minor
```

## 约束

- ❌ 不得对 P3 未标记的 claim 做搜索（避免范围蔓延）
- ❌ 不得通过"未找到"自动升级缺陷严重度（仅在确实找到反向证据时分配 D-NNN）
- ❌ 不得输出未经验证的"我有印象"类证据（必须可点回 WebSearch/WebFetch 结果）
- ✅ 必须沿用 P2 的 E-NNN 命名空间（从 E-500 起）避免冲突
- ✅ 必须复用 P2 的来源标识体系（同 P2 的 `source_type` / `source_credibility`）
- ✅ 若 P2.5 找到的证据与 P2 矛盾，必须在 `cross_check_with_p2` 字段显式记录（供 P6 审计）

## P2.5 失败模式

- ❌ 超出 P3 标记范围做"顺便"补查（破坏聚焦）
- ❌ 把"搜索不到"当 refuted（必须区分 negative_finding 和 counter_evidence）
- ❌ 输出与 P2 的 E-NNN 重复（同一条证据分配两个 E-NNN）
- ❌ 未在 `cross_check_with_p2` 中显式记录与 P2 矛盾的证据
