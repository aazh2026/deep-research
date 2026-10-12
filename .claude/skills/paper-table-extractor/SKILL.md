---
name: paper-table-extractor
description: 把 HTML/Markdown 文档中的论文清单/表格批量抽取成「每篇论文一个文件夹 + 一份 paper.md」的结构化语料库。自动从 arXiv / ACL Anthology / DOI 抓取摘要与元数据，与原表中的「核心价值/关键贡献/指标」字段合并，去重、统一命名、批量建目录。Use when the user provides an HTML or Markdown document containing a curated list/table of research papers and wants each paper extracted into its own folder with a structured markdown file — for example, "把论文下载成markdown", "extract papers from HTML", "save papers to per-paper folders", "把这份论文总表拆成每篇一个文件夹". Also use when the user wants to bootstrap a paper reading corpus from a benchmark/survey aggregation page. Skip when the user only wants a single paper's abstract, when the source is unstructured prose (no table/list), or when downstream consumption does not need per-paper files.
version: 1.0.0
---

# Paper Table Extractor Skill

把一份「论文总表」（HTML 或 Markdown）拆成一份可离线浏览、可批量阅读的结构化目录：

```
<output_dir>/
├── 01-paper-slug-1/
│   └── paper.md
├── 02-paper-slug-2/
│   └── paper.md
├── 03-paper-slug-3/
│   └── paper.md
└── INDEX.md          （可选：自动生成的目录索引）
```

每篇 `paper.md` 合并两类信息：

1. **来自原表的「策展字段」**：核心价值、关键贡献、价值指标、应用场景——这是人工整理的视角
2. **来自原文站点的「一手字段」**：完整摘要、作者全名、提交日期、分类、官方项目页——这是机器抓取的事实

## 何时激活

- 用户给了一份论文总表 HTML / Markdown（带表格 / 编号清单 / `<tr>` 行）
- 每行至少包含：论文标题 + 可点击的链接（arXiv / ACL / DOI / 项目页）
- 用户希望「每篇论文一个文件夹」而不是单文件清单
- 用户希望保留原表的策展信息（核心价值 / 关键贡献 / 指标 / 应用场景）

**不要**用于：

- ❌ 用户只想要一篇论文的摘要（用 WebFetch 直接读）
- ❌ 源文档是非结构化散文（没有表格 / 清单行）
- ❌ 源文档是 PDF（先用 pdf-to-markdown 类工具预处理）
- ❌ 用户要的不是「论文库」而是「文献综述」（用 deep-research skill）

## 工作流程

### Step 1: 探查源文档

读取用户提供的文件，识别其结构：

| 来源 | 识别特征 | 行单位 |
|---|---|---|
| HTML 表格 | `<table>` + `<tr>` + `<td class="u">` 标题单元格 | 一个 `<tr>` = 一篇论文 |
| Markdown 表格 | `\|` 分隔 + 表头分隔行 `\|---\|` | 一行 = 一篇论文 |
| 编号清单 | `1.` / `<li>` + 标题加粗 | 一个条目 = 一篇论文 |

记录：

- 标题列字段名
- 链接列字段名 / URL 模式
- 是否有「核心价值 / 关键贡献 / 指标 / 分类」字段（保留这些）
- 总论文数

向用户**口头确认**输出目录（默认 `./papers/`）和命名规范（默认带序号前缀）。

### Step 2: 解析出结构化论文列表

对每行 / 每个条目，按以下 schema 抽取：

```yaml
papers:
  - id: 1                  # 顺序编号，从 1 起
    title: "<论文标题>"
    slug: "<kebab-case-slug>"   # 见 references/folder-naming.md
    link: "<原始链接，优先 arXiv abs / ACL Anthology / DOI>"
    link_type: arxiv | acl | doi | github | webpage
    arxiv_id: "<XXXX.XXXXX>"  # 若可识别
    core_value: "<原表 核心价值字段>"   # 可选，原表有则保留
    key_contributions: "<原表 关键贡献字段>"   # 可选
    metrics: "<原表 价值指标字段>"   # 可选
    category: "<原表所属分类章节>"   # 可选
    application: "<原表应用场景>"   # 可选
```

**关键规则**：

- 标题要去掉 HTML 标签（如 `<span class="hl">`），保留文本
- 链接要从 `href` 属性抽取，不要保留 `<a>` 标签
- arxiv 链接要规整成 `https://arxiv.org/abs/<id>` 形式
- slug 生成要避免冲突（同标题不同年份加后缀）
- 原表中 `<span class="hl">` 标记的数字（如 `0.85`、`42.7%`）属于「关键区分度数值」，**必须保留**

### Step 3: 一次性创建所有目录

用一条 `Bash` 命令创建所有文件夹，避免循环调用：

```bash
mkdir -p <output_dir>/{01-slug-a,02-slug-b,03-slug-c,...}
```

完成后用 `ls` 校验目录数 == 论文数。

### Step 4: 并行抓取一手内容

按 `references/source-patterns.md` 决定抓取策略，对每篇论文调用一次 `WebFetch`：

| 链接类型 | 抓取目标 | prompt 模板 |
|---|---|---|
| arxiv | `https://arxiv.org/abs/<id>` | "Extract: title, full author list, complete abstract, submission date, last revised date, categories, project page URL" |
| arxiv HTML | `https://arxiv.org/html/<id>` | 同上 + "methodology highlights" |
| ACL Anthology | `https://aclanthology.org/<id>/` | "Extract: title, authors, abstract, venue, DOI, page numbers" |
| DOI（ICCV/CVPR/ACM） | 直接尝试 DOI URL，403 时退回 arxiv 镜像 | 同 ACL |
| OpenAccess CVF | `https://openaccess.thecvf.com/content/...` | "Extract: title, authors, abstract, venue, DOI" |
| GitHub | 仅抓项目 README 摘要 | "Extract: project description, dataset size, paper link" |

**并行度**：每批 3–6 篇同消息并发抓取，避免触发反爬。

**失败兜底**：若某篇抓取失败（如 403 / 超时），保留原表已有字段继续写入，标记 `fetch_status: failed`。

### Step 5: 写入 paper.md（并行）

按 `references/markdown-template.md` 的固定模板，对每篇论文调用一次 `Write`：

每篇 `paper.md` 必须有 6 个一级章节：

1. **基本信息**：标题、作者、年份、venue、arXiv/DOI、提交日期、分类、链接
2. **核心价值**：来自原表的策展视角
3. **关键贡献**：来自原表的策展视角
4. **摘要**：来自抓取的一手 abstract（英文原文）
5. **价值指标**：原表的「关键数值」保留为 `**加粗**` 高亮
6. **整理备注**：来源、类别、应用场景、fetch 状态

并行 `Write` 调用可放在同一消息，每批 5–7 篇为佳。

### Step 6: 生成 INDEX.md（可选）

在 `output_dir` 根目录写 `INDEX.md`，按原表的分类章节顺序，给出可点击的目录：

```markdown
# 论文目录索引

整理日期：YYYY-MM-DD ｜ 论文数：N ｜ 来源：<source_file>

## ① <章节名>
- [01-<slug>](01-<slug>/paper.md) — <论文标题> · <venue> · <arXiv id>

## ② <章节名>
- [02-<slug>](02-<slug>/paper.md) — ...
```

## 输出契约

每个 `paper.md` 必须满足：

- [ ] 一级章节顺序固定：基本信息 → 核心价值 → 关键贡献 → 摘要 → 价值指标 → 整理备注
- [ ] 基本信息含 8 个字段：标题、作者、年份、venue、arXiv/DOI、提交日期、分类、链接
- [ ] 摘要为原文 abstract，不翻译不省略
- [ ] 价值指标中关键数字用 `**bold**` 标记
- [ ] 末尾 `整理备注` 含来源出处与 fetch 状态
- [ ] 没有「待补充」「TBD」之类的占位符（除非确实需要）

## 质量门禁

完成所有写入后必须校验：

1. **目录数 == 论文数**：`ls | wc -l` 与源文档条目数一致
2. **每个目录都有 `paper.md`**：用 `find` 校验
3. **关键数值保留**：原表里 `**highlighted**` 的数字必须能在 paper.md 找到
4. **链接可达**：抽样 3 篇打开原链接验证（可在交付时报告）
5. **fetch 失败处理**：失败的论文 paper.md 不应空白，至少有原表策展字段

## 不做的事

- ❌ 不抓全文 PDF。WebFetch 拿 abstract + 元数据即可，全文 PDF 解析超出本 skill 范围
- ❌ 不翻译摘要。英文 abstract 原文保留，便于后续做文献综述
- ❌ 不评估论文质量。本 skill 只做「结构化抽取」，不做「评审」
- ❌ 不修改原表策展信息。原表的「核心价值/关键贡献/指标」是人工策展的，不应被覆写
- ❌ 不为同一篇论文创建多个文件夹（即使出现在多个章节，按首次出现归档，分类在 remarks 里补）

## 与其他 skill 的边界

| Skill | 何时用 | 与本 skill 的区别 |
|---|---|---|
| `deep-research` | 用户要研究一个问题，输出综合报告 | 本 skill 输入是现成的论文清单，输出是结构化语料 |
| `academic-rigor-review` | 用户要评审一篇论文的严谨性 | 本 skill 不评审，只抽取 |
| `markdown-to-styled-html` | 用户要把 markdown 渲染成 HTML 网页 | 本 skill 输出 markdown 文件，不是 HTML |

## 参考文件

- `references/markdown-template.md`：`paper.md` 完整模板与字段约定
- `references/folder-naming.md`：slug 生成规则与冲突处理
- `references/source-patterns.md`：arXiv / ACL / DOI / GitHub 的 URL 模式与抓取 prompt

## 示例

参考 `examples/sample-paper.md` 查看一篇完整 `paper.md` 的样板。
参考真实案例：`papers/` 目录下 21 篇论文（本 skill 由该流程抽象而来）。