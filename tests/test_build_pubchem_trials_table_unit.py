# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_trials_json(path: Path) -> None:
    rows = [
        {
            "cid": 2244,
            "collection": "ClinicalTrials.gov",
            "id": "NCT00000001",
            "id_url": "https://clinicaltrials.gov/study/NCT00000001",
            "date": "2020-01-01",
            "phase": "Phase 2",
            "status": "Completed",
            "title": "Aspirin Trial Demo",
            "smiles": "CC(=O)OC1=CC=CC=C1C(=O)O",
            "image_base64": None,
        }
    ]
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")


def _run_build(in_json: Path, out_html: Path, mode: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/build_pubchem_trials_table.py",
            "--in-json",
            str(in_json),
            "--mode",
            mode,
            "--out-html",
            str(out_html),
            "--title",
            "Unit Test PubChem Table",
        ],
        capture_output=True,
        text=True,
    )


def test_build_pubchem_trials_table_unit(tmp_path: Path):
    in_json = tmp_path / "trials.json"
    out_dt = tmp_path / "dt.html"
    out_tb = tmp_path / "tb.html"
    _write_trials_json(in_json)

    r_dt = _run_build(in_json, out_dt, "datatables")
    assert r_dt.returncode == 0, r_dt.stderr
    dt_html = out_dt.read_text(encoding="utf-8")
    assert "Export CSV" in dt_html
    assert "Export JSON" in dt_html
    assert "rows({ search: \"applied\" })" in dt_html
    assert "clinical_trials_list_filtered.csv" in dt_html
    assert "clinical_trials_list_filtered.json" in dt_html

    r_tb = _run_build(in_json, out_tb, "tabulator")
    assert r_tb.returncode == 0, r_tb.stderr
    tb_html = out_tb.read_text(encoding="utf-8")
    assert "Export CSV" in tb_html
    assert "Export JSON" in tb_html
    assert "getData(\"active\")" in tb_html
    assert "clinical_trials_list_filtered.csv" in tb_html
    assert "clinical_trials_list_filtered.json" in tb_html
