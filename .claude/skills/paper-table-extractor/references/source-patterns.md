# 来源 URL 模式与抓取策略

本 skill 抓取「原文一手元数据」而非全文 PDF。每种来源对应一个固定的 URL 模式和 prompt 模板。

## 优先级

抓取优先级从高到低：

1. **arXiv abs 页面** — 最稳定，元数据最完整
2. **arXiv HTML 全文** — 含方法节选（仅在前者信息不足时使用）
3. **ACL Anthology** — 顶会论文，有完整 BibTeX
4. **OpenAccess CVF** — ICCV / CVPR / WACV 论文
5. **ACM DL** — ACM MM 等
6. **GitHub 项目页** — 仅在论文页都不可访问时兜底

## 1. arXiv

### URL 模式

| 原表链接形式 | 抓取 URL |
|---|---|
| `https://arxiv.org/abs/XXXX.XXXXX` | 原样 |
| `https://arxiv.org/html/XXXX.XXXXX` | 用 abs 形式更稳定 |
| `arXiv:XXXX.XXXXX`（无 URL） | 构造 `https://arxiv.org/abs/XXXX.XXXXX` |
| `https://arxiv.org/pdf/XXXX.XXXXX` | 改用 abs 形式（PDF 难解析） |

### prompt 模板

```
Extract the complete paper information: title, full author list (all authors),
complete abstract, submission date, last revised date (if any), arXiv categories,
and any project page / GitHub link mentioned. Format as clean markdown.
```

### 期望返回字段

- `title`
- `authors`（完整列表，含姓名顺序）
- `abstract`（完整原文）
- `submission_date`（YYYY-MM-DD）
- `last_revised`（YYYY-MM-DD）
- `categories`（cs.CV, cs.CL, ...）
- `project_page`（URL）

### 已知问题

- `https://arxiv.org/abs/<id>` 在某些网络环境下 403
- **备用方案**：构造 ar5iv mirror `https://ar5iv.labs.arxiv.org/html/<id>` 二次抓取

## 2. ACL Anthology

### URL 模式

| 原表链接形式 | 抓取 URL |
|---|---|
| `https://aclanthology.org/2022.findings-acl.177/` | 原样 |
| `DOI:10.18653/v1/2022.findings-acl.177` | 构造 ACL Anthology URL |

### prompt 模板

```
Extract: title, full author list, complete abstract, venue (e.g. Findings of ACL 2022),
page numbers, DOI, and any project page link.
```

## 3. DOI（OpenAccess CVF）

### URL 模式

| 来源会议 | URL 模板 |
|---|---|
| ICCV / CVPR / WACV / ECCV | `https://openaccess.thecvf.com/content/<CONF><YEAR>/html/<author>_<slug>_<CONF>_<YEAR>_paper.html` |
| ACM MM | `https://dl.acm.org/doi/10.1145/<doi-suffix>` |

### 已知 403 问题

OpenAccess CVF 经常对自动化请求返回 403。

**备用方案**：通过 arXiv 镜像抓取（如 `https://arxiv.org/abs/<id>`）—— 通常 ICCV/CVPR/WACV 论文有 arXiv 预印本。

### prompt 模板

```
Extract: title, full author list, complete abstract, conference name and year,
DOI, and project page URL if available.
```

## 4. GitHub 项目页

仅在前述来源都失败时使用：

### URL 模式

- `https://github.com/<owner>/<repo>`

### prompt 模板

```
Extract: project description, paper title and link if shown in README,
dataset size, model checkpoints availability.
```

### 限制

- GitHub README 信息通常**不足以替代论文 abstract**
- `fetch_status` 应标记为 `partial`

## 失败兜底（fetch_status）

| 状态 | 触发条件 | paper.md 处理 |
|---|---|---|
| `success` | 抓取到 abstract + 至少 3 个元数据字段 | 正常填充 |
| `partial` | 抓取到部分字段，或仅 README 信息 | 缺字段标 `（无）`，保留 abstract |
| `failed` | 完全抓取失败（403 / 超时 / 不存在） | 仅靠原表数据，abstract 段可写「原表未提供摘要」 |

## 并行抓取建议

WebFetch 每批建议 3–6 篇同消息并发：

- 太少：浪费时间
- 太多：触发 arxiv 反爬限速

每批完成后校验返回值，失败项加入重试队列（最多重试 1 次，仍失败标 `failed`）。

## URL 规整工具函数

下列 URL 模式需要在 extraction step 做规整：

```python
# 伪代码
def canonicalize_url(raw: str) -> tuple[str, str]:
    """返回 (canonical_url, link_type)"""
    if 'arxiv.org/abs/' in raw:
        return raw, 'arxiv'
    if 'arxiv.org/html/' in raw:
        # 改成 abs 形式
        id = raw.split('/html/')[1].rstrip('/')
        return f'https://arxiv.org/abs/{id}', 'arxiv'
    if 'arxiv.org/pdf/' in raw:
        id = raw.split('/pdf/')[1].rstrip('.pdf')
        return f'https://arxiv.org/abs/{id}', 'arxiv'
    if 'aclanthology.org' in raw:
        return raw, 'acl'
    if 'openaccess.thecvf.com' in raw:
        return raw, 'cvf'
    if 'github.com' in raw:
        return raw, 'github'
    if raw.startswith('10.'):  # 裸 DOI
        return f'https://doi.org/{raw}', 'doi'
    return raw, 'webpage'
```

实际执行时不需要写代码，直接在 schema 抽取阶段人肉/启发式规整即可。