# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, "scripts/update_studies_history.py", *args], capture_output=True, text=True)


def test_update_studies_history_unit(tmp_path: Path):
    src = tmp_path / "src"
    src.mkdir(parents=True, exist_ok=True)

    studies = src / "studies.jsonl"
    studies.write_text('{"nct":"NCT1"}\n', encoding="utf-8")

    state = tmp_path / "data" / "collection_state.json"
    latest = tmp_path / "data" / "studies.jsonl"
    history = tmp_path / "data" / "history"
    flag = tmp_path / "changed.txt"

    r1 = _run(
        [
            "--studies-file",
            str(studies),
            "--state-file",
            str(state),
            "--latest-file",
            str(latest),
            "--history-dir",
            str(history),
            "--timestamp",
            "2026-02-10T00:00:00Z",
            "--changed-flag-path",
            str(flag),
        ]
    )
    assert r1.returncode == 0, r1.stderr
    assert "changed: true" in r1.stdout
    assert latest.exists()
    assert len(list(history.glob("studies_*.jsonl"))) == 1
    assert flag.read_text(encoding="utf-8").strip() == "true"

    r2 = _run(
        [
            "--studies-file",
            str(studies),
            "--state-file",
            str(state),
            "--latest-file",
            str(latest),
            "--history-dir",
            str(history),
            "--timestamp",
            "2026-02-10T01:00:00Z",
            "--changed-flag-path",
            str(flag),
        ]
    )
    assert r2.returncode == 0, r2.stderr
    assert "changed: false" in r2.stdout
    assert len(list(history.glob("studies_*.jsonl"))) == 1
    assert flag.read_text(encoding="utf-8").strip() == "false"

    studies.write_text('{"nct":"NCT1"}\n{"nct":"NCT2"}\n', encoding="utf-8")

    r3 = _run(
        [
            "--studies-file",
            str(studies),
            "--state-file",
            str(state),
            "--latest-file",
            str(latest),
            "--history-dir",
            str(history),
            "--timestamp",
            "2026-02-10T02:00:00Z",
            "--changed-flag-path",
            str(flag),
        ]
    )
    assert r3.returncode == 0, r3.stderr
    assert "changed: true" in r3.stdout
    assert len(list(history.glob("studies_*.jsonl"))) == 2

    state_obj = json.loads(state.read_text(encoding="utf-8"))
    assert state_obj["latest_row_count"] == 2
    assert state_obj["history_count"] == 2
