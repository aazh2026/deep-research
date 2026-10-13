# 05 — InfographicVQA 复现

> 论文：Mathew, Bagal, Tito, Karatzas, Valveny, Jawahar.
> **"InfographicVQA"** (WACV 2022). [arXiv:2104.12756](https://arxiv.org/abs/2104.12756)

## 项目目标

在 **CPU / 无 VLM** 的约束下，忠实复现 InfographicVQA 的**评测方法**（ANLS metric）与**盲 baseline**，并用结果验证 paper 的核心 claim：「信息图 VQA 显著难于文档 VQA」。

## 目录结构

```
papers/05-infographicvqa/
├── README.md                       # 本文件
├── REPRODUCTION_NOTES.md           # 8 节复现笔记
├── requirements.txt
├── paper.md                        # 论文摘要
├── src/
│   ├── data_loader.py              # mm-eval/InfographicVQA → InfoVQAQuestion
│   ├── metrics.py                  # ANLS
│   └── baselines.py                # 6 个盲 baseline
├── tests/
│   ├── test_metrics.py             # 10 个 ANLS 测试
│   └── test_baselines.py           # 19 个 baseline 测试
├── scripts/
│   └── run_experiment.py           # 跑全 6 baseline，写 outputs/results.json
└── outputs/
    └── results.json                # 评测结果
```

## 数据集

- **HuggingFace**: [`mm-eval/InfographicVQA`](https://huggingface.co/datasets/mm-eval/InfographicVQA)
- **Split**: `validation`（2801 题）
- **Schema**:
  - `id`: int
  - `media`: list[PIL.Image]（1 张信息图）
  - `messages`: JSON 字符串，list of `{role, question, hint, options, choices}`
  - `answer`: list[str]（多 gold，ANLS 取 max）
  - `question_type`: `numeric` / `open` / `yes_no`

**重要差异**：本数据集**没有 OCR `words` 字段**（与 `nielsr/docvqa` 不同），因此**无法**做「OCR-lexical」类 baseline。本项目专注于**纯答案分布的盲 baseline**。

## ANLS metric

定义（与 03-docvqa 共用）：

```
NED = edit_distance(pred, gold) / max(len(pred), len(gold))
ANLS(q) = max over gold in gts of (1 - NED if NED < 0.5 else 0)
ANLS  = mean over q of ANLS(q)
```

## 盲 baseline（6 个）

| Baseline | 描述 | 适用题型 |
|---|---|---|
| `majority` | 全数据集最常出现的答案 | all |
| `random` | 按 train 答案分布加权采样 | all |
| `type_majority` | 按 `question_type` 分桶的 majority | all |
| `numeric_median` | numeric 题答训练集数字中位数 | numeric |
| `numeric_mode` | numeric 题答训练集数字众数 | numeric |
| `type_random` | 按 `question_type` 分桶随机采样 | all |

## 复现结果（val 2801）

| Baseline | ANLS | n |
|---|---:|---:|
| majority            | **0.0243** | 2801 |
| random              | 0.0072 | 2801 |
| type_majority       | **0.0345** | 2801 |
| numeric_median      | 0.0035 | 2801 |
| numeric_mode        | 0.0236 | 2801 |
| type_random         | 0.0174 | 2801 |

**Per-type (majority baseline)**:
- `numeric` (n=1342): ANLS = 0.0492
- `open`    (n=1458): ANLS = 0.0014
- `yes_no`  (n=1):    ANLS = 0.0000

**Paper baseline 对比**：paper Table 1 报告 SOTA 模型（LayoutLMv2 + IRRA 等）ANLS≈0.45–0.55。盲 baseline 远低于此，正是 paper 想突出的「信息图 VQA 比 DocVQA 难很多」。

## 跑法

```bash
# 1. 安装依赖
.venv/bin/pip install -r requirements.txt

# 2. 跑测试
.venv/bin/pytest tests/ -v

# 3. 跑实验（全 2801）
.venv/bin/python scripts/run_experiment.py

# 3'. 跑小子集（500）
.venv/bin/python scripts/run_experiment.py --max 500
```

## 局限

- **没有 OCR**：无法做 "lexical over OCR" baseline。
- **没有 VLM**：无法跑 paper 主线 SOTA（LayoutLMv2/IRRA 等），只能跑盲 baseline 锚定下限。
- **没看图像**：所有 baseline 只看 `query` 和 `answer`。
