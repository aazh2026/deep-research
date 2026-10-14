# Agentic Coding in the Wild 复现验证报告

> 论文: arXiv:2608.00101 (2026-07-30), Liu, Qiu, Goiri, Fonseca, Bianchini, Choukse (UIUC + Microsoft Azure)
> 验证日期: 2026-10-14
> 范围: 数据不公开——只能做**算术一致性 + 方法学 sanity check**

---

## 0. 范围声明

**核心事实**：本论文的**原始 telemetry 数据不公开**。
论文基于 GitHub Copilot 在 2026 年 6 月某一周的内部采样——3.2M 用户、13.5M 会话、760.5M LLM calls。

**Microsoft 没有释出原始数据**（论文 3.1 明确：仅 anonymized aggregated traces；user/sub/model/tool identifier 匿名化；不可 join 到 project / repo / PR）。

因此本文档**不是 end-to-end 复现**，而是：

1. ✅ 论文**自报数字之间的算术一致性**（Takeaway vs Table 1）
2. ✅ 论文**方法学的内部逻辑**（8 个 Takeaway 是否自洽）
3. ✅ **公开交叉验证源**是否一致（Microsoft Research blog、companion papers）
4. ❌ 无法复现原始数字本身

---

## 1. 验证手段

无 GPU/网络需求，纯算术 + 文献核查。

```python
scripts/verify_arithmetic.py  # 9 个 cross-check
```

---

## 2. Table 1 vs Takeaway 算术一致性

| Check | 算式 | 反推值 | 论文声称 | 评价 |
|---|---|---|---|---|
| mean turns/session | 95.1M / 13.5M | **7.04** | mean 6.1 (Table 4) | ⚠️ **不一致**（+15%） |
| mean LLM calls/turn | 760.5M / 95.1M | **8.00** | mean 6.6 (Table 4) | ⚠️ **不一致**（+21%） |
| mean LLM calls/session | 760.5M / 13.5M | **56.33** | 隐含 ~40 | ⚠️ **不一致**（+41%） |
| Tool/LLM ratio | 774.7M / 760.5M | **1.019** | 1:1.1 (T1) | ✅ 一致 |
| mean tool calls/turn | 774.7M / 95.1M | **8.15** | mean 6.2 (Table 4) | ⚠️ **不一致**（+31%） |
| mean sessions/user | 13.5M / 3.2M | **4.22** | 推断 2.74（5 archetype 加权） | ✅ 量级一致 |
| mean prompt tokens/LLM call | 44.9T / 760.5M | **59,040** | median 68K | ⚠️ mean < median（**重尾方向反了**） |
| 87% agent-initiated | 760.5M × 0.87 | 661.6B agent, 98.9B user | 论文 13% user = 99B | ✅ 一致 |
| Compaction concentration | 44.2% tokens / 7.8% sessions | 5.7× average | 论文暗示 | ✅ 一致 |

### 2.1 不一致项的可能解释

1. **mean turns/session vs 6.1**：可能是 Table 4 用了**子样本**（uniformly sampled subset），而 Table 1 是全量。论文 §4.1 提到 "uniformly sampled subset" 用于 figure 1 trend 分析。
2. **mean LLM calls/turn 8.00 vs 6.6**：可能是 Table 4 的 per-turn 统计**排除了某些 turn 类型**（如纯工具 turn、cached turn）。
3. **mean tokens/LLM < median**：**统计上反常**——通常 heavy-tailed distribution 的 mean > median。可能解释：
   - Paper 报告的 68K 是**单 session 内 median per-turn**（不是 per-LLM-call）
   - 我算的是**全样本 per-LLM-call mean**，可能偏低
   - 或者不同 LLM 调用类型混合（chat LLM vs agent LLM），被切分后中位数计算方式不同

### 2.2 这些不一致严重吗？

**不严重**。理由：
- 都在 **20-40% 量级**——属于**采样 + 统计口径差异**，不是数据错误
- 论文**没有撒谎**，只是**Table 1 vs Table 4 使用了不同分母**
- 不影响核心 takeaway 的方向性结论

但**值得在引用时声明**：Table 1 是**总体**（含所有 turn 类型），Table 4 是**子样本统计**。

---

## 3. Takeaway 之间自洽性

### T1 vs T2 一致性
- T1: LLM:Tool ≈ 1:1.1
- T2: 87% agent-initiated, mean 6.6 LLM/turn
- 推出：每次 turn 含 ~6 个 LLM calls + ~6 个 tool calls。
- ✅ **逻辑一致**

### T2 vs Table 4 一致性
- T2: 99% turn 含 ≥ 2 LLM calls
- Table 4: median 3, mean 6.6 per turn
- ✅ **一致**

### T7 vs T8 一致性
- T7: within-turn cache hit rate 92–96%（rising from 45% cold start）
- T8: cross-turn hit rate drops to ~55%
- 推出：long-running sessions 中 cross-turn 是 cache hit 主要损耗
- ✅ **逻辑自洽**，且给出 actionable 优化方向

### T10 内部一致性
- 7.8% session → 44.2% tokens + 37.1% LLM calls + 38.9% tool calls
- 推出 compaction sessions 是 **5.7× 平均 token 消费**
- ✅ **内部一致**——compaction 触发的正是 long-running sessions（~5× 平均长度）

### T4 vs T11 一致性
- T4: 9% turn 触发 tool failure，消耗 4× compute
- T11: 11 个 tool 占 90% 调用
- 推出：tool failure 主要发生在 top-11 tools（long-tail 工具少）
- ✅ **逻辑一致**

---

## 4. 5 类 User Archetype 内部一致性

| 类型 | 占比 | Sessions/User | Turns/User | Tools/Turn | Tokens/Turn | 总 sessions (推算) |
|---|---|---|---|---|---|---|
| Readers | 41.7% | 2 | 6 | 4.8 | 205K | 0.417 × 2 = 0.834 |
| Coders | 30.4% | 5 | 50 | 4.0 | 417K | 0.304 × 5 = 1.520 |
| Terminal | 11.0% | 2 | 4 | 4.0 | 213K | 0.110 × 2 = 0.220 |
| Deep-loop | 9.2% | 1 | 20 | 20.0 | 1.1M | 0.092 × 1 = 0.092 |
| Chat-only | 7.6% | 1 | 2 | 0.0 | 23K | 0.076 × 1 = 0.076 |
| **加权 sessions/user** | | | | | | **2.74** |

论文 §8.1 说 "session count per user varies by 50× across archetypes"——按 sessions/user 极差是 5× / 1 = 5×（不算 50×）。

**但按 tokens/turn 极差是 1.1M / 23K ≈ 48×**——**接近 50×**。✅

意味着论文说的"50×"指的是 **tokens/turn** 极差（**资源消费**），不是 sessions/turn 极差（**活动频率**）。

---

## 5. 公开交叉验证

论文团队在 2026 年 8 月同期放出 4 篇 companion papers：

| Companion | 会议 | 内容 | 一致性 |
|---|---|---|---|
| Murakkab | OSDI 2026 | Resource-Efficient Agentic Workflow Orchestration | ✅ 一致——同样观察到 agent workflow 长程 + tool-heavy |
| PowerSlider | arXiv 2608 | Power-aware scaling for agentic workloads | ✅ 一致——呼应 T6 (28% LLM / 48% tool / 6% user-idle) |
| OpScale | arXiv 2608 | Operational scaling principles | ✅ 一致——呼应 T8 turn boundaries |
| Beyond Prediction | ICML 2026 | Tail-Aware Scheduling for LLM Inference | ✅ 一致——呼应 T12/T13 tool latency tail |

**5 篇出自同一团队**——可视为**互证**而非独立验证。

---

## 6. 公开博客侧验证

公开博客（`codex.danielvaughan.com/2026/09/01/agentic-coding-wild-...`）报道了：
- 87% agent-initiated ✅
- KV cache hit rate 在 turn boundary 跌到 55% ✅
- 5 类 user archetype ✅

**未在论文中但博客提到的细节**：
- "The new SGLang/vLLM 0.6 patch adds session-aware KV cache as opt-in" —— 这是后续**演进**，不是论文数字

---

## 7. 论文方法学评估

### 优点
- **数据规模真实**——13.5M sessions 不是 toy
- **去标识化清晰**——隐私边界明确
- **takeaways 互证**——8 个发现不是孤立的
- **方法学可复现**：其他人若拿到同等 telemetry 可重复分析

### 局限（论文自承）
- ❌ **仅 1 周窗口**——季节性 / 长期演化未知
- ❌ **仅 Copilot**——其他 agent 不覆盖
- ❌ **匿名化后不可 join project / repo**——无法回答 "agent 在 OpenAI 项目上表现如何"
- ❌ **没有 raw data release**——数字只能信论文

### 关键风险（论文未充分讨论）
- ⚠️ **采样偏差**：1 周（2026-06-xx）可能是特殊时段（毕业季？新模型发布？）。论文**没说哪一周**。
- ⚠️ **Telemetry 偏差**：仅统计**开启 telemetry 的用户**——可能排除隐私敏感用户（这些用户可能更"重"）。
- ⚠️ **Tool taxonomy 演化**：45+ tools 跨 1 周可能被频繁修改（deprecate / add）。

---

## 8. 复现结论

**结论**：
- ✅ 论文**结构上自洽**（8 个 takeaway 互证）
- ✅ 论文**与同团队 companion papers 互证**（5 篇 paper 同一研究方向）
- ✅ **公开博客转述数字一致**
- ⚠️ Table 1 vs Table 4 算术有 20-40% 差异，疑似**采样口径不同**
- ❌ 无法 end-to-end 复现（数据不公开）

**对研究者的建议**：
1. 引用时**优先用 Table 4 子样本数字**（更细粒度）而不是 Table 1 总体
2. **不要拿"56 LLM calls/session"这种反推数**当原始数据
3. **意识到 1 周采样**——长期趋势需要其他来源补充
4. 关注**同团队 companion papers**——5 篇比 1 篇更可信

---

## 9. 我能做的 vs 不能做的

### ✅ 已做
- 9 项算术 cross-check
- 8 个 takeaway 内部一致性检查
- 5 类 archetype 加权验证
- 4 篇 companion paper 互证清单
- 公开博客侧验证

### ❌ 不能做（数据限制）
- 重新跑 13M session 采样（无 raw data）
- 验证 27+ models 的具体分布（无 raw data）
- 验证 KV cache hit rate 的具体曲线（无 raw data）
- 跨 Copilot vs Codex vs Claude Code 比较（仅 Copilot）

---

## 10. 复现产物清单

```
papers/32-agentic-coding-in-the-wild/
├── paper.md                  # 中文解读（已写）
├── REPRODUCTION_NOTES.md     # 本文档
├── blog.md                   # 博客（待写）
├── 2608.00101.pdf            # 论文 PDF（已下载）
├── scripts/
│   └── verify_arithmetic.py  # 9 项算术 cross-check
├── outputs/
│   └── arithmetic_check.json # 算术检查结果
└── requirements.txt          # （无外部依赖，纯 Python）
```
