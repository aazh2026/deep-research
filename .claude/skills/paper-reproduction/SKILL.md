---
name: paper-reproduction
description: Reproduce a research paper's method end-to-end on local hardware. Use when the user picks a paper from a list and wants code that implements it, when a paper is selected for reproduction and architecture/data/training/eval need to be coded, when the user wants to verify a paper's claims with a real (often reduced) run, or when someone wants a working pipeline that mirrors a paper's structure even if final metrics are far below the paper's. Especially relevant for "方法论文" with clear architectures and public data.
version: 1.0.0
---

# Paper Reproduction

Reproduce a research paper's method end-to-end on local hardware (CPU/MPS/single GPU), honest about gaps, focused on a working pipeline before chasing paper-level metrics.

The skill is opinionated: **honest reporting of failure is a deliverable**. "EM=0, here is why" is more valuable than "EM=41.5, here is the config" if the latter is fabricated.

## When to use

Trigger this skill when the user:
- Picks a paper from a list (curated table, related work section) and wants to implement it
- Says "复现这篇论文" / "reproduce this paper" / "基于代码复现"
- Has a specific paper + dataset in mind and wants code, not a survey
- Wants to verify a paper's claims with a real run

Don't use when:
- The user just wants a paper summary or notes (use `paper-table-extractor` or similar)
- The paper uses proprietary data not accessible to the user
- The user only wants a literature review

## Core Philosophy

1. **Pipeline 通 > 数字接近** — A working end-to-end pipeline that exposes real bugs is worth more than a fake-numbers "successful" run.
2. **Document failure honestly** — Every bug, every gap, every metric you didn't hit should be in the writeup. This is the most valuable part.
3. **Faithful to architecture, pragmatic on data** — Keep the paper's architecture shape (heads, losses, decode). Cut data/epochs/backbone only when hardware forces it, and label the cut clearly.
4. **Verify data first** — Before writing any model code, confirm you can actually load the data. The HF dataset name can be a trap (e.g. `next-tat/TAT-DQA` is imagefolder, not JSON).

## Workflow

### Step 1: Paper Selection

Before any code, decide if the paper is **reproducible** in this environment. See `references/paper-selection-checklist.md`. Hard filters:

- ✅ Architecture described in detail (heads, losses, decode)
- ✅ Dataset publicly downloadable (HF, GitHub, official URL)
- ✅ Trainable on CPU/MPS or single GPU in hours
- ✅ Has a clear baseline to compare against
- ❌ Requires multi-node training / proprietary data / custom silicon

If the paper fails any hard filter, **stop and tell the user** — do not write code that pretends to work.

### Step 2: Plan and Document Tradeoffs

Create a `plan.md` that includes:

1. **What you keep** (architecture, loss formulation, eval metric, decode algorithm)
2. **What you simplify** (backbone, data size, epochs, batch size) with explicit reasons
3. **Expected metrics range** — not the paper's number, your realistic range based on simplifications
4. **Stop criteria** — when to declare "pipeline works" vs "metrics are close enough"

Be honest: "we expect 60-80% of the paper's number if we do X; we expect 30% if we do Y". Don't promise parity.

### Step 3: Data Verification (CRITICAL)

Before writing model code:

1. Find the dataset's **actual** source — search GitHub for the paper's official repo, look for `data/` or `dataset/` folders
2. Check the **real format** of HF datasets:
   ```bash
   curl -s "https://datasets-server.huggingface.co/info?dataset=<NAME>" | head
   ```
   If it says `imagefolder` or `parquet` or mixed formats, **read the file** to confirm
3. Download 1-2 samples manually and inspect the actual JSON structure
4. Note: HF dataset names can be misleading. The paper's data may live in a mirror repo (e.g. `fengbinzhu/TAT-LLM` mirrors TAT-DQA)
5. Always keep raw data in a separate folder (`data_local/`) — never assume HF download will work

### Step 4: Incremental Pipeline

Build in this order. **Don't skip steps.** Each has a verification gate:

1. **Data loader** → load 10 samples, print one per type. **Gate**: all 4 types visible, fields populated
2. **Collator** → batch 4 samples, print tensor shapes. **Gate**: shapes match model expectations
3. **Model** → forward pass on random tensor, check all head shapes. **Gate**: forward + backward without NaN
4. **Loss** → compute loss on mock batch, check it's a finite scalar. **Gate**: loss.backward() doesn't error
5. **Train loop** → 32 samples × 1 epoch, check loss decreases. **Gate**: last batch loss < first batch loss
6. **Eval** → run on 50 test samples, check metrics are computed. **Gate**: JSON report with per-type breakdown

At each gate, write a test in `tests/test_*.py`. The tests serve as **execution evidence** that the pipeline works.

### Step 5: Honest Run

Once the pipeline is verified:

1. Run a smoke training (32 × 1) and capture full output
2. Run a real training (e.g. 500 × 2) and capture metrics
3. Run evaluation and **dump the first 5-10 predictions with their golds** — visual inspection reveals bugs that metrics hide
4. Compare actual numbers to expected range from Step 2
5. If numbers are below expected range, **find the root cause**:
   - Decode format mismatch (gold is list, pred is string)
   - Head collapsing to a default position
   - Training not converged
   - Eval bug (scale semantics wrong)
6. **Do not retry endlessly to hit paper numbers** if hardware is the bottleneck. Document and move on.

### Step 6: Documentation

Write a `REPRODUCTION_NOTES.md` that includes:

1. **Paper title + what was reproduced**
2. **Tradeoff table** (paper vs reproduction)
3. **Real metrics** vs paper's, with root cause analysis if below
4. **Sample predictions** showing what the model actually outputs
5. **Engineering issues** (MPS bugs, tokenizer gotchas, etc.) — these are reusable lessons
6. **Recommendation for next iteration** — what would close the gap to paper

The notes are the **main deliverable** for anyone who reads the project after you.

## Output Contract

When this skill is invoked, the project should end up with:

```
<paper>/
├── README.md                 # quick overview + commands
├── REPRODUCTION_NOTES.md     # honest writeup (mandatory)
├── paper.md                  # paper summary notes
├── requirements.txt
├── configs/                  # yaml configs
├── data/                     # parser + collator
├── data_local/               # raw downloaded data (gitignored)
├── models/                   # model + heads
├── training/                 # train loop + losses
├── evaluation/               # metrics + eval entry
├── utils/
├── scripts/                  # CLI entry points
├── tests/                    # unit tests, runnable as `python tests/test_X.py`
└── outputs/                  # checkpoints, metrics.json
```

## Anti-Patterns (Don't Do These)

- ❌ **Don't claim "EM=41.5"** when you ran 500 samples × 2 epochs. That's a lie.
- ❌ **Don't skip data verification** and write model code first. You'll discover the dataset is imagefolder after writing 1000 lines.
- ❌ **Don't paper over bug** by changing gold format to match pred. Fix one side, document the other.
- ❌ **Don't retry hyperparameters endlessly** when training data is the bottleneck. Step back and report.
- ❌ **Don't claim "works on local CPU"** without testing. Verify before advertising.
- ❌ **Don't use `next-tat/TAT-DQA`** for text tasks — it's imagefolder. Find the JSON mirror.
- ❌ **Don't load state_dict directly to MPS** in PyTorch — use `map_location="cpu"` then `.to(device)`.

## Common Gotchas

See `references/gotchas.md` for the full list. Top 5:

1. **HF dataset format mismatch** — Always check actual format before assuming.
2. **Subword tokenizer prefix** — RoBERTa's `Ġ` means "leading space". Match by adding a space to the answer text.
3. **MPS state_dict load** — Use `map_location="cpu"` then `.to(device)` to avoid unaligned blit.
4. **yaml nested vs dataclass flat** — Write a `load_config` that flattens + filters unknown fields.
5. **scale semantic asymmetry** — In TAT-DQA-style eval, scale applies to pred only (gold is absolute).

## Honesty Checklist

Before declaring the reproduction "done", verify in `REPRODUCTION_NOTES.md`:

- [ ] All metrics in the README come from an actual run, not from the paper
- [ ] At least 5 sample predictions are shown verbatim (gold + pred) for visual inspection
- [ ] Every architectural deviation is listed with a reason
- [ ] Root cause is given for any metric that's below expected range
- [ ] Tests in `tests/` are runnable and pass
- [ ] Code in `scripts/` runs end-to-end with the documented commands
- [ ] If something doesn't work, it's labeled "did not work" — not glossed over

## Reference Files

- `references/paper-selection-checklist.md` — when to accept/reject a paper
- `references/data-source-checklist.md` — how to verify a dataset is actually usable
- `references/gotchas.md` — engineering traps and their fixes
- `examples/tat-dqa-summary.md` — concrete worked example (TAT-DQA / MHST)

## Acknowledgment

This skill is built from the TAT-DQA / MHST reproduction (2026-10). Every gotcha documented here was a real bug encountered during that work.
