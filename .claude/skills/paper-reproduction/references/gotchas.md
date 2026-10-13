# Common Engineering Gotchas

These are real bugs hit during TAT-DQA reproduction. Each took 30+ minutes to diagnose. Save yourself the time.

## 1. Subword Tokenizer Prefix Mismatch (RoBERTa, GPT-2, etc.)

**Symptom**: span head training loss doesn't go down; BIO tag finder returns all-O labels.

**Cause**: RoBERTa tokenizes `"$100"` in context (with leading space) as `["Ġ$", "100"]` (the `Ġ` indicates a leading space). But the answer text `"$100"` tokenized standalone is `["$", "100"]`. The sliding window matcher never finds a match.

**Fix**: When matching answer text against context tokens, try both forms:

```python
candidates = [ans_text]
if not ans_text.startswith(" "):
    candidates.append(" " + ans_text)  # RoBERTa will tokenize as "ĠX"

for cand in candidates:
    ans_ids = tokenizer.encode(cand, add_special_tokens=False)
    # ... sliding window match
```

Same logic for T5, GPT-2, LLaMA (each has its own prefix char: `▁` for SentencePiece).

## 2. PyTorch MPS state_dict Load Bug

**Symptom**:
```
While copying the parameter named "encoder.model.encoder.layer.10.attention.self.key.weight",
whose dimensions in the model are torch.Size([768, 768]) and whose dimensions in the
checkpoint are torch.Size([768, 768]), an exception occurred :
('destOffset % 4 == 0 INTERNAL ASSERT FAILED at ".../Copy.mm":236,
 please report a bug to PyTorch. Unaligned blit request',)
```

**Cause**: PyTorch's MPS backend has a known issue with loading state_dicts directly when the checkpoint was saved on MPS. Affects parameters with certain stride/alignment.

**Fix**: Load to CPU first, then move to MPS:

```python
state = torch.load(path, map_location="cpu", weights_only=False)
model.load_state_dict(state["model_state_dict"])
model.to(device)  # then move
```

**Affected**: PyTorch 2.x on Apple Silicon, especially RoBERTa / BERT models. CUDA / CPU are unaffected.

## 3. HF Dataset Format Mismatch

**Symptom**: `DatasetGenerationError: An error occurred while generating the dataset` after `load_dataset(...)` returns 0 examples.

**Cause**: HF datasets can declare a format (e.g. `imagefolder`) that's incompatible with what you think (text/JSON). The dataset loads "successfully" but produces no usable samples.

**Diagnosis**:
```bash
curl -s "https://datasets-server.huggingface.co/info?dataset=<NAME>" | head
```

Look for `"imagefolder"` or `"arrow"` in the response.

**Fix**: Find an alternative source:
- Paper's official GitHub repo (often has `/data` folder)
- Author's mirror repos
- Re-construct from the paper's own release (PDFs, dumps, etc.)

For TAT-DQA: `next-tat/TAT-DQA` HF is imagefolder; `fengbinzhu/TAT-LLM` GitHub has JSON files at `data/original/tatdqa/`.

## 4. yaml Nested vs Dataclass Flat Impedance

**Symptom**: `TypeError: __init__() got an unexpected keyword argument 'X'` when loading yaml config.

**Cause**: yaml is nested for human readability (`model:`, `data:`, `training:`), but your config dataclass is flat.

**Fix**: Write a `load_config` that flattens and filters:

```python
def load_config(path: str) -> TrainConfig:
    with open(path) as f:
        cfg = yaml.safe_load(f)
    flat = {}
    for section in ("model", "data", "training", "eval"):
        if section in cfg and isinstance(cfg[section], dict):
            flat.update(cfg[section])
    for k, v in cfg.items():
        if k not in ("model", "data", "training", "eval"):
            flat[k] = v
    # Only pass declared fields
    import dataclasses
    valid = {f.name for f in dataclasses.fields(TrainConfig)}
    flat = {k: v for k, v in flat.items() if k in valid}
    return TrainConfig(**flat)
```

## 5. Scale Semantic Asymmetry in Numeric QA

**Symptom**: Test asserts `compute_em_one(100, 100000000, scale="million") is True` fails, but `compute_em_one(50, 50, scale="thousand") is True` passes.

**Cause**: In TAT-DQA-style evaluation, **scale applies to the model's prediction only** (which is a relative number); the gold is the absolute value.

So:
- pred=100, scale="million" → 1e8
- gold=100000000 → 1e8
- Match ✓

But:
- pred=50, scale="thousand", gold=50 → if you apply scale to both, you get 50000 vs 50 = mismatch

**Fix**: Only apply scale to the prediction:

```python
def compute_em_one(pred, gold, scale=""):
    g_num = _to_number(gold)
    if g_num is not None:
        p_num = _to_number(pred)
        p_abs = p_num * SCALE_FACTOR.get(scale, 1.0)
        g_abs = float(g_num)  # no scale on gold
        return abs(p_abs - g_abs) < tolerance
```

## 6. Unit Tests with Type-Semantic Mismatch

**Symptom**: Test passes on simple inputs but fails on real data, with confusing error.

**Cause**: The test's intent (what the author meant) doesn't match the function's behavior. Common with metrics where the spec is ambiguous.

**Fix**: Before writing the assertion, write a docstring with the semantic. Then write the test that exercises ONE specific semantic. If two test cases imply different semantics, one of them is wrong.

Example: the failed test case `compute_em_one(50, 50, scale="thousand")` is ambiguous — does "thousand" apply to pred, gold, or both? Pick one and be consistent.

## 7. sys.path Not Set in Scripts

**Symptom**: `ModuleNotFoundError: No module named 'data'` when running `python scripts/train.py`.

**Cause**: Scripts in subdirectories don't have the project root on `sys.path` by default.

**Fix**: Add at the top of every script:

```python
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
```

Or run scripts with `python -m scripts.train` (but this requires `scripts/__init__.py`).

## 8. PEP 668 Externally-Managed Environment

**Symptom**: `error: externally-managed-environment` when running `pip install`.

**Cause**: Modern Python (3.11+) on Homebrew / system Python marks the system site-packages as managed.

**Fix**: Use a virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Or use `--break-system-packages` flag (not recommended).

## 9. torch.dtype Mismatch on MPS

**Symptom**: `RuntimeError: MPS backend does not support dtype Double` or similar.

**Cause**: Some MPS operations only support float32, not float64. RoBERTa weights are float32, but if you accidentally cast to double (e.g. `.to(torch.float64)`), MPS will fail.

**Fix**: Stay in float32 for MPS. Use `.float()` not `.double()`.

## 10. Tokenizer Cache Pollution

**Symptom**: Tests pass in isolation, fail in batch; or different runs give different results.

**Cause**: Hugging Face tokenizer caches by directory; if you have two different models in different cache dirs, or the cache gets corrupted, behavior changes.

**Fix**: Set `cache_dir` explicitly in your tokenizer calls. For tests, use the same cache dir across all tests.

## Quick Reference

| Issue | One-line fix |
|---|---|
| Tokenizer prefix | Try ` " " + answer_text` as a candidate |
| MPS state_dict | `map_location="cpu"` then `.to(device)` |
| HF imagefolder | Find JSON mirror on GitHub |
| yaml nested | Flatten + filter valid fields |
| Scale semantics | Apply scale to pred only |
| sys.path | Add project root to path in scripts |
| PEP 668 | `python3 -m venv .venv` |
| MPS dtype | Stay in float32 |

## Reporting New Gotchas

When you find a new gotcha, add it to this file with:
1. Symptom (error message or behavior)
2. Cause (root explanation)
3. Fix (concrete code)
4. One-line summary for the table

This file is the most-reused artifact in any reproduction project.
