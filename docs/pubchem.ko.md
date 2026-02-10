# PubChem 클라이언트

모듈: `src/clinical_data_analyzer/pubchem/`

이 패키지는 PubChem API를 감싸서 다음 기능을 제공합니다:

- 기본 화합물 조회
- 분류 노드(HNID)
- 임상시험 관련 PUG-View 주석
- REST payload에 NCT ID가 없을 때의 웹 fallback 조회

## PubChemClient

모듈: `src/clinical_data_analyzer/pubchem/client.py`

메서드:

- `cids_by_name(name) -> List[int]`
- `compound_properties(cid) -> Dict`
  - `CanonicalSMILES`
  - `InChIKey`
  - `IUPACName`
- `synonyms(cid, max_items=50) -> List[str]`

## PubChemClassificationClient

모듈: `src/clinical_data_analyzer/pubchem/classification_nodes.py`

메서드:

- `get_ids(hnid, id_type="cids", fmt="TXT") -> List[int]`
- `get_cids(hnid, fmt="TXT") -> List[int]`

HNID 헬퍼:

모듈: `src/clinical_data_analyzer/pubchem/clinical_trials_nodes.py`

- `download_clinical_trials_cids(out_dir="out_hnid", include_sources=True)`
  - 반환 dict 키: `clinical_trials`, `clinicaltrials_gov`, `eu_register`, `japan_niph`

## PubChemPugViewClient

모듈: `src/clinical_data_analyzer/pubchem/pug_view.py`

메서드:

- `get_compound_record(cid) -> JSON`
- `nct_ids_for_cid(cid) -> List[str]`

PUG-View JSON payload에서 URL/텍스트 스캔으로 NCT ID를 추출합니다.

fallback 순서(PUG-View 기본 payload가 비어 있을 때):

1. heading 기반 PUG-View 조회 (clinical trials / drug and medication 섹션 포함)
2. PubChem web clinicaltrials endpoint fallback (`/sdq/sphinxql.cgi`)
3. PubChem compound HTML fallback

source 경로까지 함께 가져오는 메서드:

- `nct_ids_for_cid_with_source(cid) -> (List[str], str)`

## PubChemWebFallbackClient

모듈: `src/clinical_data_analyzer/pubchem/web_fallback.py`

메서드:

- `get_sdq_payload(cid, collection="clinicaltrials", limit=200, order=None) -> Dict`
- `get_clinicaltrials_sdq_payload(cid) -> Dict`
- `get_eu_register_sdq_payload(cid) -> Dict`
- `get_japan_niph_sdq_payload(cid) -> Dict`
- `get_compound_page_html(cid) -> str`
- `nct_ids_for_cid_with_source(cid) -> (List[str], str)`
- `nct_ids_for_cid(cid) -> List[str]`

이 클라이언트는 특정 CID에서 REST 응답이 불완전할 때 fallback 레이어로 사용합니다.

## 예시

CID 및 동의어 조회:

```python
from clinical_data_analyzer.pubchem import PubChemClient

pub = PubChemClient()
cids = pub.cids_by_name("aspirin")
props = pub.compound_properties(cids[0])
syms = pub.synonyms(cids[0], max_items=20)
```

PUG-View로 NCT ID 조회:

```python
from clinical_data_analyzer.pubchem import PubChemPugViewClient

pv = PubChemPugViewClient()
print(pv.nct_ids_for_cid(2244))
```
