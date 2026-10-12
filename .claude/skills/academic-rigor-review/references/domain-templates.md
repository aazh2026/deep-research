# 领域特定评估模板（OPT-15）

> P6 的 8 维评分（`DIM-01`..`DIM-08`）默认是无差别权重 + 通用锚点。但不同学科的"严谨"含义差异极大：
>
> - **CS（计算机科学）**：可复现性 > 统计严谨；代码与算力是主要证据；baseline 必须 state-of-the-art
> - **生物医学**：统计严谨、样本量、伦理审批、盲法 > 可复现性；基线是 CONSORT/STROBE 等报告规范
> - **经济学**：识别策略（identification）、稳健性、外推有效性为核心；统计指标次要
>
> 本文件提供 3 套**起点模板**。P6 在评分前应先选择或自定义模板。**模板不改变 P0 硬规则**（P0 仍由 R1-R5 + 8 条 P0-N 触发），仅影响 8 维评分的"什么算 4 分"。

---

## 模板选择流程

### Step 1.5（新增，OPT-15）：选择领域模板

在 P1 完成后、**进入 Step 2 之前**由 orchestrator 选择领域模板：

1. **自动检测**（基于 article 关键词 + venue + 引用风格）：
   - CS 关键词：`dataset / benchmark / baseline / neural / LLM / agent / code release / GitHub`
   - 生物医学关键词：`clinical trial / patient / IRB / CONSORT / blinding / sample size / p-value / cohort`
   - 经济学关键词：`identification / IV / regression / treatment effect / RCT / panel data / robust / standard error`
   - 若无明确信号 → 使用 `default` 模板（无差别权重）

2. **用户显式覆盖**：若用户告知领域（如"这是经济学论文"），强制使用对应模板

3. **混合领域**：若文章跨领域（如"ML for healthcare"），使用 `mixed:<领域1>+<领域2>` 标记并在 `evaluation_limitations` 显式说明

输出：

```yaml
domain_template: cs   # cs / biomedical / economics / default / mixed:<...>
domain_confidence: high   # high / medium / low
domain_rationale: "venue=ICLR + GitHub release + benchmark 关键词 → CS"
```

---

## 模板 1：CS（计算机科学）

### 适用信号

- Venue：NeurIPS / ICLR / ICML / ACL / EMNLP / CVPR / AAAI / KDD / SIGGRAPH
- 关键词：accuracy / F1 / BLEU / benchmark / dataset / baseline / SOTA / GitHub / open-source
- 引用风格：通常有 arXiv ID + conference

### DIM 权重（合计 1.0）

| DIM | 权重 | 原因 |
| --- | --- | --- |
| DIM-01 理论基础 | 0.08 | CS 理论贡献相对小（更看实证） |
| DIM-02 文献与相关工作 | 0.12 | baseline 覆盖是核心 |
| DIM-03 论证与推理 | 0.10 | 通常不复杂但需逻辑清晰 |
| DIM-04 研究方法 | 0.15 | 方法创新是主要贡献 |
| DIM-05 证据与数据 | 0.15 | benchmark 结果 + 统计显著性 |
| DIM-06 有效性与偏差控制 | 0.10 | ablation + 多 seed |
| DIM-07 可复现性与可证伪性 | **0.20** | **CS 最高权重**——代码/算力/数据可获得性 |
| DIM-08 结论边界与研究贡献 | 0.10 | 限定 SOTA 范围 |

### 评分锚点（关键 DIM 摘录）

**DIM-07（可复现性）**

- `1` 严重不足：无代码、无数据、无超参、无法独立验证
- `2` 较弱：仅有部分代码（核心组件缺失），关键超参未报告
- `3` 基本成立：代码与数据公开，但缺训练脚本或环境配置
- `4` 严谨：完整代码 + 随机种子 + 环境配置 + 训练日志
- `5` 高度严谨：代码 + 数据 + 模型权重 + Docker 镜像 + leaderboard 复现实验

**DIM-05（证据与数据）**

- `1` 严重不足：单一实验 + 单 seed
- `2` 较弱：多次实验但无统计检验
- `3` 基本成立：多 seed + 标准差报告
- `4` 严谨：多 seed + 显著性检验 + 置信区间
- `5` 高度严谨：多 seed + bootstrap CI + 多种 statistical test 验证

### 领域 P0 反模式（**CS 额外必查**）

1. **缺最强 baseline**：未与同期 SOTA 对比（不只是"以前的方法"）
2. **缺 compute-matched 对照**：未报告模型大小、训练 token、GPU 时长
3. **GitHub 链接死链**：声称 release 但实际不可用
4. **单 seed 报告**：声称 SOTA 但无方差/置信区间
5. **Cherry-pick 测试集**：在未见测试集上调超参
6. **LLM judge 无校准**：用 LLM 当评估器但未验证其与人类一致性
7. **Vague SOTA claim**："achieves state-of-the-art" 但表格数字未支持

### 领域 P1 反模式（示例）

- 缺多个独立 seed（不是 single run）
- 训练超参表缺失
- 未报告 token/算力/参数数量
- 数据集划分不公开
- 评测脚本与训练脚本不一致

### Verdict 校准

- 4 页 workshop 论文（如 LLM Harmony）：D-301/D-302/D-303 等 P1 可接受，**P0 仍触发** verdict 降级
- Full conference paper：P1 标准更严，特别是 baseline 完整性
- 综述/position paper：评价标准不同（侧重 DIM-02 文献覆盖），应使用 `cs:survey` 子模板

---

## 模板 2：biomedical（生物医学）

### 适用信号

- Venue：NEJM / Lancet / JAMA / Nature Medicine / Cell / PLOS Medicine / 期刊
- 关键词：clinical trial / patient / IRB / CONSORT / STROBE / blinding / cohort / hazard ratio
- 引用风格：Vancouver 编号，无 arXiv

### DIM 权重（合计 1.0）

| DIM | 权重 | 原因 |
| --- | --- | --- |
| DIM-01 理论基础 | 0.12 | 生物学/医学机制需清晰 |
| DIM-02 文献与相关工作 | 0.10 | 引用经典研究 + 临床指南 |
| DIM-03 论证与推理 | 0.12 | 因果推断需严密 |
| DIM-04 研究方法 | **0.18** | **最高权重**——设计/样本/盲法 |
| DIM-05 证据与数据 | 0.15 | effect size + CI + p-value |
| DIM-06 有效性与偏差控制 | **0.18** | **最高权重**——混杂/选择偏差/盲法 |
| DIM-07 可复现性与可证伪性 | 0.08 | 数据通常不公开（HIPAA）但预注册要 |
| DIM-08 结论边界与研究贡献 | 0.07 | 临床意义 vs 统计意义区分 |

### 评分锚点（关键 DIM 摘录）

**DIM-04（研究方法）**

- `1` 严重不足：无对照组、单臂研究、关键混杂未控制
- `2` 较弱：有对照但未随机 / 未盲法 / 样本量过小
- `3` 基本成立：RCT 但缺样本量计算或未做 intention-to-treat
- `4` 严谨：RCT + 预注册 + 样本量计算 + ITT 分析 + 亚组预设
- `5` 高度严谨：多中心 RCT + 中央随机化 + 盲法评估 + DSMB + 预注册

**DIM-06（有效性与偏差控制）**

- `1` 严重不足：选择偏差 / 信息偏差未识别
- `2` 较弱：识别偏差但未做敏感性分析
- `3` 基本成立：主要偏差讨论 + 部分敏感性分析
- `4` 严谨：E-value 计算 + 多重敏感性分析 + 阴性对照
- `5` 高度严谨：靶向 emulation trial + 阴性对照 + 全面的 bias quantification

### 领域 P0 反模式（**biomedical 额外必查**）

1. **无 IRB / 伦理审批**：人体研究但未声明伦理审批号
2. **缺样本量计算（power analysis）**：未在方法部分报告 a priori power
3. **未预注册（clinical trial）**：RCT 声称但未在 ClinicalTrials.gov 预注册
4. **未做 ITT（intention-to-treat）**：仅 per-protocol 分析
5. **多重比较未校正**：多个 outcome 检验但无 Bonferroni / FDR 校正
6. **数据缺失未处理**：>10% 缺失但仅做 complete case analysis
7. **confounder 未调整**：已知重要混杂（年龄、性别、合并症）未在模型中
8. **脱离 CONSORT/STROBE 报告规范**：随机试验/观察研究报告严重不完整

### 领域 P1 反模式（示例）

- 缺 effect size 与 CI（仅有 p-value）
- 亚组分析未预设（post-hoc subgroup）
- 单中心未声明外推性
- 失访率 > 20% 未讨论
- 仅用 historical control 而非 concurrent

### Verdict 校准

- 临床干预 RCT：P0 触发更频繁（IRB、ITT、样本量任一缺失即 P0）
- 观察性研究：bias quantification 是核心；不能用 RCT 标准苛求
- Case report：完全不同的评价标准（应使用 `biomedical:case_report` 子模板）
- Systematic review：应使用 `biomedical:systematic_review` 子模板（侧重 DIM-02 + PRISMA 流程）

---

## 模板 3：economics（经济学）

### 适用信号

- Venue：AER / QJE / JPE / Econometrica / REStud / AEJ 系列 / 期刊
- 关键词：identification / IV / 2SLS / treatment effect / panel / fixed effects / RCT / natural experiment
- 引用风格：作者-年份，无 arXiv

### DIM 权重（合计 1.0）

| DIM | 权重 | 原因 |
| --- | --- | --- |
| DIM-01 理论基础 | **0.15** | **最高权重**——经济理论驱动假设 |
| DIM-02 文献与相关工作 | 0.10 | 需覆盖同期文献争论 |
| DIM-03 论证与推理 | **0.15** | **最高权重**——识别策略逻辑链 |
| DIM-04 研究方法 | 0.15 | identification 是核心 |
| DIM-05 证据与数据 | 0.12 | effect size + SE + CI |
| DIM-06 有效性与偏差控制 | 0.12 | 稳健性检验 |
| DIM-07 可复现性与可证伪性 | 0.08 | 数据通常公开但代码不强制 |
| DIM-08 结论边界与研究贡献 | 0.13 | 外推性 + 政策含义 |

### 评分锚点（关键 DIM 摘录）

**DIM-03（论证与推理）—— 经济学核心**

- `1` 严重不足：仅描述相关关系，无识别策略
- `2` 较弱：识别策略存在但威胁未讨论（OVB / reverse causality）
- `3` 基本成立：IV/RCT/DID + 平行趋势检验
- `4` 严谨：识别策略 + 多种 robustness（不同 IV、不同控制集）+ placebo test
- `5` 高度严谨：多种独立识别策略指向同一结论 + 全面的 threat-to-identification 检验

**DIM-04（研究方法）**

- `1` 严重不足：OLS 无固定效应 / 无聚类标准误
- `2` 较弱：基础方法但未处理关键内生性
- `3` 基本成立：DID + 平行趋势 / IV + first stage F > 10
- `4` 严谨：identification + bandwidth 选择检验 + wild bootstrap
- `5` 高度严谨：pre-trend test + multiple identification + 样本外验证

### 领域 P0 反模式（**economics 额外必查**）

1. **无识别策略**：声称因果但只是 OLS 回归相关
2. **平行趋势检验不显著或缺失**：DID 但无 pre-trend test
3. **First stage F < 10**：弱工具变量
4. **聚类标准误层级错**：个体层面聚类但只有省级变异
5. **内生性未讨论**：声称因果但完全不提 OVB / reverse causality
6. **未做 placebo test**：DID/RDD 但无 placebo
7. **多 inference 未校正**：多个 outcome 检验无校正
8. **外推性未声明**：政策含义过强但样本特殊

### 领域 P1 反模式（示例）

- 缺 robustness 表（不同控制变量组合）
- SE 未聚类
- 缺 bandwidth sensitivity（RDD）
- 缺 balance table（RCT）
- 缺样本限制说明
- 缺数据来源说明

### Verdict 校准

- 顶级 5 期刊投稿：P0 标准最严
- Working paper：P0 仍触发（不能因未发表而放松）
- Pure theory：无 DIM-04/05 评价，使用 `economics:theory` 子模板
- Replication study：使用 `economics:replication` 子模板（侧重 DIM-04/05 与原研究对比）

---

## 模板 default（无差别）

适用于：跨领域、信号不清、非上述 3 类。

DIM 权重均等（每个 0.125），锚点与 `references/p6-synthesis.md` 一致。

**P6 必须在 `evaluation_limitations` 显式说明**："未使用领域特定模板"。

---

## 模板使用规则

### 何时使用领域权重

- **DIM 平均分**计算：用领域权重加权（如 CS: DIM-07 = 0.20）
- **verdict 判定**：仍由 P0 硬规则 + 6 种 verdict 决定（P0 不变）
- **P1 缺陷严重度**：用领域权重评估"对总体严谨度的影响"（影响优先级，不影响 P0/P1 分级）

### 何时不使用领域权重

- 用户显式要求无差别评分
- 跨领域文章且用户未指定
- 模板文件中未定义的领域（如物理、化学）—— 需新增模板才能用

### 模板扩展

新增领域模板需：

1. 在本文件追加新章节
2. 给出 8 个 DIM 的领域权重（合计 1.0）
3. 至少给出 DIM-04/05/06/07 的领域评分锚点
4. 至少 5 条领域 P0 反模式（按该学科最致命的"红线"）
5. 至少 3 条领域 P1 反模式
6. 给出 verdict 校准说明
7. 提交一个真实文章测试（用模板前后对比）

### 模板选择冲突

若 P1 解析后同时命中多个领域关键词（如 "ML for healthcare" 命中 CS + biomedical）：

1. 默认使用 `mixed:<领域1>+<领域2>` 标记
2. **取两者权重的算术平均**（CS DIM-07 = 0.20, biomedical DIM-07 = 0.08 → mixed = 0.14）
3. **取两者 P0 反模式的并集**（最严标准）
4. 在 `evaluation_limitations` 显式说明使用了 mixed 模板

---

## 与 P0 硬规则的关系（重要）

| 规则 | 关系 |
| --- | --- |
| P0-R1（critical_defects P0 → verdict 体现） | **不变**（领域模板不影响 P0 触发） |
| P0-R2（precheck_p0_count >= 1 → verdict 必为 5 或 6） | **不变** |
| P0-R3（P0 必含 affected_claims/impact_scope/fix_requirement） | **不变** |
| P0-R4（P0 对应 V-NNN priority=must） | **不变** |
| P0-R5（DIM 平均不冲销 P0） | **不变**（更明显——领域加权后仍不能冲销） |
| 8 条 P0-N（P0-1..P0-8 判定） | **增强**（领域 P0 反模式提供更具体的触发点） |

**核心原则**：领域模板不创造新的 P0 触发规则，只**增强** P0-N 的"什么算 P0"的具体场景。
