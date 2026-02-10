from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


@pytest.mark.smoke
@pytest.mark.network
@pytest.mark.timeout(120)
def test_build_ctgov_table_smoke(tmp_path: Path):
    out_dir = tmp_path / "out_ctgov"
    cmd = [
        "python",
        "scripts/build_ctgov_table.py",
        "--hnid",
        "3647573",
        "--limit",
        "2",
        "--out-dir",
        str(out_dir),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    table = out_dir / "ctgov_table.csv"
    assert table.exists()
    assert table.stat().st_size > 0

    links = out_dir / "cid_nct_links.jsonl"
    assert links.exists()
    assert links.stat().st_size > 0
