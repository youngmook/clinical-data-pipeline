# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def test_build_ctgov_table_unit(tmp_path: Path):
    # Create a stub module to replace clinical_data_analyzer.* for the subprocess
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()

    (stub_dir / "clinical_data_analyzer").mkdir()
    (stub_dir / "clinical_data_analyzer" / "__init__.py").write_text("", encoding="utf-8")

    # ctgov
    (stub_dir / "clinical_data_analyzer" / "ctgov").mkdir()
    (stub_dir / "clinical_data_analyzer" / "ctgov" / "__init__.py").write_text(
        "from .client import CTGovClient\n",
        encoding="utf-8",
    )
    (stub_dir / "clinical_data_analyzer" / "ctgov" / "client.py").write_text(
        "class CTGovClient:\n"
        "    def get_study(self, nct_id, fields=None):\n"
        "        return {\"protocolSection\": {\"identificationModule\": {\"nctId\": nct_id, \"briefTitle\": \"Test Title\"},\n"
        "                          \"designModule\": {\"phases\": [\"PHASE2\"]}}}\n",
        encoding="utf-8",
    )

    # pubchem
    (stub_dir / "clinical_data_analyzer" / "pubchem").mkdir()
    (stub_dir / "clinical_data_analyzer" / "pubchem" / "__init__.py").write_text(
        "from .classification_nodes import PubChemClassificationClient\n"
        "from .pug_view import PubChemPugViewClient\n",
        encoding="utf-8",
    )
    (stub_dir / "clinical_data_analyzer" / "pubchem" / "classification_nodes.py").write_text(
        "class PubChemClassificationClient:\n"
        "    def get_cids(self, hnid, fmt=\"TXT\"):\n"
        "        return [111, 222]\n",
        encoding="utf-8",
    )
    (stub_dir / "clinical_data_analyzer" / "pubchem" / "pug_view.py").write_text(
        "class PubChemPugViewClient:\n"
        "    def nct_ids_for_cid(self, cid):\n"
        "        return [f\"NCT{cid:08d}\"]\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"
    env = {"PYTHONPATH": str(stub_dir)}

    result = subprocess.run(
        [
            sys.executable,
            "scripts/build_ctgov_table.py",
            "--hnid",
            "3647573",
            "--out-dir",
            str(out_dir),
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr

    # Validate outputs
    links = out_dir / "cid_nct_links.jsonl"
    assert links.exists()
    rows = [json.loads(line) for line in links.read_text(encoding="utf-8").splitlines() if line]
    assert rows[0]["cid"] == 111

    table = out_dir / "ctgov_table.csv"
    assert table.exists()
    with table.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        first = next(reader)
    assert header == ["cid", "nct_id", "title", "phase"]
    assert first[1].startswith("NCT")
    assert first[2] == "Test Title"
    assert first[3] == "PHASE2"
