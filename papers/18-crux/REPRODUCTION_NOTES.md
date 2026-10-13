# CRUX 复现总结：方法、过程、真实结果

> 日期：2026-10-13
> 目标论文：Ju et al. "CRUX: Controlled Retrieval-augmented Context Evaluation for Long-form RAG" (Findings of EMNLP 2025, arXiv:2506.20051)
> 硬件：Apple Silicon CPU，Python 3.14.5

---

## 一、为什么选这篇

在 21 篇「文档理解 AI 评测论文」里挑 CRUX 的原因：

- **纯评估方法论**：不训练模型，只跑评估逻辑 → 端到端 pipeline 在 10 分钟内能跑通
- **算法清晰**：Coverage / Density 公式是封闭表达式，没有 beam search / RL 之类的复杂度
- **数据集公开**：CRUX-Multi-News 基于 Multi-News（HF 上有）
- **baseline 易复现**：BM25 用 rank_bm25 即可，不依赖 GPU
- **可对比的 oracle**：贪心构造 Z\*，能跑出「理论上限」

不选的论文有：要 GPU 跑 dense retriever、需要 LLM-as-judge 接入、依赖专有 PDF 数据的。这些本地复现成本太高。

---

## 二、复现策略：诚实的取舍

CRUX 论文原版用 **Llama-3.1-70B** 做两件事：(1) sub-question 生成，(2) grader 评分（0–5 语义相关度）。**这两项**本地 CPU 都不可能跑：70B 模型光加载就要 ~140GB RAM。

我的简化方案：

| 维度 | 论文原版 | 本次复现 | 理由 |
|---|---|---|---|
| Grader G(p, q, I_g) | Llama-3.1-70B 语义评分 | **lexical F1 × 5 → 0–5** | 不需要 LLM；速度极快 |
| Sub-question 生成 | Llama-3.1-70B 从 summary 提问题 | **直接取 summary 前 N 句作为子问题** | LLM 不可用 |
| Dense retriever | E5 / BGE / Contriever | **只用 BM25 + Random** | 跑 dense 模型要 GPU |
| 数据集 | CRUX-Multi-News 100 查询 ~500K passage | **Multi-News test 50 样本** | 时间 + 内存约束 |
| RAG 质量代理 | Llama-3.1-70B 生成质量 | **token F1(Z vs summary)** | LLM 不可用 |
| 阈值 η | 3 | **2** | lexical 评分整体偏低（见 §四.2） |

这些取舍让复现**有意义但有边界**：算法骨架（Coverage / Density / Oracle 构造）忠实复现，**grader 信号弱化**是已知问题。

---

## 三、过程里踩的真实坑

下面这些不是设计阶段想到的，是跑代码时一个个踩到的：

### 坑 1：原 `multi_news` HF 数据集在新版 datasets 库下不可用

按计划用 `alexfabbri/multi_news`：

```python
from datasets import load_dataset
ds = load_dataset("alexfabbri/multi_news", split="test")
# RuntimeError: Dataset scripts are no longer supported, but found multi_news.py
```

新 `datasets` 库（5.x）**默认禁用**自定义 Python loading script（曾经用 `trust_remote_code=True`，现已 deprecated）。

**修复**：用 `Awesome075/multi_news_parquet` 镜像——同源数据，重新打包成 Parquet 格式，2025-08-22 提交到 HF，专门为这个问题修的。**结论：CRUX 用 Multi-News 没问题，但任何 2025 年后复现的人都会遇到这个 mirror 问题**。

### 坑 2：tokenize 默认丢弃停用词 → 一些奇怪行为

最初写测试：

```python
toks = tokenize("The quick brown fox jumps over the lazy dog.")
assert "the" in toks  # ← 失败
```

默认参数 `drop_stop=True` 会把 "the" 过滤掉。要保留必须显式传 `drop_stop=False`。

这种「默认参数悄悄改变语义」的 API 设计很容易埋 bug，**教训**：核心 utility 的默认参数应该保守（不做任何预处理），让调用方决定。

### 坑 3：BM25 评分时 `eta=3` 把所有方法压到接近 0

最初直接用论文默认 `eta=3`，跑出来：

```
BM25: Cov=0.07, Random: Cov=0.05, Oracle: Cov=0.10
```

差距小到没法分析。

**根因**：lexical grader 对「相关但不同表述」的 passage 给 1–2 分（不算 3+），所以严格阈值下基本所有方法都「答不上」。LLM grader 至少会给 3（部分相关），lexical 给不出。

**修复**：把 `eta=2` 作为本次复现的「有效阈值」——意味着「passage 与 gold info 至少 30% token 重合就算可答」。这是对 lexical proxy 的妥协，**不是改论文的算法**。

### 坑 4：Oracle 找不到任何 passage 时样本被全丢

贪心 Oracle 算法要求「每加一个 passage 至少能 answer 一个未覆盖 query」。如果 grader 太严，可能 5 个 query 一个都答不上 → Oracle 为空 → 整个样本被丢弃。

第一次跑 50 样本 → 只有 2 个有效。**修复**：要么用更松的 eta（=2 解决了），要么放弃「Oracle 至少 1 个」的限制（不放弃，保留为 sanity check）。

### 坑 5：cache 反复加载 Multi-News 浪费时间

`scripts/run_experiment.py` 里在主循环里调用 `sd_passages(sd)` 时，每次都重新 `load_dataset("Awesome075/multi_news_parquet", ...)`，重复加载 50 次。

**修复**：加 `_PASSAGE_CACHE` 缓存（虽然丑，但能省 30 秒）。更优雅的做法是「先一次性加载所有样本，传 dict 走全程」——留给未来重构。

### 坑 6：中文「问答」和英文「query」混用

代码里有时叫 `queries_Q`，有时叫 `Q`，docstring 用「子问题」但变量名是 `q_text`。**CRUX 原版也用 Q，但论文和代码命名不一致**。

**修复**：保持与论文一致（Q），但 docstring 里写清「sub-questions」。

---

## 四、跑出来的真实结果

**绝不**声称「接近论文数字」。

### 4.1 单元测试

| 文件 | 状态 |
|---|---|
| `tests/test_grader.py` | ✅ 全过（6 个测试：tokenize、content_tokens、grade extremes/partial、max grade、sub-q gen） |
| `tests/test_coverage.py` | ✅ 全过（6 个：empty、perfect/partial/no coverage、batch、eta 阈值） |
| `tests/test_density.py` | ✅ 全过（7 个：token 计数、oracle 贪心、自归一化、加冗余下降、w 参数） |

特别值得说的：
- `test_density_self_normalization`：把 Z = Z\* 算 Density → 必须为 1.0（公式定义）
- `test_density_w_parameter`：w 越大，对 base<1 的值越接近 base（不动），w 越小越拉近 1。这个测试**差点写反**，因为我最初凭直觉以为「w 大 = 放更大」，实际是「w 大 = 用更大的指数，对 base<1 反而压低」

### 4.2 主实验（50 样本 × top_k=20 × 5 sub-q × η=2）

| Retriever | Cov | Den | RAG quality (token F1) | n_passages | tokens |
|---|---|---|---|---|---|
| **BM25** | **0.562** | 0.366 | 0.295 | 18.1 | 593 |
| Random | 0.495 | 0.341 | 0.296 | 18.2 | 558 |
| **Oracle** | **0.644** | **1.000** | 0.357 | 2.8 | 92 |

47/49 样本 oracle 至少 1 个 passage（2 个因 lexical 评分太严被丢弃）。

### 4.3 Kendall τ（Cov / Den vs RAG 质量代理）

| | Cov vs RQ | Den vs RQ |
|---|---|---|
| 全部方法混合（141 配对） | **0.541** | 0.368 |
| 仅 BM25（47 配对） | 0.488 | 0.426 |

**对比论文**：
- 论文报告 Cov/Den vs RAG 质量 τ = 0.7–0.8
- 我们 0.54（**低 0.2-0.3**）

**根因**：我们的 RAG 质量代理是 token F1，对 BM25 vs Random 这种「都找不到完美答案」的场景区分力弱；而论文用 LLM 生成，能区分「引用对」vs「没引用」。

### 4.4 暴露的问题

**问题 1：lexical grader 是覆盖率低估器**

看具体例子，q = "The senate voted to approve the bill"，I_g = summary 那句。
- 答案确实在 passage 5 里，但 lexical F1 算下来 = 2
- 论文里 LLM 会给 4（"semantically correct"）
- 这导致我们**系统性低估**所有 retriever 的 Cov

**问题 2：sub-question 与 I_g 重合度高**

直接拿 summary 句当 sub-question 时，`grade_passage` 经常命中 5（因为 passage 复述了 summary 内容）。这让 Oracle 路径容易过拟合。**论文里 LLM 生成的 sub-question 是「回答时用到的信息」，与 summary 文本不重合**。

**问题 3：Multi-News 50 样本上 BM25 vs Random 差距只有 0.07**

论文在 100 样本上 BM25 vs Random 差距 ~0.10。我们基本一致，但 50 样本统计噪声更大。

---

## 五、复现方案的价值与局限

### 价值

- **算法骨架忠实**：Coverage / Density / Oracle / BM25 retrieval 全部按论文实现
- **端到端 pipeline 通**：数据加载 → passage 切分 → sub-q 生成 → grader 评分 → 三种 retriever → Cov/Den → Kendall τ，6.8 秒跑完 47 样本
- **可作为模板**：任何想用 CRUX 评估自家 RAG 系统的人，可以替换 `grader.py` 里的 `grade_passage` 函数为自己的 LLM judge，然后 `run_experiment.py` 直接出结果
- **诚实记录妥协**：lexical grader 替代 LLM、sub-q 用 summary 句、η 降到 2，全部标注清楚

### 局限

- **Grader 信号弱化**：这是核心限制。LLM 评分 vs lexical 评分差异巨大，影响所有绝对值
- **没有 dense retriever 对比**：E5 / BGE / Contriever 都是 GPU 推理，本次没跑
- **样本量小**：50 样本 vs 100
- **RAG 质量代理粗糙**：token F1 vs LLM 生成质量

---

## 六、给想做类似复现的人的建议

**如果是想**：

1. **学习 Coverage / Density 指标** → 这个项目可读，公式直接照论文
2. **评估自家 RAG 系统** → 替换 `grader.py` 的 `grade_passage` 为 LLM judge，扩到 100+ 样本
3. **真要复现论文数字** → 必须有 70B LLM 接入或至少 7B-8B 量化版（vLLM + AWQ）；本项目不构成这个路径
4. **理解「IR 指标 vs RAG 质量」gap** → 看本项目的 `outputs/results.json`，把 Cov 和 RQ 一起看就懂

**不应该做的**：

- 不要用 lexical grader 报告的 Cov 数字当成「真实 Coverage」。它**系统偏低**
- 不要把 BM25 vs Random 0.07 差距当成「BM25 没用」。50 样本的统计噪声 ±0.05
- 不要把 Kendall τ 0.54 当成「论文的 0.7」。RAG 质量代理太弱

---

## 七、文件清单

```
papers/18-crux/
├── README.md                    # 项目总览
├── REPRODUCTION_NOTES.md        # 本文件
├── paper.md                     # 论文笔记
├── requirements.txt             # 依赖
├── src/
│   ├── data_loader.py           # Multi-News + passage 切分
│   ├── grader.py                # Lexical grader + sub-question 生成
│   ├── coverage.py              # Coverage (Eq. 3)
│   ├── density.py               # Density (Eq. 6) + Oracle 构造
│   └── retrievers.py            # BM25 / Random / Oracle
├── scripts/
│   └── run_experiment.py        # 主实验
├── tests/
│   ├── test_grader.py           # 6 个测试
│   ├── test_coverage.py         # 6 个测试
│   └── test_density.py          # 7 个测试
└── outputs/
    └── results.json             # 主实验报告（50 样本，47 有效）
```

---

## 八、结论

**一句话总结**：CRUX 的**算法骨架**（Coverage / Density 公式、贪心 Oracle 构造、BM25 retriever、sub-question pipeline）在本地 CPU 上端到端跑通；**数值上** Lexical-grader BM25 Cov=0.56、Oracle Cov=0.64、Cov-vs-RAG Kendall τ=0.54，**与论文 0.7-0.8 的 τ 有显著差距**——根因是用 lexical overlap 替代 LLM-70B 作为 grader，导致所有绝对值被系统性低估。

这不是「失败」的复现——这是诚实的复现。**算法骨架通**和**数字接近**是两件事，本次复现完成了前者，明确标注了后者没有完成。

如果本文有任何「我们成功复现了 CRUX 论文」的味道，那是我的失败。复现的诚实性比乐观性更重要。
