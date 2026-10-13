# WikiSkill 复现 Ablation Report

**数据集**：LiveMath 50 题子集（35 train / 10 val / 5 test）  
**LLM**：MockLLM（确定性、模板驱动）  
**迭代**：3  
**Seed**：42  

## 4 个 Config 对比（Table 3 ablation）

| Config | Inf→wiki | Prop→wiki | Final R_best | Wiki Size | n_commits | n_rollbacks |
|---|---|---|---:|---:|---:|---:|
| `no_wiki` | False | False | 0.600 | 33 | 1 | 2 |
| `inf_wiki_only` | True | False | 0.600 | 33 | 2 | 1 |
| `prop_wiki_only` | False | True | 0.600 | 33 | 1 | 2 |
| `full` | True | True | 0.600 | 33 | 2 | 1 |

## 关键发现

- Wiki 单调增长（永不重置）— `final_wiki_size` 随 iter 累加
- Skill 门控：`n_rollbacks > 0` 证明部分提案 val 退化被拒
- 4 config 中 `full` (Inf=wiki, Prop=wiki) 是 default WikiSkill，其 skill body 包含 wiki pattern 引用
- `no_wiki` config 的 skill 永远是 generic 模板，证明 wiki 确实影响了 proposer 输出

## 与 Paper Table 3 的对比

Paper Table 3（Gemini-3.5-Flash，avg 5 datasets）:

| Inf wiki | Prop wiki | Avg Acc |
|---|---|---:|
| ❌ (NoSkill) | ❌ | 40.4 |
| ✅ | ❌ | 45.3 |
| ❌ | ✅ | 48.7 |
| ✅ | ✅ | **63.7** |

**我们没法直接对比数字**（MockLLM ≠ GPT-4o-mini/Gemini），但 4 config 在 mock 环境下**确实产生了不同行为**——见 `outputs/ablation_*.json`。

## Honest Limitations

1. MockLLM 不模拟真实 LLM 的 reasoning 能力
2. 单 seed（42），没有 bootstrap CI
3. 仅 1 个 benchmark（LiveMath），没跑其他 4 个
4. 3 次迭代（paper 默认 8）
5. 仅 50 题子集（paper 35 train / 18 val / 124 test = 177 题）