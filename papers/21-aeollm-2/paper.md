# Overview of the NTCIR-19 Automatic Evaluation of LLMs 2 (AEOLLM-2) Task

## 基本信息

- **论文标题**：Overview of the NTCIR-19 Automatic Evaluation of LLMs 2 (AEOLLM-2) Task
- **作者**：Junjie Chen, Yuxi Dong, Haitao Li, Yiqun Liu, Qingyao Ai
- **发表年份**：2025–2026
- **venue**：NTCIR-19（任务页 2026-03 发数据 / 07-08 评测）
- **arXiv**：2610.11598
- **提交日期**：2026-10-08
- **分类**：cs.IR
- **原文链接**：https://arxiv.org/abs/2610.11598

## 核心价值

把长报告（>1500 token，科研综述 8000+）的自动评测做成正式评测任务，给出「retrieval-assisted LLM judge + 人工校正」的可复现流水线。

## 关键贡献

- 640 份报告 / 40 中英文问题
- 多 prompt 变体与 deep research 系统
- 维度：全面性、洞察、指令遵循、可读性
- 客观维度用带检索的 LLM 判分再人工校正，可读性直接人工评
- **91 次提交 / 10 队参与**

## 摘要

In this paper, we provide an overview of the NTCIR-19 Automatic Evaluation of LLMs 2 (AEOLLM-2) task. Building on the success of the NTCIR-18 core task AEOLLM, we proposed AEOLLM-2 for NTCIR-19 to further investigate automatic evaluation methods for Large Language Models (LLMs), particularly in long-form text generation scenarios.

### 关键创新

- 引入 **Deep Research Evaluation** 子任务，评估 LLM 生成的长篇深度研究报告
- 参与者开发自动评估方法，对照人工标注的真值标签
- 收到 **91 次提交（来自 10 个团队）**

### 评测维度

- 全面性
- 洞察
- 指令遵循
- 可读性

## 价值指标（规模 / 成绩 / 指标）

- 对齐指标：
  - **pairwise accuracy**
  - **Spearman ρ**
  - **Kendall τ**
- 覆盖 640 报告的维度级人工标注，是 judge 校准研究的直接数据来源

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：⑥ 自动判分与工程化评测
- **应用场景**：深度研究评测、自动判分校准、长报告质量评估