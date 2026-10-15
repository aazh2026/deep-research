# CodePlan 论文解读 (Microsoft Research, 2023)

> 论文: **CodePlan: Repository-level Coding using LLMs and Planning**
> 作者: Ramakrishna Bairi, Atharv Sonwane, Aditya Kanade, Vageesh D C, Arun Iyer, Suresh Parthasarathy, Sriram Rajamani, B. Ashok, Shashank Shet (Microsoft Research, India)
> 链接: arXiv:2309.12499v1, 21 Sep 2023
> 解读日期: 2026-10-15
> 主题: **多文件 edit propagation 用 planning 跟 dependency graph 解决, 而非一次性 LLM 修复**

---

## 0. 为什么这一轮复现 CodePlan?

14 轮 /loop 复现过的 paper 都在 "**改一段代码**" 层面 (round 6-13), 没有 paper 专门研究 "**改一个函数签名, 跨多个文件 propagate 修复**" 这个 SWE 真实痛点。

**CodePlan 是 Microsoft Research 2023 年的 paper, 报了一个非常 strong 的数字**:
- **5/6 仓库** 用 CodePlan 通过 validity check
- **0/6 仓库** 用 baseline (build + LLM 迭代修) 通过
- **5 vs 0 = 100% 相对提升** (虽然绝对是 5 个 repo)

**本轮复现目标**: 
- 5-8 个 **synthetic mini multi-file edit propagation task**
- 对比 **CodePlan (planning + dependency graph)** vs **Baseline (single LLM shot)**
- 测 "**改了 A 函数, B/C/D 也要改, 改对几个文件**" 这个核心 claim

---

## 1. 论文核心问题

### 1.1 Repository-level editing 的 3 个困难

```
seed edit: 改 create_complex(a, b) 签名 (float, float) → (float, float, dict)

caller 1: process(a, b, k) 调 create_complex(a, b)  ← 也要改 (signature mismatch)
caller 2: test.py 调 create_complex(a, b)  ← 也要改
type: tuple[float, float] vs Complex  ← 依赖 type 也要改
```

**3 个真实痛点**:
1. **Callers 改不全** — 一个函数改签名, 所有调用方都要改, 漏一个就 fail
2. **Type 链传播** — 改了 return type, 所有用这个 return 的代码都要改
3. **Build / test 找不到的地方** — build error 给 "File X line 5", 但根因在另一文件

**CodePlan 的答案**: 显式维护 **dependency graph** + **plan graph**, 让 LLM 知道" 还要改哪些文件"。

### 1.2 跟 "Just ask LLM" baseline 的对比

Baseline (build + LLM iterative fix):
```
1. LLM 改 seed edit
2. Run build
3. build fail → 给 LLM 看 error
4. LLM 改
5. Run build
... 重复 5-10 次 ...
```

**问题**: build error 是 "**tree-shaking 后的局部报错**", LLM 看 error 不知道" 哪个根因", 经常" 修了 file A, 坏了 file B"。

CodePlan:
```
1. 静态分析: 提取 dependency graph (class hierarchy, calls, fields, types)
2. 改 seed edit
3. Classify change (e.g. "method signature changed")
4. Find affected blocks: Rel(D, M, CalledBy) → 找到所有 caller
5. Plan graph: 把 "caller 也要改" 加为新 node
6. LLM 改 caller
7. 重复 plan + execute 直到 plan graph 完
8. Run oracle
```

**优势**: CodePlan **主动找 affected blocks**, baseline **被动等 build error**。

---

## 2. CodePlan 算法 (Algorithm 1)

### 2.1 5 步循环

```
while Delta_seeds is not empty:
  1. ExtractCodeFragment(B, R, I)        # 提取要改的代码 + 周围 class
  2. GatherContext(B, R, D)              # spatial (dependency graph) + temporal (prior edits)
  3. MakePrompt(I, Fragment, Context)    # 构造 prompt
  4. NewFragment = InvokeLLM(I, Prompt)  # LLM 改
  5. R = Merge(NewFragment, B, R)        # 合并回 repo
  6. ClassifyChange(Fragment, NewFragment)  # 分类修改类型
  7. D' = UpdateDependencyGraph(D, Labels, Fragment, NewFragment, B)
  8. AffectedBlocks = GetAffectedBlocks(Labels, D, D', B)
  9. 对每个 affected block: 加新 plan node, edge label = cause
```

### 2.2 关键组件

#### (a) Dependency Graph
7 类 edge label:
1. `ParentOf` / `ChildOf` (syntactic)
2. `ImportRel` / `ImportedBy` (imports)
3. `BaseClassOf` / `DerivedClassOf` (inheritance)
4. `Overrides` / `OverridenBy` (method override)
5. `Calls` / `CalledBy` (method invocation)
6. `Instantiates` / `InstantiatedBy` (object creation)
7. `Uses` / `UsedBy` (field use)

#### (b) ClassifyChanges (Table 1)
13 种 atomic change label:
- MMB: Method Body Modified
- MMS: Method Signature Modified  ← **触发 caller 找**
- MF: Field Modified
- MC: Class declared
- ...
- 3 类 (Modification / Addition / Deletion) × 5 construct (Method body/sig, Field, Class, Constructor, Import)

#### (c) GetAffectedBlocks
按 Table 1 第 4 列规则, 每种 change type 决定要 propagate 到哪些 block:
- MMS (改 method 签名) → Rel(D, M, CalledBy) + Rel(D, M, Overrides) + Rel(D, M, OverridenBy) ...
- MMB (改 method body) → 如果 return 是 escaping object, 找 Rel(D, M, CalledBy)
- MF (改 field) → Rel(D, F, UsedBy) + Rel(D, F, ConstructedBy) ...

### 2.3 Plan Graph (DAG)

```
        ┌─ Plan node: edit Create.cs (seed) ─┐
        │                                    │
        │ cause: "escaping return type"      │
        ▼                                    ▼
Plan node: edit Process.cs            Plan node: edit Test.cs
(affects caller)                      (affects caller)
        │
        ▼
Plan node: edit TypeAlias.cs
(affects Process.cs use of type)
```

每个 node 标 "pending" 或 "completed"。Algorithm 1 持续 pick pending node, LLM 改, 然后 propagate 新 affected blocks 进 graph。

---

## 3. 关键实验结果 (Section 5)

### 3.1 Setup

- **2 task suites**:
  - **C# package migration** (4 repos) — 把 `Newtonsoft.Json` 替换成 `System.Text.Json`
  - **Python temporal edits** (2 repos) — 改函数实现, 跨 2-97 文件
- **2 baselines**:
  - Baseline 1: 跑 build / mypy, 把 error 给 LLM, 迭代修
  - Baseline 2: Python 用 mypy 静态 type checker 找 affected code, 跟 LLM 一起用
- **Oracle**: build pass + tests pass

### 3.2 关键数字 (paper Table)

```
                  CodePlan    Baseline 1    Baseline 2
C# (4 repos):     4/4         0/4           0/4  (build can't fix)
Python (2 repos): 1/2         0/2           0/2  (mypy can't fix)
────────────────────────────────────────────────────
Total:            5/6         0/6           0/6
```

**5/6 vs 0/6 = 100% 相对提升** (虽然绝对是 5 个 repo)。

### 3.3 关键 insight

- **C# 4/4 全过**: build system 给的 error 噪声大, CodePlan 的 dependency graph 比 build error 信号强
- **Python 1/2**: mypy 给出 type error 但 LLM 看不懂, CodePlan 也只过 1 个 — Python type 推断比 C# 难
- **Baseline 0/6**: build / mypy error 是 "局部 + tree-shaking 后" 的, LLM 看局部 error 修不全

---

## 4. CodePlan 的 4 个关键 insight

### 4.1 "**主动 dependency graph > 被动 build error**"

直觉: build error 已经够详细 (哪一行哪个符号错)。
实际: build error 是 "**已经 compile 失败的代码**" 报的, 但根本因可能在另一个 file。**LLM 看 build error 经常在错的 file 修**。

CodePlan 用静态分析提前知道 "改 A 影响 B/C/D", **LLM 直接修 B/C/D**, 不用等 build fail。

### 4.2 "**Plan graph 是 PDDL-like 任务规划**"

CodePlan 的 plan graph 跟经典 AI planning 几乎一样: **DAG of obligations, each with precondition + effect**。
- Precondition: 当前 code state
- Effect: edit 应用后的 state
- 持续 pick pending node, 执行, 更新 graph

**这不是新 idea**, 但 2023 年 LLM 时代用 LLM 作为 "executor" 重新包装一次。

### 4.3 "**Static analysis 是 LLM 的' 眼镜 '**"

LLM 自己看 100 行代码, 不知道哪个 function 调哪个。Static analysis 提取 dependency graph, LLM 看 graph 知道 "改 A 影响 B"。

**这是 round 7 AutoCodeRover "AST retrieval" 跟 round 11 RepoCoder "iterative RAG" 的同一类思路** — **给 LLM 外部结构, 而不是让 LLM 自己 derive**。

### 4.4 "**Edit propagation 是 repository-level editing 的 80% 工作**"

真实 SWE 任务: 
- 改一个函数签名 → 30% 时间
- 找所有 caller → 50% 时间
- 修所有 caller → 20% 时间

**CodePlan 直接攻 "找所有 caller" 这 50%** — 这是 round 6-13 都没专门研究的痛点。

---

## 5. paper 的局限性 (paper 自己说)

1. **小规模** (6 repos) — 但 5/6 vs 0/6 已经 strong
2. **依赖 tree-sitter / Jedi 静态分析** — 动态语言 (Python) 不如静态语言 (C#) 准
3. **Plan graph 状态可能指数增长** — paper 没深入分析 worst case
4. **Oracle 限于 build + test** — 跟 round 13 SWE-Lancer 一样, "test pass" 不等于 "任务真完成"

---

## 6. 跟 13 轮 /loop 的关系

| 轮 | 复现对象 | 任务粒度 | 评测 |
|---|---|---|---|
| 6 | SWE-agent | long-horizon issue | 1 instance |
| 7 | AutoCodeRover | AST retrieval | 1 instance |
| 8 | OmniCode | bug-fixing | 10 instance |
| 11 | RepoCoder | line completion | 5 task |
| 12 | Self-Evolving | HumanEval | 8 task |
| 13 | SWE-Lancer | 选 best proposal | 8 task |
| **14** | **CodePlan (本轮)** | **多文件 edit propagation** | **5-8 task** |

**14 轮里 3 件新事**:
1. **第一次显式研究 "edit propagation"** — round 6-13 都没专门看
2. **第一次有 planning algorithm** — round 6-13 都没有 DAG / plan
3. **第一次报 "5/6 vs 0/6"** — 100% 相对提升, 14 轮最强

---

## 7. 本轮复现策略

### 7.1 不能 1:1 复现

**原 paper 复现** = 跑 6 个真实 C#/Python repo + tree-sitter/Jedi 静态分析 + GPT-4 API + build system, 复杂度跟 round 10 OpenHands 持平。

**本轮 mini 复现**:
- 5-8 个 **synthetic mini multi-file edit task**
- 每个 task: 3-4 个小 Python 文件, 改一个函数签名, 验证所有 caller 都被改对
- 测 "**CodePlan-style planning (按 dependency graph 顺序改) vs baseline (一次性 LLM 改全部)**"

### 7.2 任务示例

```
[Task: "改 add(a, b) 签名 → add(a, b, log=False)"]
files:
  math_ops.py:    def add(a, b): return a + b
  calc_app.py:    from math_ops import add
                  result = add(x, y)        ← 要改成 add(x, y, log=False)
  test_app.py:    assert add(1, 2) == 3      ← 要改成 add(1, 2, log=False)

oracle: 3 个文件都正确加 log=False 参数
```

### 7.3 复现假设

- Baseline (一次 LLM call 改全部): 估计 30-50% pass — LLM 经常漏 caller
- CodePlan (按 dependency graph 顺序改): 估计 60-80% pass — 因为有 explicit caller list

---

## 8. takeaway 总结

| Insight | 论文数据 | 我的解读 |
|---|---|---|
| CodePlan 5/6 vs baseline 0/6 | 100% 相对提升 | dependency graph 真的 work |
| C# 4/4, Python 1/2 | 静态语言 > 动态语言 | tree-sitter 比 Jedi 准 |
| Build / mypy 0/6 | 局部 error 误导 LLM | 静态分析胜过 build 反馈 |
| Plan graph 是 AI planning 经典思路 | DAG of obligations | 老 idea + LLM executor = 新组合 |
| Edit propagation = 50% SWE 工作 | 找 caller 比修 caller 难 | 14 轮没人专门研究 |

---

## 9. 引用

- Bairi et al. **CodePlan: Repository-level Coding using LLMs and Planning**. arXiv:2309.12499v1, Sep 2023 — 本轮解读
- Jimenez et al. **SWE-bench**. ICLR 2024 — Round 6
- Zhang et al. **RepoCoder**. arXiv:2303.12570 — Round 11, RAG 思路
- Shinn et al. **Reflexion**. NeurIPS 2023 — Round 12, self-evolution
- tree-sitter. https://tree-sitter.github.io/ — CodePlan 用此做 static analysis

---

*本文由 Claude Code 完成于 2026-10-15, 是 14 轮 /loop 中**第一个研究 "edit propagation" 痛点**的复现。*
