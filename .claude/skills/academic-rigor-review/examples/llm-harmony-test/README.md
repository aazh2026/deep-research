# Real Paper Test: LLM Harmony (arXiv:2401.01312)

这是 R2 推荐项的产物——**用真实论文验证 P5 能否找到 P2–P4 漏掉的问题**。

## 测试目标

验证 skill 设计的核心价值——P5 独立反方视角。具体目标：
1. 跑完整 P1 → P2 → P3 → P4 → P5 → P0 预检 → P6
2. 量化 P5 找到的、P2-P4 漏掉的关键问题
3. 验证 P0 硬规则在真实场景下能可靠工作

## 文章选择

**LLM Harmony: Multi-Agent Communication for Problem Solving**
- 作者：Sumedh Rasal (Georgia Tech)
- arXiv: 2401.01312
- 日期：2024-01-02
- 长度：4 页
- 主题：基于 CAMEL 灵感的 multi-agent 框架

**选择理由**：
- 4 页短文，可在一次 WebFetch 中处理
- 主题与 skill 领域相关（多 Agent）
- 报告了具体实验数字（65%/77%/83%），便于审计
- 引用 CAMEL——可以核查 baseline 数字是否合理
- 乐观技术叙事——容易让 P2-P4 漏掉反向风险

**数据局限**：
- WebFetch 返回的是摘要而非完整 PDF 文本
- 因此本测试在 P1 阶段就声明了 `uncertainties`（模型/prompt/种子/基线实施不明）
- 这反而使 P2-P5 必须在信息不完整条件下工作，更接近现实

## 关键发现

### 1. P5 找到了 5 个 P2-P4 完全漏掉的关键问题

| P5 发现 | 严重度 | P2-P4 漏掉的原因 |
| --- | --- | --- |
| **D-301-P5**: 缺 self-consistency baseline | P1 | P2-P4 关注"是否与 CAMEL 复现一致"，但忽略了"是否跑过最强单 agent baseline"这一更基本问题 |
| **D-302-P5**: collective delusion 风险升级 | P1 | "Multi-agent 减少幻觉"的乐观叙事掩盖了反向风险（M3MAD-Bench 65% 失败属于 collective delusion） |
| **D-303-P5**: 6× 推理成本 vs fine-tuning | P2 | P3 仅指出"未量化"，未引用同期成本数据 |
| **D-304-P5**: 4-page workshop venue 限制 | P2 | P2-P4 按 full paper 标准评估，未考虑 venue/format 因素 |
| **D-305-P5**: human intervention 实际是转移 | P3 | 隐性成本不在 surface claim 表面 |

**P5 反方价值明确**：当文章有乐观技术叙事时，P5 的独立视角最关键。

### 2. P0 硬规则正确触发

- P4 报告 D-201（可复现性 P0）——模型/prompt/种子/运行次数均未报告
- Precheck 诚实纳入 D-201（input_p0_count=1）
- P6 verdict 强制降级为 `insufficient_evidence`（verdict 6）
- P0-R1 至 P0-R5 全部通过

**关键经验**：orchestrator 不应因为"想给温和 verdict"而把 P4 的 P0 标尺降级。
诚实纳入 → 强制降级 → 用户得到真实信号。

### 3. 文献核查发现重大 baseline 不符

- 文章声明 "Multi-Agent baseline 55% on GSM8K"
- CAMEL 实际 GSM8K 表现：7.35%（fine-tuned）或 88.6%（ensemble）
- 55% 与两者都不符 → baseline 实施不明 → 对比无效

### 4. 同期 multi-agent GSM8K 提升已在 +8.7 至 +24pp

| Paper | Year | Gain | Method |
| --- | --- | --- | --- |
| Du et al. (MAD) | 2023 | +8.7 pp | 3-agent debate, 3 rounds |
| More Agents | 2024 | +12-24 pp | Sampling + majority vote |
| MA-ToT Validator | 2024 | +8.8 pp | Validator agent role |
| α-UMi | 2024 | +5-10 pp | Tool-use multi-agent |
| **LLM Harmony** | **2024** | **+15 pp** | **Role-playing + validation** |

LLM Harmony 的 +15pp 在该背景下**不显著**——同期工作普遍达到该水平。
这进一步支持 P5 的 D-301-P5 主张（缺 self-consistency baseline）。

## 最终 verdict

`insufficient_evidence`（P0 可复现性缺陷导致）

### 升级到 core_qualified_supported 需满足：

1. **D-201 (P0)** 全部关闭：公开模型/prompt/种子/运行次数/完整代码
2. **D-202, D-204, D-301-P5 (P1)** 修复：compute-matched + self-consistency baseline + 明确 baseline 实施
3. **D-203, D-302-P5 (P1)** 修复：量化 hallucination + collective delusion 风险
4. **D-303-P5 (P2)** 修复：成本量化

## 文件结构

```
runs/2026-10-12-llm-harmony-test/    # 完整测试产物
├── article.md                         # 测试文章（WebFetch 摘要重建）
├── p1_object_model.yaml               # 11 claims
├── p2_literature_audit.yaml           # 3 defects (D-001-LLMH 等)
├── p3_claim_evidence.yaml             # 3 logic defects (D-101 等)
├── p4_method_review.yaml              # 4 key defects (D-201 P0 等)
├── p5_adversarial.yaml                # 5 NEW defects (D-301-P5 等)
├── precheck_p0_defects.yaml           # 1 P0 (D-201)
└── p6_synthesis.yaml                  # verdict: insufficient_evidence

examples/llm-harmony-test/             # 复制版供未来参考
└── (同 runs/ 内容)
```

## P5 反方视角的核心经验

1. **"独立"约束是关键**：P5 拒绝看 P2-P4 的判断，使其能够发现乐观叙事掩盖的反向风险
2. **关键问题往往不在表面 claim 上**：human intervention 转移、collective delusion、venue 限制——这些不是文章明说的问题
3. **同质多 agent 是高风险配置**：本文的 collective delusion 风险升级正是因为用同一 LLM 多个 persona
4. **P5 提议升级 P0 应被 P6 显式处理**：本次 P5 提议 D-302-P5 升级 P0，但保守地按 P5 报告值（P1）处理

## 局限性

1. WebFetch 仅返回摘要，P1 阶段就声明了大量 uncertainties
2. 单一论文测试——统计意义有限
3. orchestrator 同时扮演所有 P 任务（合成测试）——真实多 Subagent 部署可能产生不同结论
4. P5 提议升级 D-302-P5 为 P0 未被本次采用
