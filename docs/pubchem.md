# PubChem Clients

Module: src/clinical_data_analyzer/pubchem/

This package wraps PubChem REST APIs for:

- core compound lookup
- classification nodes (HNID)
- PUG-View annotations for clinical trials
- web fallback lookups for cases where REST payloads miss NCT IDs

## PubChemClient

Module: src/clinical_data_analyzer/pubchem/client.py

Methods:

- cids_by_name(name) -> List[int]
- compound_properties(cid) -> Dict
  - CanonicalSMILES
  - InChIKey
  - IUPACName
- synonyms(cid, max_items=50) -> List[str]

## PubChemClassificationClient

Module: src/clinical_data_analyzer/pubchem/classification_nodes.py

Methods:

- get_ids(hnid, id_type="cids", fmt="TXT") -> List[int]
- get_cids(hnid, fmt="TXT") -> List[int]

HNID helpers:

Module: src/clinical_data_analyzer/pubchem/clinical_trials_nodes.py

- download_clinical_trials_cids(out_dir="out_hnid", include_sources=True)
  - returns dict with keys: clinical_trials, clinicaltrials_gov, eu_register, japan_niph

## PubChemPugViewClient

Module: src/clinical_data_analyzer/pubchem/pug_view.py

Methods:

- get_compound_record(cid) -> JSON
- nct_ids_for_cid(cid) -> List[str]

This extracts NCT IDs from PUG-View JSON payloads using URL and text scanning.

Fallback behavior (when PUG-View default payload is empty):

1. heading-based PUG-View lookup (including clinical trials / drug and medication sections)
2. PubChem web clinicaltrials endpoint fallback (`/sdq/sphinxql.cgi`)
3. PubChem compound HTML fallback

You can also retrieve the source path:

- nct_ids_for_cid_with_source(cid) -> (List[str], str)

## PubChemWebFallbackClient

Module: src/clinical_data_analyzer/pubchem/web_fallback/

Methods:

- get_sdq_payload(cid, collection="clinicaltrials", limit=200, order=None) -> Dict
- get_clinicaltrials_sdq_payload(cid) -> Dict
- get_eu_register_sdq_payload(cid) -> Dict
- get_japan_niph_sdq_payload(cid) -> Dict
- get_normalized_trials(cid, collection="clinicaltrials", limit=200) -> List[Dict]
- get_normalized_trials_union(cid, collections=(...), limit_per_collection=200) -> (List[Dict], List[str])
- get_compound_page_html(cid) -> str
- nct_ids_for_cid_with_source(cid) -> (List[str], str)
- nct_ids_for_cid(cid) -> List[str]

This is intended as a fallback layer when REST responses are incomplete for a CID.

Normalized trial rows use a common schema across collections:
- id (ctid or eudractnumber)
- date (date or updatedate normalized to date)
- title
- phase
- status
- id_url (trial hyperlink from source)
- link (backward-compatible alias of id_url)
- cids

Union schema mode:
- Merges rows from ctgov/eu/jp collections
- Keeps common keys and collection-specific keys together
- Aligns rows so all keys exist (missing values are None)

## Examples

Resolve CID and synonyms:

```python
from clinical_data_analyzer.pubchem import PubChemClient

pub = PubChemClient()
cids = pub.cids_by_name("aspirin")
props = pub.compound_properties(cids[0])
syms = pub.synonyms(cids[0], max_items=20)
```

Get NCT IDs via PUG-View:

```python
from clinical_data_analyzer.pubchem import PubChemPugViewClient

pv = PubChemPugViewClient()
print(pv.nct_ids_for_cid(2244))
```
