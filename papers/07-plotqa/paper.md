# PlotQA: Reasoning over Scientific Plots

## 基本信息

- **论文标题**：PlotQA: Reasoning over Scientific Plots
- **作者**：Nitesh Methani, Pritha Ganguly, Mitesh M. Khapra, Pratyush Kumar
- **发表年份**：2020
- **venue**：WACV 2020
- **arXiv**：1909.00997
- **提交日期**：2019-09-03
- **分类**：cs.CV, cs.AI, cs.CL
- **原文链接**：https://arxiv.org/abs/1909.00997

## 核心价值

针对科学论文/技术报告里的曲线图，解决了「答案不在词表里」这一真实难题（真实值、开放词表）。

## 关键贡献

- 224,377 张真实来源图、28.9M 问答对
- **80.76% 的 OOV 问题答案不在固定词表中**
- 提出「词表/框抽取 + 表 QA 引擎」混合解法
- 混合模型在 DVQA 上 58%（原 SOTA 46%）

## 摘要

Existing synthetic datasets (FigureQA, DVQA) for reasoning over plots do not contain variability in data labels, real-valued data, or complex reasoning questions.

The paper addresses limitations in prior plot reasoning datasets by introducing PlotQA, which contains 28.9 million question-answer pairs over 224,377 plots sourced from real-world data. Approximately 80.76% of out-of-vocabulary (OOV) questions have answers not found in fixed vocabularies.

Existing models perform poorly on PlotQA (single-digit accuracy) because they were designed for constrained answer scenarios.

## 方法亮点

混合模型处理两类问题：

- **特定问题** → 固定词表选择或边界框提取
- **复杂问题** → 表 QA 引擎处理从检测到的视觉元素生成的结构化表

## 价值指标（规模 / 成绩 / 指标）

- **28.9M 对 / 224k 图**
- PlotQA 上模型 Acc **22.52%**（现有模型个位数），暴露 OOV 推理短板

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：③ 图表与表格解读评测
- **应用场景**：科学图表问答、开放词表数值问答