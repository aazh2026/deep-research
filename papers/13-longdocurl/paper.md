# LongDocURL: A Comprehensive Multimodal Long Document Benchmark Integrating Understanding, Reasoning, and Locating

## 基本信息

- **论文标题**：LongDocURL: a Comprehensive Multimodal Long Document Benchmark Integrating Understanding, Reasoning, and Locating
- **作者**：Chao Deng, Jiale Yuan, Pi Bu, Peijie Wang, Zhong-Zhi Li, Jian Xu, Xiao-Hui Li, Yuan Gao, Jun Song, Bo Zheng, Cheng-Lin Liu
- **发表年份**：2024
- **venue**：arXiv
- **arXiv**：2412.18424
- **提交日期**：2024-12-24（v3: 2025-07-15）
- **分类**：cs.AI, cs.CL
- **原文链接**：https://arxiv.org/abs/2412.18424

## 核心价值

在 MMLongBench-Doc 之上把评测维度做细：理解/推理/定位三维 × 证据元素 × 单页/跨页/跨元素，可做归因诊断而非只给总分。

## 关键贡献

- 2,325 高质量 QA / 33,000+ 页
- 半自动流水线（Extract&Filter→QA 生成→自动校验→人工校验）
- 20 个子任务
- 定义 TXT/LAY/FIG/TAB 四类证据与 SP/MP/CE 三类证据位置
- 报告 26 种配置下的 generalized accuracy

## 摘要

Large vision language models (LVLMs) have improved the document understanding capabilities remarkably, enabling the handling of complex document elements, longer contexts, and a wider range of tasks. However, existing document understanding benchmarks have been limited to handling only a small number of pages and fail to provide a comprehensive analysis of layout elements locating. In this paper, we first define three primary task categories: Long Document Understanding, numerical Reasoning, and cross-element Locating, and then propose a comprehensive benchmark, LongDocURL, integrating above three primary tasks and comprising 20 sub-tasks categorized based on different primary tasks and answer evidences.

### 任务分类

- **三大主任务**：
  - Long Document Understanding（长文档理解）
  - numerical Reasoning（数值推理）
  - cross-element Locating（跨元素定位）
- **20 子任务**：按主任务与答案证据分类

### 方法亮点

- 半自动 benchmark 构建流水线
- 显著优于现有文档理解基准
- 提供版式元素定位的综合分析
- 评估 26 种不同模型配置（开源 + 闭源）

## 价值指标（规模 / 成绩 / 指标）

- **2,325 对 / 33k+ 页**
- 主指标：**Generalized Accuracy (0–1)**，按 U/R/L × 证据模态 × 证据位置切片

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：④ 多页 / 长文档评测
- **应用场景**：长文档理解评测、归因诊断、模型选型