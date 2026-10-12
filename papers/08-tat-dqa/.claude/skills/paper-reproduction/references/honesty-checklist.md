# Honesty Checklist for Reproduction Reports

The hardest part of a reproduction report is not the implementation — it's writing down what actually happened. This checklist prevents the most common forms of self-deception.

## Before writing the report

### Are the numbers real?

Every metric in your report must be from a real run. Cross-check:

```bash
# Open the metrics.json and the log
cat outputs/test_metrics.json
cat outputs/metrics.json  # training history
```

If the number you want to report isn't in either of these files, **don't report it**.

### Did you cherry-pick?

If you ran 5 experiments and the report only mentions the best one, that's misleading. List all 5 with brief outcomes.

### Did you change the metric to make it look better?

If your F1 is 0.05 and you switch from F1 to "top-1 accuracy" to get 0.30, that's a problem. Report the metric the paper uses, even if it's bad for you.

## What the report must include

### 1. Real metrics table

| Configuration | Paper | Reproduction | Notes |
|---|---|---|---|
| MHST full | EM 41.5 / F1 50.7 | — | didn't run (out of scope) |
| MHST subset | — | EM 0.0 / F1 0.0 | 500×2 epoch, see root cause |

The "Notes" column is critical. Don't leave it blank.

### 2. Sample predictions

At least 5 samples, verbatim:

```text
Q: What was the total assets from AMER in 2018?
gold: ['645,791']
pred: -118.0
```

These reveal bugs that aggregate metrics hide. If your model is always predicting "EVIDENCE: 1,2...", the metric might say 0% but the cause is obvious from samples.

### 3. Tradeoff table

| Dimension | Paper | Reproduction | Reason |
|---|---|---|---|
| Backbone | LayoutLMv2_LARGE 426M | RoBERTa-base 125M | CPU/MPS memory |
| Data | 13K samples | 500 samples | Time |
| Epochs | 50 | 2 | Time |

Be specific. "Simplified" is not a reason; "CPU memory" is.

### 4. Root cause for any gap

If your number is below expected, **explain why**. Not "model didn't converge" but:

- "span head always predicts position 0-2, suggesting the [CLS] bias is not addressed"
- "Training data is 26× smaller than paper (500 vs 13K), insufficient for head convergence"
- "Eval code has gold/pred type mismatch; F1 would be higher if fixed"

### 5. Engineering issues encountered

List real bugs hit during the work:

- HF dataset `next-tat/TAT-DQA` is imagefolder, switched to `fengbinzhu/TAT-LLM` JSON mirror
- RoBERTa `Ġ` prefix caused span finder to fail
- MPS state_dict load had unaligned blit error, fixed with `map_location="cpu"`
- yaml nested vs TrainConfig flat, wrote `load_config` to flatten

These are the **most reusable** parts of your report. Future reproductions will hit the same issues.

### 6. Recommendation for next iteration

What would it take to close the gap?

- "Increase to 5000 samples × 5 epoch (would take ~1.5h on MPS)"
- "Fix eval gold/pred format mismatch (1 line change)"
- "Switch to LayoutLMv2-base (download + 100 line change in encoder)"

Don't recommend things that are out of scope. Be realistic.

## What the report must NOT include

### 1. Fake numbers

If you didn't run, don't make up. "Expected EM 35-40 based on configuration" is fine if labeled as expected. "EM 38.5" with no run is fraud.

### 2. Self-congratulation

"We successfully reproduced the paper" — only if you actually did. "We implemented the architecture and training pipeline, but did not reach paper-level performance" — true.

### 3. Vague claims of success

- ❌ "The model works well on the test set"
- ✅ "The model achieves EM=0 on the 200-sample test set; see root cause analysis"

### 4. Blaming the paper

- ❌ "The paper's results can't be reproduced because the data is bad"
- ✅ "Our reproduction's EM=0 is due to training data being 26× smaller; the paper's number is not invalidated by this"

## Format

A good `REPRODUCTION_NOTES.md` reads like a lab notebook, not a press release. Sections:

1. **Why this paper** — selection rationale
2. **Reproduction strategy** — what you kept, what you cut, and why
3. **Engineering issues** — bugs hit, how fixed
4. **Real results** — metrics + samples + root cause
5. **Value and limits** — what this reproduction is good for
6. **Recommendations for next iteration**

Total length: 200-500 lines. Concise but complete.

## The Self-Audit

Before publishing, ask:

1. "Could a skeptical reviewer re-run my code and get the same number?" — If no, your numbers are wrong.
2. "If a future engineer reads this report, would they know what to do next?" — If no, add the recommendation.
3. "If I claimed this in a job interview, would I be comfortable defending it?" — If no, tone down the claims.
4. "Does the report have any 'we achieved paper-level' claims that I can't back up?" — If yes, remove.

The goal of a reproduction report is to be **trustworthy**, not to be **positive**. A report that says "EM=0, here's why" is more trustworthy than "EM=41.5" if the latter is unverified.
