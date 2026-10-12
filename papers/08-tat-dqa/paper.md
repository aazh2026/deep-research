# Towards Complex Document Understanding By Discrete Reasoning (TAT-DQA)

## 基本信息

- **论文标题**：Towards Complex Document Understanding By Discrete Reasoning
- **作者**：Fengbin Zhu, Wenqiang Lei, Fuli Feng, Chao Wang, Haozhou Zhang, Tat-Seng Chua
- **发表年份**：2022
- **venue**：ACM Multimedia 2022
- **DOI**：10.1145/3503161.3548422
- **arXiv**：2207.11871
- **提交日期**：2022-07-25（v3: 2023-05-04）
- **分类**：cs.CV, cs.AI
- **原文链接**：https://arxiv.org/abs/2207.11871

## 核心价值

把「表格+文本」的离散推理（加/减/乘/除/计数/比较/排序）量化成可评测任务，直接对标财报解读。

## 关键贡献

- 真实财报、3,067 页、16,558 问答对，含半结构表+非结构文本
- 答案形态覆盖单 span / 多 span / 自由式
- 提出 **MHST（多模态混合选择 + 表达式树生成）**，显式预测运算类型再生成算式

## 摘要

Document Visual Question Answering (VQA) aims to understand visually-rich documents to answer questions in natural language. This work introduces **TAT-DQA**, a new Document VQA dataset with 3,067 document pages containing semi-structured tables and unstructured text, along with 16,558 question-answer pairs from real-world financial reports. The dataset requires discrete reasoning capabilities due to its numerical content.

The authors propose **MHST**, a novel multi-modal model that incorporates text, layout, and visual information to address different question types through extraction or reasoning strategies.

## 价值指标（规模 / 成绩 / 指标）

- **MHST**：EM **41.5** / F1 **50.7**
- 显著优于 TagOp 33.7 EM、NumNet+ v2 30.6 EM
- 指标：**EM**、**F1**、**算式执行校验**

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：③ 图表与表格解读评测
- **应用场景**：财报问答、表格+文本离散推理