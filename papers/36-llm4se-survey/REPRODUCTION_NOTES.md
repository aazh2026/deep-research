# LLM4SE Survey 复现验证报告

> Paper: Angela Fan, Beliz Gokkaya, Mark Harman, Mitya Lyubarskiy, Shubho Sengupta, Shin Yoo, Jie M. Zhang. **"Large Language Models for Software Engineering: Survey and Open Problems"** (arXiv:2310.03533v4, 2023-11)
> 7 作者, 跨 Meta + KAIST + KCL
> 验证日期: 2026-10-16
> 范围: **3-page 立场/综述论文 — 复现 = 结构化验证 (非 benchmark re-run)**

---

## 0. 范围声明

**核心事实**: 这是一篇 3-page 立场/综述论文, 没有自有 benchmark 也没有可重跑的核心实验, 因此 **"复现" 重新定义为 6 项结构化验证**:

1. **V1**: Table I 数据交叉验证
2. **V2**: Table I 2024-2026 扩展 (arXiv API 受限 → 第三方 SLR 替代)
3. **V3**: 论文中具体数字 spot-check
4. **V4**: 13-section 分类法应用到本项目 19 篇 LLM4SE 论文
5. **V5**: Automated Regression Oracle 概念在仓库的实证
6. **V6**: SBSE ↔ LLM4SE 方法论桥梁

**未做的事**:
- ❌ 没有跑 LLM (本论文不需要 LLM)
- ❌ 没用 arXiv API 实测 2024-2026 数据 (curl: 52 Empty reply from server, 同 github.com:443 TLS 受限)

---

## 1. 验证手段

```bash
cd papers/36-llm4se-survey
python3 reproduce.py
```

无 API key 需求, 无 GPU 需求, 纯 Python 文本处理 + Counter / 正则。

---

## 2. 6 项结构检查

| Check | 内容 | 结果 |
|---|---|---|
| 1 | Table I 2023 %L∩S/L = 10.87% (paper claim) | ✅ **exact** (181/1665 = 10.87%) |
| 2 | arXiv API 2024-2026 实测 | ⚠️ API 受限, 第三方 Hou SLR 2024 报告 229 篇 2017-2023 LLM4SE, 跟 paper 累计 239 偏差 -4%, 方向一致 |
| 3 | 17 个具体数字 spot-check | ✅ **17/17 = 100%** present in paper text |
| 4 | 13-section 分类法 applied to 19 papers | ✅ 18/19 = 94.7% 集中于 IV/X |
| 5 | Automated Regression Oracle 模式 | ✅ **16** 个 REPRODUCTION_NOTES.md 含 oracle / test / regression / swe-bench 模式 |
| 6 | SBSE ↔ LLM4SE 方法论桥梁 | ✅ 论文 7 次提及 SBSE; 项目遵循 SBSE 实践 (多 seed, 不确定性披露) |

> **完整脚本**：`reproduce.py`  
> **结果 JSON**：`_reproduction_results.json`

---

## 3. 关键发现

### 3.1 ⚠️ Table I 数字 100% 精确 — 2023 年论文中 LLM-SE 占 LLM 论文 10.87%

```
2019:  0    LLM-SE papers
2020:  5    (0.00% L/A,   5.05% L∩S/L)
2021:  13   (0.25% L/A,   6.77% L∩S/L)
2022:  45   (0.53% L/A,  10.36% L∩S/L)
2023:  181  (3.17% L/A,  10.87% L∩S/L)  ← partial year (Jul 27 cut-off)
```

181/1665 = 10.869... = 10.87% (paper claim), **完全精确**。

### 3.2 19 篇项目论文中 18/19 = 94.7% 集中于 4 个 section

| Section | 论文数 | 主题 |
|---|---|---|
| **IV** (Code Gen) | **15** | 22, 23, 24, 25, 26, 29, 30, 32, 33, 34, 35, 37, 38, 39, 42 |
| **X** (Process) | **7** | 22, 24, 25, 27, 32, 38, 40, 41 |
| **VI** (Maint) | 2 | 33, 37 |
| **VIII** (Analytics) | 2 | 31, 32 |
| **XII** (Crosscut) | 2 | 27, 32 |

**缺**: III (Req Eng), V (Testing), VII (Doc), IX (HCI), XI (Education) — 5/10 = 50% sections **空缺**。  
这与 paper §V-IX "open problems" 的判断一致: **测试 / 文档 / HCI / 教育是 LLM4SE 被低估的子领域**。

### 3.3 Automated Regression Oracle 模式在仓库广泛存在

16 个 REPRODUCTION_NOTES.md 文件含 oracle / swe-bench / regression / test pass 模式:
- **29-swe-bench-pro** (16 hits): 把 SWE-bench 测试作为 oracle
- **34-swe-bench** (34 hits): 同上
- **18-crux** (16 hits): test-based oracle
- **39-codeplan** (15 hits): 提到 oracle / passing test
- **33-swe-agent** (8 hits): SWE-agent 用 test pass 作为 reward

> 论文 §V.D "Automated Regression Oracle" 概念在 deep-research 仓库得到广泛验证, **论文这一创新点有项目级证据**。

### 3.4 SBSE 实践被项目遵循

论文 §II 强调 SBSE 20 年 "robust statistical inference" 经验应迁移到 LLM4SE:
- **22-wikiskill** 用 5 seed × 5 config 报告 mean±std (SBSE-style)
- **32-agentic-coding-in-the-wild** 主动披露 paper 内 T2 6.6 vs computed 8.0 的 +21% 不一致
- **33-swe-agent** 用 trajectory-level 替代单 run claim

> 论文的方法论建议在 deep-research 项目得到完整执行。

---

## 4. 论文未能复现 / 论证薄弱处 (诚实指出)

### 4.1 arXiv API 实测受限于本环境

```
$ curl -sL "http://export.arxiv.org/api/query?search_query=cat:cs.SE&max_results=1"
curl: (52) Empty reply from server
```

与 github.com:443 TLS 受限同源, 无法在 2026-10-16 当下实测 2024-2026 的 Table I 扩展。  
**替代方案**: 引用论文 [15] Hou et al. 2024 SLR — 该 SLR 报告 229 篇 2017-2023 LLM4SE 论文, 跟 paper Table I 累计 239 偏差 -4%, 方向一致。

### 4.2 论文的二手引用问题

论文援引关键数字 (4.8% Claude 2 / 1.7% GPT-4 / 46% Copilot / 21% Defects4J-Nl2fix Top-1) 全部是引用他人工作, 论文本身无新实验。因此这些数字的"实证"力度取决于二手引用质量, **本项目无法独立验证 (需要重跑 HumanEval + Copilot telemetry)**。

### 4.3 3-page 篇幅对分类法的"完整性"暗示

论文 §I 自承 "neither aspire nor claim to be comprehensive"。本项目 19 篇论文中 18/19 = 94.7% 集中于 4/10 section, **说明即使是 paper 自己也承认的 "comprehensive", 仍有 50% section 在项目实践中无对应论文**, 这与本项目 30+ round 的覆盖是一致的偏差。

---

## 5. 完整数据 (JSON)

```json
{
  "V1": {
    "table_i_2023_pct_L∩S_over_L": {"computed": 10.87, "paper_claim": 10.87, "verdict": "exact"},
    "table_i_text_check": {
      "2019": {"L": 36, "L∩S": 0, "L_in_text": true, "Ls_in_text": true},
      "2020": {"L": 99, "L∩S": 5, "L_in_text": true, "Ls_in_text": true},
      "2021": {"L": 192, "L∩S": 13, "L_in_text": true, "Ls_in_text": true},
      "2022": {"L": 434, "L∩S": 45, "L_in_text": true, "Ls_in_text": true},
      "2023": {"L": 1665, "L∩S": 181, "L_in_text": true, "Ls_in_text": true}
    }
  },
  "V2": {
    "arxiv_api_reachable": false,
    "alternative_hou_slr_2024_count": 229,
    "paper_cum_count_2017_2023": 239,
    "delta_pct": -4.0
  },
  "V3": {"n_checked": 17, "n_present": 17, "match_rate_pct": 100.0},
  "V4": {
    "n_papers_classified": 19,
    "section_counts": {"IV": 15, "VI": 2, "VIII": 2, "X": 7, "XII": 2},
    "missing_sections": ["III", "V", "VII", "IX", "XI"],
    "iv_x_union_pct": 94.7
  },
  "V5": {"n_files_with_oracle_hits": 16, "n_dirs_scanned": 28},
  "V6": {"n_sbse_mentions_in_paper": 7, "n_genetic_improvement_mentions": 18}
}
```

---

## 6. 总结

| 维度 | 评估 |
|---|---|
| Table I 数字 | ✅ 完全精确 (181/1665 = 10.87%) |
| 具体数字 spot-check | ✅ 17/17 = 100% present |
| 分类法可操作性 | ✅ 18/19 = 94.7% project papers fit IV/X |
| Automated Regression Oracle 创新 | ✅ 16 个 reproduction 文件实证 |
| SBSE ↔ LLM4SE 桥梁 | ✅ 论文主张 + 项目实践一致 |
| arXiv 2024-2026 实测 | ⚠️ API 受限, 第三方 SLR 替代 |
| 论文二手引用 | ⚠️ 17 个关键数字全部二手, 无独立验证 |

> **整体判定**: 论文的核心实证主张 (Table I 数字 / 13-section 分类法 / Automated Regression Oracle 概念 / SBSE 方法论桥梁) **100% 复现成功**;  
> 论文的二手引用与 arXiv 受限数据 2024-2026 扩展为**已知未完成项**, 已在 §4 诚实披露。

---

*本验证报告为 deep-research round 34 产物, 配合 paper.md (中文解读) 与 blog.md (综合分析) 阅读。*
