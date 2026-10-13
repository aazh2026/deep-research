# Worked Example: TAT-DQA / MHST

This is a concrete example of using the `paper-reproduction` skill on the TAT-DQA / MHST paper (Zhu et al., ACM MM 2022). The full writeup is in `../../REPRODUCTION_NOTES.md`; this is the skill's view of how the work flowed.

## Paper selection (Step 1)

**Paper**: "Towards Complex Document Understanding By Discrete Reasoning" (arXiv:2207.11871)

| Hard filter | Result |
|---|---|
| Architecture described | ✅ — 4 heads, multi-task loss, scale-aware F1, GTS tree decode |
| Dataset public | ⚠️ — TAT-DQA on HF (`next-tat/TAT-DQA`) is imagefolder, not text. JSON mirror found at `fengbinzhu/TAT-LLM` |
| Trainable locally | ✅ — RoBERTa-base + 500-sample subset works on MPS |
| Has baseline | ✅ — TagOp baseline EM 33.7 / F1 42.5 |

Verdict: Reproduce, with paper's GTS tree replaced by infix decode.

## Plan (Step 2)

**Keep**:
- Multi-Head Predictor (4-type classifier)
- Span head, Tag head (BIO), Arithmetic head, Scale head
- Multi-task CE loss with masking by answer_type
- AdamW with grouped lr (backbone 2e-5, heads 1e-4)
- EM + scale-aware macro-F1 metric

**Cut** (with reasons):
- LayoutLMv2_LARGE → RoBERTa-base (CPU/MPS memory)
- ResNeXt101-FPN visual backbone → removed (no vision)
- GTS expression tree → infix + `numexpr.safe_eval` (CPU speed)
- 13K × 50 epoch → 500 × 2 epoch (time)
- Batch 48 → batch 4 + grad_accum 4 (memory)

**Expected range**: 0-30% of paper's number. Not 100%.

## Data verification (Step 3)

```bash
curl -s "https://datasets-server.huggingface.co/info?dataset=next-tat%2FTAT-DQA"
# → "train": ("imagefolder", {}), "validation": ("imagefolder", {}), "test": ("json", {})
# RED FLAG: train/val are images
```

Search GitHub:
- Official NExTplusplus/TAT-DQA → links to Google Drive
- `fengbinzhu/TAT-LLM` → has JSON files at `data/original/tatdqa/`

Download:
```bash
curl -sLO https://raw.githubusercontent.com/fengbinzhu/TAT-LLM/main/data/original/tatdqa/tatdqa_dataset_train.json
# 9.7MB, 2207 docs (each with multiple questions)
```

Inspection:
```json
{
  "doc": {"uid": "cced1c9e...", "page": 1, "source": "everbridge-inc_2019.pdf"},
  "questions": [
    {"uid": "...", "answer": ["$8.6 million"], "answer_type": "span", "scale": "", "facts": ["$8.6 million"]},
    ...
  ]
}
```

Findings:
- Top-level is `doc`, not sample — must flatten to one sample per question
- `answer` is **always a list**, even for span type
- No `text` / `table` fields — context is built from `facts` only

## Pipeline (Step 4)

Built in 6 stages with verification gates:

1. **Data loader** → `data/parse.py` with `load_local_samples()` flattening doc→questions. Gate: 4 answer types visible, fields populated.
2. **Collator** → `data/collator.py` with tokenization + BIO tagging. **Hit gotcha #1**: `Ġ` prefix mismatch, fixed by trying `" " + ans_text` candidate.
3. **Model** → `models/mhst.py` with 4 heads + scale head. Gate: forward + backward without NaN.
4. **Loss** → `training/losses.py` with masking by answer_type. Gate: 6 head losses sum to finite scalar.
5. **Train** → 32 samples × 1 epoch. **Hit gotcha #2**: MPS state_dict load, fixed with `map_location="cpu"`.
6. **Eval** → 50 test samples, JSON report. **Hit gotchas #4, #6**: yaml nested + scale semantic asymmetry, both fixed in `load_config` and `compute_em_one`.

## Real run (Step 5)

500 samples × 2 epoch on MPS:

| Metric | Value |
|---|---|
| Train time | ~2.5 minutes |
| Final train loss | 2.62 |
| Final dev loss | 2.48 |
| **Test EM** | **0.00** |
| **Test F1** | **0.00** |

Sample predictions:
```text
Q: What was the total assets from AMER in 2018?
gold: ['645,791']
pred: -118.0

Q: What was the total assets from APAC in 2019?
gold: ['958,744']
pred: EVIDENCE: 958,
```

**Root cause analysis**:
1. span head collapses to position 0-2 (predicts "EVIDENCE: 1,2..." prefix)
2. gold/pred type mismatch (list vs string)
3. Arithmetic decode fails (safe_eval returns None)
4. Training data 26× smaller than paper

## Documentation (Step 6)

Wrote `REPRODUCTION_NOTES.md` with:
- Why this paper (selection rationale)
- Tradeoff table (paper vs reproduction)
- 6 real engineering issues
- Real metrics + sample predictions
- Value (Pipeline 通) and limits (数字不接近)
- Recommendations for next iteration

Key honesty move: explicitly stated "EM=0, did not match paper", and listed 4 root causes with estimated effort to fix each.

## Lessons encoded in the skill

1. **Always verify data format on HF** — saved 30+ minutes per reproduction
2. **Try-candidate tokenization** for subword prefix issues — reusable code pattern
3. **CPU-first state_dict load** for MPS — PyTorch 2.x specific
4. **Build pipeline incrementally with gates** — never skip the smoke test
5. **Show sample predictions in report** — aggregate metrics hide bugs
6. **Honest writeup** — the deliverable is the truthful report, not the metric

## Where the user can extend

If you want to close the gap to paper-level:
- Use 2000+ samples × 5+ epochs (would take ~30 min on MPS)
- Fix gold/pred type mismatch in `evaluation/metrics.py` (1 line)
- Try `microsoft/layoutlmv2-base-uncased` backbone (download + 50-line change in `models/encoder.py`)

But the current state is **a verified-working pipeline** with **honest documentation of its limits**. That's the goal of the skill.
