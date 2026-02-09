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

## Key Decisions

- Use stable public imports (e.g., `from clinical_data_analyzer.ctgov import CTGovClient`) instead of file-level imports.
- Keep `client.py` un-split for now; if growth occurs, split internally while preserving public re-exports.
- Ignore outputs in `out_*/` via `.gitignore` to avoid committing large datasets.

## Current Behavior Observations

- Some CIDs (e.g., 379) show ClinicalTrials.gov sections in PUG-View but do not include NCT IDs in the JSON payload. The NCT list appears to be referenced via an external table (`ExternalTableName: clinicaltrials`).
- NCT IDs can still be found for other CIDs (e.g., CID 441 in the 3647573 sample).

## How to Reproduce Recent Tests

- Smoke test (network):
  - `pytest -q -m "smoke and network"`
- Unit test (no network):
  - `pytest -q tests/test_build_ctgov_table_unit.py`

## Suggested Next Steps

- Investigate how to resolve PUG-View `ExternalTableName=clinicaltrials` to actual NCT IDs.
  - Check PubChem summary page network calls for the external table endpoint.
- Consider adding checkpointing and batching options if running the full HNID dataset.
- If needed, extend CT.gov fetching to include phase fields explicitly for faster table generation.
