# ClinicalTrials.gov v2 클라이언트

모듈: src/clinical_data_analyzer/ctgov/client.py

이 클라이언트는 ClinicalTrials.gov v2 API를 감싸서 페이지네이션 검색과 스터디 조회 기능을 제공합니다.

## 클래스

### CTGovClient

생성자 필드:

- base_url: API 기본 URL (기본값 https://clinicaltrials.gov/api/v2)
- timeout: 요청 타임아웃(초) (기본값 30.0)
- user_agent: HTTP 사용자 에이전트 문자열
- max_page_size: 허용되는 최대 pageSize (기본값 1000)
- log_requests: 요청 로깅 활성화 (기본값 False)
- request_id_headers: 요청 ID를 추출할 헤더 목록

### CTGovSort

정렬 파라미터 헬퍼:

- CTGovSort.LAST_UPDATE_POST_DATE
- CTGovSort.asc(field)
- CTGovSort.desc(field)

### CTGovFilterKey

자주 쓰는 필터 키:

- overallStatus
- geo
- ids
- advanced

### 쿼리 키 검증

- CTGOV_QUERY_KEYS: 검증용 허용 키 목록
- validate_query_keys: True이면 알 수 없는 키에 대해 CTGovError 발생

## 메서드

### search_studies

시그니처:

- search_studies(cond=None, intr=None, term=None, filter=None, fmt=None, fields=None,
  query=None, validate_query_keys=False, allowed_query_keys=None, sort=None,
  page_size=50, page_token=None, count_total=False)

설명:

- fields: str 또는 list, 콤마로 결합되어 전달됨
- query: 쿼리 키 dict (예: {"titles": "aspirin"})
- sort: API에 그대로 전달됨 (CTGovSort 사용 권장)
- filter: API에 그대로 전달됨
- page_size는 [1, max_page_size] 범위로 클램프됨
- count_total 기본값은 성능을 위해 False

### iter_studies

시그니처:

- iter_studies(cond=None, intr=None, term=None, fields=None, query=None,
  validate_query_keys=False, allowed_query_keys=None, sort=None, filter=None,
  fmt=None, page_size=100, max_pages=None, max_results=None,
  start_page_token=None, raise_on_empty=False, count_total=False)

설명:

- max_pages 또는 max_results 기준으로 중지
- start_page_token으로 체크포인트에서 재개 가능
- raise_on_empty=True이면 첫 페이지가 비어 있을 때 CTGovError 발생

### get_study

시그니처:

- get_study(nct_id, fields=None, fmt=None)

설명:

- fields 지원, search_studies와 동일한 정규화 규칙 적용

### get_study_compact

시그니처:

- get_study_compact(nct_id, fields=None, fmt=None)

extract_study_compact 기준의 간소화된 필드를 반환합니다.

## 헬퍼

### extract_study_compact

전체 스터디 객체에서 다음 필드를 추출합니다:

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

## 예시

기본 검색:

```python
from clinical_data_analyzer.ctgov import CTGovClient, CTGovSort

ct = CTGovClient()
res = ct.search_studies(term="aspirin", fields=["NCTId", "BriefTitle"], sort=CTGovSort.desc("LastUpdatePostDate"))
```

검증 포함 반복 조회:

```python
from clinical_data_analyzer.ctgov import CTGovClient

ct = CTGovClient()
for s in ct.iter_studies(query={"titles": "metformin"}, validate_query_keys=True, max_results=50):
    print(s.get("protocolSection", {}).get("identificationModule", {}).get("nctId"))
```
