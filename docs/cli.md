# CLI

Module: src/clinical_data_analyzer/cli.py

The CLI resolves a compound and builds datasets.

## Usage

```bash
python -m clinical_data_analyzer.cli --name aspirin --out out
```

```bash
python -m clinical_data_analyzer.cli --cid 2244 --out out
```

## Options

- --name: compound name resolved via PubChem
- --cid: direct PubChem CID
- --out: output directory (default: out)

Outputs are the same as build_dataset_for_cids (see docs/pipeline.md).
