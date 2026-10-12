# MMDocRAG: Benchmarking Retrieval-Augmented Multimodal Generation for Document QA

## 基本信息

- **论文标题**：MMDocRAG: Benchmarking Retrieval-Augmented Multimodal Generation for Document QA
- **作者**：Kuicai Dong, Yujing Chang, Shijie Huang, Yasheng Wang, Ruiming Tang, Yong Liu
- **发表年份**：2025
- **venue**：NeurIPS 2025 Datasets and Benchmarks
- **arXiv**：2505.16470
- **提交日期**：2025-05-22（v2: 2025-11-07）
- **分类**：cs.IR, cs.CL, cs.CV
- **原文链接**：https://arxiv.org/abs/2505.16470
- **项目页**：https://mmdocrag.github.io/MMDocRAG/

## 核心价值

首个同时评「多模态证据选择」和「图文交织答案生成」的 DocRAG 基准，直接对应带引用、带原图的文档助手。

## 关键贡献

- 222 份长文档（均 67 页）、4,055 专家标注 QA、8 类问题
- 四阶段标注 + 硬负例（候选 15/20 条中金证据仅占 13.5%–18.0%）
- 允许答案图文交织并带引用
- 评 60 个 VLM/LLM + 14 个检索器

## 摘要

Document Visual Question Answering (DocVQA) faces dual challenges in processing lengthy multimodal documents (text, images, tables) and performing cross-modal reasoning. Current document retrieval-augmented generation (DocRAG) methods remain limited by their text-centric approaches, frequently missing critical visual information.

The authors introduce MMDocRAG, a comprehensive benchmark featuring 4,055 expert-annotated QA pairs with multi-page, cross-modal evidence chains. Their framework introduces innovative metrics for evaluating multimodal quote selection and enables answers that interleave text with relevant visual elements.

Through large-scale experiments with 60 VLM/LLM models and 14 retrieval systems, they identify persistent challenges in multimodal evidence retrieval, selection, and integration. Key findings reveal advanced proprietary LVMs show superior performance than open-sourced alternatives. Also, they show moderate advantages using multimodal inputs over text-only inputs, while open-source alternatives show significant performance degradation. Notably, fine-tuned LLMs achieve substantial improvements when using detailed image descriptions.

## 价值指标（规模 / 成绩 / 指标）

- 最强 GPT-4.1：**Quote Selection F1 70.2%**
- 答案质量均分 **4.14/5**
- 开源模型用图文输入普遍掉点
- 指标：
  - **Quote P/R/F1（文/图分开）**
  - **BLEU/ROUGE-L**
  - **LLM-judge 5 维 0–5**

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：⑤ 多模态文档 RAG 评测
- **应用场景**：文档助手、带引用答案生成、多模态证据选择