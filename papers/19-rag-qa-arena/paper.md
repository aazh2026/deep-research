# RAG-QA Arena: Evaluating Domain Robustness for Long-form Retrieval Augmented Question Answering

## 基本信息

- **论文标题**：RAG-QA Arena: Evaluating Domain Robustness for Long-form Retrieval Augmented Question Answering
- **作者**：Rujun Han, Yuhao Zhang, Peng Qi, Yumo Xu, Jenyuan Wang, Lan Liu, William Yang Wang, Bonan Min, Vittorio Castelli
- **发表年份**：2024
- **venue**：arXiv
- **arXiv**：2407.13998
- **提交日期**：2024-07-19（v2: 2024-10-03）
- **分类**：cs.CL, cs.AI
- **原文链接**：https://arxiv.org/abs/2407.13998

## 核心价值

用「模型答案 vs 人工长答案」的成对比较替代不可靠的抽取式 EM，专门测跨域鲁棒性。

## 关键贡献

- 构建 **LFRQA**：26K 查询、7 个领域、人工撰写长式答案（多文档证据融合成连贯叙述）
- **RAG-QA Arena** 用 LLM 做成对偏好判断，并验证其与人类判断高度相关

## 摘要

Question answering based on retrieval augmented generation (RAG-QA) is an important research topic in NLP and has a wide range of real-world applications. However, most existing datasets for this task are either constructed using a single source corpus or consist of short extractive answers, which fall short of evaluating large language model (LLM) based RAG-QA systems on cross-domain generalization.

To address these limitations, we create Long-form RobustQA (LFRQA), a new dataset comprising human-written long-form answers that integrate short extractive answers from multiple documents into a single, coherent narrative, covering 26K queries and large corpora across seven different domains. We further propose RAG-QA Arena by directly comparing model-generated answers against LFRQA's answers using LLMs as evaluators.

We show via extensive experiments that RAG-QA Arena and human judgments on answer quality are highly correlated. Moreover, only 41.3% of the most competitive LLM's answers are preferred to LFRQA's answers, demonstrating RAG-QA Arena as a challenging evaluation platform for future research.

## 价值指标（规模 / 成绩 / 指标）

- 最强 LLM 答案仅 **41.3%** 被偏好于 LFRQA
- 指标：**pairwise win rate**、**与人类偏好的一致性**
- test 集 16.1K 查询

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：⑥ 自动判分与工程化评测
- **应用场景**：长式 RAG 评测、跨域鲁棒性、LLM-as-Judge