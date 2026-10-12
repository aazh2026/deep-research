# ChartQA: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning

## 基本信息

- **论文标题**：ChartQA: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning
- **作者**：Ahmed Masry, Do Xuan Long, Jia Qing Tan, Shafiq Joty, Enamul Hoque
- **发表年份**：2022
- **venue**：Findings of ACL 2022
- **页码**：2263–2279
- **DOI**：10.18653/v1/2022.findings-acl.177
- **发表日期**：May 2022
- **原文链接**：https://aclanthology.org/2022.findings-acl.177/

## 核心价值

图表解读的事实标准基准，直接对应「看报表/仪表盘回答问题」这一高频文档解读场景。

## 关键贡献

- 同时含人工问题与基于模板的问题
- 要求视觉特征引用 + 多步逻辑与算术运算
- 提出「图表数据表 + 视觉特征」统一建模的两路 Transformer 基线

## 摘要

Charts are very popular for analyzing data. When exploring charts, people often ask a variety of complex reasoning questions that involve several logical and arithmetic operations. They also commonly refer to visual features of a chart in their questions.

Most existing datasets lack focus on complex reasoning questions, as their questions are template-based with answers from a fixed vocabulary.

### 数据规模

- 9.6K 人工撰写问题
- 23.1K 基于人工图表摘要生成的问题

### 方法

- 提出两个 transformer-based 模型，统一建模视觉特征和图表数据表

## 价值指标（规模 / 成绩 / 指标）

- 主指标：**Acc（宽松/严格）**
- 数值类需执行结果校验
- 原基线在复杂推理题上显著落后人类

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：③ 图表与表格解读评测
- **应用场景**：图表问答、仪表盘解读、报表分析