# SlideVQA: A Dataset for Document VQA on Multiple Images

## 基本信息

- **论文标题**：SlideVQA: A Dataset for Document VQA on Multiple Images
- **作者**：Ryota Tanaka, Kyosuke Nishida, Kosuke Nishida, Taku Hasegawa, Itsumi Saito, Kuniko Saito
- **发表年份**：2023
- **venue**：AAAI 2023
- **arXiv**：2301.04883
- **提交日期**：2023-01-12
- **分类**：cs.CL, cs.CV
- **原文链接**：https://arxiv.org/abs/2301.04883

## 核心价值

针对 PPT 演示文稿，把「跨页证据选择 + 问答」统一到一个 seq2seq 任务里，是跨图推理的代表。

## 关键贡献

- 2.6k+ 演示文稿 / 52k+ 页 / 14.5k 问
- 覆盖单跳、多跳、数值推理
- 标注算术表达式与文本/视觉元素 bbox
- 提出 **M3D**（FiD 骨架 + 统一证据选择与生成 + 符号计算）

## 摘要

Visual question answering on document images that contain textual, visual, and layout information, called document VQA, has received much attention recently. Although many datasets have been proposed for developing document VQA systems, most of the existing datasets focus on understanding the content relationships within a single image and not across multiple images.

### 主要贡献

- **新数据集**：SlideVQA 含 2.6k+ 演示文稿 / 52k+ 幻灯片图像 / 14.5k 跨页问题
- **复杂推理**：支持单跳、多跳与数值推理
- **算术表达式标注**：提供数值答案的算术表达式
- **端到端模型**：统一 seq2seq 格式的证据选择与问答模型
- **结论**：模型优于现有 SOTA，但与人类仍有显著差距

## 价值指标（规模 / 成绩 / 指标）

- 人类 F1 ≈92%
- **M3D 证据选择 EM 75.0**
- 算术题 +**10.4** F1
- 联合 F1(JF1) **37.3**
- 指标：**EM**、**JF1**

## 整理备注

- **整理来源**：文档解读类 AI 任务评测：论文与方法总表（2026-10-12）
- **类别**：④ 多页 / 长文档评测
- **应用场景**：PPT 演示文稿问答、跨图推理、多页证据选择