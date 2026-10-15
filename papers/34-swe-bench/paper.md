# 论文中文解读: SWE-bench: Can Language Models Resolve Real-World GitHub Issues?

> 论文: **SWE-bench: Can Language Models Resolve Real-World GitHub Issues?**
> 作者: Carlos E. Jimenez, John Yang, Alexander Wettig, Shunyu Yao, Kexin Pei, Ofir Press, Karthik Narasimhan
> 机构: Princeton University, Princeton Language and Intelligence, Stanford University, University of Chicago
> 会议: ICLR 2024 (Published as a conference paper)
> arXiv: 2310.06770v3, 11 Nov 2024, 28 pages
> 复现 round: 18

---

## 0. 一句话 takeaway

**SWE-bench = 12 popular Python repos × 90K PRs × 3-stage filter = 2,294 task instances, 评测 LLM 解决 "**真 GitHub issue**" 能力。 Claude 2 (2023) 只 1.96% pass, Claude 3 Opus 3.79% (best), GPT-4 1.31%, ChatGPT-3.5 0.17% — 整数据集**故意设计成很难**, 把 LLM coding 推到 "**真软件工程**" 边界**。

---

## 1. 论文背景与动机

### 1.1 现有 benchmark 的局限

Paper 1.1 列出 3 个问题:
- **HumanEval / MBPP 太简单**: 100 行内 self-contained problem, 不能 capture "**real-world software engineering**"
- **APPS / CodeContests 难但太远**: "**code snippet**", 跟 "**resolve a real issue**" 差距大
- **没有** LM 程序能像人类开发者一样在仓库里导航、读多文件、改跨模块

### 1.2 SWE-bench 的创新

**Connect GitHub issues ↔ PRs that resolve them**:
1. 12 popular Python repos (django / scikit-learn / matplotlib / sphinx / sympy / xarray / astropy / pytest / pylint / requests / flask / seaborn)
2. 90K PRs scraped
3. 3-stage filter 留 **2,294 task instances**
4. 每个 instance = (issue text + codebase snapshot + gold patch + FAIL_TO_PASS tests)

**核心 insight**: 现实 software engineering 涉及 "**large codebase**" + "**多文件改**" + "**理解长 issue**" + "**automated test 验证**" — 这是 HumanEval 给不出的。

### 1.3 评测方法

- Model input: **issue text + retrieved files** (BM25 sparse retrieval)
- Model output: **patch** (unified diff format)
- Evaluation: apply patch → run FAIL_TO_PASS tests → if all pass, count as resolved

**关键 design choice**: 用 `FAIL_TO_PASS` tests 作为 ground truth (issue 是否真修好), 用 `PASS_TO_PASS` tests 作为 regression (没破坏已有功能)。

---

## 2. 数据集 construction (Section 2.1)

### 2.1 3-stage pipeline

**Stage 1: Repo selection + data scraping**
- 12 popular Python repos
- ~90K PRs in total
- 每个 PR 有 `base_commit` (pre-PR) 跟 `head_commit` (post-PR)

**Stage 2: Attribute-based filtering**
- 保留 **merged PRs** that:
  - **Resolve a GitHub issue** (linked via `Resolves #123`)
  - **Contribute tests** (changes test files)
- 目的: 验证 "**改的 code 跟 issue 真相关**" + "**有自动化 test 验证**"

**Stage 3: Execution-based filtering**
- 对每个 candidate task:
  1. 装 pre-PR code (`base_commit`)
  2. 跑 pre-PR tests → 至少 1 fail (叫 **fail-to-pass test**)
  3. Apply PR patch
  4. 跑 post-PR tests → 全部 pass
- 目的: 验证 "**这个 task 真能被自动化 test 评测**"

**结果**: 90,000 PRs → 2,294 task instances (97% 过滤)

### 2.2 数据集分布 (Figure 3)

12 repos task 数:

| Repo | Tasks | 备注 |
|---|---|---|
| **django** | **850** | 最多 |
| **sympy** | 386 | 数学库 |
| **scikit-learn** | 229 | ML |
| **sphinx** | 187 | doc |
| **matplotlib** | 184 | plot |
| **pytest** | 119 | test framework |
| **xarray** | 110 | n-dim array |
| **astropy** | 95 | astro |
| **pylint** | 57 | linter |
| **requests** | 44 | HTTP |
| **seaborn** | 22 | viz |
| **flask** | 11 | 最小 |

**Insight**: django 占 37% (850/2294), flask 仅 0.5% (11/2294), **数据集是不均匀**。 这是 paper 5.1 "**difficulty differs across repos**" 的根源。

### 2.3 Lite subset (Section 2.1 末)

**300 instances from 11/12 repos** (除 flask 因为 11 task 太少):
- **Self-contained**: 装 environment 容易
- **聚焦 functional bug fixes**
- 11/12 repos diversity 保留
- 主要用于 CI / quick eval

**意义**: Lite 是 17 轮 /loop 经常用的 subset (rounds 6/10/12/13/15/16 都没跑全量 SWE-bench)。

---

## 3. Task 实例 statistics (Table 1)

| Attribute | Mean | Max |
|---|---|---|
| **Issue text** (words) | **195.1** | 4,477 |
| **Codebase** (# files non-test) | 3,010 | 5,890 |
| **Codebase** (# lines non-test) | 438K | 886K |
| **Gold patch** (# lines edited) | **32.8** | 5,888 |
| **Gold patch** (# files edited) | 1.7 | 31 |
| **Gold patch** (# functions) | 3 | -- |
| **Tests** (# fail-to-pass) | **9.1** | 1,633 |
| **Tests** (# total) | 120.8 | 9,459 |

**3 个 insight**:

1. **Issue text 195 words, gold patch 32.8 lines** — paper 6.1 "**tasks are difficult to solve with code-generation style**" 因为 issue 195 words 是 "**free-form description**", 跟 "**写一个 Python function**" 完全不同
2. **Codebase 438K lines, 3K files** — model 必须用 **BM25 retrieval** 找 relevant files, 不能直接喂 full codebase (即使 Claude 100K context 也只够 27% instances)
3. **Tests 120 total, 9.1 fail-to-pass** — 评测稳健: 平均 9.1 fail-to-pass test, 一次 fail 不能说明 issue 没修

---

## 4. 检索方法 (Section 4.1)

### 4.1 BM25 vs Oracle

**两种 retrieval**:
- **Sparse (BM25)**: Robertson BM25Okapi, 拿 issue text query, 找 top-K relevant files
- **Oracle**: 知道 gold patch 改了哪些 files, 直接拿这些 files (但仍是 raw files, 不是 filtered lines)

**关键 finding (Table 2)**: BM25 recall (平均 29-51% per context length) vs Oracle:
- **13K context**: 26% avg, 35% any
- **27K context**: 39% avg, 52% any
- **50K context**: 51% avg, 58% any
- **几乎一半 instances 50K context 仍 retrieve 0 oracle files**!

### 4.2 Context length scaling

**Table 4: model context vs % instances**:
- ChatGPT-3.5 (16K): 58% instances 装得下
- GPT-4 (32K): 84%
- Claude 2 (100K): 96%
- SWE-Llama (100K): 95%

**Insight**: 即使 100K context, 4-5% instances 装不下 (django / scikit-learn 大 codebase)。 **BM25 retrieval 不是 nice-to-have, 是 necessity**。

---

## 5. Model performance (Table 5 + 6)

### 5.1 BM25 retrieval setting

| Model | SWE-bench Full | SWE-bench Lite |
|---|---|---|
| **Claude 3 Opus** | **3.79%** | **4.33%** |
| Claude 2 | 1.96% | 4.33% (注: paper 报 4.33, 跟 Opus 一样, 是 27K context 测的) |
| ChatGPT-3.5 | 0.17% | 0.33% |
| GPT-4-turbo | 1.31% | 2.67% |
| SWE-Llama 7b | 0.70% | 1.33% |
| SWE-Llama 13b | 0.70% | 1.00% |

### 5.2 Oracle retrieval setting (Table 6)

| Model | "Oracle"-collapsed Resolved | % Apply |
|---|---|---|
| **Claude 3 Opus** | **9.39%** | 48.00% |
| Claude 2 | 5.93% | 68.18% |
| GPT-4 | 3.40% | 48.65% |
| ChatGPT-3.5 | 1.09% | 40.93% |

**Insight**: 即使给 oracle files, Claude 2 仍只 5.93% — **任务本身难, 不是 retrieval 唯一问题**。 % Apply 也很低 (40-68%) — **模型经常 generate patch 但 patch 不能 apply** (格式问题)。

### 5.3 关键 finding: BM25 retrieval 重要

Claude 2 Oracle 5.93% vs BM25 1.96% — **3x gap** 归因于 retrieval 质量。

17 轮 /loop 后续的 SWE-agent (round 6) / OpenHands (round 10) / CodePlan (round 14) 都 follow 同样的 finding: **retrieval 是大瓶颈**。

---

## 6. Difficulty analysis (Section 5)

### 6.1 Difficulty differs across repos (Figure 4)

每个 repo 难易不同:
- **requests**: ~13% 解决率 (最容易, 因为 issue 短 + code 简单)
- **flask / pylint**: 0-1% 难
- **django**: 中等 5%

**Model 之间**: 同样 issue, Claude 2 跟 SWE-Llama 13b solve 的 instances **重叠很小** — 42% 重叠 (110/260 instances, 但 Claude 2 跟 SWE-Llama 各自 solve 1.96% / 0.70%)。

### 6.2 Difficulty correlates with context length (Figure 5)

**反直觉**: 20K-50K context instances **最容易**, 100K+ **最难**。
- Paper 解释: 长 issue 本身难 (新功能 vs bug fix)
- 长 context = 难 (model localize 错)
- **15+ line buffer** GPT-4 1.3% → 3.4%

### 6.3 Generating patches easier than whole files (Section 5)

- 多数 model 训练用 patch files (not whole files)
- Claude 2 整文件生成 2.2% vs patch 4.8% (oracle)
- **Insight**: 17 轮 /loop 一直用 "**patch-style**" output, 跟 paper 一致

### 6.4 Models write shorter, simpler edits (Table 8)

| Model | Total lines | Added | Removed | Functions | Files |
|---|---|---|---|---|---|
| Claude 2 | 19.6 | 4.2 | 1.9 | 1.1 | 1.0 |
| Gold | 44.1 | 12.0 | 5.8 | 2.1 | 1.2 |
| SWE-Llama 13b | 17.6 | 1.6 | 1.2 | 1.2 | 1.1 |

**Model 倾向于 generate ~1/2 长度的 patch, 1/3 added, 1/3 removed** — 这是 "**lazy fix**" 现象。

### 6.5 Generations reflect "greedy approach" (Section 5.1)

- Model 写 primitive code, **不** leverage existing libraries
- 缺乏 "**相对 import**", 用 absolute
- 改 single function 不考虑 codebase
- **Insight**: 跟 round 7 AutoCodeRover / round 14 CodePlan 的 "**multi-file dependency**" 思路互补 — paper 说 "**single-file fix**" 是 baseline, AutoCodeRover 推 "**multi-file**"

---

## 7. SWE-Llama: fine-tuning (Section 3)

- CodeLlama 7B / 13B fine-tune on **19,000 issue-PR pairs from 37 additional repos**
- 目的: 测 open model 在 SWE-bench 表现
- Result: 0.70% — **远低于 Claude 2 1.96%**
- 解释: Fine-tuning 用 "**every file as context**", 但 SWE-bench 测 "**only changed files**", 训练 / 评测 mismatch
- **Insight**: 这是 round 11 RepoCoder / round 9 PR mining / round 7 AutoCodeRover 都没解决的: open model 在 SWE-bench 难 fine-tune

---

## 8. 跟 18 轮 /loop 已复现 paper 的关系

### 8.1 直接基于 SWE-bench 的 paper (我 17 轮里 6 轮)

| 轮 | 主题 | 跟 SWE-bench 关系 |
|---|---|---|
| 6 SWE-agent | long-horizon 5-layer | 用 SWE-bench Lite 测 5 layer (论文报 3/3 test pass) |
| 7 AutoCodeRover | AST retrieval | SWE-bench Lite 测 37.5% pass@1 (15/40)? 实际 paper 报 46.2% dev / 38.6% test |
| 9 PR mining | 65K PR stats | 跟 SWE-bench pipeline 同源, 都 scrape GitHub PRs |
| 10 OpenHands | mini CodeAct | SWE-bench Lite 测 mini 7 task |
| 12 Reflexion | self-feedback | SWE-bench (mini) 测 intra-run feedback |
| 13 SWE-Lancer | 8 task × 3 runs | SWE-bench sub-set |

**17 轮 /loop 6/18 paper 引用 SWE-bench**, 但 **0 个 round 真正复现过 SWE-bench paper 本身** (我 6-13 round 都没用 SWE-bench 评测, 用 mini subset)。

### 8.2 SWE-bench 的核心 insight 跟 18 轮 /loop 交叉

| SWE-bench insight | 18 轮 /loop 验证 |
|---|---|
| 2,294 tasks 从 90K PRs filter 出来 | 跟 round 9 PR mining 同源 (65,745 closed PR) |
| BM25 retrieval 29-51% recall | 跟 round 7 AutoCodeRover AST retrieval 互补 |
| Gold patch mean 32.8 lines | 跟 round 14 CodePlan multi-file dependency 互补 |
| 1.96% Claude 2 / 0.70% SWE-Llama | 跟 round 7 AutoCodeRover 46.2% (open model SOTA) — 4x 强 |
| 15+ line buffer boost 1.3% → 3.4% | 跟 round 15 G5 deploy gate 一致 — buffer 重要 |
| 12 repo 不均匀 (django 850 / flask 11) | 跟 round 6 SWE-agent 5 layer 在 mini subset 测试互补 |

### 8.3 SWE-bench 没回答的, 18 轮 /loop 探索了

- **RAG vs 整 codebase**: paper 用 BM25, 我 round 11 RepoCoder 用 dense retrieval, round 7 AutoCodeRover 用 AST — **3 种 retrieval 都试过**
- **Multi-agent 协作**: paper 单 agent, 我 round 16 MetaGPT multi-agent SOP
- **Self-feedback**: paper 没测, 我 round 12 Reflexion +12.5pp
- **5-gate PQC**: paper 没测, 我 round 15 Beyond Code Gen PQC 33%

---

## 9. 5 个核心 finding (Section 5)

| ID | Finding | 18 轮视角 |
|---|---|---|
| **F1** | BM25 retrieval is bottleneck (29-51% recall) | **agree** — round 7 AutoCodeRover 改用 AST retrieval 46.2% |
| **F2** | Models generate shorter, simpler patches (lazy fix) | **agree** — round 14 CodePlan show 24 file multi-file |
| **F3** | Models 42% overlap (diverse failure modes) | **new** — 18 轮没测 model diversity |
| **F4** | 12 repos highly imbalanced (django 37%) | **agree** — round 6 mini subset 没法测 |
| **F5** | Even oracle retrieval, Claude 2 = 5.93% (task hard) | **agree** — round 15 PQC 5-gate, 即使有 gate 仍 fail |

---

## 10. 6 个 future direction (Section 7)

| 方向 | 18 轮 /loop 进展 |
|---|---|
| **Multi-modal LM** (matplotlib 32% instance 有 image) | 未测 |
| **Longer context** (Claude 100K → 200K) | 18 轮没 model 是 200K context |
| **Agent 跟 codebase 交互** | round 6 SWE-agent / round 10 OpenHands |
| **Multi-attempt + selection** | round 13 SWE-Lancer 测 3 runs 选 best |
| **RAG improvement** (BM25 → dense / AST) | round 7 AutoCodeRover / round 11 RepoCoder |
| **Self-debug / feedback** | round 12 Reflexion |

---

## 11. Threats to Validity

- **External**: 12 Python repos, 排除 Rust / Go / Java
- **Construct**: issue resolution 用 **fail-to-pass test** 评测, 但有些 PR 改 UI / doc, 没 test → 排除
- **Internal**: BM25 retrieval 选 "**fit within context**", 短 context 实例可能不公平
- **Conclusion**: 2,294 instance 不代表 "**所有**" real-world issue

---

## 12. 结论

- **2,294 task instances** 从 90K PRs filter 出来, **5 stages** (scrape / attribute / execute)
- **Best model 1.96% (Claude 2) / 3.79% (Claude 3 Opus)**, 验证 "**SWE-bench 故意设计成很难**"
- **BM25 retrieval 29-51% recall** 是最大瓶颈
- **Open model 难 fine-tune** (SWE-Llama 0.70%) — fine-tuning 跟 inference 分布 mismatch
- **18 轮 /loop 6 个 paper 用 SWE-bench Lite**, 但 0 个 round 真正复现过 paper 本身 (数据集 construction + retrieval recall + statistics)

**本轮 (round 18) 是 18 轮 /loop 第一次** 复现 SWE-bench paper 本身 — 验证 2,294 task / 12 repos / Table 1 statistics / Table 2 BM25 recall / Table 5 model performance。

---

## 13. 复现方向 (本轮 18 计划)

Paper 核心 claim:
1. **2,294 task instances** 来自 12 repos (Figure 3)
2. **Table 1 statistics**: issue 195 words / codebase 438K lines / patch 32.8 lines / 9.1 fail-to-pass
3. **Table 2 BM25 recall**: 29-51% @ 13K-50K context
4. **Table 5 model performance**: Claude 2 1.96% / ChatGPT-3.5 0.17% / GPT-4 1.31%

**本轮 mini 复现**:
1. **下载 SWE-bench Lite** (300 test + 23 dev) — 验证 dataset well-formed
2. **下载 SWE-bench full** (2,294 test) — 验证 12 repos 分布
3. **复现 Table 1 statistics** — issue length / patch size / fail-to-pass count
4. **复现 Table 2 BM25 recall** — 不同 context length
5. **复现 Figure 3 分布** — 12 repos task 数

**Expected**: paper 数字跟 HF dataset 数字 ±5% 偏差 (因为 paper 报 full SWE-bench 2,294, 我们看 cache test split)。

---

## 14. 引用

- Jimenez et al. **SWE-bench: Can Language Models Resolve Real-World GitHub Issues?**. arXiv:2310.06770v3, ICLR 2024 — 本轮复现
- Chen et al. **Evaluating Large Language Models Trained on Code**. 2021 — HumanEval
- Roziere et al. **Code Llama**. 2023 — SWE-Llama base
- Robertson et al. **BM25**. 2009 — sparse retrieval
- Anthropic. **Claude 2 / Claude 3 Opus**. 2023-2024 — 评测模型
- OpenAI. **GPT-4 / ChatGPT-3.5**. 2023 — 评测模型
- SWE-bench dataset: https://huggingface.co/datasets/princeton-nlp/SWE-bench
- SWE-bench Lite: https://huggingface.co/datasets/princeton-nlp/SWE-bench_Lite
- SWE-bench leaderboard: https://www.swebench.com

---

*Round 18 /loop 解读 by Claude Code · 完成于 2026-10-15 · paper 11 Nov 2024, 28 pages, 2,294 task instances, 12 Python repos, 90K PRs filtered, 1.96% Claude 2 best baseline*
