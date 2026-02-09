# Clinical Data Pipeline 문서

이 폴더는 clinical-data-pipeline 프로젝트의 모듈과 사용법을 문서화합니다.

## 목차

- docs/overview.md: 프로젝트 개요와 아키텍처
- docs/ctgov.md: ClinicalTrials.gov v2 클라이언트 API
- docs/pubchem.md: PubChem 클라이언트 (REST, Classification, PUG-View)
- docs/pipeline.md: 링크 및 데이터셋 빌더
- docs/cli.md: CLI 사용법 및 예시

## 빠른 아키텍처

이 프로젝트는 PubChem에서 화합물 데이터를 가져오고 ClinicalTrials.gov 임상시험과 연결합니다.

고수준 흐름:

1. PubChem에서 화합물 식별자(CID) 해석
2. 화합물 속성 및 동의어 수집
3. 텍스트 매칭 또는 PUG-View 주석을 통해 CT.gov 임상시험과 연결
4. JSONL 데이터셋으로 내보내기

핵심 패키지:

- clinical_data_analyzer.ctgov: ClinicalTrials.gov v2 API 클라이언트
- clinical_data_analyzer.pubchem: PubChem REST 및 PUG-View 클라이언트
- clinical_data_analyzer.pipeline: 링크 및 데이터셋 생성 로직

## 출력 (JSONL)

일반적으로 생성되는 출력은 다음과 같습니다:

- compounds.jsonl
- links.jsonl
- studies.jsonl
- cid_nct_links.jsonl

정확한 출력 형식은 docs/pipeline.md를 참고하세요.
