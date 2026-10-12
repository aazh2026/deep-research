# MME-Survey: A Comprehensive Survey on Evaluation of Multimodal LLMs

## 基本信息

- **论文标题**：MME-Survey: A Comprehensive Survey on Evaluation of Multimodal LLMs
- **作者**：Chaoyou Fu, Yi-Fan Zhang, Shukang Yin, Bo Li, Xinyu Fang, Sirui Zhao, Haodong Duan, Xing Sun, Ziwei Liu, Liang Wang, Caifeng Shan, Ran He
- **团队**：MME + MMBench + LLaVA Teams
- **发表年份**：2024
- **venue**：arXiv:2411.15296
- **提交日期**：2024-11-22 (v2: 2024-12-08)
- **分类**：cs.CV, cs.AI, cs.CL
- **原文链接**：https://arxiv.org/abs/2411.15296
- **项目页**：https://github.com/BradyFU/Awesome-Multimodal-Large-Language-Models/tree/Benchmarks

## 核心价值

唯一把「多模态大模型评测」当独立学科梳理的综述，文档理解只是其中一个应用切面。用来定评测维度、建集流程与 judge/metric/toolkit 三层体系。

## 关键贡献

- 按能力把基准分成基础能力、模型自分析、扩展应用三类
- 给出 benchmark 构建四步（数据收集→标注→注意事项）
- 系统讨论 judge 选择、指标设计与工具链（VLMEvalKit 等）

## 摘要

As a prominent direction of Artificial General Intelligence (AGI), Multimodal Large Language Models (MLLMs) have garnered increased attention from both industry and academia. Building upon pre-trained LLMs, this family of models further develops multimodal perception and reasoning capabilities that are impressive, such as writing code given a flow chart or creating stories based on an image. In the development process, evaluation is critical since it provides intuitive feedback and guidance on improving models. Distinct from the traditional train-eval-test paradigm that only favors a single task like image classification, the versatility of MLLMs has spurred the rise of various new benchmarks and evaluation methods. In this paper, we aim to present a comprehensive survey of MLLM evaluation, discussing four key aspects:

1. the summarised benchmarks types divided by the evaluation capabilities, including foundation capabilities, model self-analysis, and extented applications;
2. the typical process of benchmark counstruction, consisting of data collection, annotation, and precautions;
3. the systematic evaluation manner composed of judge, metric, and toolkit;
4. the outlook for the next benchmark.

This work aims to offer researchers an easy grasp of how to effectively evaluate MLLMs according to different needs and to inspire better evaluation methods, thereby driving the progress of MLLM research.

## 价值指标（评测维度）

评测体系四维：

- 能力分类
- 构建流程
- judge
- metric
- toolkit

**价值不在分数，在于给出可复用的评测工程框架。**

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：① 综述与评测方法论
- **应用场景**：评测体系设计、benchmark 选型、toolkit 选型