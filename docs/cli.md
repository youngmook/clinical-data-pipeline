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
