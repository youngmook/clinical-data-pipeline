# clinical-data-pipeline

A research-grade pipeline for collecting, normalizing, and linking
**clinical compound data from PubChem** with **clinical trial documents from ClinicalTrials.gov**.

This repository focuses on **reproducible, API-based data collection** without relying on
web scraping or unstable UI-dependent mechanisms.

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
   * Retrieves full clinical trial documents via the **ClinicalTrials.gov v2 API**

4. **Export analysis-ready datasets**

   * JSONL outputs for compounds, links, and clinical trial documents
   * Designed to be consumed by downstream analysis, modeling, or visualization pipelines

---

## Key design principles

* **Official APIs only**

  * PubChem PUG REST (Classification Nodes, PUG-View)
  * ClinicalTrials.gov v2 API
* **No Selenium, no UI scraping**
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
from clinical_data_analyzer.ctgov.client import CTGovClient

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
│
├─ ctgov/
│  └─ client.py                  # ClinicalTrials.gov v2 API
│
├─ pipeline/
│  └─ ...                        # Dataset builders and linkers
```

---

## Installation (development)

```bash
conda create -n clinical-pipeline python=3.11 -y
conda activate clinical-pipeline
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

Optional development dependencies:

```bash
pip install -e ".[dev]"
```

---

## License

MIT License
