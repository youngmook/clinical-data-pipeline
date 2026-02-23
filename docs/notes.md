# Notes (Handover for Next Codex)

This file is a practical handover for continuing work quickly.

## Current Direction

- Keep **service-first architecture** for CTGov step1-3 orchestration.
- Keep PubChem / CTGov clients independent, with provider-specific PubChem fallback modules.
- Use script files as thin wrappers (argument parsing + logging), and dedicated export/build scripts for static table publishing.

## What Was Completed

1. CID -> NCT fallback chain was strengthened:
   - PUG-View default
   - PUG-View heading lookup
   - PubChem web clinicaltrials endpoint (`/sdq/sphinxql.cgi`)
   - PubChem HTML fallback
   - optional CTGov term-link fallback
2. CID-level error handling improved:
   - non-fail-fast mode supported
   - error details written into output rows
3. `studies.jsonl` now includes top-level `cid` in step1-3 collector output.
4. Step1-3 collector moved toward service pattern:
   - `src/clinical_data_analyzer/pipeline/collect_ctgov_docs_service.py`
   - wrappers:
     - `scripts/collect_ctgov_docs.py`
5. Streaming collection behavior implemented for better visibility:
   - CID-by-CID mapping and immediate CTGov fetch per CID.
6. Added CTGov automation with snapshot persistence:
   - `.github/workflows/ctgov_collect.yml`
   - updates `data/ctgov/studies.jsonl`, `data/ctgov/history/studies_*.jsonl`, `data/ctgov/collection_state.json`
7. Added PubChem trials export + static table publishing workflow:
   - `.github/workflows/clinical_compound_table_pages.yml`
   - export script: `scripts/export_pubchem_trials_dataset.py`
   - table builder: `scripts/build_pubchem_trials_table.py`
8. Added client-side table UX improvements for CTGov page:
   - pagination (`25/50/100`)
   - filtered CSV/JSON export buttons
   - NCT ID linked to CTGov, plus PubChem link per row
9. Refactored PubChem fallback internals:
   - legacy single-file fallback removed
   - provider-based modules under `src/clinical_data_analyzer/pubchem/web_fallback/`
   - normalized union schema uses `id`/`date` and `id_url`

## Key Files to Read First

- `src/clinical_data_analyzer/pipeline/collect_ctgov_docs_service.py`
- `src/clinical_data_analyzer/pipeline/cid_to_nct.py`
- `src/clinical_data_analyzer/pubchem/pug_view.py`
- `src/clinical_data_analyzer/pubchem/web_fallback/`
- `scripts/collect_ctgov_docs.py`
- `scripts/update_studies_history.py`
- `scripts/export_pubchem_trials_dataset.py`
- `scripts/build_pubchem_trials_table.py`
- `.github/workflows/ctgov_collect.yml`
- `.github/workflows/clinical_compound_table_pages.yml`

## Output Contract (Step1-3 Collector)

Output folder:
- `out/<folder-name>/`

Files:
- `cids.txt`
- `cids.jsonl`
- `cid_nct_links.jsonl`
- `cid_nct_map.csv`
- `compounds.jsonl`
- `studies.jsonl` (with top-level `cid`)

## Known Environment Issue

- In restricted environments, PubChem host resolution may fail:
  - `Failed to resolve 'pubchem.ncbi.nlm.nih.gov'`
- This is a DNS/network issue, not a parser-only issue.

## Recommended Run Commands

Main step1-3 run:

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

Quick smoke:

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

## Next Practical Improvements

1. Add service-level unit tests for `collect_ctgov_docs_service.py` (stubs/mocks, resume edge cases).
2. Align all Korean docs (`README.ko.md`, `docs/*.ko.md`) with latest PubChem table workflow details.
3. Add optional throttling controls (`sleep`/rate policy) for long-running scheduled collection jobs.
4. Consider split Pages routing (CTGov table vs PubChem table) with separate paths to avoid deployment overlap.
