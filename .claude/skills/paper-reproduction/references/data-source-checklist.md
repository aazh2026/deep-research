# Data Source Verification Checklist

The data is the foundation. Most reproduction failures start with a bad data assumption. Verify before writing model code.

## 5-step verification

### 1. Find the official source

Search the paper for:
- "We release our data at..." → use that URL first
- GitHub repo mentioned in the paper → look for `data/` or `dataset/` folder
- Affiliated authors' GitHub → often have mirrors

For TAT-DQA, the official NExTplusplus/TAT-DQA repo links to Google Drive, but `fengbinzhu/TAT-LLM` has JSON mirrors on GitHub directly.

### 2. Check the HF dataset (if applicable)

HF datasets can be misleading. Always run:

```bash
curl -s "https://datasets-server.huggingface.co/info?dataset=<NAME>" | python3 -m json.tool | head -30
```

Look for:
- `"parquet"` — usually text/JSON, parseable
- `"imagefolder"` — actual images, requires vision pipeline
- `"json"` — text data
- `Mixed formats across splits` — **red flag**, paper assumed one format

Concrete trap: `next-tat/TAT-DQA` has:
```json
"train": ("imagefolder", {}),
"validation": ("imagefolder", {}),
"test": ("json", {})
```

Only test is JSON. A "load HF dataset" script will fail or silently load images instead.

### 3. Inspect the actual structure

Once you have a JSON or parquet file:

```python
import json
with open('data.json') as f:
    data = json.load(f)
print('total:', len(data))
print('top-level keys of first item:', list(data[0].keys()))
import json
print(json.dumps(data[0], indent=2)[:2000])
```

Look for:
- **Top-level shape**: is each item a sample, or is it a `doc` containing multiple `questions`?
- **Field names**: `answer` vs `answers`, `text` vs `context`, `scale` vs `magnitude`
- **Nested structures**: `answer: ["$100"]` (always list) vs `answer: "$100"` (sometimes string)
- **Missing fields**: paper says "we use table + text", dataset only has `facts`

### 4. Test loading end-to-end

Before writing the model, write a 20-line loader that:
- Reads the raw file
- Maps to your unified sample format
- Prints 1 sample per category (e.g. per answer_type)

This catches:
- File format errors early
- Field name mismatches
- Encoding issues (UTF-8 BOM, Chinese punctuation)
- Empty fields

### 5. Cache and gitignore

- Save raw data to `data_local/` (not in `data/`, which is for code)
- Add `data_local/`, `cache/`, `*.parquet` to `.gitignore`
- If the data is large (>100MB), document how to re-download it

## Common Data Traps

| Trap | Symptom | Fix |
|---|---|---|
| HF dataset is imagefolder | `DatasetGenerationError: Expected object or value` | Find JSON mirror on GitHub |
| Field name has typo in paper | Loader always returns None | Inspect raw data, fix field map |
| Answer is always a list | Type error on `len(answer)` | Always treat as list, unwrap later |
| Nested doc/questions | `parse_raw_sample` only gets partial data | Flatten in loader, not parser |
| Missing scale field | Metrics divide by None | Default to "" or 0 |
| Non-ASCII punctuation | Tokenizer splits unexpectedly | Normalize to ASCII before tokenize |
| `facts` is single string | `for f in facts` iterates characters | `if isinstance(facts, str): facts = [facts]` |

## Decision Tree

```
Found data on HF?
├── Yes → Check actual format (imagefolder? json? parquet?)
│   ├── JSON or parquet → Inspect structure, write loader
│   ├── Imagefolder → Find alternative (paper's GitHub, mirror)
│   └── Mixed → Each split may need different handling
└── No → Check paper's GitHub
    ├── Has /data folder with JSON → Use directly
    ├── Links to Google Drive / S3 → Try with curl, fall back to mirror
    └── No data at all → Stop, tell the user
```

## After verification

Document in `data/README.md` or `REPRODUCTION_NOTES.md`:
- Source URL
- Actual format (imagefolder, JSON, etc.)
- Top-level structure (one sample per file? doc → questions?)
- Field mapping (paper's name → dataset's actual name)
- Total samples per split

This documentation is gold for anyone (including future you) trying to extend the work.
