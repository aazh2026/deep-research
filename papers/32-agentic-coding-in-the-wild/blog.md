# 当 vLLM 遇上 Coding Agent：一份来自 1300 万次会话的生产级诊断书

> 写于 2026-10-14，配合 `papers/32-agentic-coding-in-the-wild/paper.md` 与 `REPRODUCTION_NOTES.md` 阅读。
> 这篇 blog 解决一个问题：**为什么 2026 年你跑 Coding Agent 还是觉得 GPU 不够用？**

---

## 引子：你以为的 LLM Serving 和真实的 Coding Agent Serving

2024–2025 年，绝大多数 LLM serving 系统都按 **chat workload** 设计：
- 请求**短**（< 2K tokens）
- 请求**独立**（stateless）
- 流量**周期性**（白天多、夜里少）

vLLM、SGLang、TensorRT-LLM 的默认配置，都是按这个画像调的。

但 2026 年的 GitHub Copilot 真实生产数据显示——

> **87%** 的 LLM 调用是 **agent 自己发起的**（不是用户触发）。
> **87%** 的 token 消费来自**不到 10%** 的会话。
> 一个 session 中位 **3 个 turn**、**15 个 LLM 调用**、**45.6 个 tool 调用**、**62.6 分钟**。
> **P90 session 超过 100 个调用 + 3 小时**。

这跟 chat workload 完全不是一回事。**你跑 Coding Agent 还是按 chat 调 vLLM，资源注定浪费 80%+。**

Microsoft Azure Research + UIUC 的 6 人团队在 2026 年 7 月放了一篇论文，把这个真实形状**第一次定量刻画**出来。

---

## 这篇论文做了什么

**数据**：GitHub Copilot 在 2026 年 6 月某一周的内部 telemetry 采样。
- **3.2M 用户**
- **13.5M 会话**
- **95.1M 用户 turn**
- **760.5M LLM 调用**
- **774.7M tool 调用**
- **44.9T prompt tokens + 39.3B completion tokens**
- **27+ 模型**、**45+ 工具**

**方法**：从 VS + VS Code 收集**匿名化** telemetry，**不收集** prompt 文本、文件内容、模型输出。

**产出**：13 个 Takeaway，覆盖 workload 形状、KV cache 行为、context compaction、tool failure、user archetype 等。

---

## 13 个核心 Takeaway 中最重要的 4 个

### Takeaway 1+2：LLM 和 tool 调用是 1:1 耦合

- 中位 **40.6 LLM calls + 45.6 tool calls per session**
- LLM:Tool ≈ **1:1.1**
- **87%** 是 agent-initiated
- 平均每个 user turn 内 **6.6 个 autonomous LLM calls**

> **含义**：serving 系统必须把 LLM 和 tool 调用视为**成对的 pair**——不是独立请求。VLLM 默认调度策略直接失效。

### Takeaway 7+8：KV cache 是 session 级资源

- Turn 内 cache hit rate 从 45% 升到 92–94%
- **跨 turn 边界跌到 ~55%**
- Idle 2–10 分钟：~70%
- Idle >10 分钟：**~0%**

> **含义**：跨 turn cache miss 是必然事件。**vLLM 的按 request 失效**策略每次 turn 都付出全量 prefill 代价。

### Takeaway 10：Context compaction 隐藏成本

- 仅 **7.8%** session 触发 compaction
- 但这 7.8% 占 **44.2%** 的 token、**37.1%** LLM 调用
- Compaction 后丢 **>70%** prompt tokens——等同于 model switch 的 cold start

> **含义**：compaction **不是免费午餐**。丢掉历史意味着重新 prefill 几万 token。

### Takeaway 6：Tool execution 主导 wall-clock

- LLM execution 占 session wall-clock **28.4%**
- Tool execution 占 **48%**
- User-idle 占 **6%**

> **含义**：你优化 LLM serving 速度是错的方向——**tool execution 才是瓶颈**。

---

## 5 类用户画像（这是我最意外的发现）

| 类型 | 占比 | 特征 |
|---|---|---|
| **Readers** | 41.7% | RAG 重度（205K tokens/turn），几乎不写代码 |
| **Coders** | 30.4% | 主写代码（417K tokens/turn）|
| **Terminal** | 11.0% | CLI 重度（4 tools/turn）|
| **Deep-loop** | 9.2% | **单 session 1.1M tokens/turn**——debug / refactor |
| **Chat-only** | 7.6% | 偶尔问问题（23K tokens/turn）|

**Tokens/turn 极差 50×**。

> **含义**：**2 个 Deep-loop 用户**消耗的资源 ≈ **100 个 Chat-only 用户**。Serving 系统必须 per-user tier，不能全员一个 SLO。

---

## 我做的算术复现（发现了一些不一致）

论文公开 Table 1（总体）和 Table 4（子样本统计）。我反推了几个数：

| Check | 反推值 | 论文声称 | 评价 |
|---|---|---|---|
| mean turns/session | 7.04 | 6.1 | ⚠️ +15% |
| mean LLM calls/turn | 8.00 | 6.6 | ⚠️ +21% |
| mean LLM calls/session | 56.33 | ~40（隐含） | ⚠️ +41% |

**不是数据错误，是 Table 1 vs Table 4 用不同分母**（Table 4 是子样本，Table 1 是全量）。**值得在引用时声明口径**，但**不影响 8 个 takeaway 的方向性结论**。

完整 9 项 cross-check 见 `REPRODUCTION_NOTES.md`。

---

## 对 LLM Serving 系统的实际意义

如果你在做 LLM infra，今天**至少该考虑 5 件事**：

### 1. Session-aware KV cache
- 不要按 request 失效——按 **session** 保留
- 跨 turn 至少 2 分钟保留窗口
- Anthropic prompt cache、vLLM 0.7+ 的 session KV API 都是这个方向

### 2. Idle-time prediction
- 用 lightweight model 预测 turn 间隔
- 论文给出 86–90% 准确率的小模型即可
- 把 idle 时间转化为 preemption 调度机会

### 3. Partial cache on compaction
- 不要一次丢 70% tokens
- Anthropic prompt cache、OpenAI cached prompt 都是这个思路
- 或者用 hierarchical KV（recent + summary）

### 4. Tool-aware scheduling
- tool failure 是 4× compute amplifier
- read 类和 edit 类分别设计 backoff
- 长 tool 应该异步（不阻塞 LLM serving）

### 5. Per-user SLO tier
- Readers / Coders / Deep-loop 是**不同 workload**
- 至少分 2 个 tier：interactive（Chat、Coder）和 heavy（Deep-loop、Reader）
- Billing 模型要重新设计——按 session 而不是 call

---

## 这篇论文和 LoopsBench 的关系

我上一轮写了 LoopsBench（`papers/23-loopsbench/`）。两篇**互补**：

| 维度 | LoopsBench | Agentic Coding in the Wild |
|---|---|---|
| 数据来源 | 112 受控任务 | 13.5M 真实 session |
| 评测对象 | Loop engineering 设计 | Production telemetry 形状 |
| 优势 | 任务结构清晰 | 真实负载形状 |
| 限制 | 小规模、纸面 | 数据不公开 |
| 工程影响 | 推动 **loop 设计** | 推动 **serving 设计** |

> **LoopsBench 告诉你 loop 应该怎么写对**，
> **这篇论文告诉你 loop 在生产中实际是什么形状**。

两者加起来才是完整的 picture。

---

## 我对这篇论文的改进建议

1. **公开 Table 1 vs Table 4 的口径差异**：避免别人误用
2. **公开 sampling window 的具体日期**（周中？周末？毕业季？）
3. **公开 1–2 个 take 的 raw aggregated traces**（不暴露 user）—— 让其他人能复用分析
4. **跨 Copilot vs Codex vs Claude Code 比较**——同样方法学再跑一遍其他 agent
5. **补充 long-term trend**——1 周不够，至少 1 个季度

---

## 结语

2026 年的 Coding Agent 已经**不是 chat 的多轮对话**，而是**session-structured 的长程 workload**。

你跑 Coding Agent 还是按 chat 调 vLLM，资源注定浪费 80%+。

这篇论文给你**13 个 actionable insight**——其中至少 4 个（LLM-tool coupling、KV cache lifecycle、compaction cost、user archetype）直接可以翻译成**serving 系统的优化决策**。

> **不读这篇论文，你可能 2027 年还在用 2024 年的 chat serving 思维跑 Coding Agent**。
> 那就太亏了。

---

## 参考

- 论文 PDF：`papers/32-agentic-coding-in-the-wild/2608.00101.pdf`
- 同团队 companion papers：
  - Murakkab (OSDI 2026)
  - PowerSlider (arXiv 2608)
  - OpScale (arXiv 2608)
  - Beyond Prediction: Tail-Aware Scheduling (ICML 2026)
- Microsoft 公告：https://msft.it/6016abyrY

> 本博客基于算术 cross-check（不接触原始 telemetry——论文未公开），详见 `REPRODUCTION_NOTES.md`。
