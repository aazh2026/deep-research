# EnSI-RAG: Entity-Structure-Indexed Retrieval-Augmented Generation for Long-Document Question Answering

## 基本信息

- **论文标题**：EnSI-RAG: Entity-Structure-Indexed Retrieval-Augmented Generation for Long-Document Question Answering
- **作者**：Xuanyu Meng, Jiashuo Sun, Jash Rajesh Parekh, Jiawei Han
- **发表年份**：2026
- **venue**：arXiv
- **arXiv**：2608.21252
- **提交日期**：2026-08-21
- **分类**：cs.CL, cs.AI, cs.DB, cs.IR
- **原文链接**：https://arxiv.org/abs/2608.21252
- **代码**：https://github.com/RamonMeng/EnSI-RAG

## 核心价值

把「实体-结构索引」引入长文档 RAG，并给出**数值聚合题与生成题分治的指标方案**——这是工程落地常被忽略的一点。

## 关键贡献

- 以实体为中心的 passage 表示 + 查询无关的实体结构索引
- 把证据定位与答案合成解耦
- 在 **Loong**（177 题，金融/法律/学术多文档）与 **Oolong**（192 题，大规模聚合）上评测
- 对比 RAG/LongRAG/GraphRAG/DocETL/Chain-of-Agent 等 9 类基线

## 摘要

Question answering (QA) over long, connected documents remains challenging because relevant evidence may span multiple entities and their relationships. Existing retrieval-augmented generation (RAG) methods typically index documents as raw chunks and retrieve them through embedding similarity. Their performance degrades when chunk boundaries separate entities from supporting evidence or when a question requires multi-hop reasoning across the corpus.

We propose EnSI-RAG (Entity-Structure-Indexed Retrieval-Augmented Generation), a framework that constructs a query-independent, entity-centered index. Each record (e, t, k, v) represents an entity e, its type t, a semantic category k in {property, relation, aspect}, and a value v, while retaining links to the original source passages.

## 价值指标（规模 / 成绩 / 指标）

- **Loong** 平均 Acc **84.64**（SLIDERS 78.57）
- **Oolong** **71.84**（SLIDERS 64.67）
- 均 Acc **78.24**（+6.62）
- 数值题用偏差指标、非数值题用 LLM judge

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：⑥ 自动判分与工程化评测
- **应用场景**：长文档问答、多跳推理、实体结构索引