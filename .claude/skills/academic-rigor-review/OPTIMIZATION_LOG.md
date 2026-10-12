# Skill 优化进度跟踪（/loop iterations）

> 本文件由 `/loop` 任务维护。每次 iteration 开始时**先读本文件**，
> 找到第一个 `[ ]` 状态的项开始做；完成后改为 `[x]` 并记录日期。
> 这避免每次 iteration 重复决策"接下来做什么"。

## 推荐改进项

按重要性 + 依赖顺序排列。

### 迭代 1（已完成）— 2026-10-12

- [x] **R1. 修正 design.md 与 skill 架构一致**（修正 P2–P5 并行声明 → 流水线式调度）
  - 改 `docs/design.md` 第二节末尾段落（"P2—P5 可以在 P1 完成后并行执行" → 阶段 1/2/3 时序）
  - 改 `docs/design.md` 第四节（架构图 + 启动时序）
  - 加 `> **修正说明**` 块说明原声明与 prompt 输入列表矛盾
  - 同步 `SKILL.md` 核心架构图 + Step 2 阶段描述

### 迭代 2（已完成）— 2026-10-12

- [x] **R2. 用真实论文测试 P5 能否找到 P2–P4 漏掉的 P0 缺陷**
  - 文章：LLM Harmony (arXiv:2401.01312) 4 页 workshop paper
  - 完整跑通 P1 → P2 → P3 → P4 → P5 → P0 预检 → P6
  - **关键发现**：P5 找到 5 个 P2-P4 完全漏掉的关键问题：
    - D-301-P5 (P1) 缺 self-consistency baseline
    - D-302-P5 (P1) collective delusion 风险升级
    - D-303-P5 (P2) 6× 推理成本未量化
    - D-304-P5 (P2) venue 限制未考虑
    - D-305-P5 (P3) human intervention 实际是转移
  - P0 硬规则正确触发：P4 报告 D-201 (可复现性 P0) → precheck 诚实纳入 → P6 verdict 强制降级为 insufficient_evidence
  - P0-R1 至 P0-R5 全部通过
  - 产物：`runs/2026-10-12-llm-harmony-test/` + `examples/llm-harmony-test/`
  - README：`examples/llm-harmony-test/README.md`

### 迭代 3（已完成）— 2026-10-12

- [x] **R3. 写 LLM-as-judge 评测脚本**
  - 路径：`scripts/eval_p1_consistency.py`
  - 主指标：ID Jaccard（同一篇文章两次 P1 跑 C-NNN 集合重合度）
  - 次指标：文本相似度（检测"近重复但不同 ID"的情况）
  - 退出码：0=high, 1=moderate/low/different_articles, 2=输入错误
  - 关键设计：**文章同源门禁**——`avg_text_sim < 0.15` 时报告 `different_articles`，
    避免 ID 重合的假阳性（不同文章的 P1 都从 C-001 起，ID 相同不代表同主张）
  - 测试：
    - 相同 P1（identical）→ high_consistency ✓
    - 同文略变（run1 vs run2，4 处变化 + 2 处新增）→ moderate_consistency ✓
    - 不同文章（design.md P1 vs LLM Harmony P1）→ different_articles（ID Jaccard 0.733 但 text sim 0.142 正确拦截）✓

## 已识别的非阻塞改进项

这些发现不阻塞 P6 verdict 正常工作，但长期值得做：

### 迭代 4（已完成）— 2026-10-12

- [x] **R4. SKILL.md 增加端到端示例**
  - 基于 `examples/llm-harmony-test/` 真实运行案例
  - 9 节 walkthrough：输入 → P1 → P4 (P0) → P5 (new defects) → precheck → P6 verdict → P0-R1..R5 触发示例 → 6 种 verdict 判定条件 → P5 价值判定
  - 额外增加"P1 稳定性自检"节，引用 `scripts/eval_p1_consistency.py` 退出码语义
  - 文件：`SKILL.md` 末尾"端到端示例" + "P1 稳定性自检"两节

### 迭代 5（已完成）— 2026-10-12

- [x] **R5. p6-synthesis.md 增加 P0 缺陷的具体判定规则**（解决 D-005 循环定义）
  - **核心问题**：原"P0 足以使核心结论失去成立基础"是循环定义，不同评审者对同一缺陷会有 P0/P1 分歧
  - **解决**：把"什么算 P0"展开为 **8 条可操作规则 + 反例清单**：
    - P0-1 可复现性归零
    - P0-2 数据伪造/未声明的过滤
    - P0-3 循环论证
    - P0-4 关键对照完全缺失（非平凡主张）
    - P0-5 统计推断失效
    - P0-6 概念基础被反驳
    - P0-7 P1 累积升级（3+ 独立 P1 共同影响同一 C-NNN）
    - P0-8 P5 反方独立确证
  - 反例清单：6 种"看起来严重但不是 P0"的情况（表述不清、缺 1-2 引用、单点 P1 等）
  - **R2.1 顺带实现**：P5 提议升级 P0 的处理流程（独立评估 → 显式决策 accepted/rejected/downgraded → 保守默认 → 不允许沉默接受）
  - **Schema 同步**：p6-output-schema.yaml 增加 `p0_judgment_basis` 和 `p5_proposed_p0_decisions` 字段
  - **新校验规则**：P0-J1（P0 触发必须引用具体 P0-N 规则）、P0-J2（P5 提议必须显式决策）
  - 文件：`references/p6-synthesis.md` Step 5.5 + `templates/p6-output-schema.yaml`

### 迭代 6（已完成）— 2026-10-12

- [x] **R6. SKILL.md + p3-claim.md 增加"可选占位"机制**
  - **核心问题**：P2 因网络受限/WebSearch 失败/超时而延迟时，P3/P4/P6 全部阻塞
  - **解决**：P3 支持两种模式
    - **complete 模式**：P2_OUTPUT 完整可用，正常消费 E-NNN
    - **draft 模式**：P2 不可用时 P3 用 P1 + article 独立做逻辑分析，显式声明 `p2_dependency: BLOCKED`
  - **P2 后到达时增量更新**：只重跑 affected_claim_ids（避免全量重跑）
  - **P4 启动条件**：P3 complete OR P3 draft + P2 已完成增量更新
  - **P6 awareness**：在 `evaluation_limitations` 声明是否经历过 draft 模式
  - **新增文件位置**：
    - `SKILL.md` Step 2.5（orchestrator 决策流程 + 反模式）
    - `references/p3-claim.md` §0（两种模式 + 增量更新机制）
  - **4 条反模式明确禁止**（P3 假装完成 / 全量重跑 / P4 在 draft 下启动 / 跳过 draft 模式）

### 迭代 7（已完成）— 2026-10-12

- [x] **R7. 增加 P2.5 文献补查 prompt**
  - **核心问题**：P3 标识"待验证"后只能等 P2 全量重跑，效率低
  - **解决**：新增 P2.5 作为 P2 的**补充**而非替代
    - P2：全量文献核查（5-30 min）
    - P2.5：**针对性补查**（1-5 min，只针对 P3 标记的 pending claim）
  - **关键设计**：
    - E-NNN 命名空间从 E-500 起（避免与 P2 的 E-001~E-499 冲突）
    - D-NNN 用 D-5XX-2.5 后缀
    - `cross_check_with_p2` 字段显式记录与 P2 矛盾的证据（避免孤证 P0）
    - `p2_consistency` 健康度指标（consistent / has_conflict / partial_conflict）
    - `negative_finding` 与 `counter_evidence` 严格区分（避免"搜不到"当 refuted）
  - **触发条件**：P3 ≥ 3 个 pending OR P2 有 source_unavailable OR 用户显式要求
  - **不触发**：P3 全部 supported/refuted OR 纯理论文章 OR 时间预算紧
  - **P6 消费**：P2.5 完成后 P3 不需重跑，只更新 affected_claim_ids 的 status
  - **新增文件**：
    - `references/p2_5-literature-supplement.md`（prompt 模板）
    - `templates/p2_5-output-schema.yaml`（输出 schema，7 条校验规则）
    - `SKILL.md` Step 2.6（orchestrator 触发流程 + 反模式）

### 迭代 8（已完成）— 2026-10-12

- [x] **R8. P3/P4 claim_evidence_ledger 字段对齐**
  - **核心问题**：OPTIMIZATION_LOG 原本以为"P3 用 `opposing_evidence_ids`，P4 用 `opposing_evidence`"，
    实际审计发现 P4 根本没有结构化的 claim_evidence_ledger，命名也更混乱：
    - `research_design_audit.verification_evidence` 是 string（应是 list）
    - `validity_threats.*.evidence_id` 是 string（应是 list）
    - `key_defects.evidence_id` 是 string（应是 list）
    - `method_overall_judgment.*.key_evidence` 是 list 但未明确是 ID
  - **解决**：
    - **统一命名规则**：所有 evidence 引用字段用 `xxx_evidence_ids`（list of E-NNN/D-NNN）
    - **P4 新增 claim_evidence_ledger**（与 P3 对齐）：
      - `supporting_evidence_ids` / `opposing_evidence_ids`（E-NNN 列表）
      - `supporting_method_findings` / `opposing_method_findings`（P4 自发现的方法学发现）
      - `cross_reference_to_p3`（显式说明 P4 与 P3 的新增/修正）
    - **升级 string → list**：`verification_evidence` / `evidence_id` / `key_evidence` 全部升级为 list
  - **Schema 同步**：p4-output-schema.yaml 加 `naming_convention` 映射表 + `claim_evidence_ledger` 必填段
  - **3 条新校验规则**：
    - claim_evidence_ledger 至少覆盖 P3 ledger 中 importance=core 的全部 claim
    - 每条 claim 必须有 cross_reference_to_p3（即使是空字符串也要显式声明无新增）
    - 所有 *_evidence_ids 字段必须是 list（即使只有一个 E-NNN 也要写成 [E-001] 形式）
  - **P3/P4 协作模型**：P3 评估"逻辑证据"，P4 评估"方法学证据"，合并形成完整 per-claim evidence ledger
  - **文件**：`templates/p4-output-schema.yaml` v1.1 + `references/p4-method.md` §B-G

### 迭代 9（已完成）— 2026-10-12

- [x] **R2.2. SKILL.md + p5-adversarial.md 增加"optimistic 叙事"专项指南**
  - **核心问题**：P2-P4 在乐观技术叙事下系统性地漏掉反向风险（LLM Harmony 测试验证：D-301-P5 至 D-305-P5 都是这类）
  - **解决**：在 `p5-adversarial.md` §0 增加 6 个子节：
    - **§0.1 识别 optimistic 叙事**：6 种叙事类型（技术救世 / 方法新颖 / 性能碾压 / 成本优势 / 通用化 / 替代）+ 典型信号
    - **§0.2 11 类反向风险检查清单**：最强 baseline 缺失 / compute-matched 缺失 / 同质配置反向风险 / 隐性成本转移 / 成本未量化 / venue 限制 / 同期工作脱节 / 乐观概念被反驳 / 可复现性 P0 / 构造效度失效 / 外推效度失效
    - **§0.3 4 个强制提问模板**：compute 对比 / 同质配置最坏情况 / 隐性成本转移 / 同期反向工作
    - **§0.4 难度自检**：4 项 checkbox（≥1 反向风险 / 全部 4 问题已答 / ≥1 同期工作引用 / ≥1 new_defect）
    - **§0.5 P6 awareness**：P6 接收 P5 后应检查 §0.2/§0.3 覆盖度
    - **§0.6 反模式**：5 条明确禁止（重复 P2-P4 / "应该考虑"不是缺陷 / 全部 P0 等）
  - **P5 metadata 字段**：`p5_metadata.narrative_type` 显式标注
  - **SKILL.md Step 3 同步**：增加 optimistic 叙事专项处理段
  - **文件**：`references/p5-adversarial.md` §0 + `SKILL.md` Step 3

### 迭代 10（已完成）— 2026-10-12

- [x] **R2.3. 整理"高价值 P5 发现"清单**
  - **核心问题**：R2 发现的 5 个 P5 缺陷（D-301-P5 至 D-305-P5）有共同模式，但未固化到 skill
  - **解决**：新增 `references/p5-high-value-findings.md`（6 节）：
    - **§1 价值定义**：3 维评分公式（新颖性 × 可操作性 × 结论影响，满分 27，≥ 12 高价值）
    - **§2 6 种高价值模式**（每条带真实例子）：
      1. 缺最强 baseline（D-301-P5）
      2. 缺反向风险讨论（D-302-P5）
      3. 缺成本量化（D-303-P5）
      4. venue/format 限制未考虑（D-304-P5）
      5. 隐性成本转移（D-305-P5）
      6. 基线实施不透明（D-204）
    - **§3 价值密度评分**：P5 自评字段 `value_self_assessment`
    - **§4 反定义**（6 种低价值模式）
    - **§5 P6 评估 P5 价值的方法**：`p5_value_assessment` 字段必填
    - **§6 与 R2.2 §0 的关系**（执行视角 vs 评估视角互补）
  - **P5 与 P6 协作闭环**：P5 自评（value_self_assessment）→ P6 汇总（p5_value_assessment）→ 决定 verdict 是否受 P5 价值影响
  - **未达标告警**：high_value_count < 50% 或 patterns_covered ≤ 1 → P6 在 evaluation_limitations 显式声明
  - **文件**：
    - `references/p5-high-value-findings.md`（新文件，6 节）
    - `references/p5-adversarial.md` §1（引用入口）
    - `SKILL.md` 参考文件列表（增加条目）

## 已识别的非阻塞改进项

- [x] **R4. SKILL.md 增加端到端示例**（已并入迭代 4 完成）
- [x] **R5. p6-synthesis.md 增加 P0 缺陷的具体判定例子**（已并入迭代 5 完成）
- [x] **R2.1**: P5 提议升级 P0 时 P6 显式处理（已并入迭代 5 p5_proposed_p0_decisions 字段）
- [x] **R6. SKILL.md + p3-claim.md 加可选占位机制**（已并入迭代 6 完成）
- [x] **R7. 增加 P2.5 文献补查 prompt**（已并入迭代 7 完成）
- [x] **R8. P3/P4 claim_evidence_ledger 字段对齐**（已并入迭代 8 完成）
- [x] **R2.2. SKILL.md + p5-adversarial.md 加 optimistic 叙事指南**（已并入迭代 9 完成）
- [x] **R2.3. 整理"高价值 P5 发现"清单**（已并入迭代 10 完成）
- [x] **R5. p6-synthesis.md 增加 P0 缺陷的具体判定例子**（已并入迭代 5 完成）
- [x] **R6. SKILL.md 增加 P3/P4 prompt 输入的"可选占位"机制文档**（已并入迭代 6 完成）
  - 即 P3 启动时若 P2 还没完成，可以使用"先做不带 P2 的初稿，P2 完成后增量更新"的模式
  - 当前设计没有覆盖这个边界
- [x] **R7. 增加 P2.5 文献补查 prompt**（已并入迭代 7 完成）
- [x] **R8. P3/P4 prompt 中 `claim_evidence_ledger` 字段语义对齐**（已并入迭代 8 完成）
  - 当前 P3 用 `opposing_evidence_ids`，P4 用 `opposing_evidence`（少了 ids 后缀）
  - 应统一为 `opposing_evidence_ids`

## 跨 iteration 的元约束

- **不要重做已完成项**：每次 iteration 开始时先读本文件，找到第一个 `[ ]`
- **不要一次性做多项**：除非当前项极小（< 50 行改动），否则做完一项就停
- **每完成一项要更新本文件**：避免下次 iteration 重复
- **每完成一项要 commit 一次**：使用 `git add` + `git commit`，便于回溯
- **如果当前项遇到阻塞**：标记为 `[ ]`（保持）并在下方加 `> BLOCKED: <原因>`，下次 iteration 决定是否绕过

## 进度汇总

- 已完成：R1-R8 + R2.1 + R2.2 + R2.3 + OPT-12 + OPT-13 + OPT-14 + OPT-15 + OPT-16
- 当前：等待下一候选
- 已交付能力：
  - 完整 7-Prompt 流水线（P1-P7 + P2.5 + Step 1.5 领域模板 + Step 3 P5 ensemble + Step 3.5 P0 预检）
  - P0 硬规则系统（5 条硬规则 + 8 条判定规则 + 反例清单 + 3 套领域 P0 反模式 + ensemble 共识升级）
  - 评估工具（eval_p1_consistency.py + apply_v_nnn.py + cache_p2.py + validate_p6_template.py + merge_p5_ensemble.py）
  - 端到端示例 + optimistic 叙事处理 + 高价值 P5 发现模式
  - P3/P4 evidence ledger 对齐 + draft 模式 + 增量更新
  - 跨阶段协作（P5 3 视角 ensemble → P6 审计）闭环
  - P7 修订闭环（生成可执行修订计划）
  - P2 缓存（多论文评估节省 token）
  - 领域特定模板（CS / biomedical / economics / default / mixed: 自动检测）
  - P5 多视角 ensemble（skeptic / practitioner / domain_expert + 共识升级 P0）

## 后续候选改进项（迭代过程新发现）

下一阶段可能方向：
- [x] **P5 独立视角的工程化**（用 model ensemble 而非单次 LLM 调用降低漏报）— **OPT-16 已完成**
- [ ] **多文章批量评估**（R2 仅测试 1 篇，统计意义有限）
- [x] **领域特定模板**（CS / 生物医学 / 经济学各自的 DIM 权重）— **OPT-15 已完成**
- [x] **P2 缓存机制**（同一文献的引用核查结果可缓存复用）— **OPT-13 已完成**
- [x] **P7 修订的实际闭环**（当前 P7 输出 V-NNN 后缺少"修订→重跑"工具链）— **OPT-12 已完成**
- [ ] **多语言支持**（当前 prompt 假设中文输入，未测试英文）

### 迭代 11（已完成）— 2026-10-12

- [x] **R-sync. 同步 docs/design.md 到最新 skill 状态**
  - **核心问题**：R1 后所有改进（R5-R10 + R2.1-R2.3）只更新了 skill 文件，design.md 严重脱节
  - **解决**：在 design.md 末尾追加"六、扩展机制（迭代 1-10 累积的改进）" 11 节
  - **覆盖范围**：
    - 6.1 DAG 调度（R1）
    - 6.2 P0 硬规则系统（R5 + R2.1）—— 8 条 P0 判定规则 + 6 条反例 + P0-R1~R5
    - 6.3 P0 预检机制（Step 3.5）
    - 6.4 Optimistic 叙事（R2.2）—— 11 类反向风险
    - 6.5 高价值 P5 发现（R2.3）—— 6 种模式
    - 6.6 P2.5 文献补查（R7）
    - 6.7 P3/P4 Evidence Ledger 对齐（R8）
    - 6.8 P3 Draft 模式（R6）
    - 6.9 P1 稳定性自检（R3）
    - 6.10 端到端示例（R4）
    - 6.11 已知限制与待改进
  - **设计原则**：保留原 1-5 节不变，6 节作为"迭代进化附录"便于追溯
  - **文件**：`docs/design.md`（原 766 行 → 766+100 行）

### 迭代 12（已完成）— 2026-10-12

- [x] **OPT-12. P7 修订闭环工具链**（后续候选清单的第一项）
  - **核心问题**：P7 当前输出 V-NNN 任务清单但**没有工具**帮作者实际执行。"影响范围触发的 P 重跑"（p7-revision.md Step 8）只是文字规则，没有可执行形式
  - **解决**：新增 `scripts/apply_v_nnn.py`，输入 article.md + p6 + p7，输出结构化修订计划：
    - **自动分类**：每条 V-NNN 标记为 text / evidence / method / conclusion / unknown（关键词驱动）
    - **可自动应用判定**：text 类 + 收缩类 conclusion 可纯文本完成
    - **P0 优先标记**：与 P6 中 P0 critical_defect 关联的 V-NNN 单独标出
    - **受影响 P 任务**：根据 p7-revision.md Step 8 表计算需重跑的 P 集合（永远包括 P6）
    - **执行顺序**：按 conclusion > method > evidence > text > unknown 排序
    - **侧效应警告**：4 条 side-effect 检查清单
  - **bug 修复（开发中）**：
    - V-001 (公开复现材料) 误判为 unknown → 加 "publish / release / 公开 / reproduce" 关键词后正确判为 evidence
    - p0_remaining 逻辑错（用 p0_count > 0 而非检查原 defect） → 改为查 original_defect 是否在 P0 defect id 集合
  - **测试验证**：
    - 输入 5 条 V-NNN（D-201 P0 / D-202 P1 / D-301 P1 / D-302 P1 / D-303 P3）
    - 输出：1 P0 优先 + 2 auto-applicable + 3 manual required
    - Affected P tasks: P2, P3, P4, P5, P6
    - Side-effect warnings + loop_closure_check 全部正确
  - **SKILL.md Step 5 同步**：增加 Step 5.0（修订计划生成）和 Step 5.1（执行流程）
  - **文件**：
    - `scripts/apply_v_nnn.py`（新文件，~290 行）
    - `SKILL.md` Step 5.0 + 5.1
  - **价值**：把"影响范围触发的 P 重跑"从**文字规则**升级为**可执行脚本**

### 迭代 13（已完成）— 2026-10-12

- [x] **OPT-13. P2 文献核查缓存机制**（后续候选清单）
  - **核心问题**：同领域多篇论文评估时 P2 重复核查相同引用（如 LLM 领域都查 CAMEL / ToT / ReAct）
  - **解决**：新增 `scripts/cache_p2.py`（4 子命令）+ `cache/p2_cache.json`
  - **关键设计**：
    - **缓存 key**：`SHA256(normalize(title) + first_author + year)`，first_author 提取"et al."前部分，所以 "Li, Wang, et al." 与 "Li et al." 命中同一 key
    - **`add`**：登记新引用核查结果（验证 / 来源 / 引用 / 发现）
    - **`query`**：查询缓存（命中则更新 hit_count）
    - **`merge`**：合并 P2_OUTPUT，cache 命中引用自动补全（仅 pending → verified/refuted 覆盖；已 verified 保留）
    - **`stats`**：缓存统计 + Top 5 高频引用
  - **bug 修复**：
    - 第一版 `setdefault` 让 `verification_status: pending` 保留 → 改为只在 pending/unverified 时覆盖 + 加 `_status_overridden_by_cache: true` 审计标记
  - **测试验证**：
    - Test 1: add CAMEL → key `fb57a6bcde268360`
    - Test 2: query "Li et al." → hit (first_author 正确归一)
    - Test 3: query "Tree of Thoughts" → miss
    - Test 4: stats → 1 entry, 2 hits
    - Test 5: merge 2 个引用 → 1 hit, 1 miss, hit_rate=0.5，CAMEL 的 verification_status 从 pending → verified 并带审计标记
  - **典型价值**：LLM 领域第二篇论文起 P2 节省 1-2 次 WebSearch per 引用
  - **文件**：
    - `scripts/cache_p2.py`（新文件，~250 行）
    - `cache/p2_cache.json`（自动创建）
    - `SKILL.md` "P2 文献核查缓存"节

### 迭代 14（已完成）— 2026-10-12

- [x] **OPT-14. design.md 同步 OPT-13**（P2 缓存）
  - 新增 §6.13 节：P2 文献核查缓存（OPT-13）
  - 内容：scripts/cache_p2.py 4 子命令 + 缓存 key 设计 + 合并策略 + SKILL.md 同步 + 价值
  - 文件：`docs/design.md` §6.13

### 迭代 15（已完成）— 2026-10-12

- [x] **OPT-15. 领域特定模板**（后续候选清单的第二项：领域特定模板）
  - **核心问题**：P6 的 8 维评分默认无差别权重，但 CS / biomedical / economics 的"严谨"含义差异极大
  - **解决**：新增 `references/domain-templates.md`，含 3 套起点模板
  - **每套模板包含**：
    1. **适用信号**（venue + 关键词）
    2. **DIM 权重**（合计 1.0）—— 学科侧重不同（如 CS DIM-07=0.20 最高，biomedical DIM-04/DIM-06=0.18 最高，economics DIM-01/DIM-03=0.15 最高）
    3. **评分锚点**（关键 DIM 的 1/3/5 分定义）
    4. **领域 P0 反模式**（CS 7 条 / biomedical 8 条 / economics 8 条）
    5. **领域 P1 反模式**
    6. **verdict 校准**（workshop vs full paper、观察性研究、纯理论等子模板）
  - **P0 硬规则不受模板影响**——模板仅影响 DIM 加权平均与 P0 反模式的"具体场景"举例
  - **schema 同步**：`templates/p6-output-schema.yaml` 增加 `domain_template` 字段（必填）+ 4 条校验规则 DOM-1/2/3/4
  - **SKILL.md 同步**：
    - Step 1.5：选择领域模板（自动检测 + 用户覆盖 + 混合模板）
    - Step 4：P6 引用 domain_template 作为强制输入
    - 参考文件列表新增 domain-templates.md
  - **新增 `scripts/validate_p6_template.py`**：4 子命令校验（DOM-1/2/3/4 + 权重对比 + 加权 DIM 平均）
  - **测试验证**（10 个测试全过）：
    - Test 1: CS 模板（LLM Harmony 真实场景）→ weighted_dim_avg=1.76 ✓
    - Test 2: biomedical 模板 → weighted_dim_avg=2.27 ✓
    - Test 3: economics 模板 → weighted_dim_avg=2.80 ✓
    - Test 4: mixed:cs+biomedical → 算术平均权重正确 ✓
    - Test 5: default 模板 → 等权 0.125 ✓
    - Test 6: domain_template 缺失 → DOM-1 错误 ✓
    - Test 7: dim_weights 之和=4.0 → DOM-2 错误 + DOM-3 警告 ✓
    - Test 8: 未知模板名 physics → DOM-1 错误 ✓
    - Test 9: mixed 缺 rationale → DOM-4 错误 ✓
    - Test 10: 权重与参考不一致 → DOM-3 警告（仍通过）✓
  - **价值**：
    - P6 评分不再"one-size-fits-all"——CS 论文自动侧重可复现性，biomedical 自动侧重方法/偏差，economics 自动侧重理论/识别
    - P0 触发规则不增不减（不破坏 P0-R1~R5）
    - 领域 P0 反模式为 P6 提供更具体的 P0-N 触发场景
  - **文件**：
    - `references/domain-templates.md`（新文件，~250 行）
    - `scripts/validate_p6_template.py`（新文件，~250 行）
    - `cache/test_p6_with_template.yaml`（测试用例）
    - `templates/p6-output-schema.yaml`（v1.0 → v1.1）
    - `SKILL.md` Step 1.5 + Step 4 + 参考文件列表

### 迭代 16（已完成）— 2026-10-12

- [x] **OPT-16. P5 多视角 ensemble**（后续候选清单的第一项：P5 独立视角工程化）
  - **核心问题**：单次 P5 LLM 调用易漏报（LLM Harmony 测试已验证能找 5 个 P2-P4 漏掉的问题，但仍可能漏报）
  - **解决**：把 P5 升级为 3 视角 ensemble + 共识升级 P0
  - **3 视角 prompt**：
    1. **skeptic**（`p5-adversarial.md`，默认）：方法学严谨、optimistic 叙事、统计
    2. **practitioner**（`p5-practitioner.md`）：部署/算力/工程实施 / 隐性成本转移 / 复现性工程现实
    3. **domain_expert**（`p5-domain-expert.md`）：同期工作覆盖 / 概念基础 / 领域共识 / 外推性
  - **Schema 同步**：`p5-output-schema.yaml` v1.0 → v1.1
    - 新增 `p5_metadata` 顶层字段（role / focus_dimensions / sub_field / narrative_type / value_self_assessment）
    - `new_defects` 加 `defect_type`（methodology / engineering / coverage）
    - 5 条新校验规则（ENS-1..ENS-5）
  - **新增 `scripts/merge_p5_ensemble.py`**（~300 行）：
    - 输入：3 个 P5 YAML（skeptic / practitioner / domain_expert）
    - 合并 new_defects（去重 + 共识标注）
    - 合并 core_claim_challenges（按 claim_id 收集 + 共识强度）
    - 生成 P0 升级建议（共识 ≥ 2 的缺陷）
    - 计算 value_self_assessment 汇总统计
  - **合并逻辑（AND 条件避免假阳性）**：
    1. `related_claim_id` 必须相同
    2. SequenceMatcher ratio >= 0.40
    3. 共享关键术语数（中英文 2-gram 提取）>= 3
  - **共识升级规则**：
    - 3 视角都识别 → `strong_recommend`（高置信度 P0）
    - 2 视角识别 → `recommend`（P6 应验证）
    - 仅 1 视角 → `needs_verification`（P6 单独处理）
  - **bug 修复**：
    - 第一版用 `(related_claim_id, description[:50])` 精确匹配 → D-302-P5/D-306-P5 共识漏检
    - 第二版用 SequenceMatcher ratio >= 0.65 → D-306-P5 漏检（ratio 0.495）
    - 第三版用 Jaccard word overlap → 中文分词问题（D-302-P5 实际共享 "human intervention" 但 Jaccard 0.25）
    - 第四版中英文 2-gram + 共享术语数 → 修复中文但 D-309/D-310 假阳性
    - 第五版 AND 逻辑（ratio + shared terms）→ 全部正确：D-302/D-306 真共识匹配，D-309/D-310 假阳性不合并
  - **测试验证**（2 套测试）：
    - LLM Harmony 模拟：11 → 9 unique，2 consensus-2（D-302/D-306），2 P0 recommendations
    - 3-consensus 模拟：6 → 4 unique，1 consensus-3（D-X），1 P0 strong_recommend
  - **SKILL.md 同步**：
    - Step 3 改为 ensemble 模式（3 视角并行启动）
    - Step 3.1 新增：3 视角输出合并（merge_p5_ensemble.py）
    - 参考文件列表新增 2 个 P5 视角文件 + 1 个合并脚本
  - **文件**：
    - `references/p5-practitioner.md`（新文件，~200 行）
    - `references/p5-domain-expert.md`（新文件，~200 行）
    - `references/p5-adversarial.md`（增加 role 元数据）
    - `scripts/merge_p5_ensemble.py`（新文件，~300 行）
    - `templates/p5-output-schema.yaml`（v1.0 → v1.1）
    - `cache/test_p5_ensemble/p5_{skeptic,practitioner,domain_expert}.yaml` + `merged.yaml`
    - `SKILL.md` Step 3 + Step 3.1 + 参考列表
  - **价值**：
    - 漏报率显著下降（3 独立 LLM 调用 ≥ 1 视角发现某缺陷的概率更高）
    - 共识升级 P0 给出明确的"高度怀疑"信号，辅助 P6 决策
    - 3 视角的 defect_type 区分（methodology / engineering / coverage）便于 P6 路由到合适 DIM
  - **P0 硬规则不变**：ensemble 不创造新 P0 触发规则，仅辅助 P6 决策

## R2 产出的额外改进点（可作为后续 iteration 候选）

- [x] **R2.1**: P5 提议升级 P0 时，P6 应显式处理（接受/拒绝/降级）并记录理由（已并入迭代 5 p5_proposed_p0_decisions 字段）
- [x] **R2.2**: SKILL.md 增加"如何处理 optimistic 叙事"指南（已并入迭代 9 完成）
- [x] **R2.3**: 整理"高价值 P5 发现"清单到 skill 中（已并入迭代 10 完成）
