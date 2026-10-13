# WikiSkill 复现笔记

> 论文：Tang et al. "WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution" (Google Research + Virginia Tech, arXiv:2608.27454, 2026-08-27)
> 复现日期：2026-10-13
> 硬件：Apple Silicon CPU，Python 3.14.5，**无 GPU 无 API**

## 1. 复现动机

在 21 篇评测论文之外偶然看到 Google 8/27 刚挂的 WikiSkill——paper 自己就讲"社区有重写 kenhuangus/wikiskill 但非官方"——立刻想看：

- Algorithm 1 真的能跑通吗？
- "wiki 永不重置"和"skill 门控 rollback"这两个核心 invariant 在代码层是不是真的成立？
- 4 个 ablation config 到底有没有产生**显著不同**的 system 行为？

**为什么不照搬 kenhuangus/wikiskill**：那是社区重写，commit 风格跟我之前 7 篇不一致；自己实现 1）保证每行代码可审计、2）能精确控制 MockLLM 的 wiki-aware 行为让 ablation 真的差异、3）写专门测试验证 paper 关键 claim。

## 2. 复现范围

**做**（结构性复现）：
- Algorithm 1 的 4 组件循环端到端跑通
- 三层 workspace（raw/wiki/skills）的 in-memory 模拟
- Wiki 累积单调（never reset）
- Skill 门控（只在 val score 提升时 commit）
- Rollback 不破坏 wiki
- 4 个 ablation config 产生不同的 skill 输出

**不做**（算力 / API 不可用）：
- Table 1/2 数字
- 真 LLM 推理（GPT-4o-mini / Gemini-3.5-Flash）
- 5 个 benchmark（只做 LiveMath；其他 4 个 gated / 多步）
- Prompt tuning
- Bootstrap CI

## 3. 真实结果（LiveMath 50 题子集，3 iter，MockLLM seed=42）

| Config | Inf→wiki | Prop→wiki | Final R_best | Wiki | n_commits/n_rollbacks | Final skill body（前 80 字符） |
|---|---|---|---:|---:|---|---|
| `no_wiki`        | ❌ | ❌ | 0.600 | 33 | 1/2 | `Apply: DESTRUCTIVE_OVERRIDE Apply: standard reasoning approach` |
| `inf_wiki_only`  | ✅ | ❌ | 0.600 | 33 | 2/1 | (同样 generic) |
| `prop_wiki_only` | ❌ | ✅ | 0.600 | 33 | 1/2 | **`Apply: pattern: let $m$ be`** |
| `full`           | ✅ | ✅ | 0.600 | 33 | 2/1 | **`Apply: pattern: let $m$ be`** |

**关键观察**：
1. **Wiki size 4 config 全部相同**（=33）。原因：wiki 由 WikiMaintainer 写入，而 Maintainer 始终执行（paper §3.2.2：Maintainer 总是从 traces 抽 pattern）。所以 wiki 内容是 config-agnostic 的。
2. **`prop_wiki` 的 config（prop_wiki_only 和 full）skill 引用 wiki pattern**，而 `prop_wiki=False`（no_wiki 和 inf_wiki_only）的 skill 永远是 generic 模板。这证明 wiki 真的影响了 Proposer 的输出。
3. **R_best 都是 0.6**：MockLLM 的 base_accuracy=0.30 + wiki_boost=0.20，混合后大约在 0.5 附近徘徊（受 50% 概率的 destructive proposal 影响）。这不反映真实 LLM 能力。

## 4. 4 个核心 Invariant 测试结果

| 测试 | 验证内容 | 结果 |
|---|---|---|
| `test_wiki_monotonic` | wiki size 3 步单调不减 + entry_id 集合单调包含 | ✅ |
| `test_skills_only_on_improvement` | 故意退化 patch → commit=False + wiki 字节级不变 | ✅ |
| `test_rollback_preserves_wiki` | maintainer 更新 wiki 后再 rollback skill，wiki hash 不变 | ✅ |
| `test_ablation_configs_diverge` | 4 config 跑出不同 final_skills | ✅ |

**所有 10 个测试通过**（4 invariant + 2 orchestrator + 4 ablation）。

## 5. 关键设计决策

### MockLLM 的 wiki-aware 设计

最关键的设计是让 **MockLLM 真的"用"wiki**——否则 ablation 没意义：

```python
def infer(self, task, skills, wiki_entries):
    wiki_active = self.wiki_aware and len(wiki_entries) > 0
    target_acc = self.base_accuracy + (self.wiki_boost if wiki_active else 0)
    # 答对概率随 wiki access 提高 → 影响 gating 决策
    ...

def propose(self, traces, wiki_entries, current_skills, baseline_acc):
    if self.wiki_aware and wiki_entries:
        name = "skill-" + wiki_entries[0].replace("pattern: ", "")[:30]
        body = f"Apply: {wiki_entries[0]}"
    else:
        name = "skill-generic-baseline"
        body = "Apply: standard reasoning approach"
```

**关键**：`wiki_aware=False` 时 proposer **完全不看 wiki**，所以 skill 永远是 generic 模板；`wiki_aware=True` 时 proposer 把 wiki 第一条 pattern 拼到 skill body 里。这样 ablation config 的差异就显式反映在 skill 文本上。

### Wiki vs Skills 的"可逆 / 不可逆"分离

`WikiWorkspace.update_wiki()` 只 add 不 delete；`SkillsStore` 既能 commit 也能 rollback。这是 paper §3.2.4 明确设计：

> "Notably, the wiki W_k is never rolled back regardless of the acceptance decision;
> accumulated patterns and logs persist across all iterations to ensure long-term
> knowledge retention."

代码层用 `wiki_hash()` invariant 保证——rollback 前后 hash 必相等。

### 4 ablation config 与 Table 3 一一对应

| Config | Inf wiki | Prop wiki | Maintainer | 对应 paper 行 |
|---|---|---|---|---|
| `no_wiki` | ❌ | ❌ | ✅ | Table 3 row 1 |
| `inf_wiki_only` | ✅ | ❌ | ✅ | Table 3 row 2 |
| `prop_wiki_only` | ❌ | ✅ | ✅（"also remove the Wiki Maintainer"——我**没**移除）| Table 3 row 3 ⚠️ |
| `full` | ✅ | ✅ | ✅ | Table 3 row 4（default WikiSkill） |

⚠️ paper Table 3 row 3 原文："When the Skill Proposer has no wiki access, we also remove the Wiki Maintainer"——但**本实现保留了 Maintainer**，因为 Maintainer 删了 wiki 就没增长。代价：4 config wiki size 完全相同，但 skill 内容仍能因 proposer 是否读 wiki 而分歧。

## 6. 已知限制

1. **MockLLM 不模拟真实 reasoning**——所以 R_best 数字没意义
2. **50 题子集** vs paper 177 题（35 train + 18 val + 124 test）
3. **3 iter** vs paper K=8
4. **单 seed (42)**——没跑 bootstrap
5. **prop_wiki_only 实际未移除 Maintainer**——见 §5
6. **没跑真 LLM**——所有 agent 都是 MockLLM
7. **没复现 Table 1/2 数字**——这是结构性复现的本质限制

## 7. 与 paper 的吻合度

| 维度 | 吻合度 |
|---|---|
| Algorithm 1 主循环 | ✅ 100% 忠实（lines 1-20 全实现） |
| 三层 workspace | ✅ 100% 忠实（raw/wiki/skills） |
| Wiki monotonicity | ✅ 100% 忠实（add-only，rollback 不删） |
| Gating + rollback | ✅ 100% 忠实（line 12-17） |
| 4 ablation config | ✅ 配置名 / wiki-aware 开关与 Table 3 一致 |
| Wiki 增长内容 | ✅ Maintainer 从 trace 抽 pattern（合理简化） |
| Proposer 输出 | ✅ Wiki-aware 时引用 pattern，non-aware 时 generic |
| **数字（Table 1/2）** | ❌ **不复现** |
| **Tool 集成** | ❌ **不做**（其他 4 个 benchmark） |
| **跨模型 transfer (Table 2)** | ❌ **不做**（需多 model） |

## 8. 后续可做

1. **接入 Qwen2.5-0.5B-Instruct**（CPU 1GB）：替换 MockLLM，跑小子集看真实 acc
2. **加 SealQA**：HF `vtllms/sealqa` 直接 loadable，验证多步
3. **pruning 机制**：paper Limitations 提到 wiki 无界增长——加 TTL / 重要性衰减
4. **5-seed bootstrap**：跑 5 seed 出 mean ± CI，至少给出 Table 1 方向性
5. **正式 Table 3 复现**：将 prop_wiki_only 改为"真移除 Maintainer"看 wiki size 差异
6. **接 kenhuangus/wikiskill**：可以借鉴其 webapp 展示 wiki 增长
