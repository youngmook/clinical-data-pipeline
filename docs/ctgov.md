# ClinicalTrials.gov v2 Client

Module: src/clinical_data_analyzer/ctgov/client.py

This client wraps the ClinicalTrials.gov v2 API and provides paginated search and study retrieval.

## Classes

### CTGovClient

Constructor fields:

- base_url: API base (default https://clinicaltrials.gov/api/v2)
- timeout: request timeout seconds (default 30.0)
- user_agent: HTTP user agent string
- max_page_size: max pageSize allowed (default 1000)
- log_requests: enable request logging (default False)
- request_id_headers: headers used to capture request id

### CTGovSort

Helpers for sort parameters:

- CTGovSort.LAST_UPDATE_POST_DATE
- CTGovSort.asc(field)
- CTGovSort.desc(field)

### CTGovFilterKey

Common filter keys:

- overallStatus
- geo
- ids
- advanced

### Query Key Validation

- CTGOV_QUERY_KEYS: allowed query keys for optional validation
- validate_query_keys: when True, unknown keys raise CTGovError

## Methods

### search_studies

Signature:

- search_studies(cond=None, intr=None, term=None, filter=None, fmt=None, fields=None,
  query=None, validate_query_keys=False, allowed_query_keys=None, sort=None,
  page_size=50, page_token=None, count_total=False)

Notes:

- fields: str or list, sent as comma-separated
- query: dict of query keys (e.g. {"titles": "aspirin"})
- sort: passed as-is to API (use CTGovSort helpers)
- filter: passed as-is to API
- page_size is clamped to [1, max_page_size]
- count_total defaults to False for performance

### iter_studies

Signature:

- iter_studies(cond=None, intr=None, term=None, fields=None, query=None,
  validate_query_keys=False, allowed_query_keys=None, sort=None, filter=None,
  fmt=None, page_size=100, max_pages=None, max_results=None,
  start_page_token=None, raise_on_empty=False, count_total=False)

Notes:

- stop by max_pages or max_results
- start_page_token allows resume from checkpoints
- raise_on_empty raises CTGovError if first page has no studies

### get_study

Signature:

- get_study(nct_id, fields=None, fmt=None)

Notes:

- fields supported, same normalization as search

### get_study_compact

Signature:

- get_study_compact(nct_id, fields=None, fmt=None)

Returns a compact subset of fields (see extract_study_compact).

## Helper

### extract_study_compact

Given a full study object, returns:

- nct_id
- brief_title
- official_title
- overall_status
- start_date
- completion_date
- conditions
- interventions
- lead_sponsor
- collaborators

## Examples

Basic search:

```python
from clinical_data_analyzer.ctgov import CTGovClient, CTGovSort

ct = CTGovClient()
res = ct.search_studies(term="aspirin", fields=["NCTId", "BriefTitle"], sort=CTGovSort.desc("LastUpdatePostDate"))
```

Iterate with validation:

```python
from clinical_data_analyzer.ctgov import CTGovClient

ct = CTGovClient()
for s in ct.iter_studies(query={"titles": "metformin"}, validate_query_keys=True, max_results=50):
    print(s.get("protocolSection", {}).get("identificationModule", {}).get("nctId"))
```
