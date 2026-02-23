#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _iter_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _iter_rows_from_shard(shard_dir: Path) -> Iterable[Dict[str, object]]:
    jsonl_path = shard_dir / "trials.jsonl"
    json_path = shard_dir / "trials.json"

    if jsonl_path.exists():
        yield from (_iter_jsonl(jsonl_path) or [])
        return

    if json_path.exists():
        arr = json.loads(json_path.read_text(encoding="utf-8"))
        if isinstance(arr, list):
            for row in arr:
                if isinstance(row, dict):
                    yield row
        return

    raise FileNotFoundError(f"No trials.jsonl or trials.json in shard dir: {shard_dir}")


def _row_signature(row: Dict[str, object]) -> str:
    # Canonical JSON signature for exact-row dedupe across shards.
    return json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _build_union_header(rows: Sequence[Dict[str, object]], base_first: Sequence[str]) -> List[str]:
    keys: Set[str] = set()
    for row in rows:
        keys.update(row.keys())
    ordered_base = [k for k in base_first if k in keys]
    rest = sorted([k for k in keys if k not in ordered_base])
    return ordered_base + rest


def _write_jsonl(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: Path, rows: Sequence[Dict[str, object]]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_csv(path: Path, rows: Sequence[Dict[str, object]], header: Sequence[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(header))
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k) for k in header})


def main() -> int:
    p = argparse.ArgumentParser(prog="merge-pubchem-trials-shards")
    p.add_argument("--shard-dirs", required=True, help="Comma-separated shard output directories")
    p.add_argument("--out-dir", required=True, help="Merged output directory")
    args = p.parse_args()

    shard_dirs = [Path(x.strip()) for x in args.shard_dirs.split(",") if x.strip()]
    if not shard_dirs:
        raise ValueError("At least one shard dir is required")

    out_dir = Path(args.out_dir)
    _ensure_dir(out_dir)

    merged_rows: List[Dict[str, object]] = []
    seen_signatures: Set[str] = set()

    input_rows = 0
    for shard in shard_dirs:
        for row in _iter_rows_from_shard(shard):
            input_rows += 1
            sig = _row_signature(row)
            if sig in seen_signatures:
                continue
            seen_signatures.add(sig)
            merged_rows.append(row)

    preferred_header = [
        "cid",
        "collection",
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
    header = _build_union_header(merged_rows, preferred_header)

    jsonl_path = out_dir / "trials.jsonl"
    json_path = out_dir / "trials.json"
    csv_path = out_dir / "trials.csv"
    cids_txt = out_dir / "cids.txt"
    summary_path = out_dir / "summary.json"

    _write_jsonl(jsonl_path, merged_rows)
    _write_json(json_path, merged_rows)
    _write_csv(csv_path, merged_rows, header)

    cids = sorted({row.get("cid") for row in merged_rows if isinstance(row.get("cid"), int)})
    cids_txt.write_text("\n".join(str(x) for x in cids) + "\n", encoding="utf-8")

    summary = {
        "schema_version": 1,
        "mode": "merged_from_shards",
        "shard_dirs": [str(p) for p in shard_dirs],
        "n_shards": len(shard_dirs),
        "n_input_rows": input_rows,
        "n_rows": len(merged_rows),
        "n_cids": len(cids),
        "jsonl": str(jsonl_path),
        "json": str(json_path),
        "csv": str(csv_path),
        "cids_txt": str(cids_txt),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"shards: {len(shard_dirs)}")
    print(f"input_rows: {input_rows}")
    print(f"rows: {len(merged_rows)}")
    print(f"cids: {len(cids)}")
    print(f"jsonl: {jsonl_path}")
    print(f"json: {json_path}")
    print(f"csv: {csv_path}")
    print(f"summary: {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
