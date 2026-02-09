# 파이프라인

모듈: `src/clinical_data_analyzer/pipeline/`

이 파이프라인은 PubChem 화합물을 ClinicalTrials.gov 임상시험과 연결하고 데이터셋을 내보냅니다.

## collect_ctgov_docs 서비스 (Step1-3)

모듈: `src/clinical_data_analyzer/pipeline/collect_ctgov_docs_service.py`

목적:

- 다음 단계만 수집:
  1. HNID -> CID
  2. CID -> NCT
  3. NCT -> CTGov study documents
- CID 단위 스트리밍 처리로 진행률이 보이고, 문서가 점진적으로 쌓입니다.

주요 API:

- `CollectCtgovDocsConfig`
- `CollectCtgovDocsResult`
- `collect_ctgov_docs(config, progress_cb=None)`

결과 객체에는 통계(count)와 출력 파일 경로가 포함됩니다.

## CompoundTrialLinker

모듈: `src/clinical_data_analyzer/pipeline/linker.py`

목적:

- PubChem 동의어와 IUPAC 명을 검색어로 사용
- ClinicalTrials.gov에서 term / intervention 쿼리 검색
- 스터디 핵심 필드 출현 여부 기반으로 매칭 점수 산정

주요 설정(`LinkerConfig`):

- `max_synonyms`: CID당 사용할 동의어 최대 개수
- `ctgov_page_size`: CT.gov 페이지 크기
- `ctgov_max_pages_per_term`: 검색어당 페이지 제한
- `min_score`: 링크 허용 최소 점수
- `max_links_per_cid`: CID당 최대 링크 수

출력:

- `LinkResult(cid, nct_id, evidence)`
- `Evidence`에는 `query_mode`, `score`, `reasons` 포함

## build_dataset_for_cids

모듈: `src/clinical_data_analyzer/pipeline/build_dataset.py`

입력:

- `cids`: PubChem CID 리스트
- `pubchem_client`
- `ctgov_client`
- `config` (`DatasetBuildConfig`)

출력(JSONL):

- `compounds.jsonl`: CID -> 기본 속성 + 동의어
- `links.jsonl`: CID -> NCT ID + 매칭 근거
- `studies.jsonl`: CT.gov 스터디 원본 객체

`DatasetBuildConfig`:

- `out_dir`: 출력 디렉터리
- `write_jsonl`: True/False
- `max_synonyms_in_compound`: compounds.jsonl에 포함할 동의어 상위 N개

## CID to NCT 내보내기 (PUG-View)

모듈: `src/clinical_data_analyzer/pipeline/cid_to_nct.py`

- `cid_to_nct_ids(cid) -> List[str]`
- `cids_to_nct_ids(cids) -> Dict[int, List[str]]`
- `export_cids_nct_dataset(...)`
  - `cid_nct_links.jsonl` 생성
  - 필요 시 `compounds.jsonl` 생성

`CidToNctConfig` 주요 옵션:

- `use_ctgov_fallback`: NCT 미발견 시 CT.gov term-link fallback 활성화
- `fail_fast`: CID 오류 시 즉시 예외 발생 여부 (기본값: `False`)

`cid_nct_links.jsonl` 필드:

- `cid`
- `nct_ids`
- `n_nct`
- `source`
- `error` (옵션, CID 처리 실패 시)

`compounds.jsonl`도 화합물 메타데이터 조회 실패 시 `error` 필드를 포함할 수 있습니다.

`collect_ctgov_docs`의 `studies.jsonl`에는 아래가 포함됩니다:

- 원본 CTGov study 객체
- 조인 편의를 위한 최상위 `cid` 필드

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
