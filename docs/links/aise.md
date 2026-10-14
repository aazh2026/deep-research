AISE（AI Software Engineering）2026 年热门论文 Top 20
如果从你关注的 AISE、Loop Engineering、Coding Agent、Agent 设计模式、Agent Memory 和工程化评测 出发，我建议不要单纯按照论文引用量排名，而是按照对 AI 软件工程实践的影响力、技术创新程度、工程可复现性和未来研究价值综合筛选。
需要先明确一个时间边界：现在是 2026 年 10 月 14 日，2026 年尚未结束。AISE 也不是一个边界完全统一的论文分类，因此下面会兼顾 AI 驱动的软件工程（AI for Software Engineering）、AI 原生研发流程、Coding Agent、自动化软件工程与持续反馈闭环等相关方向。
这里的“Top 20”应理解为研究优先级与代表性候选清单，而不是未经核实的实时引用量排行榜。2026 年新论文还需要结合最新预印本、顶会录用情况和开源实现进一步核验。
一、2026 年最值得优先阅读的 20 篇论文
下面按研究价值分为四组。优先级是针对 AISE 研究和工程落地的主观综合排序，不代表引用量或全网热度排名。
A. Loop Engineering 与长程自主研发
这组最值得关注：研究对象从“单次生成代码”转向“持续完成软件工程任务”。









1. LoopsBench: From Harness Engineering to Loop Engineering in Coding Agent Evaluation

最高优先级
 2026 · arXiv
研究 Loop Engineering 的评测问题，采用依赖 DAG、分阶段测试与回归约束评估长程任务。112 个任务覆盖 8 种语言和 9 个领域。对设计可持续运行的 Coding Agent Loop 尤其有价值。


arXiv Science



论文原文












2. Loop Engineering: Building Blocks, Adoption, and Impact
2026 · arXiv · 工程实践研究
研究 Loop Engineering 的组成要素、开源项目采用情况及研究空白。特别值得关注的是：触发机制、可机器验证的停止条件、持久状态、验证子 Agent、Token 预算和人工升级机制。


ArcXiv



论文原文












3. Self-Evolving Coding Agents
2026 · arXiv · 综述
梳理 Coding Agent 如何从执行轨迹、测试反馈和仓库上下文中改进自身，覆盖记忆、工具、技能、模型及协作结构的演进。适合作为 Agent 自进化架构的研究入口。


arXiv



论文原文












4. AgentSWE: Can Coding Agents Build the Agent You Actually Want?
2026 · arXiv · 2026-10 新作
研究 Coding Agent 能否按照需求创建、修改并优化另一个 Agent。重点是用未见测试集检验真实交付，而非只看示例效果。适合研究 Agent 构建 Agent 的闭环评测。


arXiv



论文原文












5. Beyond Code Generation: Reliability, Verification, and Cost Economics in the Agentic Software Development Lifecycle
2026 · arXiv · 研究综述与框架
将研究重心从代码产出量转向可交付的软件价值，讨论验证成本、可靠性、Token 与工具成本，以及人工审核预算。适合建立企业 AISE 的全生命周期度量体系。


arXiv



论文原文



B. Coding Agent 评测与工程能力基准
这组重点回答：如何科学衡量 Agent 的工程能力，而不是只测代码生成准确率。
#	论文	年份 / 来源	研究价值与借鉴
6	SWE-Compass: Towards Unified Evaluation of Agentic Coding Abilities for Large Language Models	2026 · ICML / PMLR	统一多类软件工程任务，覆盖 8 类任务、10 种语言；适合设计多维度能力评测。 Proceedings of Machine Learning Research
7	SWE-Bench Pro: Can AI Agents Solve Long-Horizon Software Engineering Tasks?	2026 · ICML / PMLR	面向真实仓库和复杂多文件工程任务，适合研究长程任务与真实项目能力差距。 Proceedings of Machine Learning Research
8	OmniCode: A Benchmark for Evaluating Software Development Agents	2026 · ACL Findings	覆盖修复缺陷、生成测试、修复代码审查问题与风格问题；揭示 Agent 在语言及任务类型之间的能力差异。 ACL Anthology
9	How Do AI Coding Agents Contribute to Software Development? An Empirical Study of Agentic Pull Requests	2026 · arXiv	从真实 PR 研究 Agent 的使用分布、合并情况和代码质量变化，适合研究 AISE 的实际工程效益。 arXiv
10	AgentSWE	2026 · arXiv	评测 Agent 构建 Agent 的能力，关注需求满足、隐藏用例和优化效果；也适合研究闭环自改进。 arXiv
C. Agent 运行机制、基础设施与工程架构
这一组适合进一步研究 Harness、执行轨迹、上下文管理与企业级 Coding Agent 基础设施。
#	论文	年份 / 来源	研究价值与借鉴
11	Agentic Coding in the Wild: Characterizing GitHub Copilot at Production Scale	2026 · Microsoft Research	基于生产环境的大规模 Agent 调用轨迹研究执行负载、工具调用和上下文缓存；适合设计运行时可观测性及资源调度。 Microsoft Research
12	SWE-agent: Agent-Computer Interfaces Enable Automated Software Engineering	2024 · arXiv	经典工作：研究专为软件工程设计的 Agent-Computer Interface，帮助理解工具接口如何影响 Agent 能力。
13	The SWE-bench Benchmark: Evaluating Large Language Models on Real-World Software Issues	2023 · ICLR 2024	以真实 GitHub Issue 检验代码仓库级问题解决能力，是后续 Coding Agent 评测的重要基础。
14	SWE-Lancer: Can Frontier LLMs Earn $1 Million from Real-World Freelance Software Engineering?	2025 · arXiv	用真实自由职业软件工程任务评估端到端工作能力与经济价值，适合研究从任务成功率走向价值交付。
15	A Survey on Large Language Models for Software Engineering	2023 · arXiv	建立软件工程任务、LLM 应用及研究挑战的整体知识地图，适合作为领域综述入口。
D. AISE 的评测闭环、软件质量与可持续演进
#	论文 / 研究	年份 / 来源	研究价值与借鉴
16	Self-Evolving Coding Agents	2026 · arXiv	把执行反馈转化为技能、记忆和框架改进，研究演进的可靠性、泛化与安全边界。
17	LoopsBench	2026 · arXiv	用依赖图、逐步释放的测试与回归义务检验持续研发闭环。
18	SWE-Compass	2026 · ICML	提供跨任务、跨语言的综合能力基准，可用于验证改进是否只对单一任务有效。
19	OmniCode	2026 · ACL Findings	将测试生成、代码审查修复等任务纳入评测，避免只优化缺陷修复指标。
20	SWE-Bench Pro	2026 · ICML	用真实且复杂的仓库级任务检验 Agent 的长期工程能力，补充短任务基准的不足。
说明： 第 10、16–20 项与前面的论文存在重复，是因为我将同一篇研究映射到了多个研究主题；如果你要建立严格的 20 篇去重论文库，需要替换这些重复项。上面的 2026 年研究条目优先提供了可核验的原文入口，但并非每一项都已核实正式发表状态。
二、补齐去重后的论文库：5 篇值得加入的基础研究
上面的候选清单中有重复条目。若你要形成严格的 20 篇独立论文库，建议将重复项替换为以下基础研究。它们并非 2026 年新作，而是理解 2026 年 AISE 研究的重要技术基线。
#	论文	年份	核心借鉴
16	AutoCodeRover: Autonomous Program Improvement	2024	基于程序结构与代码定位进行自动修复，适合研究工具增强型 Agent。
17	OpenHands: An Open Platform for AI Software Developers as Generalist Agents	2024	研究通用软件开发 Agent 的执行环境、工具接口与平台架构。
18	CodePlan: Repository-level Coding using LLMs and Planning	2023	关注仓库级任务规划及跨文件依赖，适合长程任务拆解研究。
19	ChatDev: Communicative Agents for Software Development	2023	研究多 Agent 协作的软件开发流程，适合分析协作模式与角色分工。
20	MetaGPT: Meta Programming for A Multi-Agent Collaborative Framework	2023	将标准化 SOP 和角色分工引入多 Agent 软件工程，适合研究流程约束。
这些基础研究的意义在于：它们分别提供代码定位、执行平台、任务规划、多 Agent 协作和流程规范等不同设计思路，可作为评估新架构时的参照系。
再补一篇，形成 20 篇去重清单：
#	论文	年份	核心借鉴
21	RepoCoder: Repository-Level Code Completion Through Iterative Retrieval and Generation	2023	研究仓库级代码检索与生成的迭代机制，适合研究上下文构建与代码库知识利用。
三、结合你的 AISE 研究，建议怎么读

第一优先级：Loop Engineering
阅读 LoopsBench 和 Loop Engineering: Building Blocks, Adoption, and Impact。重点研究任务依赖、状态持久化、停止条件、回归验证与自动调度。




第二优先级：AISE 评测方法
阅读 SWE-Compass、SWE-Bench Pro 和 OmniCode。重点研究评测集构造、任务难度、测试有效性、跨语言泛化和结果可复现性。




第三优先级：Agent 自进化
阅读 Self-Evolving Coding Agents 和 AgentSWE。重点研究执行轨迹如何转化为可验证的经验，以及如何防止只针对公开测试用例过拟合。




第四优先级：企业级工程价值
阅读 Beyond Code Generation 和 Agentic Coding in the Wild。重点研究从代码生成成功率转向可交付价值、质量、成本、风险与运行效率的度量。



我的判断： 如果你的目标是构建 AISE 研究体系，而不只是了解 Coding Agent 的进展，最值得投入的主线是：
Loop Engineering → 可执行评测 → 可靠性验证 → 反馈驱动的自进化。
这条主线可以直接连接论文研究、OpenCode 实验、设计模式对比，以及企业级 AI 应用工程能力建设。需要注意，上述列表是主题导向的研究候选清单，不是严格的 2026 年发表论文 Top 20；其中包含历史基础论文，且正式发表状态、热度排名及部分原文链接仍应逐项核验。