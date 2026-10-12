# ViDoRe: Visual Document Retrieval (ColPali / V2 / V3)

## 基本信息

- **论文标题**：
  - 主版本：ColPali: Efficient Document Retrieval with Vision Language Models
  - V2：ViDoRe (Visual Document Retrieval) v2
  - V3：ViDoRe v3
- **作者**：
  - ColPali（2024）：Manuel Faysse, Hugues Sibille, Tony Wu, Bilel Omrani, Gautier Viaud, Céline Hudelot, Pierre Colombo
  - V2（2025）：Quentin Macé, António Loison
  - V3（2026）：António Loison 等
- **发表年份**：2024–2026
- **venue**：ICLR 2025 (ColPali 主版本)
- **arXiv**：2407.01449 (ColPali) / 2505.17166 (V2) / 2601.08620 (V3)
- **原文链接**：https://github.com/illuin-tech/vidore-benchmark
- **数据集**：hf.co/vidore

## 核心价值

视觉文档检索的事实标准基准，直接评测「从文档页里把对的那几页找出来」这一 RAG 第一关。

## 关键贡献

- 多领域、多语言、多设置的页级检索任务
- 配套 ColPali 模型（VLM 页图像嵌入 + late interaction）
- V2 提高难度
- V3 扩到 10 个真实场景数据集 / 26,000 页 / 3,099 查询 / 6 语种并含 bbox 与参考答案

## 摘要

Documents are visually rich structures that convey information through text, but also figures, page layouts, tables, or even fonts. Since modern retrieval systems mainly rely on the textual information they extract from document pages to index documents -often through lengthy and brittle processes-, they struggle to exploit key visual cues efficiently. This limits their capabilities in many practical document retrieval applications such as Retrieval Augmented Generation (RAG).

To benchmark current systems on visually rich document retrieval, we introduce the Visual Document Retrieval Benchmark ViDoRe, composed of various page-level retrieval tasks spanning multiple domains, languages, and practical settings. The inherent complexity and performance shortcomings of modern systems motivate a new concept; doing document retrieval by directly embedding the images of the document pages.

We release ColPali, a Vision Language Model trained to produce high-quality multi-vector embeddings from images of document pages. Combined with a late interaction matching mechanism, ColPali largely outperforms modern document retrieval pipelines while being drastically simpler, faster and end-to-end trainable.

## 价值指标（规模 / 成绩 / 指标）

- 主指标：**Recall@k**、**nDCG@k**、**mAP**
- 按领域/语种/页类型切片
- 是检索模块选型的首选对照表

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：⑤ 多模态文档 RAG 评测
- **应用场景**：视觉文档检索、RAG 第一阶段、跨语言跨领域检索