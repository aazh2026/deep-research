# Scaling Beyond Context: A Survey of Multimodal Retrieval-Augmented Generation for Document Understanding

## 基本信息

- **论文标题**：Scaling Beyond Context: A Survey of Multimodal Retrieval-Augmented Generation for Document Understanding
- **作者**：Sensen Gao, Shanshan Zhao, Xu Jiang, Lunhao Duan, Yong Xien Chng, Qing-Guo Chen, Weihua Luo, Kaifu Zhang, Jia-Wang Bian, Mingming Gong
- **发表年份**：2025
- **venue**：ACL 2026 Main Conference
- **arXiv**：2510.15253
- **提交日期**：2025-10-17 (v3: 2026-04-20)
- **分类**：cs.CL, cs.CV
- **原文链接**：https://arxiv.org/abs/2510.15253
- **项目页**：https://github.com/SensenGao/Multimodal-RAG-Survey-For-Document

## 核心价值

把「文档解读 + RAG」的评测对象从单页抽到整库，给出按 **领域 / 检索模态 / 粒度** 三维分类法，并汇总 DocVQA、DUDE、SlideVQA、MMLongBench-Doc、ViDoRe、M3DocVQA、MMDocIR 等数据集规模对照。

## 关键贡献

- 提出多模态 RAG 分类学
- 梳理图结构索引与智能体式检索框架
- 汇总关键数据集与 benchmark：
  - M3DocVQA ≈40K 页 / 41M 视觉 token
  - VisDoMBench ≈21K 页
  - OpenDocVQA ≈206K 页
- 指出效率、细粒度表示、鲁棒性三大开放挑战

## 摘要

Document understanding is critical for applications from financial analysis to scientific discovery. Current approaches, whether OCR-based pipelines feeding Large Language Models (LLMs) or native Multimodal LLMs (MLLMs), face key limitations: the former loses structural detail, while the latter struggles with context modeling. Retrieval-Augmented Generation (RAG) helps ground models in external data, but documents' multimodal nature, i.e., combining text, tables, charts, and layout, demands a more advanced paradigm: Multimodal RAG. This approach enables holistic retrieval and reasoning across all modalities, unlocking comprehensive document intelligence.

Recognizing its importance, this paper presents a systematic survey of Multimodal RAG for document understanding. We propose a taxonomy based on domain, retrieval modality, and granularity, and review advances involving graph structures and agentic frameworks. We also summarize key datasets, benchmarks, applications and industry deployment, and highlight open challenges in efficiency, fine-grained representation, and robustness, providing a roadmap for future progress in document AI.

## 价值指标

汇总对照：

- 规模
- 模态
- 检索粒度

**工程选型价值高，无单一分数指标。**

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：① 综述与评测方法论
- **应用场景**：多模态 RAG 系统设计、检索方案选型、benchmark 选型