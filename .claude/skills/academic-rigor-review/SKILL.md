---
name: academic-rigor-review
description: 学术严谨性多 Agent 评价工作流。对论文、技术研究报告、Agent 架构模式、工程方法论进行可追溯的 P1–P7 七阶段评审（解析 → 文献核查 → 论证审查 → 方法审查 → 反方挑战 → 综合评分 → 修订复评），产出带统一 ID（C-/E-/D-/V-/DIM-）的工件而非主观印象。Use when the user wants to critique, review, or audit the rigor of a research paper, technical report, agent architecture proposal, or engineering methodology — especially when the user wants evidence-traceable verdicts rather than vibes-based feedback, or asks for "学术严谨性评价", "rigor review", "paper review", "评审", "批判性分析", "找出研究漏洞".
version: 1.0.0
---

# Academic Rigor Review Skill

基于 `docs/design.md` 实现的 7 阶段多 Agent 评价工作流。把"主观评审"拆成"可追溯的工件流"，让最终结论的每一步都能点回到具体的主张、证据、缺陷和验证任务。

## 何时激活

- 用户给出一篇论文 / 技术报告 / Agent 架构设计 / 工程方法论，要求评审
- 用户希望产出"可复核"的评分和缺陷清单，而非泛泛印象
- 用户明确提到"学术严谨性""rigor review""批判性审查""找出漏洞""check my paper"
- 用户希望基于缺陷做修订（进入 P7）

**不要**用于：纯润色、翻译、格式调整、仅总结文章内容而不评价。

## 核心架构：DAG 而非线性流水线

```
                                ┌─► P3 主张与论证审查 ─┐
P1 研究对象解析 ──┬─► P2 理论文献核查 ─┤                    ├─► P6 综合评审
                  │                  └─► P4 方法学审查 ─┘        │
                  │                                              │
                  └─► P5 反方挑战（独立视角，可与 P2 并行启动）──┘
                                                                 │
                                                                 ▼
                                                               P7 修订复评
                                                                 │
                                                          (影响范围触发 P 重跑)
```

**关键设计原则**：

1. **P1 是唯一的串行入口**：所有下游任务共享 P1 的"事实层"（主张列表 + ID）
2. **P2 与 P5 可在 P1 完成后并行启动**——P2 只依赖 P1，P5 默认也只依赖 P1
3. **P3 在 P2 完成后启动**——P3 依赖 P1 + P2 产物
4. **P4 在 P3 完成后启动**——P4 依赖 P1 + P3 产物（P2 产物经 P3 间接传递）
5. **P6 是唯一决策节点**：综合所有上游工件，但**不能简单平均**
6. **P7 影响范围触发**：只重跑被修改的 claim/evidence 涉及的 P，而不是全量重跑

> ⚠️ **修正说明**：原 `docs/design.md` 第二节描述"P2–P5 可在 P1 完成后并行执行"，
> 但各 P 任务的输入列表与该声明矛盾（P3 依赖 P2_OUTPUT，P4 依赖 P3_OUTPUT）。
> 本 skill 采用上述修正后的流水线式调度。如需 strict parallel 并行，
> 应重新设计 P3/P4 使其不依赖上游 P 输出。

## 统一 ID 规则（强制）

任何 P 任务的输出都必须使用 `references/id-conventions.md` 中规定的 ID：

- `C-NNN`：核心主张（由 P1 分配）
- `E-NNN`：证据（由 P2/P3 分配）
- `D-NNN`：缺陷（由发现它的 P 任务分配，必须关联 C-NNN）
- `V-NNN`：验证任务（由 P4/P5 提出，P7 跟踪）
- `DIM-NN`：八个评价维度（用于 P6 评分）

**违反 ID 规则的下游任务会被拒绝消费**。

## 工作流程

### Step 0: 准备

读取 `references/common-rules.md`（公共规则）和 `references/id-conventions.md`（ID 约定），并把这两份内容注入每个 P 任务的 system prompt 前缀。

读取 article（用户提供的文件路径或粘贴内容）。若用户提供的是 URL，先用 WebFetch 抓取并保存为本地 `article.md`。

为本次评审创建工作目录：

```
.claude/skills/academic-rigor-review/runs/<timestamp>-<slug>/
├── article.md
├── p1_object_model.yaml
├── p2_literature_audit.yaml
├── p3_claim_evidence.yaml
├── p4_method_review.yaml
├── p5_adversarial.yaml
├── p6_synthesis.yaml
└── p7_revision/
```

### Step 1: P1 研究对象解析（串行）

读取 `references/p1-parse.md`，把 article + 公共规则 + ID 约定作为输入，启动一个 Subagent。

**强制要求**：

- 输出严格遵循 `templates/p1-output-schema.yaml`
- 每条 claim 必须分配 `C-NNN` ID
- 记录所有"初步不确定性"（歧义、缺定义、待外部核查）

**校验**：

- [ ] P1 输出可被 YAML 解析
- [ ] 所有 claim 有 `C-NNN` 和原文位置
- [ ] 不确定性清单非空（除非文章极其清晰）

### Step 1.5: 选择领域模板（OPT-15）

在 P1 完成后、**进入 Step 2 之前**由 orchestrator 选择领域模板，详见 `references/domain-templates.md`：

1. **自动检测**（基于 article 关键词 + venue + 引用风格）：
   - CS 关键词：`benchmark / baseline / neural / LLM / agent / code release / GitHub`
   - 生物医学关键词：`clinical trial / patient / IRB / CONSORT / blinding / sample size`
   - 经济学关键词：`identification / IV / treatment effect / panel data / robust`
   - 无明确信号 → 使用 `default` 模板
2. **用户显式覆盖**：若用户告知领域，强制使用对应模板
3. **混合领域**：用 `mixed:<领域1>+<领域2>` 标记

输出写入后续 P6 产物的 `domain_template` 字段（schema 必填）。

**P0 硬规则不受模板影响**——模板仅影响 DIM 加权平均与 P0 反模式的"具体场景"举例。

### Step 2: P2 / P3 / P4 / P5 流水线式启动

读取 `references/p2-literature.md`、`p3-claim.md`、`p4-method.md`、`p5-adversarial.md`，按依赖关系分阶段启动 Subagent。

**阶段 1（P1 完成后立即启动）**：

- **P2**（只依赖 P1）→ 启动 p2-auditor Subagent
- **P5**（默认只依赖 P1）→ 启动 p5-adversary Subagent

这两个可以**同一消息中并行启动**（独立 tool call）。

**阶段 2（P2 完成后启动）**：

- **P3**（依赖 P1 + P2）→ 启动 p3-critic Subagent

**阶段 3（P3 完成后启动）**：

- **P4**（依赖 P1 + P3）→ 启动 p4-reviewer Subagent

**Subagent 工具集**：

- P2: Read + WebSearch + WebFetch（文献核查需要联网）
- P3: Read（逻辑分析）
- P4: Read + Bash + WebFetch（可跑代码验证）
- P5: Read + WebSearch + WebFetch（独立检索）

**校验**：

- [ ] P2/P3/P4/P5 输出都遵循对应 schema
- [ ] 所有 D-NNN 都关联到 C-NNN
- [ ] 证据缺口明确标记"待验证"，不得编造
- [ ] P5 实际只接收 P1 + article（除非显式进入"查漏模式"）

#### Step 2.5: P2/P3 占位机制（处理 P2 延迟或失败）

P2 因联网受限、WebSearch 失败率 > 50% 或超时（默认 30 min）而无法在合理时间内完成时，**不应**让 P3/P4/P6 全部阻塞。P3 可在 **draft 模式**下启动（详见 `references/p3-claim.md` §0）：

| 模式 | 触发 | P3 行为 | P4 启动时机 |
| --- | --- | --- | --- |
| **complete** | P2_OUTPUT 完整可用 | 正常使用 P2 提供的 E-NNN | P3 完成后立即启动 |
| **draft** | P2 不可用 / 部分 / 超时 | 显式声明 `p2_dependency: BLOCKED`，重点做不依赖 P2 也能发现的缺陷 | 等待 P2 完成后 P3 增量更新，再启动 P4 |

**orchestrator 决策流程**：

1. P1 完成 → 并行启动 P2 + P5
2. **P2 计时启动**：记录 `p2_start_time`
3. **P3 启动条件**：
   - 若 P2 完成 → 模式 A（complete）
   - 若 P2 超时（>30 min）→ 模式 B（draft），P3 启动
   - 若 P2 失败但有部分输出 → 模式 B（draft），用 `partial` 标记
4. **P2 后到达时**：P3 增量更新（只重跑 affected_claim_ids）
5. **P4 启动条件**：P3 为 complete 模式 OR P3 draft 模式 + P2 已到达并完成增量更新

**P6 awareness**：
P6 应在 `evaluation_limitations` 中显式声明本次 P3 是否经历过 draft 模式（如经历过，附 P2 到达时间差）。这避免用户在 P3 draft 期间误以为结论已稳定。

#### 反模式

- ❌ P2 失败时 P3 仍假装"全部已分析"
- ❌ P2 后到达时 P3 全量重跑
- ❌ P4 在 P3 draft 模式下启动（会因 P2 缺失而出现方法学评估偏差）
- ❌ orchestrator 跳过 draft 模式让 P3 永远阻塞等待 P2

#### Step 2.6: P2.5 文献补查（条件性，针对 P3 待验证项）

P3 完成后，若 P3 产物中 `status=pending` 的 claim 数 ≥ 1，**可选**触发 P2.5 文献补查。
P2.5 是 P2 的**补充**而非替代——比 P2 范围小、速度更快（5-10x），只针对 P3 标记的"待验证"项。

读取 `references/p2_5-literature-supplement.md`，输入：

- `{{P3_PENDING_CLAIMS}}`：P3 产物中 `status=pending` 的 claim 列表
- `{{P2_OUTPUT}}`：避免重复检索
- `{{P1_OUTPUT}}`：参考 claim 文本与位置

**触发条件**（任一）：

- P3 标识 ≥ 3 个 `status=pending` 的 claim
- P2 报告 ≥ 1 个 `evidence_status=source_unavailable` 的关键引用
- 用户显式要求"补查文献"

**不触发**：

- P3 全部 claim 都已 `supported` / `refuted`
- 文章是纯理论/方法论设计（无外部证据需求）
- 时间预算极紧（可接受 `pending_insufficient_evidence` 状态）

**P2.5 输出**：

- 新增 E-NNN（E-500 起）与可能的 D-NNN（D-5XX-2.5 后缀）
- `unresolved_claims` 标记仍未找到决定性证据的 claim
- `p2_consistency` 字段：与 P2 的证据是否一致（避免孤证）

**P6 消费方式**：
P2.5 完成后，P3 **不需要重跑**——P3 接收 P2.5 的 E-NNN 并对 affected_claim_ids 做 status 更新（这与 P2 增量更新机制一致）。P6 直接消费更新后的 P3 产物。

#### 反模式（P2.5 专属）

- ❌ 超出 P3 标记范围做"顺便"补查
- ❌ 把"搜索不到"自动当 refuted（必须区分 negative_finding 和 counter_evidence）
- ❌ 输出与 P2 重复的 E-NNN（必须从 E-500 起）
- ❌ P2.5 找到的反向证据未升级 D-NNN
- ❌ P6 直接消费 P2.5 产物而忽略 P3 的 status 更新

### Step 3: P5 反方挑战（独立视角，OPT-16 ensemble 模式）

读取 3 个 P5 视角 prompt，**并行启动 3 个 Subagent**：

- `references/p5-adversarial.md` → **skeptic 视角**（方法学严谨、optimistic 叙事）
- `references/p5-practitioner.md` → **practitioner 视角**（部署/算力/工程实施）
- `references/p5-domain-expert.md` → **domain_expert 视角**（同期工作/概念基础/外推性）

每个视角独立接收 P1 + article，**不得看其他视角的输出**（避免共识污染）。

**OPT-16 设计动机**：单次 P5 LLM 调用易漏报。3 视角独立 prompt + 独立 LLM 调用 → 漏报率显著下降；共识是更强的信号（2+ 视角独立识别 → 高置信度 P0 升级建议）。

**关键约束（违反则反方价值丧失）**：

- ⚠️ **P5 只能看 P1 + article，不得看 P2/P3/P4 的判断**
- P5 必须假设"前序评审者都被作者说服了"
- P5 的工作：独立推理 + 独立检索（可选 WebSearch），找出 P2–P4 可能漏掉的关键反例
- 读完自己的推理后，**可选地**参考 P2–P4 查漏，但不得被同化

**Optimistic 叙事专项处理**（R2.2 引入，skeptic 视角必读）：

skeptic 视角启动时**应显式判断**文章是否属于乐观叙事（见 `p5-adversarial.md` §0.1）。若是，**必须**执行：

1. §0.2 11 类反向风险检查清单（最强 baseline 缺失 / collective delusion / 隐性成本转移 / 同期工作脱节 等）
2. §0.3 4 个强制问题（compute 对比 / 同质配置最坏情况 / 隐性成本转移 / 同期反向工作）
3. §0.4 难度自检（至少 1 个反向风险 + 全部 4 问题已答 + 至少 1 个同期工作引用 + 至少 1 个 new_defect）

**Step 3.1（OPT-16）：3 视角输出合并**

3 视角完成后，用 `scripts/merge_p5_ensemble.py` 合并：

```bash
python3 scripts/merge_p5_ensemble.py \
  --skeptic p5_skeptic.yaml \
  --practitioner p5_practitioner.yaml \
  --domain-expert p5_domain_expert.yaml \
  --out p5_ensemble_merged.yaml
```

合并逻辑（AND 条件避免假阳性）：
1. `related_claim_id` 必须相同
2. SequenceMatcher ratio >= 0.40（描述相似度）
3. 共享关键术语数 >= 3（中英文混合提取）

共识升级规则：

| 共识强度 | P0 升级建议 |
| --- | --- |
| 3 视角都识别 | `strong_recommend`（高置信度 P0） |
| 2 视角独立识别 | `recommend`（P6 应基于 evidence_id 验证） |
| 仅 1 视角 | `needs_verification`（P6 单独验证） |

**输出校验**（每个视角 + 合并后）：

- [ ] P5 至少提出 3 个"前序未识别"的新增缺陷（如果找不到也要说明为什么找不到）
- [ ] 每个反方挑战都有"竞争性解释"和"区分证据"
- [ ] 不以反对数量衡量审查质量
- [ ] 合并后 `p0_recommendations` 中 2+ 视角共识的缺陷必须送 P6 优先处理
- [ ] practitioner 视角的每个工程缺陷必须给出具体成本（GPU/API/人力）

### Step 3.5: Orchestrator P0 预检（强制，不可跳过）

> **P6 启动前必须执行此步骤**。这是 P0 否决机制能可靠工作的关键。

Orchestrator 自身扫描 P2–P5 产物的 `key_defects` / `defects` / `logic_defects` / `new_defects` 字段，把所有 `severity=P0` 的 D-NNN 汇总到 `precheck_p0_defects.yaml`：

```yaml
precheck_p0_defects:
  - defect_id: D-NNN
    source_phase: P2 | P3 | P4 | P5
    related_claim_id: C-NNN
    brief_problem: <一句话问题描述>
    evidence_id: E-NNN  # 可选
  - ...

precheck_summary:
  total_p0_count: N
  by_phase:
    P2: n2
    P3: n3
    P4: n4
    P5: n5
  has_p0: true | false
```

**硬约束**：

- ❌ 不允许跳过此步骤直接启动 P6
- ❌ 不允许只预检 P2-P4 而漏掉 P5（很多 P0 恰恰是 P5 发现的）
- ✅ P5 完成后立即执行，无论 P5 产物是否看起来"完美"
- ✅ 即使 precheck 为空，也要生成空文件，作为 P6 的输入凭据

**失败处理**：

- 若 orchestrator 跳过此步骤，P6 应当检测到 `{{PRECHECK_P0_DEFECTS}}` 缺失并报告 orchestrator 错误
- 若 orchestrator 预检为空但 P2–P5 产物中实际含 P0，p6 schema 的 `precheck_p0_summary.precheck_input_was_empty=false` 会触发 P6 显式报告此 orchestrator 错误

### Step 4: P6 综合评审（决策节点）

读取 `references/p6-synthesis.md` + `references/domain-templates.md`，启动一个 Subagent。P6 是**唯一一个看全局的 agent**。

**强制输入**（除上游 P 产物外，必须额外提供）：

- `precheck_p0_defects.yaml`（来自 Step 3.5 的 P0 预检结果）
- `domain_template`（来自 Step 1.5，含 DIM 权重 + 领域 P0 反模式清单）

**强制约束**：

- ❌ 不得把 P2–P5 各维度分数简单求平均
- ❌ 不得把"待验证"自动当失败
- ❌ 不得让格式规范、文字流畅、框架复杂冒充严谨性
- ✅ **存在 P0 缺陷时，无论其他维度多高分，verdict 必须降级为以下之一**：
  - "核心结论因关键缺陷而不成立"
  - "证据不足，暂时无法作出可靠判断"
- ✅ 每个 DIM 评分必须给"评分锚点"（参照设计文档 1–5 分的 5 级锚点）
- ✅ **P0 五条硬规则（P0-R1 至 P0-R5）见 `references/p6-synthesis.md` Step 1.5，必须全部满足**

**P6 输出的最终 verdict 必须是六种之一**：

1. 核心结论获得充分支持
2. 核心结论基本成立，但部分结论需要收缩
3. 核心结论部分成立，仍需补充关键证据
4. 核心结论尚未得到充分验证
5. 核心结论因关键缺陷而不成立
6. 证据不足，暂时无法作出可靠判断

### Step 5: P7 修订与复评（条件性）

仅当用户希望根据评审结果修订文章时执行。读取 `references/p7-revision.md`。

**P7 的核心不是润色，而是把 D-NNN 翻译成可验收的 V-NNN 修订任务**。

#### Step 5.0: 修订计划生成（用 `scripts/apply_v_nnn.py`）

P7 输出 `revision_task_list` 后，**应**先运行 `scripts/apply_v_nnn.py` 生成结构化修订计划：

```bash
python scripts/apply_v_nnn.py \
  --article runs/<run-id>/article.md \
  --p6 runs/<run-id>/p6_synthesis.yaml \
  --p7 runs/<run-id>/p7_revision.yaml \
  --out runs/<run-id>/p7_revision_plan.yaml
```

脚本功能：
- **自动分类**：每条 V-NNN 标记为 text / evidence / method / conclusion / unknown
- **可自动应用判定**：text 类 + 收缩类 conclusion 可纯文本完成
- **P0 优先标记**：与 P6 中 P0 critical_defect 关联的 V-NNN 单独标出
- **受影响 P 任务**：根据 p7-revision.md Step 8 表计算需重跑的 P 集合

P7 完成后，**根据修改影响范围触发相关 P 重跑**：

| 修改内容 | 触发重跑 |
| --- | --- |
| 主张被修改/收缩 | 重跑 P3 |
| 引用/文献被修改 | 重跑 P2 |
| 方法被修改 | 重跑 P4 |
| 核心结论被修改 | **必须**重跑 P5 + P6 |

不应全量重跑所有 P，只重跑受影响的。`scripts/apply_v_nnn.py` 的 `affected_p_tasks` 字段就是这一规则的可执行形式。

#### Step 5.1: 修订执行

按 `p7_revision_plan.yaml` 的 `execution_recommendation.step_1..4` 顺序执行：

1. **先关闭 P0**：按 P0-R4 要求，所有 P0 V-NNN 修复任务 priority=must
2. **按 priority_order 顺序**：conclusion > method > evidence > text
3. **侧效应检查**：每次 conclusion 类修订后做 p7-revision.md Step 6 检查
4. **触发重跑**：根据 `affected_p_tasks` 字段重跑相应 P
5. **P6 复评**：重跑完成后再次运行 P6，verdict 应在 P0/P1 全部关闭后升级

### Step 6: 交付

向用户报告：

1. **执行了哪些 P**，每个 P 的产物路径
2. **P6 最终 verdict** + 八个 DIM 分数
3. **P0/P1 缺陷清单**（最高优先级）
4. **如执行了 P7**：修订任务清单（V-NNN）和复评结论
5. **评价局限**：哪些材料未核查、哪些结论依赖有限证据

## 质量门禁（任何一步失败都应中止并报告）

1. **Artifact 完整性**：每个 P 输出必须可被 schema 解析
2. **ID 可追溯**：所有 D-NNN 必须能追溯到 C-NNN，所有 V-NNN 必须能追溯到 D-NNN
3. **P0 否决优先**：P6 检测到 P0 缺陷时，verdict 强制降级
4. **P5 独立性**：P5 输出不得大量重复 P2–P4 已有判断（重复率 > 50% 视为失职）
5. **不虚构**：任何 P 任务若发现无法核实的信息，必须标"待验证"，不得编造

## 子 Agent 工具集

| P 任务 | 工具 | 理由 |
| --- | --- | --- |
| P1 | Read | 只读 article + 解析 |
| P2 | Read, WebSearch, WebFetch | 文献核查需要联网 |
| P3 | Read | 主要是逻辑分析 |
| P4 | Read, Bash, WebFetch | 需要查代码 / 跑实验 / 拉官方文档 |
| P5 | Read, WebSearch, WebFetch | 需要独立检索 |
| P6 | Read | 综合判断 |
| P7 | Read, Edit, Write | 需要修订文章 |

## 参考文件

- `references/common-rules.md`：所有 P 任务的公共规则
- `references/id-conventions.md`：统一 ID 规则
- `references/p1-parse.md`：P1 prompt 模板
- `references/p2-literature.md`：P2 prompt 模板
- `references/p2_5-literature-supplement.md`：P2.5 prompt 模板（针对 P3 待验证项的补查）
- `references/p3-claim.md`：P3 prompt 模板
- `references/p4-method.md`：P4 prompt 模板
- `references/p5-adversarial.md`：P5 prompt 模板（skeptic 视角，OPT-16）
- `references/p5-practitioner.md`：P5 practitioner 视角（部署/工程实施，OPT-16）
- `references/p5-domain-expert.md`：P5 domain_expert 视角（同期工作/概念基础，OPT-16）
- `references/p6-synthesis.md`：P6 prompt 模板
- `references/p5-high-value-findings.md`：P5 高价值发现清单（价值评分 + 6 种模式 + P6 评估方法）
- `references/p7-revision.md`：P7 prompt 模板
- `references/domain-templates.md`：领域特定评估模板（CS / biomedical / economics / default / mixed）
- `scripts/merge_p5_ensemble.py`：P5 3 视角合并 + 共识升级 P0 建议（OPT-16）
- `templates/p1-output-schema.yaml` 至 `p7-output-schema.yaml`：每个 P 的结构化输出 schema

## 不做的事

- ❌ 不替用户决定 verdict。P6 给出推荐 verdict，但用户可基于 P0 缺陷清单独立判断。
- ❌ 不让 Subagent 之间直接对话。所有通信通过 artifact 文件。
- ❌ 不在 P 任务中"先入为主"评价。所有评价只能在 P6 综合时形成。
- ❌ 不省略 ID 引用。所有判断必须能点回到 C-/E-/D-/V-/DIM-。

## 端到端示例

完整运行案例见 `examples/llm-harmony-test/`（LLM Harmony arXiv:2401.01312）。
以下是该案例的简化 walkthrough，展示 article → verdict 的全链路。

### 1. 输入：article.md（节选）

> **LLM Harmony: Multi-Agent Communication for Problem Solving**
> Sumedh Rasal, Georgia Tech, 4 pages, 2024-01-02
>
> 提出基于 CAMEL 灵感的多 Agent 框架。
> 在 GSM8K/SVAMP/CSQA 报告 65%/77%/83% 准确率。
> 报告称"multi-agent 减少幻觉"和"cost-effective"。

### 2. P1 产物片段（`p1_object_model.yaml`）

```yaml
claims:
  - id: C-001
    text: "多 Agent + 角色扮演 + CoT 比单 Agent 更好"
    importance: core
  - id: C-002
    text: "相比 Multi-Agent baseline 提升"
    importance: core
  - id: C-003
    text: "inter-agent validation 减少幻觉"
    importance: core
  - id: C-007
    text: "cost-effective"
    importance: important

uncertainties:
  - location: "C-001"
    issue: "未报告具体模型、prompt、随机种子、运行次数"
    downstream_impact: "可复现性存疑"
```

### 3. P4 报告 P0 缺陷（`p4_method_review.yaml`）

```yaml
key_defects:
  - defect_id: D-201
    severity: P0
    related_claim_id: C-001
    brief_problem: "可复现性严重不足：模型/prompt/种子/运行次数均未报告"
    evidence: "GitHub 仓库名为 'simulation'，无完整代码"
```

### 4. P5 反方独立发现（`p5_adversarial.yaml`）

```yaml
new_defects:
  - defect_id: D-301-P5
    severity: P1
    related_claim_id: C-001
    brief_problem: "缺 self-consistency baseline（最强单 agent 对照）"
  - defect_id: D-302-P5
    severity: P1
    brief_problem: "collective delusion 风险未量化（M3MAD-Bench 65% 失败属此类）"
  - defect_id: D-303-P5
    severity: P2
    related_claim_id: C-007
    brief_problem: "6× 推理成本未量化"
  - defect_id: D-304-P5
    severity: P2
    brief_problem: "4-page workshop venue 限制未考虑"
  - defect_id: D-305-P5
    severity: P3
    related_claim_id: C-008
    brief_problem: "human intervention 实际是转移（从运行时到设计时）"
```

### 5. Orchestrator P0 预检（Step 3.5，`precheck_p0_defects.yaml`）

```yaml
precheck_p0_defects:
  - defect_id: D-201
    source_phase: P4
    related_claim_id: C-001
    brief_problem: "可复现性 P0"
precheck_summary:
  total_p0_count: 1
  has_p0: true
```

> ⚠️ 即使 P5 提议 D-302-P5 升级 P0，本次 precheck 仅按 P5 报告值（P1）处理。
> P6 在 `p5_proposed_p0_decisions` 字段中显式记录此决策（参见 R2.1）。

### 6. P6 综合评审（`p6_synthesis.yaml` 片段）

```yaml
eight_dimension_scores:
  - dim_id: DIM-04   # 可复现性
    score: 1
    score_anchors: "1=严重不足：模型、prompt、种子、运行次数均未报告"
    main_defects: [D-201, D-202, D-203, D-204]

precheck_p0_summary:
  input_p0_count: 1
  addressed_p0_ids: [D-201]
  unaddressed_p0_ids: []
  precheck_input_was_empty: false

final_verdict:
  verdict: insufficient_evidence
  rationale: |
    P4 报告 D-201 为 P0 → 触发 P0-R2 强制降级 → verdict = 5 或 6。
    本次选 verdict 6 (insufficient_evidence) 而非 5 (core_falsified)，
    因为修复 P0 缺陷后（公开复现）可能升级。
  p0_veto_triggered: true
  p0_veto_rules_checked: [P0-R1, P0-R2, P0-R3, P0-R4, P0-R5]
```

### 7. P0 硬规则（P0-R1 至 P0-R5）触发的简化示例

| 规则 | 检查 | 本例是否通过 |
| --- | --- | --- |
| P0-R1 | 所有 P0 缺陷必须在 `critical_defects` 中显式列出 | D-201 ✓ |
| P0-R2 | 若 `input_p0_count > 0`，verdict 必须是 5 或 6 | verdict=6 ✓ |
| P0-R3 | 每个 P0 缺陷必须含 `affected_claims` / `impact_scope` / `fix_requirement` | D-201 三项齐 ✓ |
| P0-R4 | 每个 P0 缺陷必须对应 `priority=must` 的 V-NNN 修订任务 | V-001-LLMH ✓ |
| P0-R5 | rationale 不得以 DIM 平均分冲销 P0 缺陷 | 未出现 "average" ✓ |

### 8. 6 种 verdict 判定条件（简化版）

| # | verdict | 触发条件 |
| --- | --- | --- |
| 1 | 核心结论获得充分支持 | 无 P0/P1，8 个 DIM 平均 ≥ 4，关键 claim 全部 supported |
| 2 | 核心结论基本成立，部分需收缩 | 无 P0，仅少量 P2/P3，部分 claim 需窄化 |
| 3 | 核心结论部分成立，仍需补充关键证据 | 无 P0，P1 缺陷集中在"补实验/补引用"可解决的范围 |
| 4 | 核心结论尚未得到充分验证 | 无 P0，但 P1 缺陷为方法论级别（需重新设计实验） |
| 5 | 核心结论因关键缺陷而不成立 | P0 缺陷导致"现有证据反向证伪核心结论" |
| 6 | 证据不足，暂时无法作出可靠判断 | P0 缺陷是"可复现性"或"信息缺失"类（修复后可能升级） |

本例 P0 = 可复现性（修复后可能升级）→ verdict 6 而非 5。

### 9. P5 价值的判定

`p6_synthesis.yaml` 的 `p5_value_assessment` 字段应记录 P5 是否真的找到
P2-P4 漏掉的问题。判定标准：

- P5 至少 3 个 `new_defects` 是 P2-P4 漏掉的（本研究 5/5 通过）
- 至少 1 个 new_defect 与"乐观叙事掩盖的反向风险"相关
- P5 提议升级 P0 的建议被 P6 显式处理（接受/拒绝/降级，记录理由）

## P1 稳定性自检

完成 P1 后**强烈建议**跑 `scripts/eval_p1_consistency.py` 验证稳定性。
同一篇文章两次 P1 跑 C-NNN 集合重合度应 ≥ 0.8。

```bash
python scripts/eval_p1_consistency.py run-A/p1.yaml run-B/p1.yaml
# Verdict: [✓] high_consistency (ID Jaccard=0.867) → P1 输出稳定
# Verdict: [~] moderate_consistency (ID Jaccard=0.647) → 检查 P1 prompt 歧义
# Verdict: [?] different_articles (avg_text_sim=0.142) → 错误输入
```

## P2 文献核查缓存（OPT-13）

同领域多篇论文评估时，P2 的引用核查结果可缓存复用。
新增 `scripts/cache_p2.py`，4 个子命令：

```bash
# 添加核查记录
python scripts/cache_p2.py add \
  --title "CAMEL: Communicative Agents..." --authors "Li et al." --year 2023 \
  --verified true --source-url "https://arxiv.org/abs/2303.17760" \
  --credibility high --quote "..." --finding "..."

# 查询（命中则显示缓存内容）
python scripts/cache_p2.py query --title "CAMEL: ..." --authors "Li et al." --year 2023

# 合并 P2_OUTPUT（自动用 cache 补全命中引用）
python scripts/cache_p2.py merge --p2 runs/.../p2.yaml --out runs/.../p2_merged.yaml

# 统计
python scripts/cache_p2.py stats
```

**缓存 key**：`SHA256(normalize(title) + first_author + year)`。
`first_author` 提取"et al."之前部分，所以 "Li, Wang, et al." 和 "Li et al." 命中同一 key。

**合并策略**：
- 当前 `verification_status` 为 `pending`/`unverified` → 覆盖为 cache 的 verified/refuted
- 当前为 `verified`/`refuted` → 保留（信任本地人工判断，不被 cache 覆盖）
- `source_url` / `source_credibility` / `quote` 用 `setdefault` 填充
- 加 `_cache_hit` 字段记录命中的 key / 时间 / hit_count

**典型命中场景**：LLM 领域多篇论文都引用 CAMEL / ToT / ReAct，第一次 P2 跑核查后，第二次起 P2 直接读 cache（每次省 1-2 次 WebSearch）。

**存储位置**：`cache/p2_cache.json`（自动创建）。
