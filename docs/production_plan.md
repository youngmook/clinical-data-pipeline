# Production Readiness Plan

This document defines a practical path to move `clinical-data-pipeline`
from current MVP/automation state to production-grade operation.

## 1) Current Baseline (as of 2026-02-10)

- CTGov scheduled collection exists (`.github/workflows/ctgov_collect.yml`)
  - collects step1-3 pipeline outputs
  - maintains latest/history snapshots under `data/ctgov/`
- PubChem table Pages workflow exists (`.github/workflows/clinical_compound_table_pages.yml`)
  - exports PubChem trial rows and builds static table HTML
- Table UX includes:
  - search
  - pagination
  - filtered export (CSV/JSON)
  - CTGov/PubChem row links
- Core functionality works, but production controls are still partial:
  - no formal SLOs
  - limited service-level tests
  - limited alerting/runbook/incident process

## 2) Production Goals

1. Daily data collection is reliable and observable.
2. Public table outputs are reproducible and schema-stable.
3. Data history is preserved with clear change tracking.
4. Failures are detected quickly and recoverable with documented runbooks.
5. Release process is predictable (versioning, migration notes, rollback).

## 3) Scope

### In Scope

- GitHub Actions reliability and deployment model
- Data contracts and schema governance for output files
- Quality checks and trend metrics
- Operational controls (alerting, runbook, incident checklist)
- Documentation for maintainers/users

### Out of Scope (for this cycle)

- Replacing static pages with a full backend service
- Real-time streaming ingestion
- Heavy analytics/modeling features beyond current table outputs

## 4) Production Acceptance Criteria

The system is considered production-ready when all conditions are met:

1. Workflow reliability:
   - `ctgov_collect` and `pubchem_table_pages` success rate >= 98% on recent scheduled runs
2. Data freshness:
   - each scheduled run updates snapshots successfully (excluding upstream outages)
3. Schema stability:
   - versioned schema documented
   - breaking changes gated by migration notes
4. Monitoring:
   - failures and zero-row anomalies trigger notification
5. Recoverability:
   - runbook can restore a broken run within 1 business hour
6. Tests:
   - service-level tests and key script tests passing in CI

## 5) Workstreams

## WS-1. Data Contract and Schema Governance

Deliverables:

- `docs/data_contract.md` (new)
  - required/optional fields per output:
    - `data/ctgov/studies.jsonl`
    - `data/ctgov/final/clinical_compound_trials.csv`
    - `out/pubchem_trials_dataset_gh/trials.*`
- explicit schema version fields in summary/state outputs
- compatibility policy for `source_url`, `ctgov_url`, `pubchem_url`

Exit Criteria:

- Contract doc reviewed and linked from `README.md`
- CI check validates required columns in generated CSV/JSON

## WS-2. Workflow Reliability and Idempotency

Deliverables:

- retries/timeouts standardized in scripts and workflows
- safe resume behavior validated for:
  - partial runs
  - no-change runs
  - upstream transient errors
- split deployment clarity:
  - CTGov data updates vs PubChem Pages deployment

Exit Criteria:

- at least 10 consecutive scheduled runs without manual hotfix

## WS-3. Data Quality and Change Auditing

Deliverables:

- `summary.json` extensions:
  - row counts
  - unique CID/NCT counts
  - changed/new/deleted estimates
- anomaly checks:
  - sudden drop to 0 rows
  - abnormal delta spike
- historical index file for snapshots

Exit Criteria:

- Each run produces a machine-readable quality summary
- Anomaly checks fail workflow with clear reason

## WS-4. Observability, Alerting, and Runbook

Deliverables:

- notification integration (GitHub issue, webhook, or Slack/email relay)
- `docs/runbook.md` (new)
  - common failures (DNS, rate limit, Pages, push permissions)
  - step-by-step recovery
  - rollback procedure

Exit Criteria:

- Simulated failure drill completed and documented

## WS-5. Test Coverage and Release Discipline

Deliverables:

- service-level unit tests for:
  - `collect_ctgov_docs_service.py`
  - pubchem export schema normalization paths
- CI matrix:
  - script smoke tests
  - docs link checks for critical docs
- release checklist doc:
  - version bump
  - changelog
  - tag
  - post-release verification

Exit Criteria:

- CI gates required before merge to `main`

## 6) Execution Plan (Milestone-Based, No Fixed Timeline)

### Milestone A: Stabilize Interfaces

- finalize production scope and acceptance criteria
- freeze output schema for current cycle
- create `docs/data_contract.md`

### Milestone B: Reliability Hardening

- add retry/backoff/timeouts where missing
- validate resume/idempotent behavior with tests
- tighten workflow permissions and branch protections

### Milestone C: Quality Metrics and Auditing

- implement per-run summary metrics
- add anomaly thresholds and workflow guardrails
- expose trend metadata for maintainers

### Milestone D: Runbook and Alerts

- add notifier
- write and validate runbook with one simulated incident

### Milestone E: Test Expansion and CI Gates

- add service-level tests
- add schema validation checks in CI
- enforce required checks for merges

### Milestone F: Release Candidate and Go-Live

- dry-run release (`v0.3.0-rc` style internally)
- final production checklist
- publish `v0.3.0` (or agreed target) with migration notes

## 7) Risk Register

1. Upstream API instability (PubChem/CTGov)
   - Mitigation: retries, fallback chain, anomaly checks, runbook
2. GitHub Pages/Actions outages
   - Mitigation: rerun protocol, cached artifacts, clear operator guide
3. Schema drift causing table breakage
   - Mitigation: schema contract + CI validation + compatibility alias fields
4. Data growth causing client-side table slowdowns
   - Mitigation: pagination/export already in place, add lazy mode if needed

## 8) Immediate Next Actions (Priority Order)

1. Add `docs/data_contract.md` and schema validator script.
2. Add service-level tests for `collect_ctgov_docs_service.py`.
3. Add anomaly checks to scheduled workflows.
4. Add `docs/runbook.md` and connect alert channel.
5. Apply branch protection requiring CI for `main`.
