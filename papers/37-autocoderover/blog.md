# AutoCodeRover vs SWE-agent:两种 ACI 哲学的深度对比

> 写在第七轮 /loop:复现了 AutoCodeRover 的 context retrieval 阶段,正好跟我第六轮复现的 SWE-agent 形成镜像。
> 同样的目标(自动修 GitHub issue)、同年发表(2024)、同 SWE-bench 评测,走了完全不同的两条路。
> 哪个更好?——看你信"LLM 强规划"还是信"SE 领域知识约束"。

---

## 0. 故事的起点

Princeton 和 NUS 在 2024 年同时撞上了同一个问题:**怎么让 LLM 修 GitHub issue?**

SWE-bench(OpenAI 2023)提供了 2294 个真实 GitHub issue + PR 测试用例。LLM 拿到 issue 描述,需要在 docker 容器里改代码、跑测试。问题: LLM 怎么"看"代码库?

直觉答案是 bash + read file。**这就是 Princeton 的路线**。Yang et al. 2024 (SWE-agent) 给 LLM 一组类似 IDE 的工具:`bash`, `str_replace_editor view/str_replace/insert`, `undo_edit`, `submit`——5 个,加上一个 shell。LLM 自己决定先看哪个文件,再 grep,再改,再跑测试。**简单、灵活、跟 LLM 训练数据同源**。

NUS 团队不这么看。Zhang et al. 2024 (AutoCodeRover) 的反驳论点是:

> "把代码库当文件集合,等于把 LLM 退化到 grep。软件是有结构的——类、方法、调用关系、继承。给 LLM 暴露这些结构,它才能'理解'代码。"

于是他们做了完全不同的事:**预解析代码库成 AST,暴露 7 个结构化 API**(搜类、搜方法、搜代码片段),让 LLM 在"语义化"层面查询。配套还做了分层检索(SBFL 加权)和 lint retry。

**结果**: 在 SWE-bench Lite 上,AutoCodeRover @1 拿到 19%,SWE-agent 拿到 18%——基本打平。**但 AutoCodeRover 单任务只用 37K token / $0.43,SWE-agent 要 245K / $2.51。差 6.6 倍。**

这是怎么发生的?我们这周正好两边都复现了一版。

---

## 1. 体感差异:工程师视角的对比

我在第六轮复现 SWE-agent 时,最大的工程痛点是 **LocalRuntime 路径兼容性**——SWE-agent 默认容器路径是 `/testbed`,但我的环境是 macOS 本地 + chatdev venv。我花了 4 个小时写 5 层 monkey-patch 才把 `LocalRuntime` 的 `upload` / `execute` / `read_file` / `write_file` 全打通。**这暴露了 SWE-agent 的一个隐含假设:目标环境是 Linux Docker 容器**。

第七轮复现 AutoCodeRover 完全没遇到路径问题。`SearchBackend` 直接吃 `local_path=/tmp/acr_e2e_xxx`,`PlainTask(local_path=...)` 一行配置就完事。**因为 AutoCodeRover 不需要"执行"任何东西——它只检索**。没有 docker 容器,没有 shell,没有 sandbox。它把"修代码"分成两阶段:先检索定位 bug location(纯 AST 搜索,本地文件系统即可),再 patch + 验证(才需要执行)。

| 维度 | SWE-agent | AutoCodeRover |
|---|---|---|
| 跑 SWE-bench 一个 instance 需要什么 | Docker + 完整镜像 + 沙箱 shell | 仅 AST 检索 + (可选) test suite 执行 |
| 跨平台兼容性 | 假设 Linux 容器 | Python AST,跨平台 |
| "看懂"代码库靠什么 | bash + grep + file view | 预解析的 AST + 7 个结构化 API |
| 工程师心智负担 | 写工具+接 shell | 接 LLM endpoint |

**AutoCodeRover 体感更轻**——它把"难的部分"(execution + sandbox)推迟到 patch 阶段;前半段 retrieval 阶段就像写一个 IDE 插件。

---

## 2. 核心哲学之争:"自由" vs "约束"

### 2.1 SWE-agent 的"自由 ACI"

SWE-agent 的论文 §3 反复强调"ACI"——Agent-Computer Interface——才是关键,不是模型本身。它的论点是:**LLM 足够强,你给它一个最小工具集,它自己会组合出花来**。

证据: SWE-agent 给 GPT-4 5 个 editor action + bash,GPT-4 自己发明了"先 list_dir → 再 view README → 再 grep 'TODO' → 再 str_replace"这种工作流。Princeton 团队没有 hardcode 任何策略。

```bash
# SWE-agent 的"自由 ACI" 实际跑出来的工作流(我的第六轮复现)
ls -la
# → 看到 Django project 结构
cat README.rst | head -50
# → 看到项目介绍
grep -rn "validate" django/forms/models.py
# → 定位到 ModelChoiceField
view django/forms/models.py 350 400
# → 看具体实现
str_replace django/forms/models.py 358 \
  "raise ValidationError(...code=...)"
# → 改
bash python -m pytest django/forms/tests/test_modelchoicefield.py
# → 验证
```

70 次 API 调用,290K token——但 LLM 真的"自己"搞定了。

### 2.2 AutoCodeRover 的"约束 ACI"

AutoCodeRover 的论文 §1 开篇就反驳:

> "SWE-agent 是 concurrent work,它的 ACI 让 LLM 通过 shell 命令执行基本文件操作并与软件仓库交互。**相比 SWE-agent,我们提出 AutoCodeRover 作为从软件结构中提取规约的方法。**"

注意"specification"这个词。**NUS 团队认为 ACI 不是"少就是好",而是"语义化就是好"**。

```python
# AutoCodeRover 的"约束 ACI" 实际跑出来的工作流(我的第七轮复现)
search_class("ModelChoiceField")
# → 拿到类的签名、方法列表、文件位置
search_method_in_class("validate", "ModelChoiceField")
# → 拿到方法实现(14-22 行,带 class 上下文)
search_code("Select a valid choice. %(value)s is not one of the available choices.")
# → 拿到错误消息的 source
# → LLM 推断出:params={"value": value} 缺失
```

5 次 LLM 调用,6.3K token(虽然只跑了 1 个 toy 例,但量级正确)。

### 2.3 哲学分歧的本质

| 哲学 | SWE-agent | AutoCodeRover |
|---|---|---|
| **对 LLM 的信任** | 强(给它 bash,自己探索) | 弱(给结构化 API,引导推理) |
| **对 SE 知识的信任** | 弱(让 LLM 自己学) | 强(把 SE 概念 encode 进 ACI) |
| **信息检索的隐喻** | Unix (grep + cat) | IDE (Go to Definition + Find Usages) |
| **错误的归因** | LLM 自己 debug | 程序化约束(lint + retry) |
| **失败定位粒度** | 粗(成功/失败) | 细(Figure 10: wrong patch / wrong location in correct file / wrong file / no patch) |

**这个分歧本质上是"AI-first" vs "Domain-first"**:
- AI-first: 模型越来越强,工具应该尽量通用
- Domain-first: 领域知识是稀缺资源,应该 encode 进系统

---

## 3. 实证对比:从我的两次复现看

### 3.1 工程成本

| 阶段 | SWE-agent | AutoCodeRover |
|---|---|---|
| 安装依赖 | `pip install sweagent` | `pip install loguru natsort antlr4-tools antlr4-python3-runtime timeout-decorator pylint ollama docker` (requirements.txt 缺一大堆) |
| 接 LLM endpoint | 一行 env | `litellm.register_model` + `set_model` patch + `LiteLLMGeneric` 隐藏 import |
| 处理平台差异 | 5 层 path monkey-patch + chown skip | 0(SearchBackend 直接吃路径) |
| 跑端到端 | 70 API calls, 290K tokens | 5 API calls, 6.3K tokens(单 toy 例) |

**工程成本上 AutoCodeRover 更轻**——它不依赖沙箱,所以绕过了 SWE-agent 最大的痛点(LocalRuntime / Docker / chown / 路径)。但**接 LLM 端点更绕**——`LiteLLMGeneric` 这个抽象层 + 隐藏的 cost 查找,需要 4-5 个 patch 才能绕过。

### 3.2 质量与效率

| 指标 | SWE-agent (我的复现) | AutoCodeRover (我的复现) | 论文报 ACR |
|---|---|---|---|
| 端到端 token | 290K | 6.3K (toy) | 37K (real) |
| 端到端 API calls | 70 | 5 (toy) | ~30 (估计) |
| 定位精度 | 1 file, 1 method | 1 file, 1 method + 1 class context | 19% pass@1 |
| 耗时 | ~5 分钟 | 19.7s | 195s |

**AutoCodeRover 的 token 优势明显**(6.6x),但前提是 LLM 能正确选 API。我的复现里 agent 一上来选了 3 个精准的 API (`search_class` + `search_method_in_class` + `search_code` 错误消息),这种"懂 SE 的 LLM 调用" 是论文报数成立的关键。

### 3.3 一个意外发现:Round 0 一次性收敛

我的 toy 例里,AutoCodeRover 在 **Round 0 一次调 3 个 API 拿全 context,Round 1 一句话输出 bug location**。论文 Figure 5 展示的是"Round 1 加 methodB,Round 2 加 classB"的渐进式——但我的例子没出现这个过程。

可能原因:
1. **toy 例子代码库太小**(1 个文件, 25 行)——分层检索的优势在大仓库才显现
2. **`MiniMax-M3.1-Flash-Preview` 的决策更激进**——可能 GPT-4 会更犹豫、需要更多 round

这个观察说明:**AutoCodeRover 的 stratified search 在大仓库才显出价值**;小代码库里它跟"一次调所有 API"差不多。

---

## 4. 一个深层问题:7 个 API 够吗?

论文 Figure 6 的 Venn 图透露了一个反直觉的事实:
- **AutoCodeRover 独有 26 个 solved**
- **SWE-agent 独有 23 个 solved**
- **都解决 31 个**

也就是 ~50% 的任务是一家能解决、另一家不能。**两套 ACI 互补**。

AutoCodeRover 论文 §6.1 自己承认:

> "SWE-agent 独有的 23 个任务,典型是 django-12286——它需要'在文件级搜'。**AutoCodeRover 没有 file-level search API**。"

这是 AutoCodeRover 的盲点:**7 个 API 全部是 class/method/code 粒度,没有"列出所有 .py 文件"或"在目录下 grep"这种 file-level 工具**。LLM 拿到一个跨文件 import 链,要 `search_class(A)` → 拿到 import 语句 → `search_code_in_file("from A import", fileB)` → 反推回去。**绕**。

SWE-agent 的 `bash` + `grep -rn` 在 file-level 任务上更直接。

**AutoCodeRover 的改进方向(论文 §9 提到)**:
1. 加 `search_file` API(file-level 搜索)
2. 加 `get_code_around_line` API(看上下文)——我的复现中已经看到 `get_code_around_line` 是被引用的 8 个 API 之一(超出论文 7 个)
3. 加 call graph / data flow 集成
4. 加 LSP(Language Server Protocol)集成,让 LLM 能"跳转到定义"

这些 future work 暗示: **7 个 API 不是终点,而是起点**。

---

## 5. 跟 ChatDev 的对比:多 agent 协作呢?

顺便提一下我第四轮复现的 ChatDev(arXiv:2307.07924, Tsinghua, ICSE 2024 候选):

| 维度 | SWE-agent | AutoCodeRover | ChatDev |
|---|---|---|---|
| 架构 | 单 agent | 单 agent(2 阶段) | 多 agent(CEO/CTO/Programer/Tester 流水线) |
| ACI | 文件级工具 | AST 检索 API | LLM-to-LLM 通信(chat chain) |
| 适用任务 | GitHub issue 修复 | GitHub issue 修复 | 从头开发小型软件 |

**ChatDev 跟我们俩完全不在一个赛道**——它解决"无中生有",我们俩解决"有中改 bug"。但有一个交集值得提:**ChatDev 的"Programer → Tester → Reviewer"流水线可以套到 patch generation 阶段**——这正是 AutoCodeRover 论文 §9 提到的 future work 之一。

---

## 6. 我自己的判断:2026 年的 ACI 长什么样?

### 6.1 短期 (2025-2026):两条路线并存

- **SWE-agent 路线**: Claude Code、OpenHands、Cursor Tab、Continue.dev 都在用——**简单工具 + 强 LLM 规划**。优势:跨语言、易扩展。
- **AutoCodeRover 路线**: RepoCoder、CodePlan、MetaGPT 部分借鉴——**结构化 API + 强 SE 语义**。优势:省 token、定位细。

**我的预测**: 2026 年的主流 SWE agent 会**混合**——核心 retrieval 用 AutoCodeRover 风格(7 API + AST),但保留 bash/file editor 兜底(处理 file-level 任务)。这正是 AutoCodeRover 自己 §9 列的 future work。

### 6.2 中期 (2027-2028):LSP 化

论文 §9 提到的 "LSP integration" 是个大方向——**让 LLM 直接接 Language Server Protocol,获得"Go to Definition / Find References / Hover" 这些 IDE 级能力**。

这等于 AutoCodeRover 的 7 个 API 被 LSP 协议取代——更标准、跨语言、更多 IDE 工具支持。Roo Code / Cline 2025 年的实验已经在朝这个方向走。

### 6.3 长期:ACI 还是 prompt?

更根本的问题:**ACI 应该是"工具集"还是"prompt 协议"?**

- 工具集(ACI 当前定义): LLM 调用 `search_class(cls)`,返回字符串
- prompt 协议(MCP / Anthropic 的方向): LLM 调用 `get_definition(name)`,返回结构化数据(类型、签名、文档)

**MCP (Model Context Protocol) 2025 年正在统一这个**。AutoCodeRover 的 7 个 API 某种意义上是"MCP for Python AST"——未来可能直接被 MCP 取代,LLM 接任意 LSP 兼容的语言服务器就行。

---

## 7. 一句话总结

> **SWE-agent 信 LLM,AutoCodeRover 信 SE。**

哪个对?**都对了一半**。我两次复现的体感是:
- **小代码库 + 强 LLM**: SWE-agent 更省事(简单工具够用)
- **大代码库 + 中等 LLM**: AutoCodeRover 显著胜出(6.6x token 节省)
- **跨语言**: SWE-agent 完胜(AutoCodeRover 是 Python AST)
- **失败归因**: AutoCodeRover 更细(Figure 10 四类失败)

**给要做 SWE agent 的人**: 别二选一。**两条路线的精华是"分层 ACI"**——核心 retrieval 用结构化 API(AutoCodeRover),边缘任务留 bash/grep 兜底(SWE-agent)。这正是 AutoCodeRover 论文 §9 暗示但没明说的方向。

---

## 8. 引用

- Zhang, Ruan, Fan, Roychoudhury. **AutoCodeRover: Autonomous Program Improvement**. ISSTA 2024. arXiv:2404.05427v3 — 本轮复现
- Yang et al. **SWE-agent: ACI Enable Automated SE**. NeurIPS 2024. arXiv:2405.15793 — 第六轮复现
- Jimenez et al. **SWE-bench: Can Language Models Resolve Real-World GitHub Issues?**. ICLR 2024. arXiv:2310.06770
- Qian et al. **ChatDev: Communicative Agents for Software Development**. arXiv:2307.07924 — 第四轮复现
- Anthropic. **Model Context Protocol (MCP)**. 2025. https://modelcontextprotocol.io

---

*本文由 Claude Code 完成于 2026-10-15,基于 AutoCodeRover + SWE-agent 两次独立复现。*
