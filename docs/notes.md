# Notes (Handover for Next Codex)

This file is a practical handover for continuing work quickly.

## Current Direction

- Keep **service-first architecture** for pipeline orchestration.
- Keep PubChem / CTGov clients independent.
- Use script files as thin wrappers (argument parsing + logging).

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

## Key Files to Read First

- `src/clinical_data_analyzer/pipeline/collect_ctgov_docs_service.py`
- `src/clinical_data_analyzer/pipeline/cid_to_nct.py`
- `src/clinical_data_analyzer/pubchem/pug_view.py`
- `src/clinical_data_analyzer/pubchem/web_fallback/`
- `scripts/collect_ctgov_docs.py`

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

1. Align Korean docs (`README.ko.md`, `docs/*.ko.md`) with the latest streaming/service changes.
2. Add tests for `collect_ctgov_docs_service.py` (service-level unit tests with stubs/mocks).
3. Optionally add configurable fixed interval (`sleep`) between API calls when users request throttling.
