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

Outputs are the same as build_dataset_for_cids (see docs/pipeline.md).

### 2) Download HNID CIDs

```bash
python -m clinical_data_analyzer.cli hnid-cids --hnid 1856916 --out out_hnid/clinical_trials_cids.txt
```

### 3) HNID -> CID -> NCT -> ClinicalTrials.gov

```bash
python -m clinical_data_analyzer.cli collect-ctgov --hnid 1856916 --limit 10 --out out_ctgov
```

Optional fields for CT.gov:

```bash
python -m clinical_data_analyzer.cli collect-ctgov --hnid 1856916 --ctgov-fields NCTId,BriefTitle
```
