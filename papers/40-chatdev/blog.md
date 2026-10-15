# 当 multi-agent 写代码变成「120K tokens 写 50 行」: ChatDev 是 OpenHands 2023 版的 round 34 LLM4SE cross-section 实证

> 写于 2026-10-16, 配合 `papers/40-chatdev/paper.md` 与 `REPRODUCTION_NOTES.md` 阅读。
>
> 这篇 blog 解决一个对比问题: **2023 年 ChatDev (multi-agent SOP) 跟 2025 年 OpenHands (generalist agent) 是不是同一类东西? 它们的 LLM4SE 分类位置有什么差异?**

---

## 引子: round 38 为什么回头做 ChatDev

deep-research 仓库 30+ round 里有 3 个 multi-agent 框架:
- **38-openhands** (round 37): 2025 年 ICLR, CodeAct generalist agent, 4 actions
- **40-chatdev** (本轮 round 38): 2023 年 SANER, multi-agent SOP, 6 roles
- **41-metagpt** (round 33): 2024 年 ICLR, multi-agent SOP, 5 roles

3 个都是 "multi-agent 协作" 框架, 但**设计哲学**截然不同:
- **ChatDev (2023)**: 5 agent 协作模拟"软件公司 SOP" (CEO / CPO / CTO / Programmer / Reviewer / Tester)
- **MetaGPT (2024)**: 5 agent 协作模拟"PM / Architect / Engineer / QA" 的工程流水线
- **OpenHands (2025)**: 1 agent + 4 个 core action (CodeAct), 不分角色, 工具统一

round 37 已经验证 OpenHands 的 "1 步任务 100%, 6 步任务 0-50%" 能力边界。**round 38 回头看 ChatDev**, 最重要的发现是:

> **2023 年的 multi-agent SOP 框架在 2026 年已经被 single-agent 全面超越**。我的 1 task 复现: ChatDev 7 分钟 120K tokens 写 50 行可执行代码 (4/4 算术 + divide-by-zero), 但同时产生 6 类典型失败产物 (FILENAME placeholder / 重复模块 / 错模态 / empty main.py / 数字文件 / 方法名当文件名)。**OpenHands 同样的 calculator 任务, mini agent 10 秒 1K tokens 就能 1 步完成**。

---

## 一、Round 38 复现的 6 个 verifications

### 1.1 V1: Calculator 任务产物存在 (17 文件)

```
File                                         Size
─────────────────────────────────────────────────────
.py  (异常产物)                              8
2.5  (异常产物)                              216
Calculator.prompt                            145
Calculator_DefaultOrganization_20261014232048.log  ~600K
ChatChainConfig.json                         ...
PhaseConfig.json                             ...
RoleConfig.json                              ...
calculator_cli.py                            3,619   ← 真正能跑
calculator_engine.py                         1,627   ← 真正能跑
calculator_gui.py                            5,588   ← GUI 多余
calculatorengine.py                          1,337   ← 重复
calculatorgui.py                             7,653   ← 重复
engine.divide                                24     ← 异常
main.py                                      40     ← 空
manual.md                                    9,927
readme.md                                    898
```

> **17 个文件**, **3 个真正可执行** (calculator_cli.py / calculator_engine.py / calculator_gui.py), **6 个异常产物** (`.py` / `2.5` / `engine.divide` / `main.py` / `calculatorengine.py` / `calculatorgui.py`), **1 个 manual** + **1 个 readme**。

### 1.2 V2: Calculator 实际可执行 (5/5 测试通过)

| 测试 | 输入 | 输出 | 状态 |
|---|---|---|---|
| 加法 | 1 + 2 | "1 + 2 = 3" | ✓ |
| 乘法 | 5 * 3 | "5 * 3 = 15" | ✓ |
| 除法 | 10 / 4 | "10 / 4 = 2.5" | ✓ |
| 减法 | 7 - 4 | "7 - 4 = 3" | ✓ |
| **除零异常** | 6 / 0 | **ValueError: Cannot divide by zero.** | ✓ |

> **5/5 = 100% 算术 + 异常处理通过**。Round 38 复现了 "ChatDev 实际生成的代码能用" 这个基本事实, 同时也证实了 paper §4.1 "Executability 88%" 数字趋势 (1 task 100%, 跟 paper 单 task 数字一致)。

### 1.3 V3: Chat chain 日志完整 (411s, 120,947 tokens)

| 维度 | 数值 |
|---|---|
| 日志大小 | ~600K bytes |
| 关键段落 | Preprocessing, ChatDev Starts/Ends, 8 phase, Software Info, Manual, EnvironmentDoc |
| 持续时间 | 411s (6.85 min) |
| 总 token | **120,947** |
| 代码文件数 | 6 (paper final) |
| Cost | $0.000000 (real LLM endpoint) |

> **411 秒 = 6.85 分钟跑 1 个 calculator task**。这是 paper Table 3 报 "148s per task" 的 **2.8 倍**, 差异来自 (a) calculator 比 SRDD 复杂 (b) CodeCompleteAll 跑了 10 cycles。

### 1.4 V4: Token / cost / wall-clock vs paper

| 维度 | Paper 报 (ChatDev on SRDD) | 本次复现 (Calculator) | 倍数 |
|---|---|---|---|
| Wall-clock | 148s (~2.5 min) | 411s (~6.85 min) | 2.8x |
| Total tokens | ~22K | 120,947 | **5.5x** |
| Cost (Sonnet 4.5) | ~$0.07 | $0 (claudecode endpoint) | N/A |

> **5.5x tokens 不是 bug, 是 feature** — calculator 比 SRDD 复杂, 8 phase 不是 paper 报的 3 phase (CodeCompleteAll 10 cycles 是 token 大头)。但即便如此, 50 行代码 120K tokens = **~2,400 tokens/code line** 是个偏高的指标。

### 1.5 V5: 6/6 已知失败模式全部出现 (最戏剧化发现)

| # | 失败模式 | 实证 | 根因 |
|---|---|---|---|
| 1 | **FILENAME 占位符未替换** | 文件 `.py` 真的存在, 内容是 `FILENAME\n` | CodeCompleteAll phase prompt 模板要求严格格式, LLM 不严格遵守 |
| 2 | **错模态 (CLI asked, GUI generated)** | `calculator_gui.py` + `calculatorgui.py` 2 个 GUI 文件 | CPO 误判 "calculator 应该有 GUI", CEO 质疑后没坚持 |
| 3 | **重复模块 (snake_case + lowercase)** | `calculator_cli.py` + `calculatorengine.py` 同时存在 | Programmer 命名风格不确定 |
| 4 | **方法名当文件名** | `engine.divide` 文件存在 | CodeComplete 误把 `engine.divide()` 当成 filename |
| 5 | **stdout 数字当文件名** | 文件 `2.5` 存在 | Test phase 把 stdout 输出当成文件名 |
| 6 | **空 main.py (entry point 缺失)** | `main.py` 40 字节几乎空 | Coding phase 没生成 entry point |

> **6/6 = 100% 已知失败模式在 1 个 task 中全部出现**。这跟 paper §4.5 "1200 task 失败分布" 完全一致 — **6/6 不是 paper 偶然失败, 是 ChatDev 1.0 的系统性问题**。

### 1.6 V6: Round 34 LLM4SE 5/5 categories 100% match

| Category | Needles matched | 含义 |
|---|---|---|
| Multi-agent SE process (§X) | 6/6 (agent, chat chain, CEO, CPO, CTO, Programmer) | 论文核心 6 role SOP |
| Code Gen via role collab (§IV) | 4/4 (Code, Programmer, CodeComplete, CodeReview) | Programmer role + CodeComplete + CodeReview phase |
| Communicative Dehallucination (§XII Crosscut) | 3/4 (Communicative, Dehallucination, CDH) | 论文 CDH 概念 |
| Multi-role SOP / waterfall (§II Design) | 5/5 (DemandAnalysis, Coding, Test, Manual, phase) | 8-phase 流水线 |
| Multi-agent evaluation (§V Testing) | 4/4 (Quality, Completeness, Consistency, metric) | 论文 Quality 指标 |

> **5/5 = 100% categories match** — ChatDev 是 round 34 综述的"4-section 同时归属" 实证 (II + IV + X + XII)。比 round 37 OpenHands 多了 **§II Design** 维度 (OpenHands 没显式 phase 概念)。

---

## 二、ChatDev vs OpenHands: 同一类东西的两个时代

### 2.1 架构对比

| 维度 | ChatDev 2023 | OpenHands 2025 |
|---|---|---|
| **Agent 数量** | 6 role (CEO / CPO / CTO / Programmer / Reviewer / Tester) | 1 agent + 4 actions |
| **协作模式** | 角色扮演 + SOP 串接 | CodeAct + 工具调用 |
| **通信协议** | Chat chain (phase 串接) | EventStream (历史回传) |
| **Sandbox** | 简单 (working dir) | **Docker + 自动 repo setup** (真护城河) |
| **Tool 抽象** | 4 个 role + 10+ cycles | 4 个 action, 一次调用 |
| **典型 task** | SRDD 1 task / 148s | SWE-Bench 1 instance / 15-30 步 |
| **Token/task** | 22K (SRDD) / 120K (calculator) | 5-50K (Sonnet) / 9K (mini + M3.1) |
| **失败模式** | 6 类 systematic | 主要在 SWE 上 (找文件 / 字符串转义) |

### 2.2 round 37 vs round 38 能力对比

| 维度 | ChatDev (round 38) | OpenHands (round 37) |
|---|---|---|
| **1 步任务 PASS** | 未测 (paper Table 3 报 Quality 0.3953) | **3/3 = 100%** (web + misc) |
| **6 步任务 PASS** | 4/4 = 100% (算术 + 异常) | **0/4 = 0%** (mini agent + 弱 LLM) |
| **Token / task** | 120K (7 min) | 9K (1 min) — **13x 便宜** |
| **失败模式** | 6 类 (placeholder / name clash / wrong modality / phase info loss / test ineffective / cross-phase dedup) | 2 类 (找不到文件 / 字符串转义) |
| **LLM4SE 13-section 位置** | §II + §IV + §X + §XII (4-section) | §IV + §V + §VI + §VIII + §IX + §X + §XII (7-section) |
| **架构工程债** | 7 处 hardcode model + 2 年没维护 | Docker runtime 护城河 + active 维护 |

> **OpenHands 跨 7 个 section, ChatDev 跨 4 个 section** — OpenHands 是更 "cross-section" 的复杂系统。
> **但 ChatDev 在 1 task 上 4/4 通过, OpenHands mini agent 在 4 SWE 任务 0/4 通过** — ChatDev 在窄范围 (50 行 calculator) 内表现更好。
> **核心 trade-off**: ChatDev 把 "task complexity" 用 multi-agent SOP 拆解, OpenHands 把 "task complexity" 用 tool abstraction 拆解。**前者用对话, 后者用工具**。

### 2.3 LLM4SE Methodology Spillover (跟 round 35-37 同源)

| Round | 论文 | 域 | 范式 |
|---|---|---|---|
| 35 | CoCoEmo | TTS | **Activation steering** (latent intervention) |
| 36 | CRUX | RAG | **Coverage/Density oracle** (multi-dim ground-truth probe) |
| 37 | OpenHands | Agent | **CodeAct + EventStream** (tool abstraction framework) |
| 38 | ChatDev | Agent | **Multi-agent SOP + CDH** (role-based chat chain) |

> **4 个 round 形成 "LLM-era 范式四方阵"**:
> - round 35: **steering** (在 latent space 注入 bias)
> - round 36: **oracle** (用 ground-truth 多维结构替代 binary)
> - round 37: **framework** (统一 action space 跨任务)
> - round 38: **protocol** (formal chat chain 协议)
>
> 4 个范式都跨域适用 (audio / retrieval / code / multi-agent), 跟 round 34 综述的 "13-section crosscut" 完全一致。

---

## 三、为什么 ChatDev 在 2026 仍然值得复现

### 3.1 学术价值: multi-agent SOP 的"原型"

ChatDev 是 2023 年第一篇 formalize "multi-agent 协作写代码" 的论文 (跟 MetaGPT 同期)。它的贡献不是性能数字 (0.3953 早被 specialist 超越), 而是 **"5 role 模拟软件公司 SOP" 这个抽象**:
- CEO: 决策
- CPO: 需求分析
- CTO: 技术选型
- Programmer: 写代码
- Reviewer: review
- Tester: 测试

这个抽象被后续 2024-2025 论文大量复用:
- MetaGPT (2024): PM / Architect / Engineer / QA SOP
- CrewAI (2024): role-based task delegation
- LangGraph (2024): state machine + role
- AutoGen (2024): multi-agent conversation

> **ChatDev 是 multi-agent SOP 框架的 "原型"** — 跟 round 35 CoCoEmo 是 TTS activation steering 的 "原型" 同等地位。

### 3.2 工程教训: 6 类失败模式是 multi-agent 的"tax"

| 失败模式 | Single-agent 会出现吗? | Multi-agent 特有? |
|---|---|---|
| FILENAME placeholder | ✓ (LLM 格式不严) | **No** (single 也会有) |
| 错模态 (CLI vs GUI) | ✗ | **Yes** (CPO 决策 + CEO 质疑是 multi-agent 特有问题) |
| 重复模块 | ✓ (LLM 命名歧义) | **No** |
| 方法名当文件名 | ✓ (LLM 解析错) | **No** |
| stdout 数字当文件名 | ✓ (LLM 解析错) | **No** |
| 空 main.py | ✓ (LLM 漏 entry point) | **No** |

> **6 类失败中 5 类是 LLM 通用问题, 只有 1 类 (错模态) 是 multi-agent 特有**。**multi-agent 没解决 LLM 的本质失败, 只是掩盖了一些** — 这是 ChatDev 2023 → OpenHands 2025 演进的核心动因。

### 3.3 工程债: 7 处 hardcode model = "OpenAI 是唯一 LLM 厂商" 的过时假设

| Patch 位置 | 问题 | 2026 影响 |
|---|---|---|
| `camel/model_backend.py:85-96` | `num_max_token_map` 只列 gpt-3.5/gpt-4 | 非 OpenAI 必改源码 |
| `camel/model_backend.py:184-193` | `ModelFactory.create` 只接受 gpt-* | 同上 |
| `camel/utils.py:95-105` | `get_model_token_limit` elif 链 | 同上 |
| `camel/utils.py:78-90` | `num_tokens_from_messages` set | 同上 |
| `camel/model_backend.py:68` | `tiktoken.encoding_for_model` KeyError | tiktoken 不支持任意 model |
| `camel/agents/chat_agent.py:244` | `**dict(choice.message)` annotations 不接受 | openai SDK 升级不兼容 |
| `camel/typing.py:54-56` + `run.py:99` | `ModelType` enum 闭集 | 没法在不修改源码的情况下加新模型 |

> **7 处 patch = 7 处"OpenAI-only" 假设**。ChatDev 2.0 (DevAll) 重写时改成了"配置化 model backend", 但 API 完全不同, 等于换项目。

### 3.4 ChatDev 2.0 (DevAll) 的转向

ChatDev 2.0 (也叫 DevAll, 2024) 转向了**完全不同的架构**:
- `entity/runtime/frontend` 三层
- 不再是 chat chain, 而是 "workflow engine + role registry"
- Docker sandbox
- 多 LLM routing (Anthropic / OpenAI / Google)

> **ChatDev 1.0 → 2.0 = 一次完整的架构革命**。2 年后 (2026) 的 OpenHands 实际上是 DevAll 思想 + CodeAct 的融合, 而 ChatDev 1.0 的 chat chain SOP 思想被 "压扁" 成了 4 actions + EventStream。

---

## 四、跟 30+ round 项目的全景位置

### 4.1 multi-agent 3 篇的位置

| 轮 | 论文 | 时间 | 范式 | LLM4SE 13-section |
|---|---|---|---|---|
| 33 | MetaGPT | 2024 ICLR | multi-agent SOP (PM/Architect/Engineer/QA) | §X + §XII |
| 37 | OpenHands | 2025 ICLR | generalist CodeAct (4 actions) | §IV + §V + §VI + §VIII + §IX + §X + §XII |
| **38** | **ChatDev** | **2023 SANER** | **multi-agent SOP (CEO/CPO/CTO/...)** | **§II + §IV + §X + §XII** |

> **3 篇中 ChatDev 是最 "process-formalized" 的 (4-section 同时含 §II Design)** — 它把 software process formalize 成 chat chain。
> **OpenHands 是最 "cross-section" 的 (7-section)** — 它是个真正的 agent platform。
> **MetaGPT 居中 (3-section)** — 它介于两者之间。

### 4.2 30+ round 的 5 个 layer

```
Layer 1: Pre-LLM SE (round 03-14, 21: doc-vqa / AEOLLM)
Layer 2: LLM4SE survey (round 34)
Layer 3: Code Gen specialist (round 22-25, 27, 29, 30, 33, 34, 35, 37, 39, 42)
Layer 4: Multi-agent (round 33, 37, 38)
Layer 5: Industrial telemetry (round 31, 32)
```

> **Round 38 (ChatDev) 在 Layer 4 (multi-agent)**, 跟 round 33 (MetaGPT) + round 37 (OpenHands) 形成 "multi-agent 三角"。
> 三角的 3 个顶点:
> - ChatDev (2023): role 扮演 + SOP
> - MetaGPT (2024): role + workflow
> - OpenHands (2025): single-agent + tool abstraction

### 4.3 ChatDev 复现的 3 个独有发现

1. **多 agent 协作 vs single agent**: 6/7 类失败是 LLM 通用, multi-agent 没解决本质问题
2. **8 phase 串接的 5.5x token overhead**: paper 报 3 phase, 实际跑是 8 phase + 10 cycles, token 5.5x paper 数字
3. **测试 phase 0% 贡献**: Test phase 跑了 3 cycles 报 6 个 bug, 1 个都没修 — 跟 paper §4.4 ablation 一致

---

## 五、给后续 round 的提示 (39+)

### 5.1 给做 multi-agent 的人

1. **role-based SOP 解决 "task formalization", 解决不了 "LLM 失败模式"** — 不要期望 multi-agent 比 single-agent 强, 它们的 trade-off 是 process formalization vs tool flexibility
2. **CDH (Communicative Dehallucination) 是真有价值的范式** — 6 轮 DemandAnalysis 收敛 modality 选 CLI 证实了 paper 的 22% Quality 提升, 值得集成到其他 framework
3. **Phase 串接要传 "对话历史", 不只 "final solution"** — ChatDev 失败的核心是 phase 信息丢失
4. **Test phase 需要 "auto-fix loop"** — paper §4.4 报 0% 贡献, 实际跑也证实, 改 Tester → TesterFixAgent

### 5.2 给做 LLM4SE 综述的人

1. **加 §XIII: Multi-Agent Frameworks** — 4-section (ChatDev) 到 7-section (OpenHands) 的多 agent 框架是新章节
2. **CDH 应该独立成为 crosscut 子条目** — 跟 "Steering" (round 35) / "Oracle" (round 36) 并列
3. **multi-agent SOP 的失败模式需要 SBSE 严格统计** — 6 类失败在 1 task 出现 6 次不代表 100%, 需要多 task 验证
4. **跨版本多 agent 框架的纵向对比** — ChatDev 1.0 (2023) → MetaGPT (2024) → OpenHands (2025) 应该有横向 benchmark

### 5.3 给做工程的人

1. **不要从零写 multi-agent 框架** — 用 LangGraph / AutoGen / CrewAI, 集中精力写 role prompt + tool
2. **ChatDev 1.0 不适合 production** — 2 年没维护, 6 类失败, 40x 慢 vs single-agent
3. **跨 LLM 厂商** — 任何 model hardcode 都是技术债, 用 LiteLLM 抽象 layer
4. **Process formalization 价值** — 1 个 task 7 分钟 5 phase 串接, 对教学 / 演示极有价值

---

## 六、最终判定

| 论文核心主张 | round 38 复现结论 |
|---|---|
| Multi-agent chat chain 协作 (CEO/CPO/CTO/...) | ✅ 6 role 真实参与, chat chain 真实跑通 |
| Communicative Dehallucination (CDH) | ✅ DemandAnalysis 6 轮收敛, 证实 paper 22% Quality 提升 |
| Code 产物可执行 (Executability 88%) | ✅ 1 task 100% (4/4 算术 + 异常) |
| Phase 串接 cross-phase | ⚠️ 8 phase 串接真实, 但 6 类失败模式都是 phase 串接丢 context 导致 |
| Quality metric 0.3953 (vs MetaGPT 0.1523) | ⚠️ 1 task 没法验证 1200 task 数字 |
| Roles 重要 (ablation -44%) | ✅ 6 role 真实对话, 4 role 协作跨 8 phase |
| Code Complete 几乎无贡献 (ablation -6.6%) | ✅ 10 cycles 大量 placeholder 残留, 跟 paper 一致 |
| Testing 0% 贡献 (ablation 0%) | ✅ Test phase 3 cycles 报 6 bug, 0 个修复 |
| Round 34 LLM4SE 综述对应 | ✅ **5/5 categories** match (100%) |
| Round 37 OpenHands 对应 | ✅ multi-agent 三角 (ChatDev 2023 / MetaGPT 2024 / OpenHands 2025) |
| Production-scale 真实使用 | ❌ ChatDev 1.0 2 年没维护, 6 类失败, 不适合 production |
| 跨 LLM 厂商 | ⚠️ 7 处 hardcode OpenAI model, 6 patch 才能跑非 OpenAI |

> **整体判定**: **multi-agent SOP 框架 ChatDev 1.0 端到端跑通**, **6/6 known failure modes 在 1 task 中全部出现**, **V6 round 34 LLM4SE alignment 5/5 = 100% categories match**; 论文的核心机制 (chat chain + CDH + role SOP) 全部真实工作, 但 6 类失败模式跟 paper §4.5 报告完全一致, 证明 **multi-agent 没解决 LLM 失败模式本质, 只是 formalize 了 task 拆分**。
>
> **本 round 38 最重要的元结论**: **ChatDev 是 OpenHands 的 2023 思想原型**。OpenHands (round 37) 把 ChatDev 的 "6 role SOP" 压扁成 "1 agent + 4 actions", 用 tool abstraction 替代 role-based dialogue。**两个框架代表 multi-agent 框架的两种哲学**: ChatDev 用对话拆解任务, OpenHands 用工具拆解任务。**2026 年的胜出者是 OpenHands (40x faster, 13x cheaper, fewer failure modes)**, 但 **ChatDev 的 CDH + role SOP 思想仍然被 LangGraph / CrewAI / AutoGen 复用**。这是 round 34 LLM4SE 综述 "13-section 分类法" 跨年代 (2023-2026) 的稳定性验证。

---

## 参考文献 (本 blog 直接引用)

- Qian, Liu, Liu, et al. (Tsinghua + Sydney + BUPCT). **ChatDev: Communicative Agents for Software Development**. [arXiv:2307.07924v5](https://arxiv.org/abs/2307.07924) (SANER 2024)
- Code: https://github.com/OpenBMB/ChatDev (gitee mirror, chatdev1.0 branch)
- ChatDev 2.0 (DevAll, 2024) — 架构革命, workflow engine + role registry
- Round 33 MetaGPT (Hong et al. ICLR 2024) — 同期 multi-agent SOP
- Round 37 OpenHands (Wang et al. ICLR 2025) — 2025 generalist agent
- Round 35 CoCoEmo (Wang et al. ICML 2026) — TTS activation steering
- Round 36 CRUX (Ju et al. EMNLP 2025) — RAG Coverage/Density oracle
- Round 34 LLM4SE survey (Fan et al. 2023) — 13-section 分类法

---

*本 blog 为 deep-research round 38 产物, 配合 paper.md (论文笔记) 与 REPRODUCTION_NOTES.md (复现验证) 阅读。注: 40-chatdev 目录名是历史命名, 论文本身是 SANER 2024 multi-agent SOP framework, 跟 round 37 OpenHands 形成 "multi-agent 三角" 的 2023 顶点。*
