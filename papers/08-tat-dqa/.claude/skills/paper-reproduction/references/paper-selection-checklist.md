# Paper Selection Checklist

Before writing any code, decide if the paper is actually reproducible in your environment. This is faster than discovering the problem after 1000 lines of code.

## Hard Filters (must pass all)

### 1. Architecture is described in enough detail to implement

- ✅ Pass: paper has equations for losses, figures for heads, pseudo-code for decode
- ⚠️ Maybe: paper has a referenced GitHub repo with code (then you can use that as ground truth)
- ❌ Fail: paper says "we use a novel architecture" without specifics, or refers to unreleased code

### 2. Dataset is publicly downloadable

- ✅ Pass: dataset on HF Hub, official GitHub, or institutional URL with no auth required
- ⚠️ Maybe: dataset requires signing a license / DUA (count this as 2-3 hours of process)
- ❌ Fail: "we collected our own dataset", proprietary, paywalled, requires partnership

**Verify before committing**: do a `curl -I` to the data URL and confirm 200. If 404 or auth wall, stop.

### 3. Trainable on local hardware in hours, not days

- ✅ Pass: <50M params, <1M training samples, <10 epoch
- ⚠️ Maybe: 100-500M params with public smaller backbone, can downscale
- ❌ Fail: 1B+ params, full data only, 50+ epoch expected

**Rule of thumb**: if the paper's original training was on 8x A100 for a week, do not promise to reproduce on a laptop.

### 4. Has a comparable baseline

- ✅ Pass: paper has a "Simpler Baseline" or "Prior Work" table with numbers on the same dataset
- ❌ Fail: paper only has "SOTA" claims, no other models on the same eval

Without a baseline, you can't tell if your reproduction is "close to the paper" or "the paper's number is the only anchor".

## Soft Filters (consider these)

### 5. Reproducibility signals

- ✅ Paper has reproducibility checkbox marked in the venue (NeurIPS, ICML)
- ✅ Code released on GitHub
- ✅ Checkpoints released
- ✅ Hyperparameters in appendix

### 6. Architectural novelty vs engineering effort

- **High novelty / low engineering** papers are great: focus is the idea, code is small
- **Low novelty / high engineering** papers are risky: lots of code to write, modest insight

### 7. Domain relevance

Is this paper's domain something the user cares about? Reproducing a paper you have zero context for is hard — even small questions about evaluation conventions become research detours.

## Decision Matrix

| Hard Filters | Verdict |
|---|---|
| All 4 pass | Reproduce |
| 1 fails | Stop. Tell the user. |
| 2-3 fail | Stop. Tell the user. |
| 4 fails | Risky. Ask the user if they want a "close-enough" reproduction without baseline comparison. |

## Examples (TAT-DQA style)

| Paper | Filters | Verdict |
|---|---|---|
| TAT-DQA / MHST | All pass, JSON on GitHub, RoBERTa-base works, TagOp baseline | ✅ Reproduce |
| DocVQA | Dataset is images, models need vision-language pretraining | ❌ Stop (or do text-only ablation) |
| GPT-4 evaluation paper | Closed model, proprietary | ❌ Stop |
| LoRA paper | All pass, small models, public data | ✅ Reproduce |
| A paper on internal Google data | Dataset inaccessible | ❌ Stop |
| Multi-node RL training | Hardware | ❌ Stop (or do single-node version) |

## What to say when stopping

Be direct. Don't write a half-implementation.

> 这篇论文 [specific reason] 不适合本地复现：[数据不可下载 / 模型规模过大 / 没有公开代码]。建议改选 [alternative paper] 或 [less ambitious version]。
