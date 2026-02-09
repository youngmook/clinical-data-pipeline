# Changelog

All notable changes to this project are documented in this file.

## 2026-02-09

### Added

- Added staged MVP scripts under `scripts/`:
  - `fetch_cids.py`
  - `map_cid_to_nct.py`
  - `fetch_ctgov_docs.py`
  - `build_clinical_dataset.py`
  - `run_mvp_pipeline.py`
  - shared utilities in `mvp_pipeline_lib.py`
- Added PubChem web fallback client:
  - `src/clinical_data_analyzer/pubchem/web_fallback.py`
  - supports PubChem web clinical trials endpoint (`/sdq/sphinxql.cgi`) and HTML fallback.
- Added CID-level error capture in `cid_nct_links.jsonl` and `compounds.jsonl` when API calls fail.

### Changed

- Improved CID -> NCT resolution priority:
  1. PubChem PUG-View default payload
  2. PUG-View heading lookup (including Drug and Medication Information section)
  3. PubChem web clinical trials endpoint fallback (`sdq/sphinxql.cgi`)
  4. PubChem compound page HTML fallback
  5. CT.gov term-link fallback (optional)
- Updated `scripts/map_cid_to_nct.py` and `scripts/run_mvp_pipeline.py`:
  - `--use-ctgov-fallback` option supported.
- Updated `src/clinical_data_analyzer/pipeline/cid_to_nct.py`:
  - source tracking for fallback path
  - non-fail-fast behavior with per-CID error recording.

### Documentation

- Updated usage and behavior docs for new fallback strategy and output schema details.

### Tests

- Added and expanded tests for:
  - PUG-View heading fallback behavior
  - web fallback (`sdq` first, HTML second)
  - CT.gov fallback behavior
  - non-fail-fast error handling for CID mapping pipeline.
