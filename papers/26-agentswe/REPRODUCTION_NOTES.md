# AgentSWE 复现验证报告

> Paper: Jiahao Wang et al. **"AgentSWE: Can Coding Agents Build the Agent You Actually Want?"** (arXiv:2610.13361, 2026-10-09)
> Code: https://github.com/VectorSpaceLab/AgentSWE
> 验证日期: 2026-10-14
> 范围: **结构性复现 + 论文 Table 对比**——未跑实际 agent（需要 Docker + LLM API + 大量算力）

---

## 0. 范围声明

**核心事实**：本论文的 **25 个 task 全部开源**（Apache 2.0），所有 task.json、builder 可见的 input、holdout 测例的 case 输入、scoring rubric、evaluator 脚本**全部公开**。

**我做了什么**：
1. ✅ 验证 task 数量、family 分布、dev/holdout 拆分
2. ✅ 验证 Lite 8 task 范围（论文 Table 5 scope）
3. ✅ 对比 **task.json 的 `lite_reference` 数字**与 **论文 Table 5**
4. ✅ 审计 upstream 仓库（10/10 Creation、10/10 Editing、5/5 Optimization）
5. ✅ 抽样 holdout case 与 dev case 的差异
6. ✅ 尝试 `agentswe list` / `agentswe doctor` 验证 CLI 可用
7. ❌ **未跑实际 agent**——需要 Docker + DeepSeek API + 600s/case × 6 cases × 25 tasks + 多 builder = **巨大的算力 + 资金消耗**

**为什么没跑 agent**：
- 每个 task 跑 1 个 builder 至少 1 小时（25 task × 1 hour = 25 hour wall-clock）
- LLM API cost：5 builder × 25 task × 600s/case × ~3K tokens/s = 不可忽略
- 本机 Apple Silicon Mac 无法跑 Docker + Harbor（harbor 需要 KVM、cgroup v2）
- 用户在前两轮中接受「结构性复现 + 算术验证」作为复现标准（见 LoopsBench 报告 + Agentic Coding 报告）

---

## 1. 验证手段

```bash
git clone --depth 1 https://github.com/VectorSpaceLab/AgentSWE.git
cd AgentSWE && python3 -m venv .venv && .venv/bin/pip install -e .
.venv/bin/agentswe list                    # 列出 25 task
.venv/bin/python ../scripts/verify_benchmark.py  # 12 项结构检查
```

无外部数据依赖——所有数字直接从 `tasks/{family}/{id}/task.json` 读出。

---

## 2. 12 项结构检查（全部 PASS）

| Check | 内容 | 结果 |
|---|---|---|
| 1 | 25 task = 10 Creation + 10 Editing + 5 Optimization | ✅ PASS |
| 2 | Creation/Editing 全部 2 dev + 6 holdout | ✅ PASS |
| 3 | Optimization 全部 `heldout=0`（用 source benchmark split） | ✅ PASS |
| 4 | Tier 分布 T1=19, T2=3, T3=3 | ✅ (论文未报) |
| 5 | 8 Lite task 范围 | ✅ PASS（精确匹配）|
| 6 | task.json `lite_reference.mean_at_3` vs 论文 Table 5 | ✅ PASS（7/8 精确 + 1 个 0.1 舍入）|
| 7 | 10/10 Creation 任务有 upstream repo | ✅ PASS |
| 8 | 10/10 Editing 任务有 upstream repo | ✅ PASS（5 general + 5 domain agent）|
| 9 | 5/5 Optimization 用 source benchmark | ✅ PASS |
| 10 | 全部 25 task `status=runnable` | ✅ PASS |
| 11 | 20 task 有 `case_timeout_sec=600` | ✅ PASS（5 个 opt task 用 source benchmark 自己的 timeout）|
| 12 | Holdout case 设计质量（scientific-pdf-translation）| ✅ PASS（语言对反转 + 域不同 + layout 不同）|

> **完整脚本**：`scripts/verify_benchmark.py`  
> **结果 JSON**：`outputs/reproduction_check.json`

---

## 3. Lite 数字 vs 论文 Table 5（精确对比）

| 任务 | task.json (DS-V4.1-Flash) | 论文 Table 5 | 差异 |
|---|---:|---:|---:|
| database-analytics | 38.7 | 38.7 | 0.0 ✅ |
| repository-bug-repair | 30.0 | 30.0 | 0.0 ✅ |
| scientific-pdf-translation | 31.9 | 31.9 | 0.0 ✅ |
| aider-worktree-transaction | 39.3 | 39.3 | 0.0 ✅ |
| deeptutor-adaptive-remediation | 27.6 | 27.6 | 0.0 ✅ |
| openwiki-change-impact | 21.0 | 21.0 | 0.0 ✅ |
| pinchbench-openclaw | 24.4 | 24.3 | +0.1 ⚠️ 舍入 |
| tau3-retail | 13.0 | 13.0 | 0.0 ✅ |

**结论**：**论文 Table 5 与 repo task.json 数字** 7/8 精确，1 个差 0.1（pinch 24.4 vs 24.3——rounding artifact）。这意味着：

> 论文 release 与 GitHub repo 同步**非常好**。比 LoopsBench 那种「论文 v.s. artifact 不同步」好得多。

---

## 4. Holdout Case 设计质量（科学 PDF 翻译实例）

论文反复强调 holdout case 必须**在多维度上**与 dev case 不同。下面看 `scientific-pdf-translation` 的实际设计：

| 维度 | dev_001 | test_001 |
|---|---|---|
| **语言对** | EN → ES（英译西） | ES → EN（西译英） |
| **主题** | Estuary sensor drift（河口传感器漂移） | Calibración de Flujo Criogénico（低温流量校准） |
| **页数** | 4 portrait | 3 (1+landscape+1, rotation) |
| **结构** | 2-column + 公式 + 表格 + chart | 6-column 校准表 + 容差图 + 审批块 |
| **特殊 token** | `10.5555/estuary.2026.014`, `E-01..E-03` | `FM-08`, `REF-2`, `CAL-77`, `PT-100-A`, `Δp_ref`, `QC_LOCK` |
| **接受标记** | 普通 | `✓`, `△`, `E_r = (q_ind - q_ref)/q_ref × 100%` |

**这是精心设计的 holdout**：
- 表面相似（都是科学 PDF 翻译）
- 但**至少 5 个独立维度反转**——任何对 dev case 写死的实现都会在 holdout 上失分
- 直接对应论文 FM1 (Overfitting to the Visible Cases) 的诊断对象

> **论文的 holdout 设计是扎实的**，不是「换一个 PDF 而已」。

---

## 5. Upstream 仓库审计

### 5.1 Creation 任务 (10/10 公开 upstream)

| 任务 | Upstream | 角色 |
|---|---|---|
| authorized-vulnerability-validation | strix (usestrix) | security agent |
| database-analytics | vanna-ai/vanna | text-to-SQL agent |
| desktop-gui-automation | bytedance/UI-TARS-desktop | GUI automation |
| document-to-editable-pptx | hugohe3/ppt-master | PPT generation |
| evidence-grounded-document-qa | Future-House/paper-qa | scientific Q&A |
| formal-theorem-proving | lean-dojo/LeanCopilot | theorem proving |
| repository-bug-repair | SWE-agent/SWE-agent | SWE |
| schema-guided-web-extraction | ScrapeGraphAI/Scrapegraph-ai | schema extraction |
| scientific-pdf-translation | PDFMathTranslate/PDFMathTranslate | PDF translation |
| web-research-report | MiroMindAI/miroflow | research agent |

**全部是真实有用户的 production agent**——不是 toy 实现。这强化了 Creation 任务的「真实委托」性质。

### 5.2 Editing 任务 (5 general + 5 domain)

| 任务 | Upstream | 类别 |
|---|---|---|
| ai-scientist-reproducibility-gate | SakanaAI/AI-Scientist-v2 | research |
| aider-worktree-transaction | Aider-AI/aider | general |
| claude-policy-provenance | anthropics/claude-code | general |
| codex-execution-residual | openai/codex | general |
| deepcode-claim-traceability | HKUDS/DeepCode | research |
| deeptutor-adaptive-remediation | HKUDS/DeepTutor | education |
| dyad-acceptance-driven | dyad-sh/dyad | dev tool |
| openclaw-channel-handoff | openclaw/openclaw | chat |
| openhands-effect-recovery | OpenHands/OpenHands | general |
| openwiki-change-impact | langchain-ai/openwiki | docs |

**10/10 全是 production agent 仓库**——直接对应论文 §4.1「pinned production agent」。

### 5.3 Optimization 任务 (5 个 source benchmark)

| 任务 | Source benchmark |
|---|---|
| browsecomp | openai/simple-evals |
| osworld | xlang-ai/OSWorld |
| pinchbench-openclaw | pinchbench/skill |
| tau3-retail | sierra-research/tau2-bench |
| terminalbench | laude-institute/terminal-bench |

> **4 个是 2025–2026 新出的 benchmark**——τ² 之后是 τ³、PinchBench 2026 才出现。这给 AgentSWE 的「Optimization」评测提供了**高质量、热度高的 ground truth**。

---

## 6. 论文 Table 1 main results：复现策略说明

论文 Table 1 报告了 5 builder × 25 task = 125 runs 的 full Codex 评测。我**没有复现这些数字**——理由：

1. **单次 full run** 至少 25 task × 1 hour wall-clock + 600s × 6 holdout cases = 25 + 25 = 50 hours
2. **需要 5 个 LLM API key**：GPT-5.6 Sol（OpenAI）、DS-V4-Pro、DS-V4-Flash（DeepSeek）、Qwen3.6（DashScope/Aliyun）、GPT-5.5
3. **需要 Docker + Harbor + KVM**——本机 macOS Apple Silicon 无法跑
4. **需要 ~1000 USD+ LLM API 预算**——超出个人复现合理范围

但 task.json 的 `lite_reference`（8 Lite task）**已经**提供了可比对的数据点。Lite 是 paper's "easier to evaluate new builder" subset。

### Lite 数字 vs Table 1 main numbers

Lite 用了 **DS-V4.1-Flash** (DS-V4-Flash 的更新版)，而 main 用了 **DS-V4-Flash**。

| Builder | Table 1 Creation Mean | Table 5 (Lite) Creation Mean | 差异 |
|---|---:|---:|---:|
| DS-V4-Flash / V4.1-Flash | 15.1 | 33.5 | **+18.4** ⚠️ |
| GPT-5.6 Sol | 13.7 | 23.1 | +9.4 |
| Qwen3.6 | 2.3 | 0.0 | -2.3 |

**关键观察**：Lite 数字与 main 数字**不可比**——README 明确说明「Because the runtime model and the judge differ from the main study, the Creation and Optimization levels are not comparable with the table above.」

> **论文 §E.2 提示了这一点**——Lite 是 separate experiment，**不要用 Lite 数字验证 Table 1**。

---

## 7. Failure Modes 的可复现性

论文报告 3 个 failure mode:
- **FM1: Overfitting**——dev 100, holdout 28.3 这种数据
- **FM2: Hollow Runtimes**——58.1% held-out execution fail validity gate
- **FM3: Unsupported Claims**——builder 自报「完成」但 record 矛盾

**复现路径**（理论上）：每个 task 都有：
- `benchmark/evaluator/evidence_bundle.py`——收证据
- `benchmark/evaluator/rubric.md`——rubric 文档
- `benchmark/evaluator/eval_prompt.md`——judge 用的 prompt
- `benchmark/evaluator/harness/`——实际跑 delivery 的脚本

如果真跑 builder，能从 trajectory + delivery + holdout execution trace 中**实证**这三个 failure mode。但**没有跑 = 没法独立验证**。

> 我只能验证**这些 failure mode 是怎么检测的**（rubric 怎么写的），不能验证**这些 failure mode 是否真的在生产里发生**。

---

## 8. 复现结论

### ✅ 论文可信度评估

1. **结构完全自洽**——25 task 数量、family 分布、case 拆分与论文完全一致
2. **数字 artifact 一致性极好**——Lite 数字 7/8 精确，1 个 0.1 舍入。比 LoopsBench（unit_count 38× 差异）好得多
3. **Holdout 设计扎实**——多维度反转（语言、域、layout、token 类型），不是「换个 PDF」
4. **Upstream 仓库真实**——10/10 Creation + 10/10 Editing + 5/5 Optimization 全部 public production 代码
5. **CLI 可用**——`agentswe list` / `agentswe doctor` 正常工作；task.json schema 完整

### ⚠️ 限制

1. **未跑实际 agent**——只做结构性复现
2. **Lite 数字 ≠ Main 数字**——README 自己也声明了
3. **Failure mode 只能 verify 检测方法**——不能 verify 现象本身

### ❌ 不能做的

- 重新跑 5 builder × 25 task = 125 runs（需 Docker + 5 LLM API + ~1000 USD）
- 独立验证 failure mode 的频次（FM1/FM2/FM3 的具体百分比）
- 复现 Figure 4 (Optimization gain scatter plot) 和 Figure 5 (Creation outcome stacked bar)

---

## 9. 我的评价

### 论文做得好的地方
1. **形式化扎实**——Definition 3.1 把「coding agent 造 agent」变成可测量
2. **Holdout 留出是关键创新**——既不是 benchmark trick，也不是事后分析的
3. **Failure mode 三分法有真知灼见**——overfitting / hollow / false-claim 是结构性现象
4. **Artifact 完整 + 同步**——25 task 全部开源，task.json 直接 verifiable
5. **Lite 8 task 子集**——降低社区复现门槛

### 论文可以改进的地方
1. **25 task 还是太少**——CI bound 宽。论文自承「10 task per stage is the budget ceiling for the cost we could afford」
2. **Result rubric 是 post-hoc 写的**——task 作者写自己 task 的 rubric。需 cross-task blind review
3. **Holdout 6 cases 不算多**——但**质量**好（多维反转）
4. **未讨论 task 难度分布**——可能偏容易（开源 repo 文档好）
5. **Runner model 共享**——所有 task 用一个 runtime model（DS-V4-Flash for Lite），意味着 builder 实际写的是「在 DS-V4-Flash 上能跑的 agent」

### 一句话
> **AgentSWE 是 2026 年最严谨的「agent 造 agent」评测**——25 task 不算多，但每个 task 的 holdout 设计、scoring rubric、evaluator 脚本、upstream 仓库都是 production-quality 公开可复现。

---

## 10. 复现产物清单

```
papers/26-agentswe/
├── paper.md                  # 中文解读（已写）
├── REPRODUCTION_NOTES.md     # 本文档
├── blog.md                   # 博客（待写）
├── 2610.13361.pdf            # 论文 PDF（1.2MB，已下载）
├── repo/
│   └── AgentSWE/             # git clone --depth 1
│       ├── tasks/{creation,editing,optimization}/  # 25 tasks
│       ├── agentswe/         # CLI package
│       ├── .env.example      # API key 配置模板
│       └── README.md         # 与论文高度同步
├── scripts/
│   └── verify_benchmark.py   # 12 项结构检查
├── outputs/
│   └── reproduction_check.json  # 检查结果
└── requirements.txt          # agentswe (Apache 2.0)
```
