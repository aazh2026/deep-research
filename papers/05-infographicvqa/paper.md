# InfographicVQA

## 基本信息

- **论文标题**：InfographicVQA
- **作者**：Minesh Mathew, Viraj Bagal, Rubèn Tito, Dimosthenis Karatzas, Ernest Valveny, C. V. Jawahar
- **发表年份**：2022
- **venue**：WACV 2022
- **arXiv**：2104.12756
- **提交日期**：2021-04-26（v2: 2021-08-22）
- **分类**：cs.CV, cs.CL
- **原文链接**：https://arxiv.org/abs/2104.12756
- **项目页**：https://www.docvqa.org

## 核心价值

把文档从「扫描件」扩展到「信息图」，迫使模型同时推理布局、文字、图形元素与数据可视化——这是图表解读的前哨战。

## 关键贡献

- 信息图 VQA 数据 + 强 Transformer 基线
- 问题刻意设计为需要初等推理与基本算术
- 提出**布局-文本-图形-可视化联合推理**这一评测设定

## 摘要

Infographics are documents designed to effectively communicate information using a combination of textual, graphical and visual elements. In this work, we explore the automatic understanding of infographic images by using Visual Question Answering... we present InfographicVQA, a new dataset that comprises a diverse collection of infographics along with natural language questions and answers annotations.

### 数据特点

- 数据集含多样化信息图
- 自然语言 Q&A 标注
- 问题要求对文档布局、文本、图形元素与数据可视化进行联合推理
- 强调**初等推理**与**基本算术能力**

### 评估

- 评估两个 state-of-the-art 多模态 VQA 模型作为基线

## 价值指标

- 主指标：**ANLS**
- 人类近满分、两路基线均 unsatisfactory，验证「布局+算术」是独立瓶颈

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：② 单页文档 VQA 基准（DocVQA 家族）
- **应用场景**：信息图/可视化问答、布局+算术联合推理评测