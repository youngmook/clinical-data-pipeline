from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def _make_stub_pkg(tmp_path: Path, body: str) -> Path:
    stub_dir = tmp_path / "stubs"
    stub_dir.mkdir()

    pkg = stub_dir / "clinical_data_analyzer"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")

    pubchem_pkg = pkg / "pubchem"
    pubchem_pkg.mkdir()
    (pubchem_pkg / "__init__.py").write_text(body, encoding="utf-8")
    return stub_dir


def test_prefetch_hnid_cids_updates_fallback_unit(tmp_path: Path):
    stub_dir = _make_stub_pkg(
        tmp_path,
        "class PubChemClassificationClient:\n"
        "    def get_cids(self, hnid, fmt='TXT'):\n"
        "        return [3, 1, 3, 2]\n",
    )

    out_file = tmp_path / "out.txt"
    fallback_file = tmp_path / "fallback.txt"

    result = subprocess.run(
        [
            sys.executable,
            "scripts/prefetch_hnid_cids.py",
            "--hnid",
            "1856916",
            "--out-file",
            str(out_file),
            "--fallback-file",
            str(fallback_file),
            "--update-fallback",
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(stub_dir)},
    )
    assert result.returncode == 0, result.stderr

    out_lines = [x for x in out_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    fb_lines = [x for x in fallback_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert out_lines == ["3", "1", "2"]
    assert fb_lines == ["3", "1", "2"]


def test_prefetch_hnid_cids_uses_fallback_on_error_unit(tmp_path: Path):
    stub_dir = _make_stub_pkg(
        tmp_path,
        "class PubChemClassificationClient:\n"
        "    def get_cids(self, hnid, fmt='TXT'):\n"
        "        raise RuntimeError('HTTP 503 ServerBusy')\n",
    )

    out_file = tmp_path / "out.txt"
    fallback_file = tmp_path / "fallback.txt"
    fallback_file.write_text("10\n11\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "scripts/prefetch_hnid_cids.py",
            "--hnid",
            "1856916",
            "--out-file",
            str(out_file),
            "--fallback-file",
            str(fallback_file),
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(stub_dir)},
    )
    assert result.returncode == 0, result.stderr

    out_lines = [x for x in out_file.read_text(encoding="utf-8").splitlines() if x.strip()]
    assert out_lines == ["10", "11"]
    assert "using fallback" in result.stdout
