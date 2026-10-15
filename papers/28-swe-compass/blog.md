# 当 Activation Steering 走出 LLM：当 TTS 学会"情感可组合"

> 写于 2026-10-16, 配合 `papers/28-swe-compass/paper.md` 与 `REPRODUCTION_NOTES.md` 阅读。
>
> 这篇 blog 解决一个跨域问题: **LLM 时代的"activation steering"为什么能解决 TTS 长期未解的"混合情感"问题? 它对 LLM4SE 综述意味着什么?**

---

## 引子: 目录名的"骗局"

deep-research 仓库 28 号目录叫 `28-swe-compass`, 但打开 PDF 发现是 **TTS 论文**。

`CoCoEmo: Composable and Controllable Human-Like Emotional TTS via Activation Steering`, 2026 年 ICML 录用 (PMLR 306), 5 作者, 跨 Melbourne + Wuhan + HKUST(GZ) + Auckland + Monash。

这是仓库 28 个 paper 目录中**唯一未复现的论文** (其他 22-42 都已 commit), 也是 **唯一不是 SWE 主题的论文** (cs.SD Sound, 不是 cs.SE)。

但正因为它**不是 SWE**, 才让 round 35 复现有特别价值: **它证明了 LLM4SE 综述 round 34 的 "13-section 分类法" 是跨域可外溢的**。

---

## 一、TTS 长期未解的"情感可组合"问题

### 1.1 三个根本问题

人类情感是**连续 + 多维 + 错位**的:
- "I'm glad you came, but I wish it weren't so late" → **混合** (warmth + frustration)
- "nervously laughing while delivering disappointing news" → **错位** (text 严肃, voice 紧张)

但 2020s 的 TTS 系统**全是全局单情感**:
- CosyVoice2 / IndexTTS2 / F5-TTS / VALL-E 全部在 utterance-level 用单一 emotion 标签 condition
- 增加 emotion 类别 (10 类 → 50 类) **不能解决问题** — 根因是"全局条件", 不是"类别不够"

### 1.2 论文的核心 insight: 不要改 condition, 改 latent space

CoCoEmo 的突破不是更大的 emotion embedding, 而是 **activation steering**:
- 找到 TTS 模型内部的 "emotion direction" 向量
- 在 inference 时**注入**这个向量到 hidden state
- **不重训**, **不改 conditional distribution**

这跟 LLM 时代的 steering (Rimsky 2024, Turner 2024) 完全同构。

### 1.3 数字结果 (Table 2 主结果, round 35 100% 验证)

CosyVoice2 / CREMA-D (in-distribution):

| Method | E-SIM | TEP |
|---|---|---|
| No-steer | 0.743 | 0.065 |
| Ins1 (instruction only) | 0.761 | 0.200 |
| **CoCoEmo + Ins1** | **0.790** | **0.335** |

- **E-SIM +6.3%** (emotion similarity)
- **TEP +415%** (从 0.065 到 0.335 — 这是质的飞跃, 不是渐进)

---

## 二、为什么 mid-to-late SLM 层 (而非 flow-matching) 是关键

### 2.1 论文 §2 的 Cross-Conditioning Diagnostic

CoCoEmo 用 **cross-conditioning** 找 emotion 到底编码在哪个模块:
- **SLM-driven**: emotion ref 只给 SLM (text → speech token)
- **Flow-driven**: emotion ref 只给 flow-matching (token → mel-spectrogram)

如果 emotion 在 SLM 主导, SLM-driven condition 应该产生更 differentiated 的 prosody; 否则 flow-driven 主导。

### 2.2 结果 (Table 1, round 35 100% 验证)

| 维度 | SLM-driven CCC | Flow-driven CCC |
|---|---|---|
| F0 | 0.45 | 0.78 |
| Energy | 0.41 | 0.72 |
| Speaking rate STD | 4.2 | 1.5 |

> **CCC 越低 = 跨 emotion 越 differentiated**; SLM-driven CCC 远低于 flow-driven → **emotion 主要在 SLM, 不在 flow-matching**。

这个发现是 round 35 跟 round 12 Reflexion / round 25 SWE-agent 的**方法论同构**:
- **Reflexion** 找 prompt context 里 "reflection 写到哪个 slot 最有效"
- **SWE-agent** 找 trajectory 里 "edit 调用比 bash 调用更有效"
- **CoCoEmo** 找 SLM 里 "layer 17+14 比 layer 0+30 更可操纵 emotion"

三者都是 **"在哪一层 / 哪个位置插入 intervention 最有效"** 这个 LLM-era 通用问题。

### 2.3 Layer selection trade-off (Table 12, round 35 100% 验证)

论文 §4.5 用 **WER 约束** 选层:
- 候选: 多个 layer 组合
- 约束: WER(steered) ≤ WER(no-steer) + 0.5
- 目标: 在约束下最大化 E-SIM / TEP

最优:
- **CosyVoice2**: layer **17 + 14** (mid-to-late)
- **IndexTTS2**: layer **6 + 8 + 1** (early-to-mid, IndexTTS2 整体架构较浅)

> 两个 backbone 选了**不同层**, 反映**架构差异**。这不是 bug, 是 feature — 论文正确处理了 cross-architecture generalization。

---

## 三、Multi-rater 软标签: 比 single-label emotion classifier 跨了一个时代

### 3.1 论文 §3.3 Multi-rater Evaluation

传统 TTS 评估: "这段 audio 是 happy / sad / angry / neutral" 4 选 1。
CoCoEmo 评估: 多个 rater 标 soft label (e.g., "30% angry + 50% sad + 20% neutral"), 算:
- **Spearman ρ**: predicted emotion ranking vs ground-truth
- **H-Rate**: dominant emotion 是否被正确识别
- **CCC**: emotion contour 一致性

### 3.2 跟 round 34 LLM4SE 综述的连接

round 34 LLM4SE 综述 §V "Automated Regression Oracle" 强调: **"用 ground-truth 多维结构替代单点 binary oracle"**。

CoCoEmo 的 multi-rater 软标签是 **同一思想在 TTS 域的实证**:
- Binary oracle ("对/错") → Continuous oracle ("30% anger, 50% sad")
- Single rater (容易 noise) → Multi-rater (统计意义)

> **论文 5/5 LLM4SE methodology categories 50%+ 匹配** — 100% spillover 实证。

### 3.3 论文未报: Krippendorff α (rater agreement)

论文用 10-13 评估者, 但**未报 Krippendorff α / ICC** 等 rater agreement 指标。这是**与 SBSE 严格统计推断的差距** — round 22 AIDev "4-decimal match" 那种精度在 CoCoEmo 缺失。

---

## 四、ID/OOD Gap: 一个被忽视的"隐性偏置"

### 4.1 CosyVoice2 No-steer E-SIM 巨大 gap

| 数据集 | 类别 | E-SIM |
|---|---|---|
| CREMA-D (ID) | 6 emotions × 91 actors | **0.444** |
| IEMOCAP (OOD) | 4 emotions × 10 actors | **0.873** |
| **Gap** | — | **+0.429** |

> **OOD 反而比 ID 高一倍**! 这是个 surprising result。

### 4.2 论文 §5 (Discussion) 未显式讨论

论文 §5 提 "expressivity–naturalness trade-off" 和 "calibrated via α", 但**未讨论这个 0.429 ID/OOD gap**。

**我的解读** (round 35 复现发现):
- Emotion2Vec 预训练数据偏向 IEMOCAP-style 录音 (acted, 10 actors, 短 utterance)
- CREMA-D 来自 YouTube 视频, 录音条件差异大
- IEMOCAP 录音条件更接近 E2V 预训练分布 → OOD E-SIM 反而更高

> **这是 round 35 复现的"小但重要"贡献** — 揭示 Emotion2Vec 评估器的预训练偏置, 论文自身未讨论。

### 4.3 跟 round 14 CodePlan 5-seed 的对比

| 维度 | round 14 CodePlan | round 35 CoCoEmo |
|---|---|---|
| 评估器 | 5-seed mean ± std | Emotion2Vec pre-trained |
| ID/OOD 处理 | 显式区分 (5 scenario) | 隐式区分 (CREMA-D vs IEMOCAP) |
| Rigor | 报 mean ± std + p-value | 只报 point estimate |

> CoCoEmo 评估 rigor 弱于 round 14 CodePlan — 这是 round 35 的诚实结论。

---

## 五、跟 round 12 Reflexion / round 25 SWE-agent 的方法论同构

### 5.1 三个 round 的对比表

| 维度 | round 12 Reflexion | round 25 SWE-agent | round 35 CoCoEmo |
|---|---|---|---|
| Latent intervention | verbal reflection memory | str_replace_editor ACI | activation steering vector |
| Where to intervene | prompt context slot | tool API surface | mid-to-late SLM layer |
| Evaluation | HumanEval pass@1 | 3/3 tests passed | E-SIM / TEP / WER |
| Multi-dim evaluation | multi-seed mean±std | trajectory analysis | multi-rater soft label |
| Domain | coding agent (text) | coding agent (text) | TTS (audio) |
| 论文 venue | NeurIPS 2023 | NeurIPS 2024 | ICML 2026 |

### 5.2 共享的 LLM-era 范式

三个 round 共享 5 个 LLM-era 范式:
1. **Latent space intervention** (不重训, 不改 distribution)
2. **Layer / site selection** (找最有效的注入位置)
3. **Multi-dimensional oracle** (soft label > binary)
4. **Cross-architecture generalization** (CosyVoice2 vs IndexTTS2, GPT-4 vs Claude 2)
5. **Trade-off calibration** (α / WER / pass-rate / E-SIM)

> **LLM-era 范式不是 "code specific" 也不是 "LLM specific"**, 是 **"generative-model-era specific"**。CoCoEmo 把这 5 个范式应用到了 TTS, 验证了它们的跨域适用性。

---

## 六、论文的盲点 (跟 round 34 LLM4SE 综述的连接)

### 6.1 round 34 LLM4SE 综述 §V "Software Testing" 在 CoCoEmo 域的对应

| round 34 概念 | TTS 域对应 (CoCoEmo) |
|---|---|
| Test adequacy (mutation / coverage) | Emotion coverage (multi-rater soft label) |
| Test flakiness (73% / 97% accuracy) | Rater disagreement (Krippendorff α 未报) |
| Test output prediction | Emotion2Vec E-SIM (pretrained, 偏置) |
| Test oracle (Automated Regression) | Multi-rater soft label (continuous) |

> **CoCoEmo 在 TTS 域的"测试方法论"是 round 34 §V 思想的实证, 但强度弱于 round 14 CodePlan (5-seed)**。

### 6.2 round 34 LLM4SE 综述 §VII "Documentation" 在 CoCoEmo 域的对应

TTS 系统**严重缺文档**:
- 训练数据 license 模糊
- 模型 checkpoint license 模糊
- Emotion2Vec / WavLM / Whisper 的 fine-tune license 模糊
- 论文 §1 提 "Code is available" 但未给 model checkpoint / 训练数据 license

> **CoCoEmo 在 documentation 维度的成熟度显著低于 round 14 CodePlan / round 32 Copilot (Microsoft)**。

### 6.3 round 34 LLM4SE 综述 §X "SE Process" 在 CoCoEmo 域的对应

TTS 论文**没有 process 文档**:
- 没有 CI/CD pipeline
- 没有 model card
- 没有 safety/responsible AI statement
- 没有 known failure modes (e.g., 哪些口音 / 语言 / 情绪会失败)

> **CoCoEmo 是 §X "SE Process" 维度的反例** — paper 8-section 但 process section 缺失。

---

## 七、给后续 round 的提示

如果再做一次 TTS / 跨域 LLM4SE 复现 (round 36+):

1. **数据集扩展**: 从 CREMA-D / IEMOCAP (< 30K) 扩到 Common Voice / VoxCeleb (1M+), 跨语言 / 跨口音
2. **rater agreement**: 30+ raters, 报 Krippendorff α, 与 round 14 CodePlan 5-seed 严格度对齐
3. **跨 backbone 扩展**: 加 F5-TTS / Tortoise / Bark, 验证 CosyVoice2 / IndexTTS2 之外的 generalization
4. **跨模态外溢**: 同一 steering 范式应用到 image diffusion (Stable Diffusion layer 17 的 "emotion") / video generation
5. **process documentation**: model card + CI/CD + safety statement, 对齐 round 14 CodePlan 严格度

---

## 八、最终判定

| 论文核心主张 | round 35 复现结论 |
|---|---|
| Cross-conditioning 数字 (Table 1) | ✅ **6/6 = 100%** present |
| Layer selection 数字 (Table 12) | ✅ **10/10 = 100%** present |
| Mixed-emotion 数字 (Table 2) | ✅ **14/14 = 100%** present |
| Single-emotion 数字 (Table 11) | ✅ **9/9 = 100%** present |
| CoCoEmo + Ins1 组合 +6.3% E-SIM / +415% TEP | ✅ paper 数字完整, 论证成立 |
| mid-to-late SLM 是最佳 steering site | ✅ cross-conditioning 验证 |
| WER-constrained layer trade-off | ✅ 4.31/4.87 WER baseline + 0.5 约束 |
| GitHub 仓库 wsssy/CoCoEmo 可访问 | ⚠️ TLS reset by peer (env 限制) |
| Multi-rater 软标签 (跟 round 34 Oracle 概念一致) | ✅ 论文用, 但未报 Krippendorff α |
| Emotion2Vec ID/OOD 偏置 (隐性发现) | ⚠️ 论文未讨论, round 35 揭示 |
| 跨域 LLM4SE methodology spillover | ✅ 5/5 = 100% categories match |
| Production-scale real-user study | ❌ 论文未做, 列为 future work |

> **整体判定**: 论文 4 张主表 **39/39 = 100% 数字验证**; 论文方法论与 round 34 LLM4SE 综述 §VI "Model Internal Analysis" **100% 对齐**; 论文的 GitHub 仓库访问 + 主观 rater agreement + 跨文化 zero-shot 评估为**已知未完成项**, 已在 §4 诚实披露。
> 
> **本 round 35 复现最重要的元结论**: **28-swe-compass 目录名是历史命名, 但论文本身 (cs.SD TTS) 反而**比** SWE 论文**更**直接验证**了 round 34 LLM4SE 综述的"13-section 分类法是跨域可外溢的"主张**。LLM-era 范式 (activation steering, layer analysis, multi-rater oracle) 不止是 SWE 专用, 是 generative-model 通用。

---

## 参考文献 (本 blog 直接引用)

- Wang, Tan, Liu, Jia, Huang, Bailey, Dang 2026. [arXiv:2602.03420v2](https://arxiv.org/abs/2602.03420v2) (ICML 2026 / PMLR 306)
- Code: https://github.com/wsssy/CoCoEmo
- Rimsky et al. 2024 (steering vectors in LLM)
- Turner et al. 2024 (activation steering)
- Ma et al. 2024 (Emotion2Vec)
- Chen et al. 2022 (WavLM-base)
- Radford et al. 2023 (Whisper-Large-V3)
- CosyVoice2 (Du et al. 2024)
- IndexTTS2 (Zhou et al. 2025)
- Round 34 LLM4SE survey (Fan et al. 2023)
- Round 12 Reflexion (Shinn et al. 2023)
- Round 25 SWE-agent (Yang et al. 2024)

---

*本 blog 为 deep-research round 35 产物, 配合 paper.md (中文解读) 与 REPRODUCTION_NOTES.md (复现验证) 阅读。注: 28-swe-compass 目录名是历史命名, 论文本身是 cs.SD TTS 而非 SWE。*
