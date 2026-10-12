# DocVQA: A Dataset for VQA on Document Images

## 基本信息

- **论文标题**：DocVQA: A Dataset for VQA on Document Images
- **作者**：Minesh Mathew, Dimosthenis Karatzas, C. V. Jawahar
- **发表年份**：2021
- **venue**：WACV 2021
- **arXiv**：2007.00398
- **提交日期**：2020-07-01（修订 2021-01-05）
- **分类**：cs.CV, cs.IR
- **原文链接**：https://arxiv.org/abs/2007.00398
- **项目页**：https://www.docvqa.org

## 核心价值

文档解读评测的奠基基准，首次把「读文档」定义成 VQA 问题；几乎所有后续 DocVQA 论文都以它为起点做纵向对比。

## 关键贡献

- 12,000+ 文档图像、50,000 问
- 问题分 form / table-list / layout / running-text / handwritten 等 9 类
- 同时给出 Task1 单文档抽取与 Task2 文档集合检索
- **定义 ANLS（Average Normalized Levenshtein Similarity）作为主指标**，对小写、空格、OCR 误识容错

## 摘要

We present a new dataset for Visual Question Answering (VQA) on document images called DocVQA. The dataset consists of 50,000 questions defined on 12,000+ document images.

Although the existing models perform reasonably well on certain types of questions, there is large performance gap compared to human performance (94.36% accuracy).

The models need to improve specifically on questions where understanding structure of the document is crucial.

## 价值指标（规模 / 成绩 / 指标）

- **50k 问 / 12k+ 图**
- 人类 94.36% Acc
- Task2 最佳 MAP **0.8090**
- 主指标：**ANLS**、**MAP**

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：② 单页文档 VQA 基准（DocVQA 家族）
- **应用场景**：文档 VQA 评测基线、字段抽取任务