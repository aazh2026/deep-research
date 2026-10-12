# P5 高价值发现清单（R2.3 引入）

> 本文件整理"P5 反方挑战最有价值的发现"模式。
> 来自 R2 LLM Harmony 测试的 5 个 P5 缺陷（D-301-P5 至 D-305-P5）的归纳。

## §1 什么是"高价值"的 P5 发现

**判断标准**：P5 的新发现 vs P2-P4 已知发现，价值差异由下列 3 维决定：

| 维度 | 高价值 | 低价值 |
| --- | --- | --- |
| **新颖性** | P2-P4 完全未识别 | P2-P4 已识别但 P5 重述 |
| **可操作性** | 有明确 fix_requirement | "作者应该考虑 X" 类建议 |
| **结论影响** | 改变 verdict 或 DIM 评分 | 仅影响适用边界或措辞 |

**价值评分公式**：
```
high_value_score = 新颖性 × 可操作性 × 结论影响
                  (1-3)    (1-3)      (1-3)
```

满分 27。P5 的 new_defects 应优先给出 ≥ 12 分的发现。

## §2 高价值发现的 6 种模式

### 模式 1：缺最强 baseline（Pattern: Missing Strongest Baseline）

**识别信号**：
- 文章报告"超越 baseline"
- 但未与同期 SOTA baseline 对比
- 仅与作者自实现或过时的 baseline 对比

**P5 应问的问题**：
- 文章报告的提升，与同期最强单 agent baseline 对比如何？
- 是否做了 compute-matched 对照？
- baseline 实施是否公开可复现？

**真实例子**：D-301-P5（缺 self-consistency baseline）
- 文章对比 multi-agent vs multi-agent baseline（55%）
- 未与 single-agent + self-consistency (Wang 2023) 对比
- 同期工作 Du 2023, More Agents 2024, MA-ToT 2024 已达到 +8.7~+24pp
- 文章 +15pp 在该背景下不显著

**反模式**：
- ❌ "baseline 不够强" 但未指出具体应与哪个 baseline 对比
- ❌ "应该做更多 baseline 对比"（无具体目标）

### 模式 2：缺反向风险讨论（Pattern: Missing Reverse Risk）

**识别信号**：
- 文章使用乐观词汇（"减少"、"降低"、"提升"）
- 但未讨论反向场景（什么情况下会失败 / 风险升级）
- 同期文献有报告反向结果的工作未被引用

**P5 应问的问题**：
- 文章的核心方法在什么场景下会**失败**？
- 同期文献有没有报告反向结果？
- 文章的乐观主张被什么实验证伪过？

**真实例子**：D-302-P5（collective delusion 风险）
- 文章："multi-agent 减少幻觉"
- 反向证据：M3MAD-Bench 2025 报告同质多 agent 65% 失败属 collective delusion
- 作者未引用、未讨论、未量化

**反模式**：
- ❌ "文章没讨论失败场景" 但未指出具体应讨论什么
- ❌ 反向证据强度不够（如只是博客文章）但当 P0 处理

### 模式 3：缺成本量化（Pattern: Missing Cost Quantification）

**识别信号**：
- 文章使用"高效"、"轻量"、"cost-effective"等定性词
- 但无具体成本数据（API 费用、推理时间、token 数）
- 未与替代方案的成本对比

**P5 应问的问题**：
- 文章报告的方法每条 query 多少 token / 多少美元？
- 与 fine-tuning 一次性成本 / 缓存成本 / 规则方法的成本对比？
- 隐性成本（设计、运营、维护）是否被忽略？

**真实例子**：D-303-P5（6× 推理成本未量化）
- 文章："cost-effective multi-agent"
- 实际：3 agents × N rounds → 6× 推理成本
- 与 fine-tuning 一次性成本对比 → 长期更贵
- 未量化

**反模式**：
- ❌ "成本应该量化" 但未给出具体对比基线
- ❌ 把隐性成本算到主结论（应是 P3，不应触发 verdict 降级）

### 模式 4：venue/format 限制未考虑（Pattern: Venue Constraints Ignored）

**识别信号**：
- 文章发表在 workshop / 短文 / 非顶会 venue
- 实验设计 / 写作风格符合该 venue 的约束
- 但作者按 full paper 标准自我宣传

**P5 应问的问题**：
- 文章的 venue 是什么？该 venue 的典型实验规模？
- 当前的实验规模是否合理（与 venue 期望匹配）？
- 后续是否有 full paper 承诺？承诺的时间线？

**真实例子**：D-304-P5（4-page workshop venue 限制）
- 文章：4 pages, workshop paper
- 实验：3 个数据集，无统计显著性，无 compute 控制
- 作者结论：与 full venue paper 同样强度
- 实际：venue 限制下实验规模本就有限，结论应明确边界

**反模式**：
- ❌ "workshop paper 不严谨"（venue 不是缺陷，是约束）
- ❌ 把 venue 限制当 P0（应是 P2-P3）

### 模式 5：隐性成本转移（Pattern: Hidden Cost Transfer）

**识别信号**：
- 文章声称"减少 X 成本"
- 但 X 成本被转移到 Y 环节（用户、运维、设计阶段）
- Y 环节成本不在主表面对比中

**P5 应问的问题**：
- 文章说"减少 X"，X 真的减少了吗？还是从 A 转移到 B？
- B 环节的成本由谁承担？
- 综合 A+B 的总成本变化如何？

**真实例子**：D-305-P5（human intervention 转移）
- 文章："减少 human intervention"
- 实际：runtime human intervention 减少，但 design-time prompt engineering 大幅增加
- 设计阶段成本从"未报告"变成"占主导"
- 净效果：human effort 未减少，只是转移

**反模式**：
- ❌ "应该有 cost breakdown" 但未指出具体哪类成本被转移
- ❌ 把"转移"等同于"消失"（应是 P2-P3，不是 P0）

### 模式 6：基线实施不透明（Pattern: Opaque Baseline Implementation）

**识别信号**：
- 文章对比自己的方法 vs 引用文献的方法
- 但未明确实施细节（prompt、模型版本、API 参数）
- 引用文献的"标准结果"与文章对比的数字不符

**P5 应问的问题**：
- 文章报告的 baseline 数字与原始文献一致吗？
- baseline 的 prompt / 模型 / 超参数是否公开？
- 第三方能否独立复现 baseline？

**真实例子**：D-204（baseline 实施不明）
- 文章："Multi-Agent baseline 55% on GSM8K"
- CAMEL 原文 GSM8K：7.35% (fine-tuned) 或 88.6% (ensemble)
- 55% 与两者都不符
- 实施细节未公开

**反模式**：
- ❌ "baseline 数字不对" 但未做核查（必须引用原始文献）
- ❌ baseline 偏差归 P0（除非影响核心结论的对比）

## §3 价值密度评分

每条 P5 new_defect 完成后，P5 应自评：

```yaml
new_defects:
  - id: D-301-P5
    # ... 其他字段
    value_self_assessment:
      novelty: 3            # P2-P4 完全未识别
      actionability: 3      # 明确 fix_requirement（加 self-consistency baseline）
      conclusion_impact: 2  # 改变 DIM-05 评分但不直接降级 verdict
      total: 18             # 3×3×2
      high_value: true      # total ≥ 12
```

P6 在 `p5_value_assessment` 中应汇总：
- 全部 new_defects 的总价值分
- ≥ 12 分的发现数量
- 覆盖了 §2 中哪几种模式（"模式 1 + 模式 3 + 模式 5"）

## §4 P5 高价值发现的"反定义"（什么不是高价值）

| 类型 | 为什么低价值 | 正确处理 |
| --- | --- | --- |
| 重述 P2-P4 已识别的缺陷 | 失去 P5 独立视角价值 | 仅在 P2-P4 漏掉某具体子点时补充 |
| "应该增加更多实验" | 无具体实验设计 | 应给"compute-matched 对照 + 5 次运行 + t 检验" |
| 挑战作者主观判断（"我觉得不够好"） | 主观不可证伪 | 应给"具体反例 / 同期文献" |
| 把 venue 限制当 P0 | venue 不是缺陷是约束 | 限 P2-P3 |
| 把建议当缺陷 | "建议作者考虑 X" 是建议不是缺陷 | 限于"作者未考虑 X" 才算缺陷 |
| 收集低 strength（"弱"）的凑数条目 | 稀释真正有价值的反方发现 | P5 失败模式之一 |

## §5 P6 评估 P5 价值的方法

P6 在 `p5_value_assessment` 字段应包含：

```yaml
p5_value_assessment:
  total_new_defects: 5
  high_value_count: 5              # value_self_assessment.total ≥ 12
  avg_value_score: 17.4           # 平均分
  patterns_covered:               # 来自 §2 的模式
    - "Pattern 1: Missing Strongest Baseline (D-301-P5)"
    - "Pattern 2: Missing Reverse Risk (D-302-P5)"
    - "Pattern 3: Missing Cost Quantification (D-303-P5)"
    - "Pattern 4: Venue Constraints (D-304-P5)"
    - "Pattern 5: Hidden Cost Transfer (D-305-P5)"
  p5_independence_verified: true   # P5 new_defects 与 P2-P4 defects 重叠度 < 50%
  critical_question: |
    P5 是否真的找到了 P2-P4 漏掉的问题？
    本次：5/5 命中。P5 反方价值明确。
```

**P5 价值未达标的情况**：
- high_value_count < new_defects 总数的 50%
- patterns_covered 仅命中 1 种或 0 种
- p5_independence_verified = false（与 P2-P4 重叠 > 50%）

此时 P6 应在 `evaluation_limitations` 显式声明"P5 反方价值不足，本次评审与仅跑 P2-P4 等效"。

## §6 与 R2.2 §0.2 的关系

| 文件 | 视角 |
| --- | --- |
| **p5-adversarial.md §0.2** | P5 **执行**时的检查清单（"应该找什么"） |
| **p5-high-value-findings.md** | P5 **自评**和 P6 **审计**时的价值判定（"什么算高价值"） |

两者互补：§0.2 是输入（找什么），本文件是输出（找到的如何评分）。
