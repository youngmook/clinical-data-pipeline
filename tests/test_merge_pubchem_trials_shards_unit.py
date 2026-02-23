from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_merge_pubchem_trials_shards_unit(tmp_path: Path):
    shard1 = tmp_path / "shard1"
    shard2 = tmp_path / "shard2"
    shard1.mkdir()
    shard2.mkdir()

    row_a = {
        "cid": 11,
        "collection": "ClinicalTrials.gov",
        "id": "NCT00000011",
        "title": "Trial 11",
        "date": "2020-01-01",
    }
    row_b = {
        "cid": 12,
        "collection": "ClinicalTrials.gov",
        "id": "NCT00000012",
        "title": "Trial 12",
        "date": "2020-01-02",
    }

    (shard1 / "trials.jsonl").write_text(
        json.dumps(row_a, ensure_ascii=False) + "\n" + json.dumps(row_b, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    # Duplicate row_b across shards to validate dedupe.
    (shard2 / "trials.jsonl").write_text(
        json.dumps(row_b, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "merged"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/merge_pubchem_trials_shards.py",
            "--shard-dirs",
            f"{shard1},{shard2}",
            "--out-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    rows = [json.loads(x) for x in (out_dir / "trials.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 2

    summary = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["n_shards"] == 2
    assert summary["n_input_rows"] == 3
    assert summary["n_rows"] == 2
    assert summary["n_cids"] == 2
