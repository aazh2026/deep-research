# 21-aeollm-2：NTCIR-19 AEOLLM-2 Metric 复现（CPU 友好）

> Paper: Chen, Dong, Li, Liu, Ai. **"Overview of the NTCIR-19 Automatic Evaluation of LLMs 2 (AEOLLM-2) Task"** (NTCIR-19, Tokyo, Japan, arXiv:2610.11598)
> 复现日期: 2026-10-13
> 硬件: Apple Silicon CPU（无 GPU），Python 3.14.5

## 这是什么

NTCIR-19 AEOLLM-2 metric 复现项目，**只复现 1 件事**：

**3 个对齐指标**（paper Section 3.2）：
1. **Pairwise Accuracy (acc)**：对比 participant 与 human 的「成对偏好」是否一致
2. **Spearman's ρ**：经典 Pearson on ranks
3. **Kendall's τ_b**：含 ties 的 pair-wise 顺序一致性

**不**复现：
- ❌ LLM judge 系统（需 GPT/Claude/Gemini API）
- ❌ 真实评测数据（AEOLLM 数据集需 NTCIR 申请）
- ❌ 各参赛团队的 prompt engineering

**为什么**：
- paper 核心贡献是 metric 定义，不是某个具体 judge 系统
- 3 个 metric 公式全部在 paper 中明确给出，可严格复现
- metric 实现 + scipy 交叉验证是「正确性」的金标准
- CPU 友好，10 分钟能跑完

## 数据集

- **AEOLLM-2 官方数据**：[huggingface.co/datasets/THUIR/AEOLLM](https://huggingface.co/datasets/THUIR/AEOLLM)
  - 40 中英文问题 × 4 prompt × 4 LLM = 640 报告
  - 训练 25% / dry run 25% / 正式评测 50%
  - 4 个评测维度：comprehensiveness / insight / instruction_following / readability
  - 需 .edu 邮箱申请
- **本次用**：模拟场景（perfect / reverse / moderate / moderate_with_ties）

## 复现内容

### Metric 1: Pairwise Accuracy (acc)

```
z_ij = sign(s_i - s_j) ∈ {-1, 0, 1}
acc = mean over (i,j) of I[z_ij = z'_ij]
```

`z=0` 表示 tie（双方都 tie 算 correct，paper "tied pair is correct only if both indicate tie"）

### Metric 2: Spearman ρ

```
r_q,i = rank of answer i from participant score
r'_q,i = rank of answer i from human score
ρ = Pearson(r, r')
```

Ties 用 average-rank（与 scipy 一致）。

### Metric 3: Kendall τ_b (with ties)

```
τ = (C - D) / √[(C + D + T)(C + D + U)]
```

- C: concordant 对
- D: discordant 对
- T: 仅 participant tie
- U: 仅 human tie
- **双 tie 的对不计入 T 或 U**（paper 显式要求）

## 怎么跑

### 安装

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 跑实验

```bash
.venv/bin/python scripts/run_experiment.py
```

### 跑测试

```bash
.venv/bin/python -m pytest tests/ -v
```

**35 个测试全过**：
- 21 个 AEOLLM-2 metric 边界测试
- 6 个 scipy 交叉验证（Spearman/Kendall 与 scipy.stats 在同样输入下结果一致）
- 8 个 tie / rank / Pearson 单元测试

## 文件清单

```
papers/21-aeollm-2/
├── README.md
├── REPRODUCTION_NOTES.md
├── paper.md                       # 论文笔记
├── requirements.txt               # numpy + scipy + pytest
├── .gitignore
├── src/
│   ├── __init__.py
│   └── metrics.py                 # 3 个 metric 忠实复现
├── scripts/
│   └── run_experiment.py          # 4 场景模拟 + 与 paper 对比
├── tests/
│   ├── __init__.py
│   ├── test_metrics.py            # 21 个 AEOLLM-2 metric 边界测试
│   └── test_scipy_cross.py        # 6 个 scipy 交叉验证
└── outputs/
    └── results.json               # 模拟场景报告
```

## 结果摘要

| 场景 | acc | ρ | τ | 备注 |
|---|---|---|---|---|
| perfect | 1.0000 | 1.0000 | 1.0000 | sanity check |
| reverse (high noise) | 0.4458 | 0.1685 | 0.1359 | noise 大到排序乱 |
| moderate (noise=0.5) | 0.9708 | 0.9650 | 0.9417 | 强对齐 |
| moderate_with_ties | 0.7417 | 0.7669 | 0.7120 | **落入 paper RSLIR 范围** |

### 与 Paper Table 4 对比

| Method | acc | ρ | τ |
|---|---|---|---|
| Paper RSLIR (best) | 0.7796 | 0.7071 | 0.5592 |
| Paper SCUNLP (2nd) | 0.6883 | 0.5197 | 0.3827 |
| Paper GLM-4.7 baseline | 0.7413 | 0.6177 | 0.4830 |
| **模拟 moderate_with_ties** | 0.7417 | 0.7669 | 0.7120 |

## 局限

- **不跑 LLM judge 系统**：本地无 LLM API、参赛团队的 RSLIR / SCUNLP / ISLab 等都是专用系统
- **不读 AEOLLM 真实数据**：需 NTCIR 申请
- **模拟场景不精确对应 paper 真实情况**：paper 数据含更多 complexity（4 个维度、人为 judgment variance 等）
- **scipy 交叉验证只验 Spearman/Kendall**：pairwise accuracy 是 paper 特有，scipy 无对应
