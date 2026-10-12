# MMLongBench-Doc: Benchmarking Long-context Document Understanding with Visualizations

## 基本信息

- **论文标题**：MMLongBench-Doc: Benchmarking Long-context Document Understanding with Visualizations
- **作者**：Yubo Ma, Yuhang Zang, Liangyu Chen, Meiqi Chen, Yizhu Jiao, Xinze Li, Xinyuan Lu, Ziyu Liu, Yan Ma, Xiaoyi Dong, Pan Zhang, Liangming Pan, Yu-Gang Jiang, Jiaqi Wang, Yixin Cao, Aixin Sun
- **发表年份**：2024
- **venue**：NeurIPS 2024 Datasets and Benchmarks Track（Spotlight）
- **arXiv**：2407.01523
- **提交日期**：2024-07-01
- **分类**：cs.CV, cs.CL
- **原文链接**：https://arxiv.org/abs/2407.01523
- **项目页**：https://mayubo2333.github.io/MMLongBench-Doc

## 核心价值

长上下文文档解读的标杆基准：明确量化了「跨页」与「图文表证据」两大衰减源，并把幻觉探测做成正式题目。

## 关键贡献

- 130 份 PDF（均 49.4 页 / 20,971 token）、1,062 专家标注问
- 单页 44.0% / 跨页 33.2% / 不可答 22.8%
- 证据模态覆盖：text 36.1%、table 25.9%、chart 20.5%、image 34.4%
- 三阶段协议（生成→GPT-4o 答案规整→规则打分）

## 摘要

Understanding documents with rich layouts and multi-modal components is a long-standing and practical task. Recent Large Vision-Language Models (LVLMs) have made remarkable strides in various tasks, particularly in single-page document understanding (DU). However, their abilities on long-context DU remain an open problem. This work presents MMLongBench-Doc, a long-context, multi-modal benchmark comprising 1,062 expert-annotated questions.

Distinct from previous datasets, it is constructed upon 130 lengthy PDF-formatted documents with an average of 49.4 pages and 20,971 textual tokens. Towards comprehensive evaluation, answers to these questions rely on pieces of evidence from (1) different sources (text, image, chart, table, and layout structure) and (2) various locations (i.e. page number). Moreover, 33.2% of the questions are cross-page questions requiring evidence across multiple pages. 22.8% of the questions are designed to be unanswerable for detecting potential hallucinations.

Experiments on 14 LVLMs demonstrate that long-context DU greatly challenges current models. Notably, the best-performing model, GPT-4o, achieves an F1 score of only 42.7%, while the second-best, GPT-4V, scores 31.4%. Furthermore, 12 LVLMs (all except GPT-4o and GPT-4V) even present worse performance than their LLM counterparts which are fed with lossy-parsed OCR documents. These results validate the necessity of future research toward more capable long-context LVLMs.

## 价值指标（规模 / 成绩 / 指标）

- **GPT-4o 总体 F1 仅 42.7%**（GPT-4V 31.4%）
- 12 个 LVLM 用视觉输入反而差于喂 OCR 文本的纯 LLM 版
- 指标：**按答案类型的 Acc/F1**、**不可答检测**

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：④ 多页 / 长文档评测
- **应用场景**：长上下文文档理解、跨页证据定位、幻觉检测