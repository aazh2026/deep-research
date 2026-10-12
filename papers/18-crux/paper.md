# CRUX: Controlled Retrieval-augmented Context Evaluation for Long-form RAG

## 基本信息

- **论文标题**：CRUX: Controlled Retrieval-augmented Context Evaluation for Long-form RAG
- **作者**：Jia-Huei Ju, Suzan Verberne, Maarten de Rijke, Andrew Yates
- **发表年份**：2025
- **venue**：Findings of EMNLP 2025
- **arXiv**：2506.20051
- **提交日期**：2025-06-24（修订 2026-01-09）
- **分类**：cs.IR
- **原文链接**：https://arxiv.org/abs/2506.20051

## 核心价值

解决了长式 RAG 的核心难题：**检索好不好，不能只看相关度**，要看「是否覆盖回答问题所需的信息、且不过度冗余」。

## 关键贡献

- 用人工摘要控制信息边界生成 oracle 子问题
- 定义 **Coverage**（子问题可答比例）与 **Density**（单位 token 的覆盖率，惩罚冗余）
- 设 oracle retrieval 上下界
- 在 **CRUX-DUC**（50 查询）/ **CRUX-Multi-News**（100 测试查询，约 50 万候选 passage）验证

## 摘要

Retrieval-augmented generation (RAG) enhances large language models by incorporating context retrieved from external knowledge sources. While the effectiveness of the retrieval module is typically evaluated with relevance-based ranking metrics, such metrics may be insufficient to reflect the retrieval's impact on the final RAG result, especially in long-form generation scenarios. We argue that providing a comprehensive retrieval-augmented context is important for long-form RAG tasks like report generation and propose metrics for assessing the context independent of generation.

We introduce CRUX, a Controlled Retrieval-augmented conteXt evaluation framework designed to directly assess retrieval-augmented contexts. This framework uses human-written summaries to control the information scope of knowledge, enabling us to measure how well the context covers information essential for long-form generation. CRUX uses question-based evaluation to assess RAG's retrieval in a fine-grained manner.

Empirical results show that CRUX offers more reflective and diagnostic evaluation. Our findings also reveal substantial room for improvement in current retrieval methods, pointing to promising directions for advancing RAG's retrieval.

## 价值指标（规模 / 成绩 / 指标）

- **Coverage/Density 与最终 RAG 质量的 Kendall's τ 达 0.7–0.8**，显著优于传统 IR 指标
- oracle retrieval Cov ≈**64%**
- BM25 仅 35–38%

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：⑥ 自动判分与工程化评测
- **应用场景**：长式 RAG 检索评测、报告生成质量评估