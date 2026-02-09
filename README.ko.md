# clinical-data-pipeline (한국어)

PubChem의 임상 관련 화합물 데이터와 ClinicalTrials.gov 임상시험 문서를 연결하기 위한 연구용 파이프라인입니다.

이 저장소는 **공식 API 기반의 재현 가능한 수집**에 집중하며, 웹 스크래핑이나 UI 의존 방식은 사용하지 않습니다.

---

## 이 프로젝트가 하는 일

이 프로젝트는 최소한의 핵심 기능을 제공하면서도 확장 가능한 파이프라인을 제공합니다:

1. **PubChem에서 임상시험 관련 화합물(CID) 조회**

   * 공식 **PubChem PUG REST Classification Nodes API** 사용
   * *Clinical Trials*, *ClinicalTrials.gov* 등 특정 분류 노드(HNID)에서 CID 목록 수집

2. **PubChem에서 화합물 메타데이터 수집**

   * Canonical SMILES, InChIKey, IUPAC name
   * PUG REST를 통한 동의어 및 식별자 수집

3. **PubChem 화합물을 ClinicalTrials.gov와 연결**

   * PubChem 주석(PUG-View)에서 **NCT ID** 추출
   * **ClinicalTrials.gov v2 API**로 임상시험 문서 조회

4. **분석용 데이터셋 내보내기**

   * 화합물, 링크, 임상시험 문서에 대한 JSONL 출력
   * 다운스트림 분석/모델링/시각화 파이프라인에서 사용 가능

---

## 핵심 설계 원칙

* **공식 API만 사용**

  * PubChem PUG REST (Classification Nodes, PUG-View)
  * ClinicalTrials.gov v2 API
* **Selenium/웹 UI 스크래핑 사용 안 함**
* **재현 가능성**

  * Classification Nodes(HNID)는 안정적인 식별자
* **모듈화**

  * PubChem 관련 기능은 독립적인 서브패키지로 구성

---

## PubChem 분류 노드 (HNID)

PubChem은 분류 노드에 연결된 식별자를 공식 API로 제공합니다:

```
https://pubchem.ncbi.nlm.nih.gov/rest/pug/classification/hnid/{HNID}/{id_type}/{format}
```

현재 프로젝트는 임상시험 관련 노드에서 **화합물 CID 조회**를 지원합니다.

### 사용 중인 임상시험 관련 HNID

| HNID    | 설명                                |
| ------- | ----------------------------------- |
| 1856916 | Clinical Trials (전체 소스)         |
| 3647573 | ClinicalTrials.gov                  |
| 3647574 | EU Clinical Trials Register         |
| 3647575 | NIPH Clinical Trials Search of Japan|

---

## 빠른 예시

### 1) 임상시험 관련 PubChem CID 다운로드 (HNID 기반)

```python
from clinical_data_analyzer.pubchem.clinical_trials_nodes import download_clinical_trials_cids

results = download_clinical_trials_cids(out_dir="out_hnid")

print("Clinical Trials (all):", len(results["clinical_trials"]))
print("ClinicalTrials.gov only:", len(results["clinicaltrials_gov"]))
```

생성되는 파일 예시:

```
out_hnid/
├─ clinical_trials_cids.txt
├─ clinicaltrials_gov_cids.txt
├─ eu_register_cids.txt
└─ japan_niph_cids.txt
```

---

### 2) HNID → CID → ClinicalTrials.gov 문서

아래 예시는 전체 파이프라인을 보여줍니다:

1. PubChem HNID에서 임상시험 관련 CID 다운로드
2. PubChem PUG-View 주석에서 NCT ID 추출
3. ClinicalTrials.gov에서 임상시험 문서 조회

```python
from clinical_data_analyzer.pubchem import (
    PubChemClient,
    PubChemClassificationClient,
    PubChemPugViewClient,
)
from clinical_data_analyzer.ctgov.client import CTGovClient

# Clinical Trials HNID
HNID = 1856916

pubchem = PubChemClient()
class_nodes = PubChemClassificationClient()
pug_view = PubChemPugViewClient()
ctgov = CTGovClient()

# Step 1: HNID → CID list
cids = class_nodes.get_cids(HNID)
print("Total CIDs:", len(cids))

# (optional) limit for a quick test
cids = cids[:10]

# Step 2–3: CID → NCT → CTGov study document
for cid in cids:
    nct_ids = pug_view.nct_ids_for_cid(cid)
    for nct in nct_ids:
        study = ctgov.get_study(nct)
        print(cid, nct, study.get("protocolSection", {}).get("identificationModule", {}).get("briefTitle"))
```

이 예시는 개별 모듈을 조합하여 재현 가능한 엔드투엔드 파이프라인을 구성하는 방법을 보여줍니다.

생성되는 파일 예시:

```
out_hnid/
├─ clinical_trials_cids.txt
├─ clinicaltrials_gov_cids.txt
├─ eu_register_cids.txt
└─ japan_niph_cids.txt
```

---

## 패키지 구조

```
src/clinical_data_analyzer/
├─ pubchem/
│  ├─ client.py                  # PUG REST: CID, properties, synonyms
│  ├─ classification_nodes.py    # HNID → CID (Classification Nodes API)
│  ├─ clinical_trials_nodes.py   # 임상시험 관련 HNID 헬퍼
│  └─ pug_view.py                # PUG-View: NCT ID 추출
│
├─ ctgov/
│  └─ client.py                  # ClinicalTrials.gov v2 API
│
├─ pipeline/
│  └─ ...                        # 데이터셋 빌더 및 링크 로직
```

---

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

---

## Documentation

프로젝트 문서는 `docs/` 폴더에 있습니다.

- English:
  - docs/overview.md
  - docs/ctgov.md
  - docs/pubchem.md
  - docs/pipeline.md
  - docs/cli.md
- Korean:
  - docs/overview.ko.md
  - docs/ctgov.ko.md
  - docs/pubchem.ko.md
  - docs/pipeline.ko.md
  - docs/cli.ko.md

---

## CLI 사용법

파이썬 코드를 작성하지 않고도 재현 가능한 실행을 위한 최소 CLI를 제공합니다.

### 도움말

```bash
clinical-data-analyzer --help
```

### 임상시험 관련 CID 다운로드 (HNID)

*Clinical Trials* 분류 노드와 연결된 PubChem 화합물 ID를 다운로드합니다:

```bash
clinical-data-analyzer hnid-cids \
  --hnid 1856916 \
  --out out_hnid/clinical_trials_cids.txt
```

공식 PubChem Classification Nodes API 사용:

```
/rest/pug/classification/hnid/{HNID}/cids/TXT
```

### 엔드투엔드 예시: HNID → CID → ClinicalTrials.gov 문서

빠른 검증을 위한 소규모 엔드투엔드 실행:

```bash
clinical-data-analyzer collect-ctgov \
  --hnid 1856916 \
  --limit 10 \
  --out out_ctgov
```

이 명령은 다음을 수행합니다:

1. 지정한 HNID에서 CID 조회
2. PubChem PUG-View에서 NCT ID 추출
3. ClinicalTrials.gov에서 임상시험 문서 다운로드

생성되는 파일:

```
out_ctgov/
├─ compounds.jsonl
├─ links.jsonl
└─ studies.jsonl
