# WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution

## 基本信息

- **论文标题**：WikiSkill: Compiling Agent Experience into Persistent Knowledge for Skill Evolution
- **作者**：Liyan Tang¹, Cyrus Rashtchian¹, Chun-Sung Ferng¹, Andrew Tomkins¹, Da-Cheng Juan¹, Tu Vu¹·²
- **机构**：¹ Google Research，² Virginia Tech
- **arXiv**：2608.27454v1 [cs.AI]
- **提交日期**：2026-08-27
- **分类**：cs.AI
- **原文链接**：https://arxiv.org/abs/2608.27454
- **PDF**：paper.pdf（本地，1.1MB）

## 核心问题

AI agents 完成多步任务后会"忘记"经验；现有的 **skill-evolution** 方法（Trace2Skill、EvoSkill、SkillOpt）只把知识散落在**优化历史**（rejected proposals、trajectory 摘要、训练日志）里，**没有维护一个独立的、不断演化的知识表示**。

受 Karpathy 2026「**LLM Wiki**」构想启发，本文问：**「agent 经验能否像编译进一个持久化、可组合的知识库那样，被用于长期 skill 演化？」**

## 核心方案：三层架构 + 四组件循环

**三层工作空间**（图 2）：

| 层 | 路径 | 性质 | 内容 |
|---|---|---|---|
| **Raw Layer** | `raw/` | 不可变、write-once | 完整执行 trace（reasoning + tool calls + outputs） |
| **Wiki Layer** | `wiki/` | **持续累积、永不重置** | 结构化模式 + 演化日志 + skill impact tracker |
| **Skills Layer** | `skills/` | 可逆、conditional update | SKILL.md（流程）+ PURPOSE.md（对应 wiki 条目） |

**四个 agent 角色**（每个 iteration）：

1. **Inference Agent**：用 `S_{k-1}` 执行任务，**不能读 wiki**（避免训练-推理偏差）
2. **Wiki Maintainer**：用 trace + 现有 wiki 做 root-cause 分析，写新 pattern / 更新旧 pattern / 追加 logs
3. **Skill Proposer**（ReAct style）：读 wiki + trace，自主用 `read_file` 工具深挖，提出「新增一个 skill」或「patch 现有 skill」的原子提案
4. **Gating & Rollback**：在 `D_val` 上验证提案；score 升就接受、否则回滚（**但 wiki 永远不回滚**）

**关键设计**：skill 可滚、wiki 不可滚——这正是「编译进持久知识」的精髓。

## 实验设置

**5 个 benchmark**：
- LiveMath（数学推理）
- SealQA（web search）
- SpreadSheetBench（电子表格）
- OfficeQA（长文档 QA）
- ALFWorld（交互式 embodied）

**5 个模型**：
- Gemini-3.5-Flash（封闭）
- Qwen-3.5-4B / 9B、Qwen-3.6-27B
- Gemma-4-31B

**4 个 baseline**：No skill / Trace2Skill / EvoSkill / SkillOpt

**3 次独立 run + paired bootstrap test (p < 0.05)**。

## 关键结果

### Table 1：5 模型 × 5 benchmark 平均 Acc

| 模型 | NoSkill | Trace2Skill | EvoSkill | SkillOpt | **WikiSkill** | Δ |
|---|---:|---:|---:|---:|---:|---:|
| Qwen-3.5-4B | 26.2 | 32.1 | 33.7 | 35.2 | **38.5** | +12.3 |
| Qwen-3.5-9B | 29.9 | 36.7 | 42.3 | 40.2 | **47.4** | +17.5 |
| Qwen-3.6-27B | 39.4 | 47.3 | 53.3 | 50.7 | **63.3** | +23.9 |
| Gemma-4-31B | 41.3 | 45.8 | 43.4 | 49.1 | **54.9** | +13.6 |
| Gemini-3.5-Flash | 49.5 | 55.6 | 56.1 | 55.9 | **68.1** | +18.6 |

**WikiSkill 在所有 5 个模型上 SOTA**。

### 关键发现

1. **Skill evolution 与 model scaling 互补**（Qwen 家族：+12.3 / +17.5 / +23.9 随模型增大）
2. **9B + WikiSkill > 27B 无 skill**：Qwen-3.5-9B WikiSkill 47.4 vs Qwen-3.6-27B NoSkill 39.4
3. **强模型产生的 skill 也能帮小模型**：Qwen-3.6-27B 产生的 skill 让 Qwen-3.5-9B 在 ALFWorld 上 70.2（vs self-evolved 63.4）
4. **存在负迁移**：Qwen-3.5-4B skill 让 Gemini-3.5-Flash 在 SpreadSheet 上从 50.5 → 18.1（low-level workarounds 反而约束强模型）
5. **OfficeQA 难**：所有模型在该任务上 skill 增益都小（长文档多步检索对弱模型是反模式）

## 贡献（paper 自述）

1. 引入 **WikiSkill 框架**——agent skill 与持久知识库共演化
2. 5 benchmark × 5 model 系统验证，ablation 证明 wiki 不可缺
3. 系统研究 skill evolution × model capability 的交互，证 skill 可跨模型/家族迁移

## 局限与开放问题

- **依赖 LLM API**：Inference / Maintainer / Proposer 全是 LLM agent，本地复现需 API budget
- **使用 Gemini-3.5-Flash**：封闭模型，无法在 CPU 离线复现
- **5 个 benchmark 计算量大**：每跑一遍需对每个 (model, dataset) 跑 3 次独立演化
- **未发布代码**（截至 2026-10-13）
- **「LLM Wiki」概念本身有争议**：wiki 越长，prompt 越满；何时「压缩」「遗忘」仍是开放问题

## 复现可行性

| 维度 | 难度 | 说明 |
|---|---|---|
| 数据集 | ✅ 公开 | LiveMath/SealQA/SpreadSheetBench/OfficeQA/ALFWorld 都在 HF |
| 模型 | ❌ API-only | 核心实验靠 Gemini-3.5-Flash 闭源模型 |
| 计算 | ❌ 大 | 3 runs × 5 models × 5 datasets + 多次 LLM 调用 |
| 代码 | ❌ 未开源 | arXiv v1，GitHub 暂无仓库（2026-10-13 搜） |

**结论**：纯 CPU + 开源模型**无法**复现主表（Table 1）的 WikiSkill 数字；可做：
1. 用 Qwen-3.5-9B（或更小的 Qwen-2.5-7B）实现**简化版** WikiSkill 框架，跑小子集验证「wiki 持久化的边际收益」方向性
2. 抽象 `wiki/` 文件结构 + `gating` 机制做 toy demo（不靠 LLM 演化 skill，只测 gating + rollback 机制本身）

## 资源

- arXiv 链接：https://arxiv.org/abs/2608.27454
- PDF：https://arxiv.org/pdf/2608.27454
- 论文本地副本：`papers/22-wikiskill/paper.pdf`
