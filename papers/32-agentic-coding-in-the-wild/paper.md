# Agentic Coding in the Wild 论文中文解读

> Paper: Banruo Liu, Haoran Qiu, Íñigo Goiri, Rodrigo Fonseca, Ricardo Bianchini, Esha Choukse. **"Agentic Coding in the Wild: Characterizing GitHub Copilot at Production Scale"** (arXiv: 2608.00101, 2026-07-30)
> 单位: UIUC + Microsoft Azure Research
> 解读日期: 2026-10-14

---

## 一句话定位

> 第一次用 **生产 telemetry**（不是 benchmark）刻画了 2026 年 Coding Agent 的真实负载：3.2M 用户、13M 会话、760M LLM 调用、44.9T prompt tokens。
> 核心结论：**LLM 与 tool 调用近乎 1:1 耦合**，长程 agent loop 对 KV cache、context compaction、user turn boundary 提出了**完全不同于 chat serving** 的工程要求。

---

## 1. 为什么这件事重要

2024–2025 的 LLM serving 系统（vLLM、SGLang、TensorRT-LLM）都是按 **chat workload** 设计的：
- 请求**短**（< 2K tokens）
- 请求**独立**（stateless）
- 流量**周期性**（昼夜峰谷）

但 2026 年的 **Coding Agent workload 完全不同**：
- 会话**长**（P90 超过 100 个 LLM 调用 + 3 小时）
- 内部调用**强耦合**（LLM → tool → LLM 链）
- **session-structured** 流量（KV cache 是 session-level 资源）
- 工具调用占 28% prompt tokens

**论文贡献**：基于 GitHub Copilot 真实生产数据，给出**首次生产级定量刻画**，并挑战了**当前 LLM serving 系统的设计假设**。

---

## 2. 数据集与方法

| 维度 | 数字 |
|---|---|
| 时间窗口 | 1 周（2026 年 6 月） |
| 采样 | 13.5M sessions from 3.2M users |
| 规模 | 95.1M user turns, 760.5M LLM calls, 774.7M tool invocations |
| Token | 44.9T prompt, 39.3B completion |
| 多样性 | 27+ distinct models, 45+ tools |
| 去标识化 | 所有 user/subscription/tool 名称匿名化 |

**方法**：从 Visual Studio + VS Code 收集 telemetry，**不收集** prompt 文本、文件内容、模型输出。**匿名化 user/sub/model/tool identifier** 后跨表 join。

---

## 3. Session Hierarchy

论文定义 3 层结构（与 SWE-bench 类 benchmark 完全不同的视角）：

```
Session     = coding agent session lifetime
  Turn      = 一个 user-initiated conversation（含很多 LLM calls）
    Step    = 一个 LLM invocation 或 tool invocation
```

> Session → Turn → Step 三层递归，是后续所有分析的基础。

---

## 4. 八大核心发现（论文编号 Takeaway 1–13）

### Takeaway 1：1:1 LLM ↔ Tool coupling

- **87%** LLM 调用是 **agent-initiated**（不是用户触发）
- 平均每个 user turn 内 **6.6 个 autonomous LLM calls**
- LLM:Tool ≈ **1:1.1**（中位 40.6 LLM calls, 45.6 tool calls per session）
- **99%** turn 含 ≥ 2 个 LLM call；20.2% turn 含 ≥ 10 个

> **含义**：serving 系统必须把 LLM 和 tool 调用视为**成对的 pair**，而不是独立请求。

### Takeaway 2：87% LLM calls 是 agent-initiated

- 用户主动 prompt 占比仅 **13%**
- **87%** 来自 agent 自动循环
- 大多数来自 session serving 期间（不是直接 user interaction）

> **含义**：agent 自动循环主导 serving load。idle time 与 user inter-turn gap 才是关键调度因子。

### Takeaway 3：Execution 极度异构 + 串行

- 论文观察到 **inverted-U pattern**（P50–P90 KV cache 并行度）
- 串行执行 turn 比并行**多 4–6 倍**

> **含义**：serving 系统应有 KV-cache 状态保留，而非简单 stateless 调度。

### Takeaway 4：Tool 严重异构 + 失败放大

- 40+ distinct tools，但 4 个最常用（get_file 35%、apply_patch 12%、replace_string 8.1%、grep_search 6.6%）
- **9% 的 turn 触发 tool failure**，消耗 **4× 中位 compute**（retry loop）
- 失败工具里 73% 是 read-and-search 类（get_file、code_search），20% 是 edit 类（apply_patch、replace_string）

> **含义**：tool failure 是 compute 放大的主要来源，需 robustness 设计（idempotency、retry-with-backoff、compaction-aware error reporting）。

### Takeaway 5：Prompt 极度长 + 不均匀

- 中位 prompt token = **68K**
- 中位 completion token = **247**
- 比例 **275:1**（input-heavy）
- Conversation history 占 prompt 的 **48%**，tool result 占 **28%**，剩余是 system prompt + user content

> **含义**：输入主导的 workload，**KV cache 是关键资源**。Serving 系统应**保留长 prompt**。

### Takeaway 6：Agent session 主要是 LLM-bound

- LLM execution 占 session wall-clock 的 **28.4%**
- Tool execution 占 **48%**
- User-idle 占 **6%**

> **含义**：tool execution **主导 wall-clock**，不是 LLM。Serving 系统需要**双轨调度**。

### Takeaway 7：Prefix cache hit rate 高（~98% 起始）

- 中位 cache hit rate = **45%**（首调用冷启动）
- 后续 turn 增长到 **92–94%**
- 3rd 调用后稳定在 ~98%
- **全 agent workload 整体命中率 92–96%**

> **含义**：KV cache 复用是巨大的优化杠杆。

### Takeaway 8：Turn boundaries destroy cache

- 跨 turn 边界，**hit rate 跌到 ~55%**
- Idle gap 2–10 分钟：降到 **~70%**
- 超过 10 分钟：**~0%**

> **含义**：跨 turn cache miss 是必然事件。需要**预测 idle time** 来做 preemption。

### Takeaway 9：Idle-time 预测可达 86–90% 准确率

- 一个轻量级 predictor（用 turn-level + session-level features）可捕获 **86–90%** idle time
- 中位 within-turn idle = 1.2s
- 中位 cross-turn idle = 172s
- 容器 idle at turn boundary = 4.1min

> **含义**：scheduling-aware serving 完全可行。

### Takeaway 10：Context compaction 隐藏成本

- **7.8%** session 触发 compaction
- 但这些 session 占据 **44.2%** total tokens, **37.1%** LLM calls, **38.9%** tool calls
- Compaction 之后丢 **>70%** prompt tokens，等于 model switch 的 cache cold start

> **含义**：compaction **不免费**——丢掉历史意味着上下文重建成本。

### Takeaway 11：Tool usage 集中

- 11 个最常用 tool 占 **>90%** 调用
- Top 27 个 tool 占 **>99%**
- 其中 "Other" 占 4.6%（长尾工具）

> **含义**：tool latency profiling 应该**优先覆盖 top 11–27 个**。

### Takeaway 12：Tool 调用长尾 + 重叠

- 93% tool batch 含单个 tool
- 但 **76%** execution time 有 LLM↔tool overlap（同一时间窗内并行）
- 长任务（>30s+）几乎 **100%** overlap LLM+tool

> **含义**：**per-call 调度**比 batch 调度更有效。

### Takeaway 13：Tool-LLM overlap 是 pervasiveness

- 97% tool batch 含一个 LLM call 在窗口内
- 但**很多 tool 调用是 long-running 串行**，不能被 LLM 加速

> **含义**：overlap 真实存在但**有限度**——不是所有 tool 都能异步。

---

## 5. 5 类 User Archetype

| 类型 | 占比 | 特征 |
|---|---|---|
| **Readers** | 41.7% | 2 sessions/user, 6 turns, 4.8 tools/turn, 205K tokens/turn（**最大 token 消费**，RAG-heavy）|
| **Coders** | 30.4% | 5 sessions/user, 50 turns, 4.0 tools/turn, 417K tokens/turn（**主代码写作**）|
| **Terminal** | 11.0% | 2 sessions/user, 4 turns, 4.0 tools/turn, 213K tokens/turn（CLI 重度）|
| **Deep-loop** | 9.2% | 1 session/user, 20 turns, **20.0 tools/turn**, 1.1M tokens/turn（**最重 agent loop**，refactor/debug）|
| **Chat-only** | 7.6% | 1 session/user, 2 turns, 0.0 tools/turn, **23K tokens/turn**（最轻）|

> **含义**：5 类用户**资源消费差异 50×**（7.6% 用户可能比 9.2% 用户少 50 倍 tokens）。Serving 系统需要 per-user SLO。

---

## 6. Cache Compaction 的工程含义

论文 Figure 17–20 是 cache 行为最精彩的实证：
- **7.8% session 触发 compaction**，但占 44% tokens
- compaction 后的 cache hit rate 跌到 **0% 起步**
- 平均 drop 66.1%，尾部 drop 99%+
- **21% cases 触发 model switch**——这是更严重的 cold start

> **含义**：compaction 必须做成 **partial cache 保留**（类似 Anthropic 的 prompt cache，保留 KV cache 头部）。否则反而更贵。

---

## 7. 服务端优化建议（论文给出 9 条）

1. **Session-aware KV cache lifecycle**——不是 stateless serving
2. **Idle-time prediction**——把 idle 转化为 scheduling 杠杆
3. **Tool-aware scheduling**——tool failure 是 compute amplifier
4. **LLM-Tool overlap scheduling**——长 tool 应该异步不阻塞 LLM
5. **Per-user SLO**——5 类用户资源差异 50×
6. **Partial cache on compaction**——不要全丢
7. **Model switch minimization**——一次 switch 掉 8% cache
8. **Failure-aware retry**——9% 失败 turn 消耗 4× compute
9. **Token type breakdown 观测**——48% history + 28% tool result 是 prefix-reuse 的金矿

---

## 8. 个人思考（reviewer notes）

### 优点
- **首次**用生产 telemetry 量化 Coding Agent workload 的真实形状
- 数字**有 8 个不同 Takeaway 互相印证**——不是单点 case study
- 对**serving 系统设计**有直接 actionable 影响
- 5 类 user archetype 的发现**反直觉但数据扎实**

### 局限（论文自承）
- **仅 1 周窗口**——季节性 / 长期趋势没覆盖
- **仅 Copilot 数据**——其他 agent（Codex、Claude Code、Cursor）可能不同
- **去标识化后无法 join**到具体 project / repo / PR
- **没有公开原始 telemetry**——数字只能信论文

### 关键风险
- 87% agent-initiated 调用意味着 **GPU cost 主要由 agent 决策驱动**，而不是 user prompt 数量。**Billing 模型需要重构**（按 session 计费 vs 按 call 计费）。
- KV cache 是 session-level 资源 → **serving 系统从 stateless 转向 stateful**——这是 LLM infra 的根本性转折。

---

## 9. 与 LoopsBench 的关系

| 维度 | LoopsBench | Agentic Coding in the Wild |
|---|---|---|
| 数据来源 | 112 受控任务 | 13.5M 真实 session |
| 评测对象 | Loop engineering | Production telemetry |
| 优势 | 任务结构清晰 | 真实负载形状 |
| 限制 | 小规模、纸面 | 不可复现，仅能信数字 |
| 工程影响 | 推动 loop 设计 | 推动 serving 设计 |

两者**互补**：LoopsBench 告诉你 loop 怎么做对，这篇论文告诉你 loop 在生产中**实际是什么形状**。

---

## 10. 落地建议（如果你在做 LLM serving）

1. **不要用 vLLM 默认配置**直接 serve Coding Agent——stateless 不适用
2. **KV cache 按 session 保留**，不要按 request 失效
3. **Tool-aware retry**：为 read 类和 edit 类分别设计 backoff
4. **预测 idle time**：用 lightweight ML model 帮 scheduler 做 preemption
5. **Compaction 做成 partial**：丢掉 70% tokens 是浪费
6. **分用户 tier**：reader / coder / deep-loop 是**不同 workload**，分开调度
