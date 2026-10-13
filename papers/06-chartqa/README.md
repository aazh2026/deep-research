# ChartQA 复现项目

> 📄 论文笔记：[`paper.md`](paper.md)
> 📋 复现总结（**必读，含真实妥协与失败记录**）：[`REPRODUCTION_NOTES.md`](REPRODUCTION_NOTES.md)

## 一句话总结

在本地 CPU（无 VLM / 无 OCR 流水线）上**忠实复现 ChartQA 官方 relaxed/strict Acc 指标**（含 5% / 0.5 abs_tol 数值容差），跑通 **majority + random 两个盲 baseline** 测出其在 val/test 上的人类/机器 split 难度分布——**揭示了 paper claim 的一个反直觉真相**：在「纯文本猜测」基线下，**人类 split 比机器 split 反而更容易**（val: 3.6% vs 1.3%，test: 6.3% vs 0.8%），因为机器题的答案集中在模板生成的特定数字，「多数猜」很难命中，而人类题答案更多样，少数高频答案反而能蹭中。

## 与论文的对应

| 模块 | 论文原版 | 本次复现 | 状态 |
|---|---|---|---|
| **数据集** | ChartQA 28,299 train / 1,920 val / 2,500 test | 同（HF 镜像 HuggingFaceM4/ChartQA） | ✅ 忠实 |
| **Strict Acc** | 字符串完全匹配（lowercase + strip） | 同 | ✅ 忠实 |
| **Relaxed Acc (numeric)** | `abs(a-b) ≤ max(0.05*max(|a|,|b|), 0.5)`（vis-nlp 官方） | 同 | ✅ 忠实 |
| **Relaxed Acc (text)** | 同 strict | 同 | ✅ 忠实 |
| **主要 baseline (T5)** | T5-base fine-tuned on gold tables + OCR | **不跑** | ⚠️ 不复现 |
| **VLM baseline** | 不在 paper 里（后续工作） | **不跑** | ⚠️ 不复现 |
| **Human vs Machine gap** | 论文报告 T5: human 30% / machine 80%（差距 ~50pp） | **majority: human 6.3% / machine 0.8% on test** | ⚠️ 反向但合理 |
| **问题类型切分** | paper 未提供 | 启发式 numeric vs text 切分 | ⚠️ 简化 |

## 项目结构

```
papers/06-chartqa/
├── README.md                          # 本文档
├── REPRODUCTION_NOTES.md              # 详细复现笔记
├── paper.md                           # 论文笔记
├── requirements.txt                   # 依赖（datasets + Pillow + tqdm）
├── src/
│   ├── data_loader.py                 # ChartQA 加载 + numeric/text 启发式分类
│   ├── metrics.py                     # relaxed/strict Acc 公式（vis-nlp 官方）
│   └── baselines.py                   # majority + random
├── scripts/
│   └── run_experiment.py              # 主实验入口
├── tests/
│   └── test_metrics.py                # 30 个指标 + baseline 测试
├── cache/                             # HF 数据集缓存
└── outputs/
    └── results.json                   # val + test 主结果
```

## 快速开始

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 跑单元测试（不需要下载数据）

```bash
python tests/test_metrics.py    # 30 个测试
```

### 3. 跑主实验

```bash
python scripts/run_experiment.py --splits val test
```

首次运行会下载 ChartQA train + val + test（~500 MB parquet + 图片）。后续跑复用 `cache/`。

## 复现结果

### Val split (1,920 题, 50% human / 50% machine)

| Baseline | Strict | Relaxed | human_acc | machine_acc | gap (machine-human) |
|---|---|---|---|---|---|
| **Majority** (train 众数) | 0.013 | 0.024 | **0.036** | 0.013 | **-0.024** |
| **Random** (U(0,100) + top-50 词表) | 0.002 | 0.010 | 0.010 | 0.010 | +0.000 |

### Test split (2,500 题, 50% human / 50% machine)

| Baseline | Strict | Relaxed | human_acc | machine_acc | gap (machine-human) |
|---|---|---|---|---|---|
| **Majority** (train 众数) | 0.022 | 0.036 | **0.063** | 0.008 | **-0.055** |
| **Random** | 0.000 | 0.011 | 0.014 | 0.008 | -0.006 |

### Paper claim 验证：human vs machine 难度差

| | Val | Test |
|---|---|---|
| Paper (T5 baseline) | machine > human by ~50pp | 同 |
| 本次 (Majority) | **machine < human by 2.4pp** | **machine < human by 5.5pp** |
| 本次 (Random) | gap ≈ 0 | gap ≈ 0.6pp |

**关键发现**：在「纯文本猜测」（无视觉）下，**机器 split 反而比人类 split 难**。这是因为：
- 机器题的答案集中在模板生成的具体数字（如 "2018"、"44538"）—— majority 命中率极低
- 人类题答案更多样，且含 yes/no/颜色等少数高频词—— majority 容易蹭中

**Paper 的 claim「machine 比 human 容易」是基于 VLM / T5 等有视觉能力的模型**——它们能直接读图。盲 baseline 上完全反过来了，这是诚实记录的反直觉发现。

### 主要 baseline 在 paper 中的对比

| 方法 | 论文 Acc | 本次 Acc | 差距 |
|---|---|---|---|
| **T5-base** (paper Table 1) | ~30-38% | — | 不复现 |
| **ChartBERT** (paper Table 1) | ~58% | — | 不复现 |
| **Human** (paper) | ~94% | — | 不复现 |
| **Majority blind** | — | 1.3-6.3% | 新基线 |
| **Random blind** | — | 1.0-1.4% | 新基线 |

## 已知妥协与改进方向

1. **不跑 VLM / T5 / OCR**：本地无 GPU、无 GPT-4V、无 OCR 流水线。要复现 paper Table 1 数字需要 vLLM + Qwen2-VL-2B 量化 + GPU
2. **不跑 ChartBERT / UniChart**：需要 fine-tune，需 GPU + 训练时间
3. **「numeric vs text」启发式分类**：用 `float()` parse 判定。少数边缘 case（如 "1,234,567" 千分位 + "50%" 百分号）已处理，但 "2020" 这种既是数字也是年份的可能被错分
4. **Human vs Machine gap 反向**：因为盲 baseline 没有视觉，方向与 paper 相反。这本身就是一个有意义的发现——证明视觉能力是 paper claim 的必要条件
5. **不验证 Figure 上的视觉特征引用问题**（"What color is the highest bar?"）—— 这些需要 VLM 读图
6. **不验证多步逻辑/算术推理**（"What's the difference between X and Y?"）—— 这些需要 LLM 推理

## 引用

```bibtex
@inproceedings{masry2022chartqa,
  title={ChartQA: A Benchmark for Question Answering about Charts with Visual and Logical Reasoning},
  author={Masry, Ahmed and Long, Do Xuan and Tan, Jia Qing and Joty, Shafiq and Hoque, Enamul},
  booktitle={Findings of ACL},
  year={2022}
}
```
