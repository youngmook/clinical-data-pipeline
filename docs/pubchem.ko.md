# PubChem 클라이언트

모듈: src/clinical_data_analyzer/pubchem/

이 패키지는 PubChem REST API를 감싸서 다음 기능을 제공합니다:

- 기본 화합물 조회
- 분류 노드(HNID)
- 임상시험 관련 PUG-View 주석

## PubChemClient

모듈: src/clinical_data_analyzer/pubchem/client.py

메서드:

- cids_by_name(name) -> List[int]
- compound_properties(cid) -> Dict
  - CanonicalSMILES
  - InChIKey
  - IUPACName
- synonyms(cid, max_items=50) -> List[str]

## PubChemClassificationClient

모듈: src/clinical_data_analyzer/pubchem/classification_nodes.py

메서드:

- get_ids(hnid, id_type="cids", fmt="TXT") -> List[int]
- get_cids(hnid, fmt="TXT") -> List[int]

HNID 헬퍼:

모듈: src/clinical_data_analyzer/pubchem/clinical_trials_nodes.py

- download_clinical_trials_cids(out_dir="out_hnid", include_sources=True)
  - 반환 dict 키: clinical_trials, clinicaltrials_gov, eu_register, japan_niph

## PubChemPugViewClient

모듈: src/clinical_data_analyzer/pubchem/pug_view.py

메서드:

- get_compound_record(cid) -> JSON
- nct_ids_for_cid(cid) -> List[str]

PUG-View JSON 페이로드에서 URL/텍스트 스캔을 통해 NCT ID를 추출합니다.

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
