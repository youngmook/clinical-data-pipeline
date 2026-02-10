# clinical-data-pipeline

A research-grade pipeline for collecting, normalizing, and linking
**clinical compound data from PubChem** with **clinical trial documents from ClinicalTrials.gov**.

Korean README: README.ko.md

This repository focuses on **reproducible, API-based data collection**.
It prioritizes official APIs and uses web-derived fallbacks only when PubChem REST payloads
do not expose trial IDs for specific compounds.

---

## Beginner Quickstart (Copy & Paste)

If this is your first run, use this section first.

### Option A: Conda (recommended if you already use conda)

```bash
conda create -n clinical-pipeline python=3.11 -y
conda activate clinical-pipeline
pip install -e .
```

Run a small smoke test (first CID + first NCT):

```bash
PYTHONUNBUFFERED=1 python -u scripts/collect_ctgov_docs.py \
  --hnid 3647573 \
  --limit-cids 1 \
  --limit-ncts 1 \
  --folder-name ctgov_docs_first1 \
  --out-root out \
  --use-ctgov-fallback \
  --show-progress \
  --progress-every 1
```

### Option B: uv (recommended if you prefer fast Python tooling)

```bash
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e .
```

Run the same smoke test:

```bash
PYTHONUNBUFFERED=1 uv run python -u scripts/collect_ctgov_docs.py \
  --hnid 3647573 \
  --limit-cids 1 \
  --limit-ncts 1 \
  --folder-name ctgov_docs_first1 \
  --out-root out \
  --use-ctgov-fallback \
  --show-progress \
  --progress-every 1
```

Expected output files:

```
out/ctgov_docs_first1/
├─ cids.txt
├─ cids.jsonl
├─ cid_nct_links.jsonl
├─ cid_nct_map.csv
├─ compounds.jsonl
└─ studies.jsonl
```

---

## What this project does

This project provides a minimal but extensible pipeline to:

1. **Retrieve clinical-trial–related compounds from PubChem**

   * Uses the official **PubChem PUG REST Classification Nodes API**
   * Retrieves compound lists (CIDs) from specific classification nodes (HNIDs),
     such as *Clinical Trials* and *ClinicalTrials.gov*

2. **Collect compound metadata from PubChem**

   * Canonical SMILES, InChIKey, IUPAC name
   * Synonyms and identifiers via PUG REST

3. **Link PubChem compounds to ClinicalTrials.gov**

   * Extracts **NCT IDs** from PubChem annotations (PUG-View)
   * Uses fallback sources when needed (PUG-View heading lookup, PubChem web clinicaltrials endpoint, optional CT.gov term linking)
   * Retrieves full clinical trial documents via the **ClinicalTrials.gov v2 API**

4. **Export analysis-ready datasets**

   * JSONL outputs for compounds, links, and clinical trial documents
   * Designed to be consumed by downstream analysis, modeling, or visualization pipelines

---

## Key design principles

* **Official APIs first**

  * PubChem PUG REST (Classification Nodes, PUG-View)
  * ClinicalTrials.gov v2 API
  * PubChem web clinicaltrials endpoint fallback (`/sdq/sphinxql.cgi`) when REST payload is incomplete
* **No Selenium/browser automation**
* **Reproducible**

  * Classification nodes (HNID) are stable identifiers
* **Modular**

  * PubChem-related functionality is organized as a self-contained subpackage

---

## PubChem classification nodes (HNID)

PubChem provides an official API to retrieve identifiers associated with
classification nodes:

```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/classification/hnid/{HNID}/{id_type}/{format}
```

This project currently supports **compound (CID) retrieval** from clinical-trial–related nodes.

### Clinical trial–related HNIDs used

| HNID    | Description                          |
| ------- | ------------------------------------ |
| 1856916 | Clinical Trials (all sources)        |
| 3647573 | ClinicalTrials.gov                   |
| 3647574 | EU Clinical Trials Register          |
| 3647575 | NIPH Clinical Trials Search of Japan |

---

## Quick examples

### 1) Download PubChem CIDs for clinical trials (HNID-based)

```python
from clinical_data_analyzer.pubchem.clinical_trials_nodes import download_clinical_trials_cids

results = download_clinical_trials_cids(out_dir="out_hnid")

print("Clinical Trials (all):", len(results["clinical_trials"]))
print("ClinicalTrials.gov only:", len(results["clinicaltrials_gov"]))
```

This will create files such as:

```
out_hnid/
├─ clinical_trials_cids.txt
├─ clinicaltrials_gov_cids.txt
├─ eu_register_cids.txt
└─ japan_niph_cids.txt
```

---

### 2) From HNID → CID → ClinicalTrials.gov documents

The example below shows the full pipeline:

1. download clinical-trial–related CIDs from PubChem (HNID)
2. extract NCT IDs from PubChem annotations (PUG-View)
3. retrieve full trial documents from ClinicalTrials.gov

```python
from clinical_data_analyzer.pubchem import (
    PubChemClient,
    PubChemClassificationClient,
    PubChemPugViewClient,
)
from clinical_data_analyzer.ctgov import CTGovClient

# Clinical Trials HNID
HNID = 1856916

pubchem = PubChemClient()
class_nodes = PubChemClassificationClient()
pug_view = PubChemPugViewClient()
ctgov = CTGovClient()

# Step 1: HNID → CID list
cids = class_nodes.get_cids(HNID)
print("Total CIDs:", len(cids))

# (optional) limit for a quick test
cids = cids[:10]

# Step 2–3: CID → NCT → CTGov study document
for cid in cids:
    nct_ids = pug_view.nct_ids_for_cid(cid)
    for nct in nct_ids:
        study = ctgov.get_study(nct)
        print(cid, nct, study.get("protocolSection", {}).get("identificationModule", {}).get("briefTitle"))
```

This example demonstrates how the individual modules can be composed
into a reproducible, end-to-end data collection pipeline.

This will create files such as:

```
out_hnid/
├─ clinical_trials_cids.txt
├─ clinicaltrials_gov_cids.txt
├─ eu_register_cids.txt
└─ japan_niph_cids.txt
```

---

## Package structure

```
src/clinical_data_analyzer/
├─ pubchem/
│  ├─ client.py                  # PUG REST: CID, properties, synonyms
│  ├─ classification_nodes.py    # HNID → CID (Classification Nodes API)
│  ├─ clinical_trials_nodes.py   # Clinical-trial–related HNID helpers
│  └─ pug_view.py                # PUG-View: NCT ID extraction
│  └─ web_fallback/              # Web clinicaltrials endpoint/HTML fallback for NCT IDs
│
├─ ctgov/
│  └─ client.py                  # ClinicalTrials.gov v2 API
│
├─ pipeline/
│  └─ ...                        # Dataset builders and linkers
```

---

## Environment Setup

Choose one environment setup.

### uv (Recommended for fast local setup)

Create environment and install:

```bash
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -e .
```

Optional development dependencies:

```bash
uv pip install -e ".[dev]"
```

Run without activating shell state (optional):

```bash
uv run python scripts/run_mvp_pipeline.py --hnid 3647573 --out-dir out_mvp --use-ctgov-fallback --resume
```

### Conda (Recommended if you already use conda)

```bash
conda create -n clinical-pipeline python=3.11 -y
conda activate clinical-pipeline
pip install -e .
```

Optional development dependencies:

```bash
pip install -e ".[dev]"
```

### venv (Alternative)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

Optional development dependencies:

```bash
pip install -e ".[dev]"
```

---

## Documentation

Project documentation is in the `docs/` folder.

- English:
  - docs/overview.md
  - docs/ctgov.md
  - docs/pubchem.md
  - docs/pipeline.md
  - docs/cli.md
- Korean:
  - docs/overview.ko.md
  - docs/ctgov.ko.md
  - docs/pubchem.ko.md
  - docs/pipeline.ko.md
  - docs/cli.ko.md

---

## CLI usage

A minimal command-line interface is provided for quick, reproducible runs
without writing Python code.

### Show help

```bash
clinical-data-analyzer --help
```

## Script usage (MVP)

For staged execution:

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

Step1-3 only (streaming CID -> NCT -> CTGov docs, progress-friendly):

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

Quick smoke (first CID + first NCT):

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

## Scheduled Automation (GitHub Actions)

The repository includes a scheduled workflow:

- `.github/workflows/ctgov_collect.yml`

What it does on each run:

1. collect/refresh CTGov docs (`collect_ctgov_docs.py --resume`)
2. build normalized dataset (`build_clinical_dataset.py`)
3. build static table page (`build_studies_table.py`)
4. update persistent data snapshots in repo:
   - `data/ctgov/studies.jsonl` (latest)
   - `data/ctgov/history/studies_*.jsonl` (history, only when changed)
   - `data/ctgov/collection_state.json` (last collected/changed metadata)
5. deploy table page from `docs/data` to GitHub Pages

Manual run (Actions UI) supports optional:

- `hnid`
- `limit_cids`
- `limit_ncts`

### Download clinical-trial–related CIDs (HNID)

Download PubChem compound IDs associated with the *Clinical Trials* classification node:

```bash
clinical-data-analyzer hnid-cids \
  --hnid 1856916 \
  --out out_hnid/clinical_trials_cids.txt
```

This uses the official PubChem Classification Nodes API:

```
/rest/pug/classification/hnid/{HNID}/cids/TXT
```

### End-to-end example: HNID → CID → ClinicalTrials.gov documents

Run a small end-to-end collection for a quick sanity check:

```bash
clinical-data-analyzer collect-ctgov \
  --hnid 1856916 \
  --limit 10 \
  --out out_ctgov
```

This will:

1. retrieve CIDs from the given HNID
2. extract NCT IDs from PubChem annotations (PUG-View)
3. download full trial documents from ClinicalTrials.gov

Generated files:

```
out_ctgov/
├─ compounds.jsonl
├─ links.jsonl
└─ studies.jsonl
```

---

## License

MIT License
