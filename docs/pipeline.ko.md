# 파이프라인

모듈: src/clinical_data_analyzer/pipeline/

이 파이프라인은 PubChem 화합물을 ClinicalTrials.gov 임상시험과 연결하고 데이터셋을 내보냅니다.

## CompoundTrialLinker

모듈: src/clinical_data_analyzer/pipeline/linker.py

목적:

- PubChem 동의어 및 IUPAC 명을 검색어로 사용
- ClinicalTrials.gov에서 term 및 intervention 쿼리로 검색
- 스터디 핵심 필드 내 출현 여부로 매칭 점수 산정

주요 설정 (LinkerConfig):

- max_synonyms: CID당 사용할 동의어 최대 개수
- ctgov_page_size: CT.gov 페이지 크기
- ctgov_max_pages_per_term: 검색어당 페이지 수 제한
- min_score: 링크를 허용하는 최소 점수
- max_links_per_cid: CID당 최대 링크 수

출력:

- LinkResult(cid, nct_id, evidence)
- Evidence에는 query_mode, score, reasons 포함

## build_dataset_for_cids

모듈: src/clinical_data_analyzer/pipeline/build_dataset.py

입력:

- cids: PubChem CID 리스트
- pubchem_client
- ctgov_client
- config (DatasetBuildConfig)

출력 (JSONL):

- compounds.jsonl: CID -> 기본 속성 + 동의어
- links.jsonl: CID -> NCT ID + 매칭 근거
- studies.jsonl: CT.gov 스터디 원본 객체

DatasetBuildConfig:

- out_dir: 출력 디렉터리
- write_jsonl: True/False
- max_synonyms_in_compound: compounds.jsonl에 포함할 동의어 수

## CID to NCT 내보내기 (PUG-View)

모듈: src/clinical_data_analyzer/pipeline/cid_to_nct.py

- cid_to_nct_ids(cid) -> List[str]
- cids_to_nct_ids(cids) -> Dict[int, List[str]]
- export_cids_nct_dataset(...)
  - cid_nct_links.jsonl 생성
  - 선택적으로 compounds.jsonl 생성

## 예시

```python
from clinical_data_analyzer import CTGovClient, PubChemClient
from clinical_data_analyzer.pipeline import build_dataset_for_cids

pub = PubChemClient()
ct = CTGovClient()

cids = pub.cids_by_name("aspirin")[:1]
paths = build_dataset_for_cids(cids, pub, ct)
print(paths)
```
