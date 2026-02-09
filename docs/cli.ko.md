# CLI

모듈: src/clinical_data_analyzer/cli.py

이 CLI는 화합물을 해석하고 데이터셋을 생성합니다.

## 사용법

```bash
python -m clinical_data_analyzer.cli --name aspirin --out out
```

```bash
python -m clinical_data_analyzer.cli --cid 2244 --out out
```

## 옵션

- --name: PubChem으로 해석할 화합물 이름
- --cid: PubChem CID 직접 지정
- --out: 출력 디렉터리 (기본값: out)

출력은 build_dataset_for_cids와 동일합니다 (docs/pipeline.md 참고).
