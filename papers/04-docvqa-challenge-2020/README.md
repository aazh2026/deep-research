# 04-docvqa-challenge-2020：DocVQA Challenge 2020 复现（CPU 盲 baseline + ANLS/MAP）

> Paper: Mathew, Tito, Karatzas, Manmatha, Jawahar. **"Document Visual Question Answering Challenge 2020"** (arXiv:2008.08899, DAS 2020 / CVPR 2020 Workshop)
> 复现日期: 2026-10-13
> 硬件: Apple Silicon CPU（无 GPU），Python 3.14.5

## 这是什么

DocVQA Challenge 2020 复现项目，**只复现 3 件事**：

1. **ANLS metric 公式**（Task 1，与 03-docvqa 严格一致）
2. **MAP metric 实现**（Task 2，Mean Average Precision 文档检索）
3. **4 个盲 baseline 的下限锚定**（majority / random / lexical / span_exact）

**不**复现：
- ❌ LayoutLMv2 / T5 / BERT fine-tune（GPU 任务）
- ❌ PingAn-OneConnect Gammalab-DQA 冠军方案（VLM 联合）
- ❌ 视觉特征引用题

**为什么**：
- 本地无 GPU，跑不了 LayoutLMv2-base（约 200M 参数）
- ANLS + MAP metric 是 paper 核心可验证部分
- 盲 baseline 给出「不做视觉时能拿多少」的诚实下限
- paper Table 1 报 "Plain BERT QA" text-only baseline = 0.35 ANLS——这正是 text-only 上限，**我们的 span_exact baseline 是它的 8%**

## 数据集

- **Task 1 (VQA on Document Images)**：[nielsr/docvqa_1200_examples](https://huggingface.co/datasets/nielsr/docvqa_1200_examples)（与 03-docvqa 同源）
  - paper 报：50K QA / 12,767 imgs（test 5188 QA / 1287 imgs）
  - 本次用：1000 题

- **Task 2 (VQA on Document Image Collection)**：DocCVQA 14,362 imgs / 20 queries
  - paper 报：DQA 0.8090 MAP，DOCR 0.7915 MAP
  - 本次：本地无镜像，仅 toy 验证 MAP 实现

## 复现内容

### Metric 1: ANLS（Task 1, `src/metrics.py`）

```python
ANLS(Q) = mean over Q of max( S(pred, gt) over all gold gts )
S(a, b) = 1 - NED  if NED < τ
       = 0                 otherwise
NED = edit_distance / max(|a|, |b|)
τ = 0.5
```

### Metric 2: MAP（Task 2, `src/metrics.py`）

```python
AP(q) = (1/|R_q|) * sum over k where retrieved[k] in R_q of (precision at k)
MAP   = mean over q of AP(q)
P@k   = |top-k ∩ relevant| / k
R@k   = |top-k ∩ relevant| / |relevant|
```

### 4 个 Baseline（`src/baselines.py`）

| Baseline | 实现 | 期望 ANLS |
|---|---|---|
| **Majority** | 全数据集最常出现的答案 | ~1% |
| **Random** | 按 train 答案分布采样 | ~0% |
| **Lexical** | OCR 文本 + 关键词检索 + 4 启发式 | ~3% |
| **Span-Exact** | OCR 文本 + 关键词 overlap + 5-token 窗口抽取 | ~3% |

Paper Table 1 报告的 Plain BERT QA text-only baseline = **0.35 ANLS**——这是 text-only 模型的上限。我们的 span_exact 2-3% ANLS 是它的 8% 弱版本（无监督 + 简单关键词窗口）。

Paper Table 1 完整排名：

| Method | ANLS |
|---|---|
| PingAn-OneConnect Gammalab-DQA | **0.85** |
| Structural LM v2 | 0.75 |
| QA_Base_MRC_1 | 0.74 |
| HyperDQA_V4 | 0.69 |
| bert fulldata finetuned | 0.59 |
| **Plain BERT QA**（text-only） | **0.35** |
| HDNet | 0.34 |
| CLOVA OCR | 0.33 |
| docVQAQV_V0.1 | 0.30 |

## 怎么跑

### 安装

```bash
python3 -m venv .venv
.venv/bin/pip install datasets editdistance Pillow pytest
```

### 跑实验

```bash
.venv/bin/python scripts/run_experiment.py --max_questions 1000
```

第一次会从 HF 下载数据集（约 14s，缓存到 `./cache`）。

### 跑测试

```bash
.venv/bin/python -m pytest tests/ -v
```

**44 个测试全过**：覆盖 ANLS（13 个）、MAP（9 个）、P@k/R@k（6 个）、4 个 baseline（16 个）。

## 文件清单

```
papers/04-docvqa-challenge-2020/
├── README.md
├── REPRODUCTION_NOTES.md
├── paper.md                       # 论文笔记
├── requirements.txt
├── .gitignore
├── src/
│   ├── __init__.py
│   ├── data_loader.py             # Task 1 加载（与 03-docvqa 同源）
│   ├── metrics.py                 # ANLS + MAP
│   └── baselines.py               # 4 个盲 baseline（含 span_exact）
├── scripts/
│   └── run_experiment.py          # 主实验入口（Task 1 + Task 2 toy）
├── tests/
│   ├── __init__.py
│   ├── test_metrics.py            # 13 ANLS + 9 MAP + 6 P@k/R@k 测试
│   └── test_baselines.py          # 16 个 baseline 测试
└── outputs/
    └── results.json               # 1000 题 Task 1 + Task 2 toy 报告
```

## 结果摘要

### Task 1 (test split, n=170)

| Baseline | ANLS | 备注 |
|---|---|---|
| Majority | 0.0118 | 多数答案 |
| Random | 0.0000 | 答案分布采样 |
| Lexical | **0.0367** | 4 启发式 |
| Span-Exact | 0.0298 | 5-token 关键词窗口 |

### Task 2 (toy 模拟)

| 场景 | MAP | 备注 |
|---|---|---|
| 完美 retrieval | 1.0000 | 验证公式 |
| 弱 retrieval (BM25-like) | 0.1735 | paper 冠军 0.8090，差距 4.7x |

### Paper 报数对比

| 任务 | Paper Best | Paper Text-Only | 本次 (best blind) | 差距 |
|---|---|---|---|---|
| Task 1 ANLS | 0.85 (PingAn) | 0.35 (Plain BERT) | 0.0367 (lexical) | 9.5x vs Plain BERT |
| Task 2 MAP | 0.8090 (DQA) | — | 0.1735 (toy) | 4.7x |

## 局限

- **不跑 LayoutLMv2 / T5 / BERT fine-tune**（CPU 跑不动）
- **不跑 PingAn-OneConnect 冠军方案**（专用 VLM）
- **不验证 layout 特征引用**："标题在页面哪个位置" 需要 LayoutLMv2
- **Task 2 仅 toy 验证**——本地无 DocCVQA 14K 图像数据集
- **span_exact baseline 弱于 Plain BERT**——后者是有监督的 SQuAD-style span 抽取，我们只能做无监督关键词窗口
