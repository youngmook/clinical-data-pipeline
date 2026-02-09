# CLI

모듈: src/clinical_data_analyzer/cli.py

이 CLI는 단일 화합물 데이터셋 생성과 HNID 기반 수집 흐름을 지원합니다.

## 사용법

### 1) 단일 화합물 (레거시 경로)

```bash
python -m clinical_data_analyzer.cli --name aspirin --out out
```

```bash
python -m clinical_data_analyzer.cli --cid 2244 --out out
```

옵션:

- --name: PubChem으로 해석할 화합물 이름
- --cid: PubChem CID 직접 지정
- --out: 출력 디렉터리 (기본값: out)

출력은 build_dataset_for_cids와 동일합니다 (docs/pipeline.md 참고):

- compounds.jsonl
- links.jsonl
- studies.jsonl

### 2) HNID CID 다운로드

```bash
python -m clinical_data_analyzer.cli hnid-cids --hnid 1856916 --out out_hnid/clinical_trials_cids.txt
```

### 3) HNID -> CID -> NCT -> ClinicalTrials.gov

```bash
python -m clinical_data_analyzer.cli collect-ctgov --hnid 1856916 --limit 10 --out out_ctgov
```

출력:

- cid_nct_links.jsonl
- compounds.jsonl
- studies.jsonl

CT.gov 필드 선택(옵션):

```bash
python -m clinical_data_analyzer.cli collect-ctgov --hnid 1856916 --ctgov-fields NCTId,BriefTitle
```
