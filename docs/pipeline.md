# Pipeline

Module: src/clinical_data_analyzer/pipeline/

The pipeline links PubChem compounds to ClinicalTrials.gov studies and exports datasets.

## CompoundTrialLinker

Module: src/clinical_data_analyzer/pipeline/linker.py

Purpose:

- Uses PubChem synonyms and IUPAC name as search terms
- Searches ClinicalTrials.gov with term and intervention queries
- Scores matches based on occurrences in study core fields

Key config (LinkerConfig):

- max_synonyms: max number of synonyms used per CID
- ctgov_page_size: page size for CT.gov
- ctgov_max_pages_per_term: limit pagination per term
- min_score: minimum score to accept a link
- max_links_per_cid: stop after this many links

Output:

- LinkResult(cid, nct_id, evidence)
- Evidence includes query_mode, score, and reasons

## build_dataset_for_cids

Module: src/clinical_data_analyzer/pipeline/build_dataset.py

Inputs:

- cids: list of PubChem CIDs
- pubchem_client
- ctgov_client
- config (DatasetBuildConfig)

Outputs (JSONL):

- compounds.jsonl: CID -> basic properties + synonyms
- links.jsonl: CID -> NCT ID + matching evidence
- studies.jsonl: raw CT.gov study objects

DatasetBuildConfig:

- out_dir: output directory
- write_jsonl: True/False
- max_synonyms_in_compound: include top N synonyms in compounds.jsonl

## CID to NCT export (PUG-View)

Module: src/clinical_data_analyzer/pipeline/cid_to_nct.py

- cid_to_nct_ids(cid) -> List[str]
- cids_to_nct_ids(cids) -> Dict[int, List[str]]
- export_cids_nct_dataset(...)
  - writes cid_nct_links.jsonl
  - optionally compounds.jsonl (basic properties)

`CidToNctConfig` supports:

- use_ctgov_fallback: enable CT.gov term-link fallback when no NCT IDs are found
- fail_fast: raise immediately on CID errors (default: False)

`cid_nct_links.jsonl` row fields:

- cid
- nct_ids
- n_nct
- source
- error (optional, when CID-level retrieval fails)

`compounds.jsonl` row fields include optional `error` when compound metadata retrieval fails.

## Example

```python
from clinical_data_analyzer import CTGovClient, PubChemClient
from clinical_data_analyzer.pipeline import build_dataset_for_cids

pub = PubChemClient()
ct = CTGovClient()

cids = pub.cids_by_name("aspirin")[:1]
paths = build_dataset_for_cids(cids, pub, ct)
print(paths)
```
