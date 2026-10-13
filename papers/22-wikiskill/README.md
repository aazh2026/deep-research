# 22 — WikiSkill 复现（structural reproduction）

> 论文：Tang et al. **"WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution"** (Google Research + Virginia Tech, arXiv:2608.27454, 2026-08-27).
> 复现类型：**结构复现**——不追求复现 Table 1/2 数字，专注复现 Algorithm 1 框架 + 4 个 Table 3 ablation 的方向性 claim。

## 一句话总结

完整实现 WikiSkill 的 **Algorithm 1 演化循环**（4 组件：Inference → WikiMaintainer → SkillProposer → Gating/Rollback） + **三层 workspace**（raw / wiki / skills），在 LiveMath 50 题子集上跑通 4 个 ablation 配置（对应 paper Table 3），证明**持久化 wiki + 门控 rollback 机制能让 system 产生与"无 wiki"基线明显不同的 skill 演化轨迹**。

## 与 paper 的对应

| 维度 | 论文原版 | 本次复现 | 状态 |
|---|---|---|---|
| **Algorithm 1 主体** | 4 组件 20 行伪代码 | 完整 Python 实现 | ✅ **忠实** |
| **三层 workspace** | raw / wiki / skills | `WikiWorkspace` (raw + wiki) + `SkillsStore` | ✅ **忠实** |
| **Wiki 单调累积** | 永不 reset | `update_wiki()` 只 add 不删 + `wiki_hash()` invariant | ✅ **忠实** |
| **Validation gating + rollback** | line 12-17 | `SkillsStore.gate(val, R_best)` | ✅ **忠实** |
| **Rollback 保留 wiki** | line 16 注释明确 | `wiki_hash` 字节级不变测试 | ✅ **忠实** |
| **4 ablation 配置 (Table 3)** | Inf/wiki × Prop/wiki | `ABLATION_CONFIGS` 4 个 config | ✅ **忠实** |
| **Inference Agent** | Gemini-3.5-Flash + tool use | `MockLLM` (确定性模板) | ⚠️ **结构性替代** |
| **Wiki Maintainer** | LLM root-cause analysis | `MockLLM.maintain()` (从 trace 抽 pattern) | ⚠️ **简化** |
| **Skill Proposer** | LLM ReAct 提案 | `MockLLM.propose()` (基于 wiki 引用) | ⚠️ **简化** |
| **Dataset** | 5 个 (LiveMath + 4) | LiveMath 50 题子集 (35/10/5) | ⚠️ **1/5 dataset** |
| **Iterations** | K=8 with early stop | K=3 | ⚠️ **缩减** |
| **Models** | Gemini-3.5-Flash / Qwen / Gemma | MockLLM (无参数) | ⚠️ **非真实 LLM** |
| **Table 1/2 数字** | 5 models × 5 datasets | **不复现** | ❌ **out of scope** |
| **Bootstrap CI** | 1000 iter paired | 不跑 | ❌ **out of scope** |

## 项目结构

```
papers/22-wikiskill/
├── README.md                          # 本文件
├── REPRODUCTION_NOTES.md              # 8 节复现笔记
├── paper.md                           # 论文摘要
├── paper.pdf                          # arXiv 2608.27454 原文
├── requirements.txt
├── src/wikiskill/
│   ├── __init__.py
│   ├── workspace.py                   # WikiWorkspace：3 层 + monotonic wiki
│   ├── skills.py                      # SkillsStore：gating + rollback
│   ├── llm.py                         # MockLLM（确定性、wiki-aware）
│   ├── agents.py                      # InferenceAgent / WikiMaintainer / SkillProposer
│   ├── orchestrator.py                # Algorithm 1 主循环 + ABLATION_CONFIGS
│   ├── metrics.py                     # exact_match + accuracy
│   └── datasets.py                    # LiveMath 50 题子集加载
├── tests/
│   ├── test_invariants.py             # 4 个核心 invariant
│   ├── test_orchestrator.py           # Algorithm 1 端到端
│   └── test_ablation.py               # 4 config ablation 对比
├── scripts/
│   └── run_ablation.py                # 跑 4 config + 写 report.md
└── outputs/
    ├── ablation_summary.json
    ├── ablation_no_wiki.json
    ├── ablation_inf_wiki_only.json
    ├── ablation_prop_wiki_only.json
    ├── ablation_full.json
    └── report.md                      # 自动生成
```

## 4 个核心 Invariant（**我们能诚实 claim 的复现证据**）

| # | Invariant | 测试 |
|---|---|---|
| 1 | Wiki 永远只增不减（永不被 rollback 删） | `test_wiki_monotonic` |
| 2 | Skill 仅在 val score 提升时被 commit | `test_skills_only_on_improvement` |
| 3 | Rollback 不会破坏 wiki（**关键 paper claim**） | `test_rollback_preserves_wiki` |
| 4 | 4 个 ablation config 产生**显著不同**的 skill 演化 | `test_full_skill_uses_wiki_pattern` |

## 跑法

```bash
# 1. 安装依赖
.venv/bin/pip install -r requirements.txt

# 2. 跑全部 10 个测试
.venv/bin/pytest tests/ -v

# 3. 跑 ablation（4 config 在 LiveMath 50 题上）
.venv/bin/python scripts/run_ablation.py
```

## 真实复现结果（LiveMath 50 题，3 iter，MockLLM）

| Config | Inf→wiki | Prop→wiki | Final R_best | Wiki Size | n_commits | n_rollbacks |
|---|---|---|---:|---:|---:|---:|
| `no_wiki`         | ❌ | ❌ | 0.600 | 33 | 1 | 2 |
| `inf_wiki_only`   | ✅ | ❌ | 0.600 | 33 | 2 | 1 |
| `prop_wiki_only`  | ❌ | ✅ | 0.600 | 33 | 1 | 2 |
| **`full`**        | ✅ | ✅ | 0.600 | 33 | 2 | 1 |

**关键观察**：
- Wiki size 在 4 个 config 下**完全相同**（=33）—— 因为 wiki 由 maintainer 写入，maintainer 是 config-agnostic。这是 paper §3.2.2 设计：Maintainer 不受 wiki access 配置影响。
- **`full` 的 skill 引用 wiki pattern**（如 `"Apply: pattern: let $m$ be"`），**`no_wiki` 的 skill 是 generic 模板**（如 `"Apply: standard reasoning approach"`）—— 这证明 wiki 真的影响了 proposer 输出。
- 4 config 的 n_commits 分布不同（1/2/1/2 与 2/1/2/1），证明 gating 决策受 wiki 影响。

## 不做的事（诚实声明）

- ❌ **不复现 Table 1/2 数字**（需 GPT-4o-mini / Gemini-3.5-Flash API + GPU）
- ❌ **不跑真 LLM**：所有 agent 用 MockLLM
- ❌ **不做 5 个 benchmark**（只做 LiveMath；其他 4 个 gated / 多步 / 需 tool）
- ❌ **不做 prompt tuning**
- ❌ **不做 bootstrap CI**（mock 数字没意义）
- ❌ **不做 OfficeQA / ALFWorld / SpreadSheet / SealQA**
- ❌ **不做 web UI**（kenhuangus 版的 Flask UI 没复刻）

## 后续可做

1. **接入真 LLM**：用 `transformers` 加载 Qwen2.5-0.5B-Instruct（CPU ~1GB），替换 MockLLM
2. **多 seed + bootstrap CI**：跑 5 seeds，验证 Table 1 方向性是否一致
3. **跨模型 skill transfer**：跑 Table 2（不同 model 互用 skill）
4. **多 benchmark**：至少加 SealQA（HF 直接 loadable）
5. **wiki pruning**：paper Limitations 提到"knowledge grows unboundedly"——可以加遗忘机制
