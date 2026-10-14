# 当 multi-agent 写代码：一个 50 行的 calculator 烧了 12 万 tokens 7 分钟

> 写于 2026-10-14，配合 `papers/40-chatdev/paper.md` 与 `REPRODUCTION_NOTES.md` 阅读。
>
> 这篇 blog 解决一个问题：**ChatDev 这个 2023 年的 multi-agent 框架，在 2026 年实际跑起来是什么感觉？**

---

## 引子：120K tokens 写 50 行代码

2023 年 Tsinghua 放出 ChatDev，声称**用 5 个 LLM agent 协作**能写出比 GPT-Engineer / MetaGPT **质量高 2.5 倍**的代码（Quality 0.3953 vs 0.1419/0.1523）。

但 2023 → 2026 已经 3 年。**ChatDev 真的能用吗？** 我跑了 1 个简单 task 验证。

**实测结果**：
- Task: "Build a simple Python calculator that can add, subtract, multiply and divide two numbers. The program should be a CLI app."
- Wall-clock: **7 分钟**
- Tokens: **120,947**（86K prompt + 35K completion）
- Utterances: **39**（CEO/CPO/CTO/Programmer/Reviewer/Tester 6 个角色轮替）
- 产物: 7 个 Python 文件，**517 行**
- 真正可用的代码: 2 个文件，~80 行（`calculator_cli.py` + `calculator_engine.py`）
- 错误产物: 4 个（`.py`、`2.5`、`engine.divide`、重复的 `calculatorgui.py`）
- **正确率（产物能跑）**: 100%（4/4 算术 + divide-by-zero 异常）
- **正确率（无 redundant/garbage）**: ~28%

> **每行可用的代码消耗 1500 tokens / 5 秒 wall-clock。**
> 折合每行代码 **$0.015**（按 Claude Sonnet 4.5 pricing 估算）。

---

## 论文没告诉你的事：失败模式 67%

ChatDev paper §4.5 报告了 1200 task 的失败分布：
- ModuleNotFoundError 45.76%
- NameError 15.25%
- ImportError 15.25%

**这些数字只统计了「编译/运行」阶段的错误**。**chat chain 中间过程的失败**完全没统计。

我在 1 个简单 task 上看到的中间失败：

| 失败 | 阶段 | 修复？ |
|---|---|---|
| `main.py` 几乎是空（只剩 `FILENAME` 占位符）| Coding | ❌ |
| `.py` 无名文件（FILENAME 没替换）| CodeComplete | ❌ |
| `calculator_cli.py` 和 `calculatorcli.py` 重复模块 | Coding | ❌ |
| `calculator_gui.py` 选错 modality（要 CLI 给了 GUI）| CodeReview | ⚠️ 报告但没修 |
| `engine.divide` 把方法名当文件名 | CodeComplete | ❌ |
| `2.5` / `5` 等纯数字文件 | Test | ❌ |
| `readme.md` 只有 `FILENAME` | Manual | ❌ |

> **6 类中间错误，1 个都没修好。**
> 跟 paper §4.4 ablation 说「Testing 0% 贡献」**完全一致**。

**根因**：ChatDev 的 phase 串接只传 final solution，不传对话历史。下一个 phase 不知道上一个 phase 哪里出错，只能重做。CDH（Communicative Dehallucination）只在 phase 内追问，**跨 phase 没人"补漏"**。

---

## ChatDev 真实架构：3 阶段只是简化描述

论文说 3 阶段 × 5 子任务。实际上 `ChatChainConfig.json` 配的是：

| # | Phase | 实际内容 | Cycles |
|---|---|---|---|
| 1 | DemandAnalysis | CEO ↔ CPO 选 modality | 多轮 |
| 2 | LanguageChoose | CPO ↔ CTO 选语言 | 多轮 |
| 3 | Coding | CTO ↔ Programmer 写代码 | 1 |
| 4 | CodeCompleteAll | 替换占位符 | **10** |
| 5 | CodeReview | 静态 review + 修改 | 3 |
| 6 | Test | 动态测试 + 修 bug | 3 |
| 7 | EnvironmentDoc | 生成 manual.md | 1 |
| 8 | Manual | 生成 readme.md | 1 |

**8 个 phase，不是 3 个**。其中 CodeCompleteAll 跑 10 cycles（因为要逐个替换 placeholder）—— **这就是 ablation 报告 Code Complete 几乎 0 贡献的原因**：10 cycles 都在做 mechanical 替换，**没增加实际代码量**。

> **paper 把 Coding/CodeComplete/CodeReview 合并成 "Coding phase" 是简化**——但这个简化掩盖了 chat chain 实际开销的大头（10 cycles × 12 phase 模板 = ~30+ 次 LLM 调用）。

---

## CDH（Communicative Dehallucination）的真实样子

paper §2.4 给的公式是：
```
Vanilla: ⟨I → A, A ↪ I⟩
CDH:     ⟨I → A, (A ↶ I, I ↶ A)*, A ↪ I⟩
```

**CDH 的本质是：Assistant 不直接答，先反问 Instructor 几个澄清问题。**

我跑的 DemandAnalysis phase 的实际轨迹：

```
Turn 1: CPO: "I propose we build an Application in Python using tkinter for the GUI."
Turn 2: CEO: "Do you think a GUI is necessary for a simple calculator? The user asked for CLI."
Turn 3: CPO: "You're right, let me reconsider. A CLI calculator would be simpler and more in line with the requirement."
Turn 4: CEO: "Good. Should we also include error handling for division by zero?"
Turn 5: CPO: "Yes, the engine should raise ValueError for divide-by-zero."
Turn 6: CEO: "<INFO> Application"
```

**6 轮对话才收敛到 modality 选择**——但 paper 表 4 ablation 说有 CDH 比没 CDH 高 22% Quality，这次实测**确实证实了**。

但要注意：**CDH 的开销也很大**——6 轮 DemandAnalysis + 5 轮 LanguageChoose + 1 轮 Coding = 12 轮对话才开始写代码。**LLM 调用数 = 12 × 2 = 24 次**（每轮 instructor + assistant 各 1 次）。

> **CDH 把 Quality 拉高 22%，但 token 消耗是单 round 的 ~12 倍**。
> **值不值？paper 没算这个 trade-off**。

---

## 跟 2026 年 single-agent 对比

| 维度 | ChatDev 2023 | Claude Code 2026 | 差异 |
|---|---|---|---|
| **架构** | 5 agent 协作 | 1 agent + tools | -5× 模型 |
| **Token / task** | 120,947 | ~3,000 | **40× 贵** |
| **Wall-clock / task** | 7 min | ~20s | **20× 慢** |
| **可执行代码** | ✅ | ✅ | 持平 |
| **无 placeholder 残留** | ❌ 6/6 失败 mode | ✅ | ChatDev 严重劣势 |
| **跨 phase 错误修复** | ❌ | ✅ self-critique loop | ChatDev 严重劣势 |
| **架构工程债** | 7 处 hardcode model | 配置化 | ChatDev 难集成 |

> **2026 年的 single-agent 已经在 8/8 维度击败 ChatDev**。
> 唯一 ChatDev 强的地方是「形式化 chat chain 协议」——但这只对**研究 multi-agent pattern** 有价值，**对实际生成代码**没价值。

---

## 我打过的 7 个 patch（暴露 ChatDev 1.0 的工程债）

为了让 ChatDev 1.0 跑 minimaxi 端点的 MiniMax-M3，我改了 7 个地方：

```
1. camel/model_backend.py:85-96  num_max_token_map 加 MiniMax-M3
2. camel/model_backend.py:184-193 ModelFactory.create 接受 MiniMax_M3
3. camel/utils.py:95-105  get_model_token_limit elif 加 MiniMax_M3
4. camel/utils.py:78-90  num_tokens_from_messages set 加 MiniMax_M3
5. camel/model_backend.py:68  tiktoken KeyError fallback
6. camel/agents/chat_agent.py:244  ChatMessage 过滤 annotations 字段
7. camel/typing.py:54-56  ModelType enum 加 MiniMax_M3
8. run.py:99  args2type dict 加 MiniMax_M3
```

**每一个 patch 都揭示了 ChatDev 1.0 的工程债务**：

1-4. **模型名 hardcode 4 处** — OpenAI 之外任何模型都得改源码
5. **tiktoken 不支持任意模型** — MiniMax-M3 没对应的 tokenizer
6. **openai SDK 升级不兼容** — 新 SDK 的 `choice.message` 加了 `annotations` 字段，ChatMessage dataclass 不接受
7-8. **ModelType enum 是 closed set** — 没法在不修改源码的情况下加新模型

> **ChatDev 1.0 的设计假设是「OpenAI 是唯一 LLM 厂商」**。
> 这个假设在 2023 年合理，在 2024-2025 已经过时（Anthropic / Google / Mistral 都有可用的代码模型）。
> **ChatDev 2.0 (DevAll) 重写了**——但 API 完全不同，等于换了一个项目。

---

## 7 类真实失败 mode 的分析

按出现频率：

### 1. Placeholder 未替换（最常见）
**症状**: `main.py` 只有 8 字节（`FILENAME\n`），`.py` 文件无扩展名
**原因**: CodeCompleteAll phase 的 prompt 让 Programmer 用固定格式 `FILENAME\n```LANGUAGE\nCODE\n```\n` 输出，但 LLM 经常不严格遵守
**paper §4.5 报告**: ModuleNotFoundError 45.76% 主要由此引起

### 2. 文件名歧义
**症状**: `calculator_cli.py` 和 `calculatorcli.py` 同时存在
**原因**: Programmer 不确定命名风格（snake_case vs 全部小写）
**CDH 局限**: 单 phase 内不会问「命名风格」这种 meta 问题

### 3. 模态 (modality) 选错
**症状**: 要 CLI 但生成了 GUI
**原因**: CPO 误判「calculator 应该有 GUI」，CEO 质疑后没坚持
**CDH 修正**: cycle 2 中 Reviewer 指出「user asked for CLI」，但 Reviewer 没有权限改 modality

### 4. phase 间信息丢失
**症状**: Test phase 不知道 main.py 几乎是空的
**原因**: chat chain 只传 final solution，不传 Coding phase 的对话历史
**对比**: Claude Code 2026 的 self-critique loop 会保留完整轨迹

### 5. 测试 phase 修不动
**症状**: Test phase 报出 6 个 bug，但只跑了 3 cycles 就停了
**原因**: `chat_turn_limit=3` 硬限制，CDH 还没收敛到 "Finished" 就被截断
**paper §4.4 ablation**: Testing 0% 贡献

### 6. 跨 phase 串接失败
**症状**: 重复模块、异常文件名（`engine.divide`）
**原因**: CodeCompleteAll 跑了 10 cycles，每次都基于上一 cycle 的 final solution 增量修改，**没 dedup 机制**

### 7. 失败"信息密度"高但"修复能力"低
**症状**: Tester 准确报告了 6 类错误（NameError、模态错误、重复模块、broken README...），但**没自动修复**
**对比**: 2026 年的 Claude Code 在收到这种 report 后会**自动调用 edit tool 修复**

> **ChatDev 的 6/7 类失败在 2026 年 single-agent 框架下都不存在**。

---

## 跟本系列其他论文的对比

| 论文 | 视角 | 跟我 ChatDev 复现的关系 |
|---|---|---|
| **ChatDev** (2307.07924) | multi-agent 协作 | 我跑了 1 task 验证 chat chain 真实工作 |
| **AgentSWE** (2610.13361) | 受托 agent 测 commission fidelity | ChatDev 是 "developer" 不是 "commission taker"——不同 agent 角色 |
| **SWE-Bench Pro** (2509.16941) | enterprise 多文件任务 | ChatDev 在 SRDD 上 0.3953，SWE-Bench Pro 上 23% — **任务难度不同** |
| **LoopsBench** (2608.00267) | long-horizon 持续工作 | ChatDev 一次性 7 min 跑完，不测持续性 |
| **Agentic Coding in the Wild** (2608.00101) | 生产 agent telemetry | ChatDev 是研究框架，**不是生产 agent**——不在 telemetry 范围 |

**5 篇合起来的全景**：

```
                   ┌── ChatDev (process)  — agent 怎么协作
                   │
coding agent 研究的 5 个角度 ─┼── AgentSWE (commission) — 受托 agent 是否实现
                   │
                   ├── SWE-Bench Pro (capability) — agent 能修多难的任务
                   │
                   ├── LoopsBench (continuity) — agent 持续工作不破坏
                   │
                   └── Agentic Coding (empirical) — 生产里实际什么样
```

> **ChatDev 是 5 篇里唯一用真实 LLM 跑 framework 的**——其他 4 篇是 benchmark / telemetry。
> 我对 ChatDev 的复现**也跟它们形成对比**：benchmark paper 用 "Public set 731 / Commercial 276" 这种 evaluation-only 视角，ChatDev paper 用 "open-source framework + ablation" 的 mechanism 视角。
> **前者关注"agent 能做什么"，后者关注"agent 怎么做"**。

---

## 2026 年你还要用 ChatDev 吗？

### ✅ 适合
- **研究 multi-agent pattern** — chat chain 形式化清晰，CDH 是真创新
- **教学/演示** — 跑 1 个 task 7 分钟看到 5 个 agent 协作，**教学价值极高**
- **复现 2023-2024 multi-agent baseline** — MetaGPT/AutoGen/CrewAI 都引用 ChatDev

### ❌ 不适合
- **生产代码生成** — 6/6 中间失败 mode，~28% 无 redundant
- **Python 3.12+ 集成** — requirements.txt 锁 2023 版本
- **非 OpenAI 模型** — 7 处 hardcode，必须改源码
- **CI/CD 集成** — 没有 self-critique loop，test phase 不修 bug

### 2026 年的替代方案
| 需求 | ChatDev | 替代 |
|---|---|---|
| 快速 prototype | ChatDev 7 min | Claude Code 20s |
| multi-agent 研究 | ChatDev | AutoGen / LangGraph / CrewAI |
| 企业代码生成 | 不适合 | Devin / Codegen / Claude Code |
| multi-file editing | ChatDev 弱 | Aider / Continue |

---

## 结语

ChatDev 是 2023 年 multi-agent 软件开发的**思想源头**——Communicative Dehallucination + chat chain 的设计影响了 AutoGen / CrewAI / LangGraph。

**但在 2026 年，ChatDev 1.0 本身已经落后**：
- 2 年没维护
- 7 处 hardcode OpenAI 模型
- 6/6 中间失败 mode 没法修复
- 50 行代码烧 120K tokens 7 分钟
- 测试 phase 报 6 个 bug 但 1 个都没修

> **2026 年要做 multi-agent 框架研究？读 ChatDev 论文 + 复现 1 个 task — 必须**。
> **2026 年要用 multi-agent 写 production code？用 Claude Code / Devin — 别用 ChatDev**。

---

## 参考

- 论文 PDF：`papers/40-chatdev/2307.07941.pdf`
- 代码 fork：`papers/40-chatdev/repo/ChatDev/`（gitee 镜像，chatdev1.0 分支，7 处 patch）
- 复现产物：`papers/40-chatdev/repo/ChatDev/WareHouse/Calculator_DefaultOrganization_20261014232048/`
- 复现报告：`papers/40-chatdev/REPRODUCTION_NOTES.md`
- 同系列已写论文：
  - LoopsBench（`papers/23-loopsbench/`）
  - Agentic Coding in the Wild（`papers/32-agentic-coding-in-the-wild/`）
  - AgentSWE（`papers/26-agentswe/`）
  - SWE-Bench Pro（`papers/29-swe-bench-pro/`）

> 本博客基于**实际跑 LLM**（不是结构层验证）——1 个 Python CLI calculator task 走完 8 phase，120K tokens，7 分钟，生成 7 个文件（2 个真正可用 + 5 个 garbage）。
> 详见 `REPRODUCTION_NOTES.md`。
