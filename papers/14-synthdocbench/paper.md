# SynthDocBench: Controlled Benchmark for Long-Context Visual Document Understanding

## 基本信息

- **论文标题**：SynthDocBench: Controlled Benchmark for Long-Context Visual Document Understanding
- **作者**：Abhigya Verma, Khyati Mahajan, Amit Kumar Saha, Shruthan Radhakrishna, Sagar Davasam, Vikas Yadav, Sai Rajeswar Mudumba
- **发表年份**：2026
- **venue**：COLM 2026（Accepted）
- **arXiv**：2607.10400
- **提交日期**：2026-07-11
- **分类**：cs.CV, cs.AI
- **原文链接**：https://arxiv.org/abs/2607.10400
- **License**：CC BY 4.0

## 核心价值

用组合设计把「长度、布局、模态、题型」解耦，专门做失败归因——这是现有真实基准做不到的事。

## 关键贡献

- 全合成、六类布局原型 + 40% 随机覆盖防捷径
- 每个因素独立变化
- 测 7 个前沿 VLM
- 挖出三类新失败模式：
  - 长度陡降
  - **中段最难**（6 模型中 5 个，Early-to-Late 最大落差 8.3 个百分点）
  - 长文档下图表理解崩溃

## 摘要

Vision language models (VLMs) have achieved strong performance on visual document understanding benchmarks such as DocVQA, ChartQA, and MMLongBench-Doc. However, real-world documents combine multiple factors such as length, layout complexity, modality, and question difficulty, which makes it difficult to attribute model failures to specific causes. We introduce SynthDocBench, a fully synthetic benchmark for long-context visual document understanding that systematically controls factors including document length, layout structure, modality composition, and question type.

The benchmark is constructed using a combinatorial design, each factor is varied independently across generated documents, enabling controlled analysis of model behavior. Documents are generated end to end using an LLM pipeline across six layout archetypes, with a 40 percent random override to prevent models from exploiting spurious correlations. Additionally, SynthDocBench spans long-context documents with substantially greater length and structural diversity than existing benchmarks.

Evaluating seven frontier VLMs, we uncover three failure modes that existing benchmarks cannot surface:

1. **Sharp degradation with document length**
2. **Systematic positional sensitivity**: middle third of a document is hardest for five of six models; steepest Early-to-Late decline: 8.3 percentage points
3. **Breakdown of chart comprehension in long-document settings**

These results suggest that current models may be overfitting to benchmark artifacts rather than achieving robust long-context visual document understanding.

## 价值指标（规模 / 成绩 / 指标）

- 主指标：**按因素切片的 Acc**
- 价值在诊断能力，不在排名
- 可复用于新模型的回归测试

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：④ 多页 / 长文档评测
- **应用场景**：失败归因分析、模型回归测试、组合设计诊断