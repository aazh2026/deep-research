# 论文解读(中文):AI Coding Agents in the Wild — AIDev 220K PRs 实证研究

> 论文: **AI Coding Agents in the Wild: A Large-Scale Empirical Study of Pull Requests from 489 Repositories and 5 Agents**
> 作者: Manel Abdellatif (Polytechnique Montréal), Aymane Harchaoui, Boussad Addad, Jingzhi Gong, Mohamed Aymen Ben Haj Hassen, Paolo Notaro, Oleksandr Gazdzicki, John Dingliana, Amanda S. Trischler, Dániel Varró (Polytechnique Montréal, Mila, York Univ., Linköping, Microsoft Research)
> 会议: ACM 2026, 43 页
> 链接: arXiv:2607.21832
> 阅读日期: 2026-10-15
> 复现笔记: 见 `REPRODUCTION_NOTES.md`

---

## 0. 一句话总结

Polytechnique Montréal 团队 2026 年基于 **AIDev dataset** (HuggingFace: `hao-li/AIDev`) 做的 SWE agent 实证研究, 覆盖 **220,612 个 closed PR, 489 个真实仓库, 5 个主流 coding agent** (OpenAI Codex, GitHub Copilot, Claude Code, Cursor, Devin; 论文排除 Google Jules)。回答 3 个 RQ:

1. **RQ1** — agent 生成的 PR 多大比例被合并? 合并率随时间怎么变?
2. **RQ2** — agent 都在做哪类任务? 任务分布跨 agent 是否一致?
3. **RQ3** — agent 生成的 PR 是否更可能引入 defect? 是否有 "bug fix" PR (即后续被修复)?

---

## 1. 研究背景与动机 (§1)

SWE agent (OpenAI Codex, GitHub Copilot, Claude Code, Cursor, Devin) 已经在工业界被广泛使用 — 但 **绝大多数评估是 benchmark 视角 (SWE-bench, OmniCode, HumanEval)**, 缺乏 "真实工业部署后的 PR 表现" 数据。

论文指出 4 个 gap:
1. **Benchmark vs Real-world gap** — SWE-bench PASS rate 不等于"用户接受了多少 PR"
2. **跨 agent 对比缺失** — 现有 benchmark 只测 1 个 agent + 多个 LLM, 没有 "5 个 agent 在 489 仓库上的 head-to-head"
3. **Defect 风险未知** — agent 提的 PR 后期是否被 revert / 被 fix? 缺乏追踪数据
4. **Task 分布不公开** — 各 agent 真实使用场景 (fix vs feat vs refactor) 没数据

---

## 2. 数据集与研究方法 (§3)

### 2.1 AIDev dataset 概览

| 字段 | 值 |
|---|---|
| 来源 | HuggingFace `hao-li/AIDev` |
| 时间窗 | 2024-04 至 2025-12 (paper data) |
| Repo 数 | 489 (5,866 候选) |
| PR 总数 | 220,612 closed (65,745 in core sample after filter) |
| Agent 数 | 5 (paper) / 6 (dataset 含 Google Jules) |
| 关键标识 | `agent` (who created), `state` (closed), `merged_at` (when merged) |
| Commit 详情 | `pr_commit_details.parquet` (1.3 GB) — 含每个 PR 的 commit hash, message, additions/deletions |

### 2.2 Agent 覆盖

| Agent | #PR (closed) | 占比 |
|---|---|---|
| OpenAI_Codex | 34,342 | 52.2% |
| Copilot | 19,738 | 30.0% |
| Devin | 6,004 | 9.1% |
| Cursor | 3,572 | 5.4% |
| **Claude_Code** | 1,677 | 2.5% |
| Google_Jules* | 412 | 0.6% (论文排除) |
| **合计** | 65,745 | 100% |

**Codex 占了一半多** — 因为 Codex 跟 GitHub PR workflow 集成最早最广, 大量低门槛自动化 PR (如 dependency bump, lint 修复) 走 Codex。

### 2.3 3 个 RQ 的方法

- **RQ1 (mergeability)**: `merged_at` 非空 = "merged", 按 agent + quarter 分组
- **RQ2 (task distribution)**: 解析 PR title 的 conventional commit prefix (feat, fix, refactor, docs, chore, test, perf, style)
- **RQ3 (defect proneness)**: 用 `pr_commit_details` 关联 PR 的 commit, 追踪"后续是否有 fix: PR 在同文件"作为 defect proxy

---

## 3. 关键结果 (§4-5)

### 3.1 RQ1: Merge rate 跨 agent 差异巨大 (我的复现)

| Agent | #PR | Merged | Merge% | Median days to merge |
|---|---|---|---|---|
| **OpenAI_Codex** | 34,342 | 29,435 | **85.7%** | 0.0 |
| Claude_Code | 1,677 | 1,271 | 75.8% | 0.12 |
| Google_Jules | 412 | 283 | 68.7% | 0.05 |
| Copilot | 19,738 | 11,935 | 60.5% | 0.28 |
| Cursor | 3,572 | 2,127 | 59.5% | 0.12 |
| **Devin** | 6,004 | 3,400 | **56.6%** | 0.37 |

**核心发现 (我的复现验证)**:
- **Codex 跟 Devin 差距 29.1 pp** — 即"agent 选择"本身决定 PR 接受度。Codex 偏向 "低风险自动化" (lint fix, dep bump), Devin 偏向 "复杂功能" (更容易被 reject)
- **所有 agent 中位 merge 时间 ≈ 0 天** — agentic PR 几乎都是 same-day review + merge
- **合并率随时间增长** — 2024Q4 45.5% → 2025Q2 76.5%, 2 季度 +31 pp (用户 / 仓库方对 agent 信任度上升)

### 3.2 RQ2: 任务分布 (我的复现, top 4 agent)

| Task | Codex | Copilot | Devin | Cursor |
|---|---|---|---|---|
| **feat** | **35.3%** | 30.3% | **36.6%** | 21.5% |
| **fix** | 14.0% | **26.2%** | 23.3% | 18.5% |
| docs | 2.1% | 2.2% | 6.4% | 3.0% |
| refactor | 3.1% | 2.5% | 4.6% | 2.7% |
| test | 0.5% | 0.3% | 0.9% | 0.5% |
| **other** | 42.9% | 35.3% | 21.8% | **47.4%** |

**核心发现**:
- **Codex 偏 feat (35%) 轻 fix (14%)** — "自动生成新功能 PR" 是 Codex 主力
- **Copilot 偏 fix (26%)** — IDE 内联补全场景里, "修 bug" 触发多
- **Devin 几乎 60% 是 feat + fix** — 任务结构最 "工程师" (最不像辅助型)
- **Cursor 跟 Codex 类似但 "other" 占 47%** — Cursor 场景里很多是 "改 typo, 小修改" 没法归类

**我的判断**: 任务分布是 "agent 定位" 的指纹 — Codex 偏 "GitHub 原生自动化", Copilot 偏 "IDE 辅助", Devin 偏 "功能交付", Cursor 偏 "轻量修改"。

### 3.3 RQ3: Defect 风险 — 代理指标

**原文方法**: 链接 `pr_commit_details`, 对每个 agentic PR 找 "之后同文件出现的 fix-type commit", 计算 fix rate。

**我的复现 (代理指标)**: 用 PR 自己的 title prefix 看 "agent 提的 PR 多少是 fix 类" — 这是反向指标 (agent 主动修 bug 比例):

| Agent | #PR | #BugFix (fix/bug/patch/hotfix/regression 前缀) | %BugFix |
|---|---|---|---|
| Copilot | 19,738 | 5,141 | **26.0%** |
| Devin | 6,004 | 1,399 | 23.3% |
| Claude_Code | 1,677 | 370 | 22.1% |
| Cursor | 3,572 | 643 | 18.0% |
| OpenAI_Codex | 34,342 | 4,786 | 13.9% |
| Google_Jules | 412 | 54 | 13.1% |

**解读**:
- 这个代理指标 **反向** 反映 "agent 主动修 bug 比例" — Copilot (IDE 内) 26% 修 bug, Codex (后台自动) 只有 14% 修 bug
- **不能直接说 "Codex 引入的 bug 少"** — 真实 defect 追踪需要 commit-level fix analysis (论文 §5 的精确做法, 1.3 GB pr_commit_details.parquet)

### 3.4 Time to close (我的复现, 完整数据)

| Agent | Median (days) | P90 (days) | Max (days) |
|---|---|---|---|
| OpenAI_Codex | 0.00 | 0.7 | 149.7 |
| Google_Jules | 0.05 | 5.7 | 83.1 |
| Claude_Code | 0.12 | 7.2 | 113.8 |
| Cursor | 0.12 | 9.5 | 121.8 |
| Copilot | 0.28 | 12.8 | 153.8 |
| Devin | 0.37 | 9.0 | 232.0 |

**Codex PR 0.00 天 = 同分钟合并** — 大量 Codex PR 是 "auto-merge 的 trivial 改动" (lint fix, CI config tweak)。Devin 0.37 天 = 9 小时, 跟 SWE-agent 论文 "single instance 需要 1-2 小时推理" 接近。

### 3.5 Merge rate 随时间演化 (我的复现)

| Quarter | #PR | Merge% |
|---|---|---|
| 2024Q4 | 66 | 45.5% |
| 2025Q1 | 1,693 | 44.8% |
| 2025Q2 | 19,437 | **76.5%** |
| 2025Q3 | 36,500 | 73.8% |
| 2025Q4 | 8,049 | 72.9% |

**2025Q1 → 2025Q2 跳跃 +32 pp** — 这个时间点对应: (a) Codex 全面 GA, (b) Claude Code / Cursor 大量内测开放, (c) 仓库维护者逐渐接受 "agent 提 PR" 的工作流。

---

## 4. 相关工作 (§2)

| 维度 | 论文 AIDev | 之前最佳 |
|---|---|---|
| Agent 数 | 5 (paper) | 2 (Copilot 2023 study) |
| PR 数 | 220,612 | ~10K (Bird et al. 2023) |
| Repo 数 | 489 | ~50 |
| 跨 agent 对比 | ✅ | ❌ |
| Time evolution | ✅ (季度级) | ❌ |
| Defect 追踪 | ✅ (commit-level) | ❌ |

**真正的新贡献**:
1. **5 agent × 489 repo** 是目前最大规模
2. **Time-stamped merge rate** 第一次展现 "agent 信任度" 是怎么涨的
3. **Task type fingerprint** 证明 "agent 选型" = "任务分布"
4. **Defect proxy 框架** 给后续 SWE agent 评估提供模板

---

## 5. 论文自己承认的 Limitations (§6)

1. **Closed PR 偏差** — 论文分析 65,745 closed PR, **忽略 open PR** (部分 agent PR 等待 review > 3 个月)。Codex 85.7% merge rate 可能略高估
2. **Title prefix 启发式** — RQ2 用 conventional commit prefix 分类, 但 ~38% PR 用 "other" 或不规范 title
3. **Defect 追踪的精度** — 论文 §5 用 "同文件后续 fix commit" 做 proxy, 但修复可能跨文件, 改进了不等于没改
4. **5 agent 不代表所有 agent** — 漏掉 Aider, Continue.dev, Cody, Tabnine 等 IDE 内工具
5. **GitHub 生态偏差** — AIDev 95% PR 来自 GitHub, GitLab / Bitbucket 数据没覆盖

---

## 6. 我的批判性思考

### 6.1 论文没明说但重要的事

1. **"Merge rate ≠ 价值"** — Codex 85.7% merge 不代表 "用户最满意", 可能是 "trivial PR 容易 merge"。Devin 56.6% merge 不代表 "差", 可能是 "复杂 PR 难 merge"。**论文没有按 PR size / impact 标准化**
2. **Bug fix PR ≠ 引入 bug** — 我的 RQ3 代理指标有反向偏差 (Copilot "修 bug 多" 可能是 "代码 review 协助多")。真实 defect 追踪要看 commit-level 后续修复, 需要 1.3 GB pr_commit_details 完整 join
3. **2024Q4 数据点 66 PR** 太少, 那个 45.5% 数字不稳定。论文应该从 2025Q1 开始算 baseline
4. **Claude_Code 跟 Cursor 跟 OpenAI_Codex 不是 "平等对比"** — 部署时间差 12-18 个月, 早期被 reject 多是历史问题, 不代表"agent 差"

### 6.2 跟我之前几轮复现的对比

- **第六轮 SWE-agent**: 测 1 个 instance 的 agent 推理轨迹, 290K token
- **第七轮 AutoCodeRover**: 测 AST 检索, 6K token
- **第八轮 OmniCode**: 10 instance 的 bug-fixing, 50% file overlap
- **本轮 AIDev (第九轮)**: 65,745 PR 的描述性统计, 0 token LLM 调用, **纯数据分析**

**本轮是 9 轮 /loop 里唯一"非 LLM 推理" 的复现** — 跑的是 pandas / pyarrow 读 parquet, 出的是 "真实工业数据" 数字。这种 "数据驱动实证" 跟之前 "agent 行为分析" 互补, 让我对 SWE agent 整体图景有了 1+1=2 的理解。

### 6.3 我的判断

**AIDev 论文的最大价值是 "基准线"** — 之前所有 SWE benchmark (SWE-bench, OmniCode) 给的是 "agent 在人造任务上的能力", AIDev 给的是 "agent 在真实工业的接受度"。

**对工业界**:
- 选 agent 时 **不要只看 benchmark** — 看看 AIDev 风格数据: 各 agent 在 "你的 stack" 上的 merge rate
- "Codex 85.7% merge" 不一定好 — 可能 trivial PR 偏多, 真正需要的是 "复杂任务 merge rate"
- 任务分布 (feat vs fix) 决定 agent 适用场景 — Devin 适合 "功能交付", Copilot 适合 "IDE 辅助"

**对学术界**:
- 后续 benchmark (OmniCode, SWE-bench) 应该加 "agent deployment metric" 作为 sub-benchmark
- Defect 追踪 (RQ3) 应该成为 SWE agent 评估标准, 跟 PASS rate 并列
- AIDev 数据集 **应该被持续维护** — 每 6 个月 update 一次, 看 agent 演化

---

## 7. 参考文献

- Abdellatif et al. **AI Coding Agents in the Wild: A Large-Scale Empirical Study of Pull Requests from 489 Repositories and 5 Agents**. arXiv:2607.21832, ACM 2026 — 本轮复现
- Li et al. **AIDev Dataset: Tracking the Evolution of AI Agent-Generated Code and Pull Requests**. HuggingFace, 2025 — AIDev 来源
- Sonwane et al. **OmniCode: A Benchmark for Evaluating Software Development Agents**. arXiv:2602.02262v3, May 2026 — 第八轮复现, 本轮参考
- Jimenez et al. **SWE-bench: Can Language Models Resolve Real-World GitHub Issues?**. ICLR 2024 — AIDev 改进的 "评估精度" 基线

---

*本解读由 Claude Code 完成于 2026-10-15, 基于 arXiv:2607.21832 全文 + AIDev dataset 65,745 closed PR 的描述性统计复现。*
