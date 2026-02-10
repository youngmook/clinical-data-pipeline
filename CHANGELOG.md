# Changelog

All notable changes to this project are documented in this file.

## v0.3.0 - 2026-02-10

### Added

- Added scheduled GitHub Actions workflow for CTGov collection and table publishing:
  - `.github/workflows/ctgov_collect.yml`
- Added dedicated GitHub Pages workflow for PubChem trials table publishing:
  - `.github/workflows/pubchem_table_pages.yml`
- Added static table builder:
  - `scripts/build_studies_table.py` (CSV -> `docs/data/{studies.csv,studies.json,index.html}`)
- Added studies history updater:
  - `scripts/update_studies_history.py`
  - persists latest studies snapshot and change history in:
    - `data/ctgov/studies.jsonl`
    - `data/ctgov/history/studies_*.jsonl`
    - `data/ctgov/collection_state.json`
- Added dual study links in normalized/table outputs:
  - `ctgov_url` and `pubchem_url` in clinical compound trial dataset
  - static table now shows both CTGov and PubChem links
- Added PubChem trials export pipeline:
  - `scripts/export_pubchem_trials_dataset.py`
  - exports normalized union rows across ctgov/eu/jp collections (`trials.jsonl`, `trials.csv`, `trials.json`, `summary.json`)
- Added PubChem trials HTML builders:
  - `scripts/build_pubchem_trials_table.py`
  - supports `vanilla`, `datatables`, and `tabulator` modes

### Changed

- Refactored PubChem web fallback modules from a single file to provider-based package layout.
- Normalized PubChem trial row schema now uses unified fields:
  - `collection`, `collection_code`, `id`, `date`, `id_url`, `title`, `phase`, `status`, `cids`
- PubChem trial export now stores structure images as base64 data URIs in output rows.
- Added fallback to `ConnectivitySMILES` when `CanonicalSMILES` is missing in compound properties.
- Updated `ctgov_collect` workflow to focus on scheduled collection/snapshot updates, while Pages deployment is handled by `pubchem_table_pages`.

### Tests

- Added unit test for studies history update behavior:
  - `tests/test_update_studies_history_unit.py`
- Added unit test for static studies table builder:
  - `tests/test_build_studies_table_unit.py`
- Added unit test for PubChem trials export script:
  - `tests/test_export_pubchem_trials_dataset_unit.py`

## v0.2.0 - 2026-02-09

### Added (Service Refactor)

- Added service-oriented CTGov collection module:
  - `src/clinical_data_analyzer/pipeline/collect_ctgov_docs_service.py`
  - `CollectCtgovDocsConfig`
  - `CollectCtgovDocsResult`
  - `collect_ctgov_docs(...)`
- Added thin script wrappers:
  - `scripts/collect_ctgov_docs.py` (main step1-3 runner, also supports quick smoke via limits)

### Changed (Collection Flow)

- Refactored step1-3 collection to **streaming mode**:
  - process one CID at a time
  - map NCT IDs for that CID
  - fetch CTGov study docs immediately (instead of waiting for all CID mapping to finish)
- Updated collected `studies.jsonl` rows to include top-level `cid` for easier downstream joins.
- Improved user-facing progress logs and startup context messages.
- Improved failure messaging in script layer with human-readable reason + raw error.

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

### Removed

- Removed one-off demo wrapper `scripts/collect_ctgov_docs_first1.py`.
- Standardized smoke test path to `scripts/collect_ctgov_docs.py --limit-cids 1 --limit-ncts 1`.

### Documentation

- Updated usage and behavior docs for fallback strategy, streaming collection flow, and service-oriented structure.

### Tests

- Added and expanded tests for:
  - PUG-View heading fallback behavior
  - web fallback (`sdq` first, HTML second)
  - CT.gov fallback behavior
  - non-fail-fast error handling for CID mapping pipeline.
