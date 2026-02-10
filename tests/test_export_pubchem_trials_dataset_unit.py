from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def test_export_pubchem_trials_dataset_unit(tmp_path: Path):
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()

    pkg = stub_dir / "clinical_data_analyzer"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")

    pubchem_pkg = pkg / "pubchem"
    pubchem_pkg.mkdir()
    (pubchem_pkg / "__init__.py").write_text(
        "class PubChemClassificationClient:\n"
        "    def get_cids(self, hnid, fmt='TXT'):\n"
        "        return [119]\n\n"
        "class PubChemClient:\n"
        "    def compound_properties(self, cid):\n"
        "        return {'CanonicalSMILES':'C1=CC=CC=C1','InChIKey':'KEY','IUPACName':'benzene'}\n\n"
        "class PubChemWebFallbackClient:\n"
        "    def get_normalized_trials_union(self, cid, collections=('clinicaltrials',), limit_per_collection=200):\n"
        "        rows=[\n"
        "          {'collection':'clinicaltrials','id':'NCT00000001','title':'Trial A','phase':'Phase 2','status':'Completed','date':'2020-01-01','id_url':'https://clinicaltrials.gov/study/NCT00000001','link':'https://clinicaltrials.gov/study/NCT00000001'},\n"
        "          {'collection':'clinicaltrials_eu','id':'2006-006023-39','title':'Trial EU','phase':'Phase 2','status':'Completed','date':'2007-09-24','id_url':'https://www.clinicaltrialsregister.eu/ctr-search/search?query=2006-006023-39','link':'https://www.clinicaltrialsregister.eu/ctr-search/search?query=2006-006023-39','eudractnumber':'2006-006023-39'},\n"
        "        ]\n"
        "        keys=sorted({k for r in rows for k in r.keys()})\n"
        "        return rows, keys\n",
        encoding="utf-8",
    )

    out_dir = tmp_path / "out"
    env = {"PYTHONPATH": str(stub_dir)}

    result = subprocess.run(
        [
            sys.executable,
            "scripts/export_pubchem_trials_dataset.py",
            "--hnid",
            "3647573",
            "--out-dir",
            str(out_dir),
            "--skip-images",
        ],
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.returncode == 0, result.stderr

    jsonl_path = out_dir / "trials.jsonl"
    csv_path = out_dir / "trials.csv"
    json_path = out_dir / "trials.json"
    summary_path = out_dir / "summary.json"

    assert jsonl_path.exists()
    assert csv_path.exists()
    assert json_path.exists()
    assert summary_path.exists()

    rows = [json.loads(x) for x in jsonl_path.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert len(rows) == 2
    assert rows[0]["cid"] == 119
    assert rows[0]["smiles"] == "C1=CC=CC=C1"

    with csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)
    assert len(csv_rows) == 2
    assert csv_rows[0]["id"] == "NCT00000001"

    json_arr = json.loads(json_path.read_text(encoding="utf-8"))
    assert isinstance(json_arr, list)
    assert len(json_arr) == 2

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["n_cids"] == 1
    assert summary["n_rows"] == 2
