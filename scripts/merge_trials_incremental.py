#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set


def _load_rows(path: Path) -> List[Dict[str, object]]:
    if not path.exists():
        return []
    obj = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(obj, list):
        return [x for x in obj if isinstance(x, dict)]
    if isinstance(obj, dict):
        return [obj]
    return []


def _row_key(row: Dict[str, object]) -> str:
    cid = row.get("cid")
    collection_code = row.get("collection_code") or row.get("collection")
    trial_id = row.get("id")
    return f"{cid}|{collection_code}|{trial_id}"


def _build_header(rows: Iterable[Dict[str, object]], base_first: Sequence[str]) -> List[str]:
    keys: Set[str] = set()
    for row in rows:
        keys.update(row.keys())
    ordered_base = [k for k in base_first if k in keys]
    rest = sorted([k for k in keys if k not in ordered_base])
    return ordered_base + rest


def _write_csv(path: Path, rows: List[Dict[str, object]], header: Sequence[str]) -> int:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(header))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in header})
    return len(rows)


def main() -> int:
    p = argparse.ArgumentParser(prog="merge-trials-incremental")
    p.add_argument("--base-json", required=True, help="Existing full trials.json")
    p.add_argument("--delta-json", required=True, help="New incremental trials.json")
    p.add_argument("--out-dir", required=True, help="Output dataset directory")
    args = p.parse_args()

    base_rows = _load_rows(Path(args.base_json))
    delta_rows = _load_rows(Path(args.delta_json))

    merged_map: Dict[str, Dict[str, object]] = {}
    for row in base_rows:
        merged_map[_row_key(row)] = row
    for row in delta_rows:
        merged_map[_row_key(row)] = row

    merged_rows = list(merged_map.values())

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "trials.json"
    csv_path = out_dir / "trials.csv"
    cids_path = out_dir / "cids.txt"
    summary_path = out_dir / "summary.json"

    json_path.write_text(json.dumps(merged_rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    preferred_header = [
        "cid",
        "collection",
        "collection_code",
        "id",
        "id_url",
        "title",
        "phase",
        "status",
        "date",
        "smiles",
        "inchikey",
        "iupac_name",
        "image_base64",
        "compound_error",
    ]
    header = _build_header(merged_rows, preferred_header)
    csv_rows = _write_csv(csv_path, merged_rows, header)

    cids = sorted({row.get("cid") for row in merged_rows if isinstance(row.get("cid"), int)})
    cids_path.write_text("\n".join(str(x) for x in cids) + ("\n" if cids else ""), encoding="utf-8")

    summary = {
        "base_json": args.base_json,
        "delta_json": args.delta_json,
        "n_base_rows": len(base_rows),
        "n_delta_rows": len(delta_rows),
        "n_rows": len(merged_rows),
        "n_cids": len(cids),
        "json": str(json_path),
        "csv": str(csv_path),
        "cids": str(cids_path),
        "csv_rows": csv_rows,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"base_rows: {len(base_rows)}")
    print(f"delta_rows: {len(delta_rows)}")
    print(f"merged_rows: {len(merged_rows)}")
    print(f"out_json: {json_path}")
    print(f"out_csv: {csv_path}")
    print(f"summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
