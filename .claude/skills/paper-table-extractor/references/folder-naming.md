# 文件夹命名规范

每个论文文件夹的名字由「**序号 + slug**」组成：`NN-<slug>`。

## 命名格式

```
NN-<slug>/
```

- `NN`：两位数字（01–99），按原表的章节顺序 + 章节内出现顺序连续编号
- `-`：半角连字符
- `<slug>`：论文标题的 kebab-case 形式

## slug 生成规则

1. 取论文标题，**去掉标点与特殊字符**：`! ? : ; , . ( ) [ ] { } " '` 等
2. 转小写
3. 空格 / 多个空白 → 单个 `-`
4. 缩写词保留：`RAG`、`VQA`、`DocVQA`、`CRUX`、`ColPali`、`M3D` 维持大写
5. 长度上限：60 字符；超过则截断到最后一个完整词

### 示例

| 原标题 | slug |
|---|---|
| `DocVQA: A Dataset for VQA on Document Images` | `docvqa` |
| `ChartQA: A Benchmark for QA about Charts with Visual and Logical Reasoning` | `chartqa` |
| `Hierarchical Multimodal Transformers for Multi-Page DocVQA (MP-DocVQA)` | `mp-docvqa`（缩写优先） |
| `InfographicVQA` | `infographicvqa` |
| `Towards Complex Document Understanding By Discrete Reasoning (TAT-DQA)` | `tat-dqa` |
| `Document Understanding Dataset and Evaluation (DUDE)` | `dude` |
| `Scaling Beyond Context: A Survey of Multimodal RAG for Document Understanding` | `multimodal-rag-survey` |
| `MME-Survey: A Comprehensive Survey on Evaluation of Multimodal LLMs` | `mme-survey` |

## 冲突处理

同一论文在原表中出现在多个章节时，**按首次出现归档**：

- 例如 `SlideVQA` 若同时出现在「多页」和「演示文稿」两个章节，文件夹只在多页章节建
- 在 `整理备注` 中补充「亦见 XX 章节」

不同论文 slug 重名时，附加短后缀：

- 第一篇：`05-chartqa`
- 第二篇同年：`05b-chartqa-extended`

## 序号分配

按原表章节顺序分配序号，不按字母排序：

```
① 综述 → 01, 02
② 单页 VQA → 03, 04, 05
③ 图表与表格 → 06, 07, 08
④ 多页/长文档 → 09, 10, ..., 14
⑤ 多模态 RAG → 15, 16, 17
⑥ 自动判分 → 18, 19, 20, 21
```

序号在 `INDEX.md` 中作为显示编号。

## 不允许的命名

❌ 中文 slug（`文档解读-综述`）— 跨平台兼容性差
❌ 大写 / 驼峰（`DocVQA`）— 与小写风格冲突
❌ 含 arXiv ID（`05-infographicvqa-arxiv-2104-12756`）— ID 在 paper.md 里已记录
❌ 含年份（`05-infographicvqa-2022`）— 年份在 paper.md 里已记录
❌ 太长（`05-towards-complex-document-understanding-by-discrete-reasoning`）— 用缩写 `tat-dqa`

## 输出目录

默认输出目录：`./papers/`（与源文档同级目录）

用户可指定其他路径，如 `./corpus/2026-10/`、`./literature/`。

每篇论文的 `paper.md` 路径：

```
<output_dir>/<NN>-<slug>/paper.md
```