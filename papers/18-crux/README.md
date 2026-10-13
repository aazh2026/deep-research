# CRUX 评估框架复现项目

> 📄 论文笔记：[`paper.md`](paper.md)
> 📋 复现总结（**必读，含真实妥协与失败记录**）：[`REPRODUCTION_NOTES.md`](REPRODUCTION_NOTES.md)

## 一句话总结

完整复现 CRUX（Findings of EMNLP 2025）的**算法骨架**（Coverage / Density 公式 + 贪心 Oracle 构造 + BM25 retriever），用 **lexical overlap 替代 Llama-3.1-70B grader** + **Multi-News 50 样本子集** 在 Apple Silicon CPU 上端到端跑通，得到 **BM25 Cov=0.56 vs Oracle Cov=0.64** 的可对比指标，以及 **Cov 与 RAG 质量代理的 Kendall τ = 0.54**（论文报告 0.7-0.8）。

## 与论文的对应

| 模块 | 论文原版 | 本次复现 | 状态 |
|---|---|---|---|
| **Coverage 公式 (Eq. 3)** | `Cov(Z) = #{q ∈ Q | max G(p,q,I_g) ≥ η} / |Q|` | 同 | ✅ 忠实 |
| **Density 公式 (Eq. 6)** | `(Cov(Z)/tok(Z) / (Cov(Z*)/tok(Z*)))^w` | 同 | ✅ 忠实 |
| **阈值 η** | 3（LLM 0–5 评分） | **2**（lexical 0–5 评分） | ⚠️ 阈值偏移 |
| **权重 w** | 0.5 | 同 | ✅ 忠实 |
| **Oracle Z\* 构造** | 贪心：每次加能 answer 最多未覆盖 query 的 passage | 同 | ✅ 忠实 |
| **Grader G(p, q, I_g)** | Llama-3.1-70B（0–5 评分） | **lexical F1 缩放 0–5** | ⚠️ 关键妥协 |
| **Sub-question 生成** | Llama-3.1-70B 从 summary 生成 | **直接取 summary 前 N 句作为子问题** | ⚠️ 关键妥协 |
| **检索对比系统** | BM25、E5、BGE、Contriever | **BM25 + Random**（CPU 跑得动） | ⚠️ 简化 |
| **数据集** | CRUX-DUC（50）+ CRUX-Multi-News（100, ~500K passage） | **Multi-News test，50 样本** | ⚠️ 缩减 |
| **RAG 质量代理** | Llama-3.1-70B 生成质量 | **token F1(Z ∥ summary)** | ⚠️ 简化 |

## 项目结构

```
papers/18-crux/
├── README.md                          # 本文档
├── REPRODUCTION_NOTES.md              # 详细复现笔记
├── paper.md                           # 论文笔记
├── requirements.txt                   # 依赖（rank_bm25 + datasets + nltk）
├── src/
│   ├── data_loader.py                 # Multi-News 加载 + passage 切分
│   ├── grader.py                      # Lexical grader + sub-question 生成
│   ├── coverage.py                    # Coverage 公式 (Eq. 3)
│   ├── density.py                     # Density 公式 (Eq. 6) + Oracle 构造
│   └── retrievers.py                  # BM25 / Random / Oracle
├── scripts/
│   └── run_experiment.py              # 主实验入口
├── tests/
│   ├── test_grader.py                 # grader + tokenize 测试
│   ├── test_coverage.py               # Coverage 公式测试
│   └── test_density.py                # Density 公式 + Oracle 测试
└── outputs/
    └── results.json                   # 主实验报告
```

## 快速开始

### 1. 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. 跑单元测试

```bash
python tests/test_coverage.py
python tests/test_density.py
python tests/test_grader.py
```

### 3. 跑主实验

```bash
python scripts/run_experiment.py --n_queries 50 --top_k 20 --n_subquestions 5 --eta 2
```

输出 `outputs/results.json` + 控制台汇总。

## 复现结果

### 50 样本 × top_k=20 × 5 sub-questions × η=2

| Retriever | Cov | Den | RAG quality (token F1) | 平均 n_passages | 平均 tokens |
|---|---|---|---|---|---|
| BM25 | **0.562** | 0.366 | 0.295 | 18.1 | 593 |
| Random | 0.495 | 0.341 | 0.296 | 18.2 | 558 |
| Oracle (贪心) | **0.644** | **1.000** | 0.357 | 2.8 | 92 |

### 关键观察

- **BM25 > Random**（+0.07 Cov）：BM25 信号真实存在，不是 noise
- **Oracle > BM25**（+0.08 Cov）：仍有 0.08 提升空间 — 与论文「BM25 35–38% vs Oracle 64%」的相对差距方向一致
- **Oracle Den = 1.0**：自归一化验证
- **Oracle 用 2.8 个 passage 顶 BM25 的 18.1 个**：6.5× token 效率

### Kendall τ（Coverage / Density vs RAG 质量代理）

| | Cov vs RQ | Den vs RQ |
|---|---|---|
| 全部 47 样本 × 3 方法（141 配对） | **0.541** | 0.368 |
| 仅 BM25（47 配对） | 0.488 | 0.426 |

论文原版报告 Cov/Den vs RAG 质量 τ = 0.7–0.8。**我们用 lexical grader 拿到 0.54** —— 数量级一致但偏低，原因详见 REPRODUCTION_NOTES.md「妥协」一节。

## 已知妥协与改进方向

1. **Lexical grader ≠ LLM grader**：本次用 passage vs gold info 的 content-token F1 × 5 → 0–5 评分。LLM 能识别「改写但不丢失语义」的 passage，lexical 不能。改进：接 Qwen-7B 或 Llama-3.1-8B 等小 LLM 跑本地打分
2. **Sub-question 用 summary 前 N 句代替**：LLM 生成会避免「答案包含在问题里」的情况；我们用 summary 句当子问题时 grader 会「自报家门」拿满分。改进：让 LLM 从 summary 提取「信息点」而不是直接拿句
3. **只有 BM25 + Random 两个 baseline**：论文对比 E5 / BGE / Contriever / SPLADE 等。改进：把这些 dense retriever 加进对比
4. **50 样本 vs 100 论文查询**：CPU 上 50 样本已经 6.8s（含两次 Multi-News 加载），扩到 100 大约 14s
5. **RAG 质量代理 = token F1**：和真正的 LLM 生成质量会有差距，但作为「相对指标」可用
6. **η=2 vs 论文 η=3**：因为 lexical 评分整体偏低（很多「相关但不同表述」的 passage 在 lexical 下拿 1-2），硬上 η=3 会把所有方法压到几乎为 0

## 引用

```bibtex
@inproceedings{ju2025crux,
  title={CRUX: Controlled Retrieval-augmented Context Evaluation for Long-form RAG},
  author={Ju, Jia-Huei and Verberne, Suzan and de Rijke, Maarten and Yates, Andrew},
  booktitle={Findings of EMNLP},
  year={2025}
}
```
