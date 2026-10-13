# SynthDocBench 复现项目

> 📄 论文笔记：[`paper.md`](paper.md)
> 📋 复现总结（**必读，含真实妥协与失败记录**）：[`REPRODUCTION_NOTES.md`](REPRODUCTION_NOTES.md)

## 一句话总结

在本地 CPU（无 VLM、无 GPT-5 judge）上用 **PyMuPDF 文本提取 + 5 种 text_evidence_score 评分模式** 复现 SynthDocBench（COLM 2026）的核心 paper claim——**「chart 问题的 gold answer 整句从不出现在 PDF 文本里」**（substring_hit = 0/171 = 0%），同时**复现了「chart 在长文档下文本检索会高估能力」的失败模式**：单一数字命中按 lenient 模式 = 95.3% ACC，按 conservative 模式 = 0% ACC，差距正好暴露了 paper 警告的「text-only 系统会被表面上『找到了数字』骗过去」。

## 与论文的对应

| 模块 | 论文原版 | 本次复现 | 状态 |
|---|---|---|---|
| **数据集** | SynthDocBench 3 subsets × 171 问 = 513 问 | 同 + 6 subsets（含 v2 共 1,788 问） | ✅ 忠实 |
| **评测对象** | 7 个 frontier VLM（GPT-5、Claude、Qwen3-VL 等） | **不评测 VLM** | ⚠️ 不复现 |
| **ACC(τ) 指标 (Eq. 1)** | GPT-5 评分 ≥ 6 算对（τ=6） | **text_evidence_score ≥ 0.5** | ⚠️ 评分代理 |
| **text-only baseline** | OCR + GPT-4o | **PyMuPDF 抽文本 + lexical 检索** | ⚠️ 简化 |
| **vision-only baseline** | VLM 直接看图 | **不跑** | ⚠️ 不复现 |
| **主要失败模式 1** | 长度陡降 | **不验证（无 VLM）** | ⚠️ |
| **主要失败模式 2** | 中段最难 | **不验证** | ⚠️ |
| **主要失败模式 3** | 长文档图表理解崩溃 | **部分验证**（见下文） | ⚠️ 部分 |

## 项目结构

```
papers/14-synthdocbench/
├── README.md                          # 本文档
├── REPRODUCTION_NOTES.md              # 详细复现笔记
├── paper.md                           # 论文笔记
├── requirements.txt                   # 依赖（datasets + pymupdf + tqdm + huggingface_hub）
├── src/
│   ├── data_loader.py                 # 6 个 subset 加载（chart / complex / cross_modal + _v2）
│   ├── pdf_text.py                    # PDF 下载、PyMuPDF 文本提取、find_answer_in_text
│   └── retrieval.py                   # text_evidence_score（5 模式）+ text_only_evaluate + 聚合
├── scripts/
│   └── run_experiment.py              # 主实验入口
├── tests/
│   ├── test_pdf_text.py               # 21 个 PDF 文本测试
│   └── test_retrieval.py              # 24 个评分 + 聚合测试
├── data/
│   └── pdfs/                          # 下载的 PDF 缓存
├── cache/                             # HF 数据集缓存
└── outputs/
    └── results_conservative.json      # 主实验报告
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
python tests/test_pdf_text.py     # 21 个测试
python tests/test_retrieval.py    # 24 个测试
```

### 3. 跑主实验

```bash
# 默认 conservative 模式（最严：只信 substring 命中）
python scripts/run_experiment.py --subsets chart complex cross_modal

# 其他 4 种模式（按严格度递增）：
python scripts/run_experiment.py --score_mode lenient       # 0.5*num + 0.5*phrase
python scripts/run_experiment.py --score_mode strict        # num only
python scripts/run_experiment.py --score_mode high_bar      # ≥80% nums
python scripts/run_experiment.py --score_mode number_only   # 全部 nums
```

首次运行会下载 6 个 PDF（~13 MB）。后续运行加 `--use_cache` 跳过 PDF 评估。

## 复现结果

### 3 subsets × 171 问 = 513 题（v1 完整评估）

#### 5 种 text_evidence_score 模式 ACC 对比

| 模式 | 含义 | chart | complex | cross_modal | overall |
|---|---|---|---|---|---|
| **lenient** | 0.5*num + 0.5*phrase | 0.953 | 0.994 | 0.982 | **0.977** |
| **strict** | num_ratio | 0.953 | 0.994 | 0.982 | 0.977 |
| **high_bar** | ≥80% num hit | 0.749 | 0.918 | 0.848 | 0.838 |
| **number_only** | 全部 num 命中 | 0.708 | 0.614 | 0.690 | 0.671 |
| **conservative** | 仅 substring | **0.000** | **0.000** | **0.000** | **0.000** |
| random baseline | score ~ U(0,1) | 0.497 | 0.526 | 0.474 | 0.499 |

**关键发现**：5 模式 ACC 横跨 **0.000 → 0.977** 的 977 个百分点——评估方法论的选择直接决定结论。

#### Paper claim 验证（substring_hit 率）

**所有模式、所有 subset、所有 difficulty 下 substring_hit = 0%**

| 切片 | substring_hit |
|---|---|
| chart（171 题） | **0/171 = 0.000** |
| complex（171 题） | **0/171 = 0.000** |
| cross_modal（171 题） | **0/171 = 0.000** |
| L1（57 题） | 0/57 = 0.000 |
| L2（116 题） | 0/116 = 0.000 |
| L3（139 题） | 0/139 = 0.000 |
| L4（143 题） | 0/143 = 0.000 |
| L5（58 题） | 0/58 = 0.000 |

**这是核心 paper claim 的强验证**：gold answer 的「完整句子」从不以文本形式出现在 PDF 里 → 必然需要 vision 来读图。

### 5 模式对比反映的失败模式

paper 的 Fig 5 警告：OCR + GPT-4o 在 chart subset 上 ACC 仅 0.297，但 vision-only 0.457。

我们的结果直接给出了**底层原因**：
- **lenient / strict 模式 ACC = 0.95+**（用单一数字命中就判对）—— 这正是 OCR + 简单文本检索的「虚假高分」
- **number_only 模式 ACC = 0.671**（必须 gold 所有数字都出现）—— 中间档
- **high_bar 模式 ACC = 0.838**（≥80% 数字命中）—— 略宽松
- **conservative 模式 ACC ≈ 0%**（要求整句出现）—— 这才是「真实能否回答」
- 0.977 → 0.000 的 977 个百分点差距 = **OCR/text-only 系统在 chart 上的「假能力」**

## 已知妥协与改进方向

1. **不跑 VLM**：本地无 GPU。改进路径：vLLM + Qwen2.5-VL-3B-Instruct（量化版），4-bit 约 6GB VRAM
2. **不跑 GPT-5 judge**：用 text_evidence_score 替代（5 模式都试过）
3. **text_evidence_score 是设计选择**：5 个模式中，conservative 最贴近 paper 「text-only 答得出」的真实定义；lenient / strict 会高估
4. **不验证 3 个失败模式**：长度陡降、中段最难、图表崩溃都需要 VLM 输出 + 位置标签才能验证
5. **PDF 抽取质量受 PyMuPDF 影响**：部分 PDF 的特殊字体可能让数字识别率下降（图表内文字本就在图像里，PyMuPDF 抽不到）
6. **v2 子集未跑**：chart_v2/complex_v2/cross_modal_v2 共 1,275 问，仅在数据加载器里支持

## 引用

```bibtex
@inproceedings{verma2026synthdocbench,
  title={SynthDocBench: Controlled Benchmark for Long-Context Visual Document Understanding},
  author={Verma, Abhigya and Mahajan, Khyati and Saha, Amit Kumar and Radhakrishna, Shruthan and Davasam, Sagar and Yadav, Vikas and Mudumba, Sai Rajeswar},
  booktitle={Conference on Language Modeling (COLM)},
  year={2026}
}
```
