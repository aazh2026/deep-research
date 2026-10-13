# 03-docvqa：DocVQA 复现（CPU 盲 baseline + ANLS metric）

> Paper: Mathew, Karatzas, Jawahar. **"DocVQA: A Dataset for VQA on Document Images"** (WACV 2021)
> 复现日期: 2026-10-13
> 硬件: Apple Silicon CPU（无 GPU），Python 3.14.5

## 这是什么

DocVQA 复现项目，**只复现 3 件事**：

1. **ANLS 官方 metric 公式**（τ=0.5 的 NED 归一化 Levenshtein 相似度，多 gold 取 max）
2. **多 gold max-sim 机制**（每题多个标注者答案，取与预测最接近的）
3. **盲 baseline 的下限锚定**（majority / random / lexical 检索——不读图）

**不**复现：
- ❌ LayoutLMv2 / T5 / BERT fine-tune（GPU 任务）
- ❌ 视觉 Transformer
- ❌ 真正的 VQA 模型推理

**为什么**：
- 本地无 GPU，跑不了 LayoutLMv2-base（约 200M 参数）
- ANLS metric 公式是 paper 核心可验证部分
- 盲 baseline 给出「不做视觉时能拿多少」的诚实下限

## 数据集

- 数据源：[nielsr/docvqa_1200_examples](https://huggingface.co/datasets/nielsr/docvqa_1200_examples)
- 原始数据：DocVQA train 39,463 题 / val 5,349 / test 5,188
- 本次用：1000 题（数据集会自动下载）
- 字段：id, image, query（多语言 dict）, answers, words, bounding_boxes, answer

## 复现内容

### ANLS 指标（`src/metrics.py`）

```python
ANLS(Q) = mean over Q of max( S(pred, gt) over all gold gts )
S(a, b) = 1 - NED(a, b)   if NED < τ
       = 0                 otherwise
NED = edit_distance / max(|a|, |b|)
τ = 0.5
```

**关键设计**：
- lowercase + strip 预归一化
- 多 gold 取 max
- NED ≥ τ 给 0（区分「轻微 OCR 错」vs「完全错」）
- 空 + 空 = 1.0

### Baseline（`src/baselines.py`）

| Baseline | 实现 | 期望 ANLS |
|---|---|---|
| **Majority** | 全数据集最常出现的答案 | ~1% |
| **Random** | 按 train 答案分布采样 | ~0% |
| **Lexical** | OCR 文本 + 关键词检索 + 4 个启发式 | ~3% |

Paper 报 LayoutLMv2 在 DocVQA test 集达到 ANLS 78.08，RoBERTa 约 70——盲 baseline 与之差两个数量级。

## 怎么跑

### 安装

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 跑实验

```bash
.venv/bin/python scripts/run_experiment.py --max_questions 1200
```

第一次会从 HF 下载数据集（约 13s，缓存到 `./cache`）。

### 跑测试

```bash
.venv/bin/python -m pytest tests/ -v
```

**48 个测试全过**：覆盖 ANLS metric + 3 个 baseline + 数据加载。

## 文件清单

```
papers/03-docvqa/
├── README.md
├── REPRODUCTION_NOTES.md
├── paper.md                       # 论文笔记
├── requirements.txt
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── data_loader.py             # 加载 nielsr/docvqa_1200_examples
│   ├── metrics.py                 # ANLS 公式
│   └── baselines.py               # majority / random / lexical
├── scripts/
│   └── run_experiment.py          # 主实验入口
├── tests/
│   ├── __init__.py
│   ├── test_metrics.py            # 24 个 ANLS 测试
│   └── test_baselines.py          # 24 个 baseline 测试
└── outputs/
    └── results.json               # 1000 题实验报告
```

## 结果摘要

| Split (n) | Majority | Random | Lexical |
|---|---|---|---|
| train (660) | 0.0061 | 0.0018 | 0.0316 |
| dev (170) | 0.0118 | 0.0000 | 0.0180 |
| test (170) | 0.0118 | 0.0000 | **0.0367** |

**对比**：
- 盲 baseline ≤ 4% ANLS
- Paper LayoutLMv2_base ANLS = 78.08（差 ~22 倍）
- 盲 baseline 证实 paper claim「视觉对 DocVQA 至关重要」

## 局限

- **不跑 LayoutLMv2 / T5**（CPU 跑不动）
- **不验证 BERT 路径**（GPU 训练）
- **lexical baseline 启发式覆盖不全**——只针对 title/date/关键词 3 种模式
- **多语言 query 只用英文版**——多语言扩展未做
- **切分比例不是 paper 原版**（paper 39K/5K/5K，我们按 train split 切成 660/170/170）
