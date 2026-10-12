# Document Visual Question Answering Challenge 2020

## 基本信息

- **论文标题**：Document Visual Question Answering Challenge 2020
- **作者**：Minesh Mathew, Rubèn Tito, Dimosthenis Karatzas, R. Manmatha, C. V. Jawahar
- **发表年份**：2020
- **venue**：DAS 2020（CVPR 2020 Workshop "Text and Documents in the Deep Learning Era"）
- **arXiv**：2008.08899
- **提交日期**：2020-08-20（v2: 2021-07-18）
- **分类**：cs.CV, cs.IR
- **原文链接**：https://arxiv.org/abs/2008.08899

## 核心价值

把 DocVQA 变成可竞赛、可复现的评测任务，给出了任务拆分与基线实现的标准范式。

## 关键贡献

- 在 DocVQA 数据上组织挑战赛
- 明确抽取式（Task1，ANLS）与检索式（Task2，MAP）双轨
- 报告冠军 PingAn-OneConnect Gammalab-DQA **ANLS 0.85**
- 指出纯文本模型系统性落后、手写与长文类是难点

## 摘要

This paper presents results of Document Visual Question Answering Challenge organized as part of 'Text and Documents in the Deep Learning Era' workshop, in CVPR 2020. The challenge introduces a new problem - Visual Question Answering on document images.

### 数据集规模

- Task 1: 50,000 QA pairs / 12,767 文档图像
- Task 2: 20 questions / 14,362 文档图像（共享同一模板）

### 任务定义

- **Task 1**：单文档 VQA（ANLS 评价）
- **Task 2**：文档集合检索（MAP 评价）

## 价值指标

- 冠军 **ANLS 0.85**
- Task2 检索 MAP **0.8090**，但无系统能同时完成「检索+抽取」

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：② 单页文档 VQA 基准（DocVQA 家族）
- **应用场景**：文档 VQA 竞赛基线、挑战赛组织参考