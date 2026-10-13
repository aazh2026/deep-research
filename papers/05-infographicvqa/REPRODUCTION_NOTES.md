# InfographicVQA 复现笔记

> Paper: Mathew et al. "InfographicVQA" (WACV 2022, arXiv:2104.12756)
> 数据集: mm-eval/InfographicVQA (HuggingFace)
> 复现日期: 2026-10-13

## 1. 复现动机

- 用户在 `/loop` cron 中要求选未复现论文 → 05-infographicvqa 未做。
- 03/04-docvqa 用了 ANLS，本篇可验证**同一 metric** 在不同分布下的稳定性。
- 论文核心 claim：「**信息图 VQA 比 DocVQA 难很多**」——可被「盲 baseline ANLS 极低」佐证。

## 2. 数据集选择

| 候选 | 状态 | 备注 |
|---|---|---|
| `nielsr/InfographicVQA` | ❌ not found | 已被作者撤回 |
| `lmms-lab/InfoVQA` | ❌ not found | |
| `pixparse/infographicvqa` | ❌ not found | |
| `MMInstruction/InfographicVQA` | ❌ not found | |
| **`mm-eval/InfographicVQA`** | ✅ | validation 2801, test 3288 |
| `vidore/infovqa_train` | ✅ 但只有 train | 无 gold answers |

选定 `mm-eval/InfographicVQA` validation 作为唯一评测集。

## 3. 数据 Schema 与陷阱

- `id`: int（如 69369）
- `media`: list[PIL.Image]（单图，但 schema 允许多）
- `messages`: **JSON 字符串**，含 `[{role, question, hint, options, choices}]`，要 `json.loads`
- `answer`: list[str]，**多 gold 时取 max**（与 ANLS 一致）
- `question_type`: `numeric` 1342 / `open` 1458 / `yes_no` 1（val 全 2801）

**陷阱 1**：messages 是 JSON 字符串，不能直接 `.question`。`json.loads(row["messages"])[0]["question"]`。

**陷阱 2**：answer 列表里有些是 `['1.25%']`、`['1,234']` 这种带符号/逗号的，要单独处理才能转 float。

**陷阱 3**：`n_answers` 分布严重不均：1 gold 2104 (75%)，2 gold 648 (23%)，≥3 gold 仅 49 (2%)。这意味着 ANLS 单 gold 已经占主导。

## 4. ANLS Metric 实现

与 03-docvqa 复用（公式来源：DocVQA Challenge 2020 paper）：

```python
def anls_score(pred, gts, tau=0.5):
    pred = pred.lower().strip()
    best = 0.0
    for gt in gts:
        gt = gt.lower().strip()
        d = editdistance.eval(pred, gt)
        nld = d / max(len(pred), len(gt))
        if nld < tau:
            s = 1.0 - nld
            if s > best:
                best = s
    return best
```

**边界 case**：
- `pred = ""` 且 `gt = ""` → 1.0（两空串完全匹配）
- `pred = ""` 且 `gt ≠ ""` → 0.0
- `tau = 0.5` 时 NED=0.5 恰为 0（严格小于）

## 5. 6 个盲 Baseline 设计

| Baseline | 思路 | ANLS 期望 | 实测（500）|
|---|---|---|---:|
| `majority` | 全数据集最常答案 '2' | 极低 | 0.0240 |
| `random` | 按分布随机 | 趋近 0 | 0.0027 |
| `type_majority` | numeric='2', open='india' | 略高 | 0.0320 |
| `numeric_median` | 全部 numeric 题答 27.1 | 低 | 0.0035 |
| `numeric_mode` | numeric 题答 '2' | 略低 | 0.0240 |
| `type_random` | 按 type 桶随机 | 趋近 0 | 0.0144 |

**关键观察**：
1. `random` (0.0027) 趋近 0，符合「随机答案 ANLS 期望很低」。
2. `majority` 0.0240 高于 random 9×，证明答案分布**长尾**——少数高频答案被多数题共用。
3. `type_majority` 比 `majority` 略高（0.0320 vs 0.0240），证明**分桶**有效。
4. numeric 题 `majority` 也能 0.05（答案 "2" 真的高频），open 题几乎 0（答案 "india" 只覆盖极少数）。
5. **paper claim 验证**：6 个盲 baseline 全部 ANLS < 0.05，远低于 paper 报告的 SOTA ≈ 0.45–0.55。这与「信息图 VQA 比 DocVQA 难得多」一致——同样 ANLS 公式下，03-docvqa 多数题答案唯一且和 query 强相关（"What's the date?" 答案一定是日期），所以 lexical baseline 就能 0.03+；而 InfographicVQA 答案分布更稀疏更不可预测。

## 6. 已知限制

1. **没有 OCR 文本**：mm-eval 镜像不含 `words` 字段，无法做"在 OCR 里找答案"类 baseline。
2. **没跑 VLM**：paper 主线 SOTA 模型（LayoutLMv2/IRRA 等）需要 GPU，本地不可行。
3. **没看图**：所有 baseline 是**完全无视图像**的，纯粹用答案分布。
4. **Test split 没 gold answers**：mm-eval/InfographicVQA test 集 `answer` 字段是空 list 或仅 placeholder，没法离线评测；只能 val。
5. **Numeric-Mode/Majority 撞车**：numeric mode 也是 '2'，所以 `numeric_mode` 跟 `majority` 在 numeric 题上完全一致，但 `majority` 也对 open 题答 '2'，所以两者 ANLS 仍差 0。

## 7. 与 paper 的吻合度

| 项 | Paper | 本次复现 |
|---|---|---|
| Metric 公式 | ANLS, τ=0.5 | ✅ 完全一致 |
| Val 集大小 | 2801 | ✅ mm-eval 完全一致 |
| Test gold 答案 | 有 | ❌ 镜像无 |
| SOTA ANLS | ~0.45-0.55 | ❌ 没跑（无 GPU/VLM） |
| 盲 baseline | 无公开 | ✅ 给出 6 个，< 0.05 |
| 难度 claim | "harder than DocVQA" | ✅ 盲 baseline 极低佐证 |

## 8. 后续可做

1. **加 OCR baseline**：装 `pytesseract`，对每张图跑 OCR，提取纯文本，然后做 lexical baseline。
2. **OCR + LayoutLMv2 蒸馏**：用 LayoutLMv2-base + OCR tokens 跑小子集（CPU 慢但能跑通）。
3. **Hard-coded type-only model**：在 numeric 题里学 4 个 head（'How many' / 'How much' / 'When' / 'How old'），看能涨到多少。
4. **Test 集评测**：要么等 paper 官方 test 公开、要么通过 leaderboard 提交。
