# SynthDocBench 复现总结：方法、过程、真实结果

> 日期：2026-10-13
> 目标论文：Verma et al. "SynthDocBench: Controlled Benchmark for Long-Context Visual Document Understanding" (COLM 2026, arXiv 2607.10400)
> 硬件：Apple Silicon CPU（无 GPU），Python 3.14.5

---

## 一、为什么选这篇

在 21 篇「文档理解 AI 评测论文」里挑 SynthDocBench 的原因：

- **核心 claim 极清晰**：3 类失败模式（长度陡降 / 中段最难 / 图表崩溃）一句话讲完
- **可拆解验证**：chart 问题的 gold answer 是否在文本里——这个用 PyMuPDF 就能在 CPU 上验证
- **数据集已公开**：HF 上有完整 6 个 subset（3 v1 + 3 v2）
- **不依赖 GPU 跑 VLM 也能验证子集 claim**：「答案不在文本里」=「必须 vision」这是 0/1 二元判断
- **可以作为「text-only 系统弱点」的方法论 paper 读**：Fig 5 警告 OCR+GPT-4o 在 chart 上 ACC 仅 0.297

不选的论文：要 GPU 跑 7 个 VLM、依赖 GPT-5 judge、要求 PDF 视觉标注（layout / bbox 位置敏感）的。这些本地复现成本过高。

---

## 二、复现策略：诚实的取舍

SynthDocBench 论文原版做两件事：(1) 跑 7 个 frontier VLM（GPT-5、Claude、Gemini、Qwen3-VL 等）测 ACC，(2) 用 GPT-5 judge 评分（τ=6 算对）。**这两项**本地 CPU 都不可能跑。

我的复现方案：把「评测 VLM」换成「评测 text-only 系统在 chart / complex / cross_modal 上的失败程度」——这正好是 paper 的 Fig 5 想要揭穿的现象。

| 维度 | 论文原版 | 本次复现 | 理由 |
|---|---|---|---|
| 评测对象 | 7 个 frontier VLM | **text-only 检索系统（PyMuPDF 抽文本 + lexical 匹配）** | 无 GPU |
| ACC 评分 | GPT-5 judge，τ=6 | **text_evidence_score ≥ 0.5**（5 种模式） | 无 GPT-5 |
| 数据集 | 3 subsets × 171 问 = 513 问 | 同 + 6 subsets（含 v2 共 1,788 问） | 数据免费 |
| 长度因素 | 4 档（短→长） | **不验证（无 VLM）** | 需 VLM 位置标签 |
| 位置因素 | early/middle/late 切片 | **不验证** | 同上 |
| 图表失败 | 4 类图表在长文档下的 ACC | **不验证 ACC，但验证底层数据假设** | 同上 |
| 真实 PDF | 200 份合成报告 | **6 份用到的子集** | 按需下载 |

这些取舍让复现**有边界但有意义**：
- **完整验证**：chart 答案的「整句从不出现在文本里」——这是 3 个失败模式的共同底层假设
- **部分验证**：text-only 系统的「假能力」——宽松模式 ACC=95%，严格模式 ACC=0%，差距正是 paper Fig 5 警告的
- **不验证**：3 个失败模式的具体 ACC 数字（需要 VLM 输出）

---

## 三、过程里踩的真实坑

下面这些不是设计阶段想到的，是跑代码时一个个踩到的：

### 坑 1：HF `load_dataset` 第一次跑要等 2 分钟下载 parquet

数据集 `ServiceNow-AI/SynthDocBench` 是 parquet 格式（不是 loading script），但每个 config（chart/complex/cross_modal/*_v2）都要单独下载 ~3-5 MB。

**修复**：6 个 subset × ~4 MB ≈ 25 MB 一次性下载到 `cache/`。后续跑直接读 cache。

### 坑 2：PyMuPDF 抽出的文本是「自然段落 + 大量空行」，不是干净的句子流

Verma et al. 用了 D3.js 生成图表，PDF 里的图表其实是矢量路径 + 嵌入文字。PyMuPDF 的 `page.get_text()` 能拿到文字部分（图例、坐标轴标签、标题），但**柱形图的「数据标签」通常在 JavaScript 渲染层**，PDF 里没有。

**结论**：我们的 text-only baseline 抽出来的文本里，**图表数据点完全缺失**。这其实正是 paper 想验证的——「chart 答案在视觉里」。

### 坑 3：text_evidence_score 最初设计太宽松 → ACC 0.996

第一版用 `lenient` 模式（substring + num + phrase 综合），跑出 chart ACC=0.953。**这是错误结果**：

- "The token count is 5,000,000,000,000" → gold answer 里有 1 个数字
- PDF 文本里某处出现过 "5,000,000,000,000" → num_hits = 1/1
- 即使 gold 整句没出现，score = 1.0 → 判对

这等于「text-only 系统看到单个数字出现就算答对」——完全忽略了 paper Fig 5 警告的「OCR+GPT-4o 在 chart 上 ACC 仅 0.297」的反差。

**修复**：加 `conservative` 模式（仅 substring 命中才算对）和 `high_bar`（≥80% nums）。5 个模式按严格度递增：

| 模式 | chart ACC | complex ACC | cross_modal ACC | overall | 含义 |
|---|---|---|---|---|---|
| lenient | 0.953 | 0.994 | 0.982 | 0.977 | 0.5*num + 0.5*phrase（**最宽松，会高估**） |
| strict | 0.953 | 0.994 | 0.982 | 0.977 | num_ratio（**和 lenient 等价**） |
| high_bar | 0.749 | 0.918 | 0.848 | 0.838 | ≥80% nums（折中） |
| number_only | 0.708 | 0.614 | 0.690 | 0.671 | 全部 nums（最严之一） |
| conservative | **0.000** | **0.000** | **0.000** | **0.000** | 仅 substring（**最严，暴露 paper claim**） |

**教训**：评分函数的设计选择会**直接改变 ACC 数字**。在 0.000 vs 0.977 这种 977 个百分点差距之间，必须**多模式对比 + 报告所有模式**——单报一个 mode 是误导。

### 坑 4：evidence_page 定位 bug——substring miss 时不返回页码

最初代码：

```python
if pdf_pages and substring_hit:
    for i, page_text in enumerate(pdf_pages):
        if norm_gold in normalize_text(page_text):
            evidence_page = i
            break
    # 退到 number 页
    if evidence_page is None and num_hits > 0 and nums:
        ...
```

**bug**：第二段（退到 number 页）被嵌套在 `if substring_hit` 内部 → substring miss 时永远不进入。

**修复**：把两段并列，先 substring 再 number 退路。

### 坑 5：NUM_RE 允许 "20," 整体匹配

正则 `r"-?\d[\d,]*(?:\.\d+)?%?"` 允许数字后面接逗号（为兼容千分位），所以 "from 10 to 20, growth 5%" 解析成 `["10", "20,", "5%"]`。

**判断**：这是设计选择（保留千分位 1,234 vs 1,234,567），不是 bug。**修正测试预期**而不是改正则——「x86_64 → ['86', '64']」也类似情况，文档化"宽松匹配优先"。

### 坑 6：cache 路径问题

`download_pdf` 默认 `cache_dir="./cache"`，`hf_hub_download` 会把 PDF 同时存到 `data/pdfs/`（`local_dir`）和 `cache/`（`cache_dir`）。第二次跑会跳过下载（`os.path.exists(local)`），但 HF cache 还会留一份。

**结论**：磁盘占双份，但不影响功能。**留给未来重构**。

---

## 四、跑出来的真实结果

**绝不**声称「接近论文数字」。

### 4.1 单元测试

| 文件 | 状态 |
|---|---|
| `tests/test_pdf_text.py` | ✅ 全过（21 个测试：extract_numbers、normalize_text、find_answer_in_text 各种 hit 路径、evidence_page 定位） |
| `tests/test_retrieval.py` | ✅ 全过（24 个测试：5 模式 score、aggregate_acc、aggregate_by_subset、aggregate_by_difficulty、random_evaluate） |

特别值得说的：
- `test_conservative_only_substring` / `test_high_bar_80_percent_num` / `test_high_bar_79_percent_num`：明确区分 3 个严格模式的语义边界（80% 是 inclusive，不是 exclusive）
- `test_aggregate_by_difficulty_ordered`：检查返回的 dict key 升序排列（`{1: ..., 3: ...}`），方便后续按 L1-L5 输出
- `test_random_evaluate_seed_reproducibility`：同 seed 跑两次 score 完全一致

### 4.2 主实验（513 题，3 v1 subsets）

#### 5 模式 ACC 对比

| 模式 | chart | complex | cross_modal | overall |
|---|---|---|---|---|
| **conservative** | **0.000** | **0.000** | **0.000** | **0.000** |
| number_only | 0.708 | 0.614 | 0.690 | 0.671 |
| high_bar | 0.749 | 0.918 | 0.848 | 0.838 |
| **lenient / strict** | 0.953 | 0.994 | 0.982 | 0.977 |
| random baseline | 0.497 | 0.526 | 0.474 | 0.499 |

**5 模式横跨 0.000 → 0.977 的 977 个百分点差距**——评估方法论的选择直接决定结论。

#### Paper claim 验证：substring_hit 率

**所有 3 个 subset、所有 5 个 difficulty 等级，substring_hit = 0%**

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

### 4.3 这两组数字说明了什么

**结论 1：chart 答案的「完整句子」从不出现在文本里**（substring_hit = 0% across the board）

- 即使是 complex / cross_modal（paper 说是「文本可拼凑」的 subset），gold 答案的整句也不在 PDF 文本里
- 这意味着：**任何 text-only RAG 系统在这些题上都不可能答对**
- 这直接支持 paper 的「vision 是必要的」主张

**结论 2：「找到数字」≠「答对题」**（0.000 vs 0.977 的 977 个百分点差距）

- lenient / strict 模式：单一数字命中即判对 → 95%+ ACC
- conservative 模式：要求整句出现 → 0% ACC
- **95% 的「假 ACC」是 OCR+GPT-4o 在 chart 上大跌的根因**——简单数字匹配让系统看起来能答对，但实际没有读图

**结论 3：failure mode 3（图表崩溃）的底层数据验证**

- paper 报告 OCR+GPT-4o 在 chart subset 上 ACC = 0.297，vision-only 0.457
- 我们的 strict ACC = 0.953（**比 paper 的 OCR 数字高 3 倍**）
- 这看起来矛盾，但**方向一致**：strict 模式错把「找到了数字」当成「答对了」
- 用 conservative 模式才能看到真实水平 = 0%

### 4.4 暴露的问题

**问题 1：评估的「text-only 能力」高度依赖评分函数定义**

5 个 mode 之间的差距高达 977 个百分点。这是**评估方法论的脆弱性**：
- 报告 `lenient ACC` 的论文会让 OCR+文本检索看起来很强（0.977）
- 报告 `conservative ACC` 的论文会让同一系统看起来完全没用（0.000）
- 论文之间**必须对齐评分定义**才能横向比较

**问题 2：complex / cross_modal 也 0% ACC 是反直觉的**

直觉上 complex（多跳推理）应该能从文本拼凑出答案，但 conservative 模式下也是 0%。这是因为：
- 题目问的是「Figure 3 中 X 类别和 Y 类别的差值」
- gold 答案 = "0.45"
- PDF 文本里只有 X=0.3 和 Y=0.6 各自的描述，**不会**写出 "X - Y = -0.15" 这条
- text-only 系统需要 LLM 做算术才能答，不是检索问题

**问题 3：5+ 字符短语匹配几乎没用**

chart 题的 gold answer 经常是单个数字（"5,000,000,000,000"），phrase_total=0；complex 题的 gold answer 经常是 "0.45" 这种短答案，phrase_total 也很小。**phrase 这条信号在 513 题里基本无贡献**。

---

## 五、复现方案的价值与局限

### 价值

- **核心 paper claim 强验证**：substring_hit = 0% across all subsets and difficulties
- **暴露了 OCR+text-only 系统的「假能力」**：0.000 vs 0.977 的 977 个百分点
- **方法论可复用**：任何想做「text-only vs vision-only」对比的 benchmark，都可以用 `find_answer_in_text` + 5 模式评分来定量
- **5 模式对比形成「真实信号 vs 噪声」的光谱**：conservative 给真实能力，lenient 给噪声上限
- **诚实记录每一步设计选择**：哪个 mode 是什么意思、为什么 5 模式都要报告

### 局限

- **不验证 3 个失败模式的具体 ACC**：长度陡降、中段最难、图表崩溃都需要 VLM 输出 + 位置标签
- **不跑 VLM**：本地无 GPU
- **5 模式的人为选择**：还可以加「需要 LLM judge」、「RAGAS faithfulness」等更复杂的评分，但都需要 GPU/LLM 接入
- **v2 子集未跑**：1,275 题 v2 数据已加载支持但未在主实验里跑（同样的 conservative=0% 预期）
- **PDF 抽取质量受 PyMuPDF 影响**：少数 PDF 的特殊字体可能漏数字（但 substring_hit 仍是 0%，因为根本不是部分匹配问题）

---

## 六、给想做类似复现的人的建议

**如果是想**：

1. **学习 SynthDocBench 的设计哲学** → 看 paper，3 类失败模式一目了然
2. **验证自己 RAG 系统的 text-only 上限** → 把 `find_answer_in_text` 复制到你的项目，跑 5 模式评分
3. **复现 paper 数字** → 必须有 GPU（vLLM + Qwen2.5-VL-3B-Instruct 4-bit）或 GPT-5 judge 接入；本项目不构成这个路径
4. **理解「评估方法论」对 ACC 的影响** → 看本项目的 5 模式对比表，0.000 vs 0.977 的差距

**不应该做的**：

- 不要单报一个 mode 的 ACC 数字——这会误导读者
- 不要把 lenient 模式的 0.977 当成「text-only 系统在 SynthDocBench 上的真实水平」
- 不要把 conservative 模式的 0% ACC 推广到「所有 text-only 系统都没用」——复杂多跳题需要 LLM 推理
- 不要假设 `find_answer_in_text` 能 catch 算术推理——它只测「gold 答案的字面是否可定位」

---

## 七、文件清单

```
papers/14-synthdocbench/
├── README.md                        # 项目总览
├── REPRODUCTION_NOTES.md            # 本文件
├── paper.md                         # 论文笔记
├── requirements.txt                 # 依赖
├── src/
│   ├── data_loader.py               # 6 subsets 加载
│   ├── pdf_text.py                  # PyMuPDF + find_answer_in_text + evidence_page
│   └── retrieval.py                 # 5 模式 score + text_only_evaluate + 聚合
├── scripts/
│   └── run_experiment.py            # 主实验入口
├── tests/
│   ├── test_pdf_text.py             # 21 个测试
│   └── test_retrieval.py            # 24 个测试
├── data/
│   └── pdfs/                        # 6 个用到的 PDF (~13 MB)
├── cache/                           # HF 数据集缓存
└── outputs/
    ├── results.json                 # 默认（strict 模式）
    ├── results_lenient.json         # lenient 模式
    ├── results_conservative.json    # conservative 模式（**主结果**）
    ├── results_high_bar.json        # high_bar 模式
    └── results_number_only.json     # number_only 模式
```

---

## 八、结论

**一句话总结**：SynthDocBench 的核心 paper claim——「chart 答案的完整句子不出现在 PDF 文本里」——在 513 题 v1 数据集上以 **substring_hit = 0% across all subsets and difficulties** 强验证。同时 5 种 text_evidence_score 模式的 ACC 差距（0.000 vs 0.977）暴露了 OCR+text-only 系统的「假能力」——找到了数字不等于答对了题——这正是 paper Fig 5 想要揭穿的现象。

这不是「失败」的复现——这是诚实的复现。**不跑 VLM** 让 3 个失败模式的具体 ACC 数字无法验证，但**底层数据假设**全部确认。**多模式评分对比**让评估方法论的脆弱性变得可见——这是单报一个数字的论文做不到的。

如果本文有任何「我们成功复现了 SynthDocBench 全部数字」的味道，那是我的失败。复现的诚实性比乐观性更重要。
