# M3DocRAG: Multi-modal Retrieval is What You Need for Multi-page Multi-document Understanding

## 基本信息

- **论文标题**：M3DocRAG: Multi-modal Retrieval is What You Need for Multi-page Multi-document Understanding
- **作者**：Jaemin Cho, Debanjan Mahata, Ozan Irsoy, Yujie He, Mohit Bansal
- **发表年份**：2024
- **venue**：arXiv
- **arXiv**：2411.04952
- **提交日期**：2024-11-07
- **分类**：cs.CV, cs.AI, cs.CL
- **原文链接**：https://arxiv.org/abs/2411.04952
- **项目页**：https://m3docrag.github.io

## 核心价值

把文档 RAG 从「OCR 出文本再向量检索」改成「按页图像做视觉检索」，从根本上避免图表/版式信息在解析环节丢失。

## 关键贡献

- 多模态 RAG 框架（多模态 retriever + MLM）
- 兼容 closed/open-domain、单跳/多跳、text/chart/figure 证据
- 新建 **M3DocVQA**：3,000+ PDF / 40,000+ 页开放域 DocVQA
- 系统分析索引方式、MLM 与检索器组合

## 摘要

Document visual question answering (DocVQA) pipelines that answer questions from documents have broad applications. Existing methods focus on handling single-page documents with multi-modal language models (MLMs), or rely on text-based retrieval-augmented generation (RAG) that uses text extraction tools such as optical character recognition (OCR). However, there are difficulties in applying these methods in real-world scenarios:

(a) questions often require information across different pages or documents, where MLMs cannot handle many long documents;
(b) documents often have important information in visual elements such as figures, but text extraction tools ignore them.

We introduce M3DocRAG, a novel multi-modal RAG framework that flexibly accommodates various document contexts (closed-domain and open-domain), question hops (single-hop and multi-hop), and evidence modalities (text, chart, figure, etc.). M3DocRAG finds relevant documents and answers questions using a multi-modal retriever and an MLM, so that it can efficiently handle single or many documents while preserving visual information.

Since previous DocVQA datasets ask questions in the context of a specific document, we also present M3DocVQA, a new benchmark for evaluating open-domain DocVQA over 3,000+ PDF documents with 40,000+ pages. In three benchmarks (M3DocVQA/MMLongBench-Doc/MP-DocVQA), empirical results show that M3DocRAG with ColPali and Qwen2-VL 7B achieves superior performance than many strong baselines, including state-of-the-art performance in MP-DocVQA.

## 价值指标（规模 / 成绩 / 指标）

- ColPali + Qwen2-VL 7B 在 M3DocVQA / MMLongBench-Doc / MP-DocVQA 上超强基线
- 取 MP-DocVQA SOTA
- 开放域 4 万页检索延迟 **2s/query**（原 20s）

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：⑤ 多模态文档 RAG 评测
- **应用场景**：多页多文档问答、多模态 RAG 框架、开放域 DocVQA