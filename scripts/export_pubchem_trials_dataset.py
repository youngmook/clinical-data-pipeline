#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

import argparse
import base64
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

import requests

from clinical_data_analyzer.pubchem import PubChemClassificationClient, PubChemClient, PubChemWebFallbackClient


def _parse_csv_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_jsonl(path: Path, rows: Iterable[Dict[str, object]]) -> None:
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _iter_jsonl(path: Path) -> Iterable[Dict[str, object]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def _extract_processed_cids(path: Path) -> Set[int]:
    out: Set[int] = set()
    for row in _iter_jsonl(path) or []:
        cid = row.get("cid")
        if isinstance(cid, int):
            out.add(cid)
    return out


def _build_union_header(path: Path, base_first: Sequence[str]) -> List[str]:
    keys: Set[str] = set()
    for row in _iter_jsonl(path) or []:
        keys.update(row.keys())
    ordered_base = [k for k in base_first if k in keys]
    rest = sorted([k for k in keys if k not in ordered_base])
    return ordered_base + rest


def _write_csv_from_jsonl(jsonl_path: Path, csv_path: Path, header: Sequence[str]) -> int:
    n = 0
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(header))
        w.writeheader()
        for row in _iter_jsonl(jsonl_path) or []:
            w.writerow({k: row.get(k) for k in header})
            n += 1
    return n


def _write_json_array_from_jsonl(jsonl_path: Path, json_path: Path) -> int:
    n = 0
    with json_path.open("w", encoding="utf-8") as out:
        out.write("[\n")
        first = True
        for row in _iter_jsonl(jsonl_path) or []:
            if not first:
                out.write(",\n")
            out.write(json.dumps(row, ensure_ascii=False))
            first = False
            n += 1
        out.write("\n]\n")
    return n


def _fetch_png_data_uri(cid: int, *, image_size: str = "400x400", timeout: float = 60.0) -> Tuple[Optional[str], Optional[str]]:
    url = f"https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/{cid}/PNG"
    params = {"image_size": image_size}

    with requests.Session() as s:
        r = s.get(url, params=params, timeout=timeout)
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            return None, f"image_http_error:{r.status_code}:{e}"
        b64 = base64.b64encode(r.content).decode("ascii")
        return f"data:image/png;base64,{b64}", None


def _dedupe(values: Sequence[int]) -> List[int]:
    seen: Set[int] = set()
    out: List[int] = []
    for v in values:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def _sanitize_trial_row(row: Dict[str, object]) -> Dict[str, object]:
    # Keep normalized schema (`id`, `date`) only.
    drop_keys = {"ctid", "eudractnumber", "updatedate"}
    return {k: v for k, v in row.items() if k not in drop_keys}


def _print_progress(
    *,
    idx: int,
    total: int,
    cid: int,
    added_rows: int,
    total_rows: int,
    skipped: bool = False,
    errored: bool = False,
) -> None:
    pct = (idx / total * 100.0) if total else 0.0
    status = "skipped" if skipped else ("error" if errored else "ok")
    print(
        f"[export] {idx}/{total} ({pct:.1f}%) cid={cid} status={status} "
        f"added_rows={added_rows} total_rows={total_rows}"
    )


def main() -> int:
    p = argparse.ArgumentParser(prog="export-pubchem-trials-dataset")
    p.add_argument("--hnid", type=int, default=1856916, help="PubChem HNID (default: 1856916)")
    p.add_argument("--extra-hnids", default=None, help="Comma-separated extra HNIDs")
    p.add_argument("--limit-cids", type=int, default=None, help="Limit number of CIDs for testing")
    p.add_argument("--out-dir", default="out/pubchem_trials_dataset", help="Output directory")
    p.add_argument(
        "--collections",
        default="clinicaltrials,clinicaltrials_eu,clinicaltrials_jp",
        help="Comma-separated SDQ collections",
    )
    p.add_argument("--limit-per-collection", type=int, default=200, help="Max rows per collection per CID")
    p.add_argument("--image-size", default="400x400", help="2D PNG size (e.g. 300x300)")
    p.add_argument("--skip-images", action="store_true", help="Do not fetch 2D PNG images")
    p.add_argument("--resume", action="store_true", help="Resume from existing trials.jsonl")
    p.add_argument("--progress-every", type=int, default=50, help="Progress print interval")
    p.add_argument("--show-progress", action="store_true", help="Print per-CID progress logs")
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    _ensure_dir(out_dir)

    cids_txt = out_dir / "cids.txt"
    jsonl_path = out_dir / "trials.jsonl"
    csv_path = out_dir / "trials.csv"
    json_path = out_dir / "trials.json"
    summary_path = out_dir / "summary.json"

    class_client = PubChemClassificationClient()
    pubchem = PubChemClient()
    fallback = PubChemWebFallbackClient()

    hnids = [args.hnid] + [int(x) for x in _parse_csv_list(args.extra_hnids)]

    # 1) Collect and dedupe CIDs
    cids: List[int] = []
    for hnid in hnids:
        cids.extend(class_client.get_cids(hnid, fmt="TXT"))
    cids = _dedupe(cids)

    if args.limit_cids is not None:
        cids = cids[: args.limit_cids]

    cids_txt.write_text("\n".join(str(c) for c in cids) + "\n", encoding="utf-8")

    collections = tuple(_parse_csv_list(args.collections))
    if not collections:
        raise ValueError("At least one collection is required")

    processed_cids: Set[int] = set()
    if args.resume and jsonl_path.exists():
        processed_cids = _extract_processed_cids(jsonl_path)

    print(
        f"[export] start hnids={hnids} collections={list(collections)} "
        f"cids={len(cids)} resume={args.resume} skip_images={args.skip_images}"
    )

    total_rows = 0
    total_with_trials = 0
    total_with_errors = 0

    # 2) CID -> trials union rows + smiles + image
    for idx, cid in enumerate(cids, start=1):
        if cid in processed_cids:
            if args.show_progress:
                _print_progress(
                    idx=idx,
                    total=len(cids),
                    cid=cid,
                    added_rows=0,
                    total_rows=total_rows,
                    skipped=True,
                )
            continue

        smiles = None
        inchikey = None
        iupac_name = None
        compound_error = None
        try:
            props = pubchem.compound_properties(cid)
            smiles = props.get("CanonicalSMILES")
            inchikey = props.get("InChIKey")
            iupac_name = props.get("IUPACName")
        except Exception as e:
            compound_error = f"compound_props_error:{type(e).__name__}:{e}"

        image_base64 = None
        if not args.skip_images:
            image_base64, _ = _fetch_png_data_uri(cid, image_size=args.image_size)

        try:
            union_rows, _ = fallback.get_normalized_trials_union(
                cid,
                collections=collections,
                limit_per_collection=args.limit_per_collection,
            )
        except Exception as e:
            err_row = {
                "cid": cid,
                "collections": list(collections),
                "error": f"trials_union_error:{type(e).__name__}:{e}",
                "smiles": smiles,
                "inchikey": inchikey,
                "iupac_name": iupac_name,
                "compound_error": compound_error,
                "image_base64": image_base64,
            }
            _write_jsonl(jsonl_path, [err_row])
            total_rows += 1
            total_with_errors += 1
            if args.show_progress:
                _print_progress(
                    idx=idx,
                    total=len(cids),
                    cid=cid,
                    added_rows=1,
                    total_rows=total_rows,
                    errored=True,
                )
            continue

        if union_rows:
            total_with_trials += 1
        else:
            # Keep a placeholder row for traceability
            union_rows = [
                {
                    "collection": None,
                    "id": None,
                    "title": None,
                    "phase": None,
                    "status": None,
                    "date": None,
                    "id_url": None,
                    "cids": None,
                    "note": "no_trials_found",
                }
            ]

        out_rows: List[Dict[str, object]] = []
        for r in union_rows:
            row = _sanitize_trial_row(dict(r))
            row.update(
                {
                    "cid": cid,
                    "smiles": smiles,
                    "inchikey": inchikey,
                    "iupac_name": iupac_name,
                    "compound_error": compound_error,
                    "image_base64": image_base64,
                }
            )
            out_rows.append(row)

        _write_jsonl(jsonl_path, out_rows)
        total_rows += len(out_rows)

        if args.show_progress:
            _print_progress(
                idx=idx,
                total=len(cids),
                cid=cid,
                added_rows=len(out_rows),
                total_rows=total_rows,
            )

        if args.progress_every > 0 and (idx % args.progress_every == 0 or idx == len(cids)):
            print(f"[export] processed {idx}/{len(cids)} cids, rows={total_rows}")

    # 3) Export CSV and JSON array from JSONL
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
    header = _build_union_header(jsonl_path, preferred_header)
    csv_rows = _write_csv_from_jsonl(jsonl_path, csv_path, header)
    json_rows = _write_json_array_from_jsonl(jsonl_path, json_path)

    summary = {
        "hnids": hnids,
        "collections": list(collections),
        "n_cids": len(cids),
        "n_rows": total_rows,
        "n_cids_with_trials": total_with_trials,
        "n_error_rows": total_with_errors,
        "jsonl": str(jsonl_path),
        "csv": str(csv_path),
        "json": str(json_path),
        "csv_rows": csv_rows,
        "json_rows": json_rows,
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"cids: {len(cids)}")
    print(f"rows: {total_rows}")
    print(f"jsonl: {jsonl_path}")
    print(f"csv: {csv_path}")
    print(f"json: {json_path}")
    print(f"summary: {summary_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
