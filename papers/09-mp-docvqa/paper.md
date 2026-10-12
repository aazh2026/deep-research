# Hierarchical Multimodal Transformers for Multi-Page DocVQA (MP-DocVQA)

## 基本信息

- **论文标题**：Hierarchical Multimodal Transformers for Multi-Page DocVQA
- **作者**：Rubèn Tito, Dimosthenis Karatzas, Ernest Valveny
- **发表年份**：2023
- **venue**：Pattern Recognition（2022 arXiv 预印本）
- **arXiv**：2212.05935
- **提交日期**：2022-12-07（v2: 2023-04-01）
- **分类**：cs.CV, cs.AI, cs.CL
- **原文链接**：https://arxiv.org/abs/2212.05935

## 核心价值

DocVQA 从单页走向多页的起点；同时给出「逐页摘要→整文档解码」这一至今仍在用的长文档建模范式，并附带可解释的页级证据定位。

## 关键贡献

- 46,176 问 / 47,952 页图 / 5,928 份多页文档（最多 20 页，85.95% 真多页）
- 提出 **Hi-VT5**，用 M 个可学习 [PAGE] token 逐页压缩，解码端融合
- 单阶段同时输出答案与证据页

## 摘要

Document Visual Question Answering (DocVQA) refers to the task of answering questions from document images. Existing work on DocVQA only considers single-page documents. However, in real scenarios documents are mostly composed of multiple pages that should be processed altogether. In this work we extend DocVQA to the multi-page scenario.

For that, we first create a new dataset, MP-DocVQA, where questions are posed over multi-page documents instead of single pages. Second, we propose a new hierarchical method, Hi-VT5, based on the T5 architecture, that overcomes the limitations of current methods to process long multi-page documents. The proposed method is based on a hierarchical transformer architecture where the encoder summarizes the most relevant information of every page and then, the decoder takes this summarized information to generate the final answer.

Through extensive experimentation, we demonstrate that our method is able, in a single stage, to answer the questions and provide the page that contains the relevant information to find the answer, which can be used as a kind of explainability measure.

## 价值指标（规模 / 成绩 / 指标）

- **46k 问 / 48k 页**
- 指标：**ANLS**、**证据页召回**
- 首次验证「页级压缩」可兼顾长文档与可解释性

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：④ 多页 / 长文档评测
- **应用场景**：多页文档 VQA、长上下文建模、可解释 AI