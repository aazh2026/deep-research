# P5: 独立反方挑战 Prompt（practitioner 视角，OPT-16）

> **关键约束**：P5 是这个工作流中最重要的反方环节。本文件是 P5 ensemble 中的 **practitioner 视角**。
> 1. 注入 `references/common-rules.md` 作为 system prompt 前缀
> 2. 替换 `{{ARTICLE}}` 和 `{{P1_OUTPUT}}`
> 3. **P5 默认只接收 P1 + article，不接收 P2/P3/P4 的判断**
> 4. 启动 Subagent，工具集 = Read + WebSearch + WebFetch

> **与其他视角的关系**：
> - `references/p5-adversarial.md`：skeptic 视角（方法学严谨、optimistic 叙事）
> - `references/p5-domain-expert.md`：domain_expert 视角（同期工作、概念基础）
> - 3 视角产出由 `scripts/merge_p5_ensemble.py` 合并

---

# 任务：从实际部署与工程实施角度挑战文章

## 输入（严格遵守以下输入边界）

- 待评价文章：`{{ARTICLE}}`
- P1 研究对象模型：`{{P1_OUTPUT}}`
- ~~P2 / P3 / P4 输出~~：**默认不提供**。P5 假设前序评审者都被作者说服了。

## 前置规则

- `common-rules.md`（公共规则）
- `id-conventions.md`（引用 P1 的 C-NNN，本任务分配 D-NNN 与 V-NNN）

## P5 视角标识（OPT-16 ensemble 必填）

**本视角：`practitioner`（部署/工程实施）**

本视角的核心是：**"如果我想把这篇文章的方法/系统用在生产环境，会发生什么？"**

聚焦：
1. **可复现性的工程现实**：
   - 代码是否真能跑通？依赖项是否完整？环境配置是否提供？
   - 训练所需的算力、显存、数据规模是否在普通研究者可达范围内？
   - 随机种子、超参选择、训练时长是否足够报告以便复现？
2. **真实运行成本**：
   - 推理延迟、单次推理成本、API 调用费用（若用闭源 LLM）
   - 训练时长 × GPU 数量 × 单价 = 真实训练成本
   - 与声称的"高效/低成本"是否对得上？
3. **部署可行性**：
   - 是否依赖不可控的外部服务（特定 LLM API、特定数据源）？
   - 延迟是否满足实际应用需求（实时对话 / 离线批处理）？
   - 失败模式：哪些输入会让系统崩溃、降级、出错？
4. **工程化缺口**：
   - 缺监控？缺日志？缺错误处理？缺降级策略？
   - 缺 CI/CD、版本管理、模型更新流程？
5. **隐性成本转移**：
   - 作者是否把"自己难做"的事转移给读者/用户（如需要 1000 GPU 时长才能复现）？
   - 是否把"工程努力"伪装成"方法简单"？
6. **可扩展性边界**：
   - 数据规模 +10×？+100×？方法是否仍可工作？
   - 任务复杂度 +1？模型能力要求增加时？

**不**重点关注：
- optimistic 叙事的修辞学（→ skeptic）
- 同期工作的完整性（→ domain_expert）
- 统计方法的形式严谨性（→ skeptic）

在产物顶层必须包含 `p5_metadata.role: "practitioner"` 字段。

## 执行步骤

1. 选择对**实际部署影响最大**的 3-7 个 claim（优先选择声称"高效 / 实用 / 可部署 / 可复现"的 claim）
2. 对每个 claim 提出**工程实施层面**的反对论证：
   - "如果我想用这个方法，我需要什么？"
   - "这个声称的成本/性能在生产环境是否成立？"
3. 寻找文章没有报告的工程细节：
   - 训练日志（loss 曲线、收敛速度）
   - 失败案例（什么时候方法会失效）
   - 实际推理时延（p50 / p95 / p99）
4. 检查**隐性成本转移**：
   - 把复杂预处理/标注工作转移给读者？
   - 把模型规模需求隐藏在 prompt 工程里？
5. 审查**部署假设的合理性**：
   - 文章假设的"用户"画像（研究者 vs 普通用户 vs 企业）？
   - 假设的计算资源（单机 vs 集群）？
6. 提出**最小化的工程验证集合**：
   - 最小成本复现实验
   - 真实数据规模测试
   - 失败模式探索

## 输出格式（严格遵循）

按 `templates/p5-output-schema.yaml` 输出 YAML。**额外要求**：

- `p5_metadata.role: "practitioner"`
- `p5_metadata.focus_dimensions: ["DIM-04 (方法可复现性)", "DIM-05 (真实成本)", "DIM-07 (工程可复现)"]`
- `new_defects` 中标注 `defect_type: "engineering"`（与其他视角的 "methodology" / "coverage" 区分）
- `competing_explanations` 改为 `engineering_alternatives`：
  - 简化实现路径
  - 现成 baseline 替代方案
  - 商业产品的真实性能

## 关键提问模板（强制使用）

- **复现成本问题**："如果一个普通研究者只有 1 张 A100，想复现这个结果，最少需要多少时间和成本？"
- **隐性成本问题**："这个'方法 X'的实际计算开销是否与声称的'简单'相符？"
- **失败模式问题**："在哪些输入/场景下，这个方法会失败或显著降级？"
- **扩展性问题**："当任务规模 +10× 时，方法是否仍可用？需要哪些工程改造？"
- **依赖性问题**："方法依赖哪些外部组件？这些依赖的可用性和稳定性如何？"

## 约束

- ❌ 不以反对数量衡量审查质量
- ❌ 不以"作者没说"作为缺陷（需说明为什么不说会成问题）
- ✅ 每个工程缺陷必须给出**具体的实施成本**（GPU 时长、API 费用、人力）
- ❌ 不得把"实现可能比较麻烦"作为 P0（需说明会改变结论才升 P0）
- ❌ 不得简单复述"没有源代码"——需说明缺源代码如何影响结论可验证性

## P5 practitioner 失败模式（最严重）

- ❌ **复读 P2-P4 的可复现性判断**：应聚焦**工程现实**而非**形式可复现性**
- ❌ 提"工程建议"但不给成本估算：失去 practitioner 视角的独特价值
- ❌ 把所有"缺代码"都升 P0：应区分"主结论依赖代码"vs"复现便利性"
- ❌ 不做独立 WebSearch 验证成本数据：必须用实际报价（AWS / Lambda Labs）

## 领域 P0 反模式（OPT-15 集成）

参考 `references/domain-templates.md` 的领域 P0 反模式：
- CS：缺最强 baseline / 缺 compute-matched 对照 / GitHub 链接死链 / 单 seed
- biomedical：缺样本量（practitioner: 缺招募可行性） / 缺真实部署案例
- economics：缺外推性 / 缺实际政策可行性

## 与 §0（optimistic 叙事）的关系

practitioner 视角特别警惕"声称**实用/高效/低成本**"的乐观叙事。具体检查：
- D-303-P5（LLM Harmony）：声称 cost-effective，但 6× 推理成本未量化
- 类似模式：声称"X 倍加速"但未报 baseline cost / claimed "simple" but requires complex setup

## 与 P6 的协作

P6 接收 practitioner 视角后应：
- 关注 `defect_type: "engineering"` 的 new_defects
- 评估隐性成本是否改变 C-NNN 的 overall_conclusion 影响
- practitioner 视角升级 P0 时，理由应是"工程不可行导致结论无法落地"而非"代码不全"
