# clinical-data-pipeline (한국어)

PubChem의 임상 관련 화합물 데이터와 ClinicalTrials.gov 임상시험 문서를 연결하는 연구용 파이프라인입니다.

이 저장소는 **공식 API 기반 수집**에 집중하며, 웹 스크래핑이나 UI 의존 방식을 사용하지 않습니다.

## 핵심 기능

1. **PubChem 임상 관련 화합물(CID) 조회**
   - PubChem PUG REST Classification Nodes API 사용
2. **화합물 메타데이터 수집**
   - SMILES, InChIKey, IUPAC name, 동의어
3. **ClinicalTrials.gov와 연결**
   - PUG-View에서 NCT ID 추출
   - CT.gov v2 API로 임상시험 문서 조회
4. **분석용 JSONL 데이터셋 생성**

## 문서

- 개요: docs/overview.ko.md
- CT.gov 클라이언트: docs/ctgov.ko.md
- PubChem 클라이언트: docs/pubchem.ko.md
- 파이프라인: docs/pipeline.ko.md
- CLI: docs/cli.ko.md

## 설치 (개발)

```bash
conda create -n clinical-pipeline python=3.11 -y
conda activate clinical-pipeline
pip install -e .
```

개발용 의존성:

```bash
pip install -e ".[dev]"
```
