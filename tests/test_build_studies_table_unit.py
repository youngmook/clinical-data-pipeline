# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def test_build_studies_table_unit(tmp_path: Path):
    in_dir = tmp_path / "in"
    out_dir = tmp_path / "site"
    in_dir.mkdir(parents=True, exist_ok=True)

    dataset_csv = in_dir / "clinical_compound_trials.csv"
    with dataset_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "cid",
                "nct_id",
                "compound_name",
                "title",
                "phase",
                "overall_status",
                "conditions",
                "interventions",
                "targets",
                "start_date",
                "completion_date",
                "last_update_date",
                "ctgov_url",
                "pubchem_url",
                "source_url",
            ]
        )
        w.writerow(
            [
                "2244",
                "NCT00000001",
                "aspirin",
                "Aspirin Trial",
                "PHASE2",
                "COMPLETED",
                "Condition A",
                "Aspirin",
                "",
                "2010-01-01",
                "2011-01-01",
                "2012-01-01",
                "https://clinicaltrials.gov/study/NCT00000001",
                "https://pubchem.ncbi.nlm.nih.gov/compound/2244",
                "https://clinicaltrials.gov/study/NCT00000001",
            ]
        )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_studies_table.py",
            "--dataset-csv",
            str(dataset_csv),
            "--out-dir",
            str(out_dir),
            "--title",
            "Unit Test Table",
        ],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr

    out_csv = out_dir / "studies.csv"
    out_json = out_dir / "studies.json"
    out_html = out_dir / "index.html"

    assert out_csv.exists()
    assert out_json.exists()
    assert out_html.exists()

    rows = json.loads(out_json.read_text(encoding="utf-8"))
    assert rows and rows[0]["nct_id"] == "NCT00000001"

    html = out_html.read_text(encoding="utf-8")
    assert "Unit Test Table" in html
    assert "studies.json" in html
    assert "pubchem" in html
