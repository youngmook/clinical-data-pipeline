# CLI

모듈: `src/clinical_data_analyzer/cli.py`

CLI는 단일 화합물 데이터셋 생성과 HNID 기반 수집 흐름을 지원합니다.

## 사용법

### 1) 단일 화합물 (레거시 경로)

```bash
python -m clinical_data_analyzer.cli --name aspirin --out out
```

```bash
python -m clinical_data_analyzer.cli --cid 2244 --out out
```

옵션:

- `--name`: PubChem으로 해석할 화합물 이름
- `--cid`: PubChem CID 직접 지정
- `--out`: 출력 디렉터리 (기본값: `out`)

출력은 `build_dataset_for_cids`와 동일합니다 (`docs/pipeline.md` 참고):

- `compounds.jsonl`
- `links.jsonl`
- `studies.jsonl`

### 2) HNID CID 다운로드

```bash
python -m clinical_data_analyzer.cli hnid-cids --hnid 1856916 --out out_hnid/clinical_trials_cids.txt
```

### 3) HNID -> CID -> NCT -> ClinicalTrials.gov

```bash
python -m clinical_data_analyzer.cli collect-ctgov --hnid 1856916 --limit 10 --out out_ctgov
```

출력:

- `cid_nct_links.jsonl`
- `compounds.jsonl`
- `studies.jsonl`

CT.gov 필드 선택(옵션):

```bash
python -m clinical_data_analyzer.cli collect-ctgov --hnid 1856916 --ctgov-fields NCTId,BriefTitle
```

## 스크립트 기반 MVP 흐름

단계별 실행이 필요하면 아래 스크립트를 사용하세요:

```bash
python scripts/fetch_cids.py --hnid 3647573 --out-dir out_mvp
python scripts/map_cid_to_nct.py --cids-file out_mvp/cids.txt --out-dir out_mvp --use-ctgov-fallback
python scripts/fetch_ctgov_docs.py --links-file out_mvp/cid_nct_links.jsonl --out-path out_mvp/studies.jsonl --resume
python scripts/build_clinical_dataset.py --links-file out_mvp/cid_nct_links.jsonl --studies-file out_mvp/studies.jsonl --out-dir out_mvp/final
```

원샷:

```bash
python scripts/run_mvp_pipeline.py --hnid 3647573 --out-dir out_mvp --use-ctgov-fallback --resume
```

### Step1-3 스트리밍 수집기 (CTGov docs 권장)

이 실행기는 다음 단계만 수행합니다:

1. HNID -> CID
2. CID -> NCT
3. NCT -> CTGov study docs

CID 단위 스트리밍으로 처리하여 진행 상황이 연속적으로 보입니다.

```bash
PYTHONUNBUFFERED=1 conda run -n clinical-pipeline python -u scripts/collect_ctgov_docs.py \
  --hnid 3647573 \
  --folder-name ctgov_docs_run1 \
  --out-root out \
  --use-ctgov-fallback \
  --resume \
  --show-progress \
  --progress-every 1
```

스모크 테스트(첫 CID + 첫 NCT):

```bash
PYTHONUNBUFFERED=1 conda run -n clinical-pipeline python -u scripts/collect_ctgov_docs.py \
  --hnid 3647573 \
  --limit-cids 1 \
  --limit-ncts 1 \
  --folder-name ctgov_docs_first1 \
  --out-root out \
  --use-ctgov-fallback \
  --show-progress \
  --progress-every 1
```
