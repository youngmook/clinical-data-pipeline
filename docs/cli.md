# CLI

Module: src/clinical_data_analyzer/cli.py

The CLI supports single-compound dataset builds and HNID-based collection flows.

## Usage

### 1) Single compound (legacy path)

```bash
python -m clinical_data_analyzer.cli --name aspirin --out out
```

```bash
python -m clinical_data_analyzer.cli --cid 2244 --out out
```

Options:

- --name: compound name resolved via PubChem
- --cid: direct PubChem CID
- --out: output directory (default: out)

Outputs are the same as build_dataset_for_cids (see docs/pipeline.md):

- compounds.jsonl
- links.jsonl
- studies.jsonl

### 2) Download HNID CIDs

```bash
python -m clinical_data_analyzer.cli hnid-cids --hnid 1856916 --out out_hnid/clinical_trials_cids.txt
```

### 3) HNID -> CID -> NCT -> ClinicalTrials.gov

```bash
python -m clinical_data_analyzer.cli collect-ctgov --hnid 1856916 --limit 10 --out out_ctgov
```

Outputs:

- cid_nct_links.jsonl
- compounds.jsonl
- studies.jsonl

Optional fields for CT.gov:

```bash
python -m clinical_data_analyzer.cli collect-ctgov --hnid 1856916 --ctgov-fields NCTId,BriefTitle
```

## Script-based MVP flow

Use staged scripts when you want explicit step-by-step control:

```bash
python scripts/fetch_cids.py --hnid 3647573 --out-dir out_mvp
python scripts/map_cid_to_nct.py --cids-file out_mvp/cids.txt --out-dir out_mvp --use-ctgov-fallback
python scripts/fetch_ctgov_docs.py --links-file out_mvp/cid_nct_links.jsonl --out-path out_mvp/studies.jsonl --resume
python scripts/build_clinical_dataset.py --links-file out_mvp/cid_nct_links.jsonl --studies-file out_mvp/studies.jsonl --out-dir out_mvp/final
```

One-shot:

```bash
python scripts/run_mvp_pipeline.py --hnid 3647573 --out-dir out_mvp --use-ctgov-fallback --resume
```

### Step1-3 streaming collector (recommended for CTGov docs)

This runner focuses on:
1. HNID -> CID
2. CID -> NCT
3. NCT -> CTGov study docs

and processes CID records in streaming order so progress appears continuously.

```bash
PYTHONUNBUFFERED=1 conda run -n clinical-pipeline python -u scripts/collect_ctgov_docs.py \
  --hnid 3647573 \
  --folder-name ctgov_docs_run1 \
  --out-root out \
  --use-ctgov-fallback \
  --resume \
  --show-progress \
  --progress-every 1
```

Quick smoke mode (first CID + first NCT):

```bash
PYTHONUNBUFFERED=1 conda run -n clinical-pipeline python -u scripts/collect_ctgov_docs.py \
  --hnid 3647573 \
  --limit-cids 1 \
  --limit-ncts 1 \
  --folder-name ctgov_docs_first1 \
  --out-root out \
  --use-ctgov-fallback \
  --show-progress \
  --progress-every 1
```

## GitHub Actions automation

Workflow file:

- `.github/workflows/ctgov_collect.yml`

Behavior:

1. scheduled/manual collection of CTGov docs (resume mode)
2. normalized dataset build
3. static table build (`docs/data`)
4. persistent `studies.jsonl` snapshot update with history:
   - `data/ctgov/studies.jsonl`
   - `data/ctgov/history/studies_*.jsonl`
   - `data/ctgov/collection_state.json`
5. deploy table to GitHub Pages
