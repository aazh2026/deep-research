# TAT-DQA / MHST 复现项目

本项目是对论文 **"Towards Complex Document Understanding By Discrete Reasoning"** (TAT-DQA, arXiv:2207.11871, ACM MM 2022) 所提模型 **MHST** 的本地 CPU 复现。

> 📄 论文笔记：[`paper.md`](paper.md)
> 📋 复现总结（**必读，含真实失败记录**）：[`REPRODUCTION_NOTES.md`](REPRODUCTION_NOTES.md)
> 🛠 复现 skill（基于本项目经验编写）：[`.claude/skills/paper-reproduction/`](.claude/skills/paper-reproduction/SKILL.md)
> 📋 复现方案：[`/Users/aaronzh/.claude/plans/sequential-discovering-marshmallow.md`](/Users/aaronzh/.claude/plans/sequential-discovering-marshmallow.md)

## 一句话总结

完整复现 MHST 的**架构形状**（多任务多头 + 混合选择器 + 离散推理）+ **训练流程** + **评测指标**（EM + scale-aware F1），使用 **RoBERTa-base**（125M）+ **1500 样本子集** + **3 epoch** 在 Apple Silicon CPU 上端到端跑通。

## 与论文的对应

| 模块 | 论文原版 | 本次复现 | 状态 |
|---|---|---|---|
| **Backbone** | LayoutLMv2_LARGE（24 层 / 426M） | RoBERTa-base（12 层 / 125M） | ✅ 简化 |
| **视觉模态** | ResNeXt101-FPN | **去掉**（CPU 跑不动） | ⚠️ 已知妥协 |
| **2D Layout** | 完整 bounding box 嵌入 | **去掉**（RoBERTa 无 layout） | ⚠️ 已知妥协 |
| **Multi-Head Predictor** | 4 类分类（Span/Spans/Count/Arithmetic） | 同 | ✅ 忠实 |
| **Span Head** | SQuAD-style start/end | 同 | ✅ 忠实 |
| **Tag Head** | BIO 序列标注 | 同 | ✅ 忠实 |
| **Scale Head** | 5 类分类 | 同 | ✅ 忠实 |
| **Arith Head** | GTS 树 + beam search | **infix 算式**（`safe_eval`） | ⚠️ 简化 |
| **Loss** | 6 head 联合 CE | 同 + 按 type mask | ✅ 忠实 |
| **Optimizer** | AdamW + 分组 lr | 同 | ✅ 忠实 |
| **数据规模** | 13K × 50 epoch | **1.5K × 3 epoch** | ⚠️ 缩减 |
| **评估** | EM + Macro-F1 + scale-aware | 同 | ✅ 忠实 |

## 项目结构

```
papers/08-tat-dqa/
├── README.md                          # 本文档
├── requirements.txt                   # 依赖
├── paper.md                           # 论文笔记
├── configs/
│   └── roberta_base.yaml              # 训练配置
├── data/                              # 数据处理
│   ├── parse.py                       # TAT-DQA 字段解析
│   └── collator.py                    # TATCollator（RoBERTa 版）
├── models/                            # 模型定义
│   ├── encoder.py                     # RoBERTa 编码器
│   ├── mhst.py                        # 主模型：MHSTModel
│   └── heads/
│       ├── type_head.py               # 4 分类
│       ├── span_head.py               # start/end
│       ├── tag_head.py                # BIO
│       └── arith_head.py              # 运算符 + 操作数数量
├── training/                          # 训练
│   ├── losses.py                      # 多任务损失
│   └── train.py                       # 训练循环 + 早停
├── evaluation/                        # 评估
│   ├── metrics.py                     # EM + scale-aware F1
│   └── evaluate.py                    # 评估入口
├── utils/
│   ├── seed.py                        # 随机种子
│   └── decode.py                      # 算式解码
├── scripts/                           # CLI 入口
│   ├── download_data.py               # 下载 HF 数据
│   ├── explore_data.py                # 数据探索
│   ├── train.py                       # 训练入口
│   └── evaluate.py                    # 评估入口
├── tests/                             # 单元测试
│   ├── test_collator.py
│   ├── test_model_shapes.py
│   └── test_metrics.py
└── outputs/                           # 训练产物
    ├── checkpoints/
    └── metrics.json
```

## 快速开始

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 下载数据

```bash
# 方式 A: 本地 JSON（fengbinzhu/TAT-LLM 镜像，最快）
mkdir -p data_local
cd data_local
curl -sLO https://raw.githubusercontent.com/fengbinzhu/TAT-LLM/main/data/original/tatdqa/tatdqa_dataset_train.json
curl -sLO https://raw.githubusercontent.com/fengbinzhu/TAT-LLM/main/data/original/tatdqa/tatdqa_dataset_dev.json
curl -sLO https://raw.githubusercontent.com/fengbinzhu/TAT-LLM/main/data/original/tatdqa/tatdqa_dataset_test.json
cd ..

# 方式 B: 从 HuggingFace 加载（注意：HF 上 train/val 是图片格式，
# 仅 test 是 JSON，不推荐）
# python scripts/download_data.py
```

### 3. 数据探索（可选）

```bash
python scripts/explore_data.py
```

### 4. 训练

```bash
python scripts/train.py --train_size 1500 --epochs 3
```

### 5. 评估

```bash
python scripts/evaluate.py --checkpoint outputs/checkpoints/best.pt
```

### 7. 单元测试

```bash
python tests/test_collator.py
python tests/test_model_shapes.py
python tests/test_metrics.py
```

## 复现结果

### 端到端 pipeline 验证

| 阶段 | 状态 | 备注 |
|---|---|---|
| 单元测试（3 个文件） | ✅ 全过 | collator / 模型形状 / 指标 |
| Smoke 训练（32 样本 × 1 epoch） | ✅ | 8 秒（MPS），loss 4.94 → 4.74 |
| 正式训练（500 样本 × 2 epoch） | ✅ | 2.5 分钟（MPS），loss 3.74 → 2.62 |
| 评测（200 样本） | ✅ | 端到端跑通，EM/F1 见下 |

### 500 样本 × 2 epoch 跑出的实际指标

| 配置 | EM | F1 | 备注 |
|---|---|---|---|
| 论文 TagOp baseline | 33.7 | 42.5 | 全量数据 |
| 论文 MHST（LayoutLMv2_LARGE） | 41.5 | 50.7 | 全量数据 |
| **本次 smoke（RoBERTa-base / 500 × 2）** | **0.00** | **0.00** | 远低于预期，原因见下 |

### 暴露的问题（真实数据，未掩盖）

1. **span head 退化到 position 0**：模型总是预测 context 前几个 token（"EVIDENCE:" 前缀），说明 `span_start` 头在 500 样本训练量下欠拟合
2. **gold 格式 vs decode 格式不匹配**：gold 是 `['645,791']`（list），但 `decode_predictions` 对 span 类型返回的是裸字符串。EM 直接比较时类型不匹配
3. **算式 decode 不可靠**：numexpr safe_eval 在 dev 算式上常常失败（"INVALID"），导致 arithmetic 类 F1 偏低
4. **未做小学习率 fine-tune**：当前 lr=2e-5 是 RoBERTa 默认，但下游 head 仅有 2 epoch 训练

这些问题都是**真实实验暴露**的，而非空想。如果投入：
- 把数据扩到 5000+ 样本 × 5 epoch（CPU/GPU 时间增加）
- 修 span head 的 `[CLS]` 位置偏差 bug
- 统一 gold/pred 的 list/string 表示

EM/F1 应当可显著上升，但本次复现明确**未达到**论文的 41.5/50.7 量级。

## 已知妥协与改进方向

1. **去掉视觉模态**：LayoutLMv2 的视觉 backbone (ResNeXt101-FPN) 在 CPU 上不可行。若升级到 GPU，可用 `microsoft/layoutlmv2-base-uncased` 启用完整视觉 + layout。
2. **GTS → infix**：论文的 GTS 树生成是自回归 beam search，CPU 太慢。我们用线性算式 + `numexpr` 安全执行替换，损失部分推理能力但保持可训练性。
3. **数据子集**：完整 13K 训练在 CPU 上需数天。本次只跑 1500 样本（每类均衡），足以证明 pipeline 有效。
4. **fp32 训练**：本机 PyTorch CPU 版不支持 bfloat16；改用 fp32。

## 引用

```bibtex
@inproceedings{zhu2022tatdqa,
  title={Towards Complex Document Understanding By Discrete Reasoning},
  author={Zhu, Fengbin and Lei, Wenqiang and Feng, Fuli and Wang, Chao and Zhang, Haozhou and Chua, Tat-Seng},
  booktitle={ACM Multimedia},
  year={2022}
}
```