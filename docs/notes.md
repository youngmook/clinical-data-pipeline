# Notes

This file summarizes recent work and decisions for the clinical-data-pipeline project.

## Summary of Changes

- Added a comprehensive CT.gov v2 client with support for fields, query dicts, filters, sorting, paging, rate-limit handling, and compact extraction helpers.
- Expanded CLI to support:
  - `hnid-cids` (HNID -> CID list)
  - `collect-ctgov` (HNID -> CID -> NCT -> CT.gov documents)
  - legacy single-compound flow remains supported.
- Added scripts for end-to-end table generation from HNID:
  - `scripts/build_ctgov_table.py` produces `cid_nct_links.jsonl`, `studies.jsonl`, and `ctgov_table.csv`.
- Added documentation in `docs/` and Korean translations (`*.ko.md`).
- Added smoke and unit tests for the new script, plus doc-backed example tests.
- Registered pytest markers in `pyproject.toml`.
- Standardized imports to use `clinical_data_analyzer.ctgov` and `clinical_data_analyzer.pubchem` public entry points to avoid future breakage when files are reorganized.
- Added CID -> NCT fallback chain improvements:
  - PUG-View heading lookup
  - PubChem web clinicaltrials endpoint fallback (`/sdq/sphinxql.cgi`)
  - HTML fallback
  - optional CT.gov term-link fallback
- Added CID-level non-fail-fast behavior and error recording in outputs.
- Added staged MVP scripts:
  - `scripts/fetch_cids.py`
  - `scripts/map_cid_to_nct.py`
  - `scripts/fetch_ctgov_docs.py`
  - `scripts/build_clinical_dataset.py`
  - `scripts/run_mvp_pipeline.py`

## Key Decisions

- Use stable public imports (e.g., `from clinical_data_analyzer.ctgov import CTGovClient`) instead of file-level imports.
- Keep `client.py` un-split for now; if growth occurs, split internally while preserving public re-exports.
- Ignore outputs in `out_*/` via `.gitignore` to avoid committing large datasets.

## Current Behavior Observations

- Some CIDs can still fail in restricted environments due to DNS/network limits.
- With non-fail-fast mode, processing continues and records per-CID errors in output files.

## How to Reproduce Recent Tests

- Smoke test (network):
  - `pytest -q -m "smoke and network"`
- Unit test (no network):
  - `pytest -q tests/test_build_ctgov_table_unit.py`

## Suggested Next Steps

- Add optional quality controls for fallback outputs (e.g., source-level confidence tagging).
- Consider checkpointing and batching options for full HNID runs.
- Add Korean docs updates for the latest fallback and script workflow changes.
