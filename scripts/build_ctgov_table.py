#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from clinical_data_analyzer.ctgov import CTGovClient
from clinical_data_analyzer.pubchem import PubChemClassificationClient
from clinical_data_analyzer.pubchem import PubChemPugViewClient


def _parse_csv_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def _write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _load_existing_links(path: Path) -> Set[int]:
    if not path.exists():
        return set()
    cids: Set[int] = set()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            cid = obj.get("cid")
            if isinstance(cid, int):
                cids.add(cid)
    return cids


def _load_existing_studies(path: Path) -> Dict[str, Tuple[str, str]]:
    if not path.exists():
        return {}
    ncts: Dict[str, Tuple[str, str]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            obj = json.loads(line)
            nct = (
                obj.get("protocolSection", {})
                .get("identificationModule", {})
                .get("nctId")
            )
            if isinstance(nct, str) and nct:
                ncts[nct] = _extract_title_phase(obj)
    return ncts


def _extract_title_phase(study: dict) -> Tuple[str, str]:
    ps = study.get("protocolSection") or {}
    ident = ps.get("identificationModule") or {}
    title = ident.get("briefTitle") or ident.get("officialTitle") or ""

    design = ps.get("designModule") or {}
    phases = design.get("phases")
    if isinstance(phases, list):
        phase_str = ", ".join([p for p in phases if isinstance(p, str)])
    elif isinstance(phases, str):
        phase_str = phases
    else:
        phase_str = ""

    return title, phase_str


def _write_table_header(path: Path) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cid", "nct_id", "title", "phase"])


def main() -> int:
    p = argparse.ArgumentParser(prog="build-ctgov-table")
    p.add_argument(
        "--hnid",
        type=int,
        default=3647573,
        help="PubChem HNID (default: 3647573 for ClinicalTrials.gov)",
    )
    p.add_argument(
        "--extra-hnids",
        default=None,
        help="Comma-separated extra HNIDs to include (e.g., 3647574,3647575)",
    )
    p.add_argument("--limit", type=int, default=None, help="Limit number of CIDs")
    p.add_argument("--out-dir", default="out_ctgov", help="Output directory")
    p.add_argument(
        "--ctgov-fields",
        default=None,
        help="Comma-separated CT.gov fields to request (optional)",
    )
    p.add_argument("--resume", action="store_true", help="Resume from existing outputs")
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    cids_path = out_dir / "cids.txt"
    links_path = out_dir / "cid_nct_links.jsonl"
    studies_path = out_dir / "studies.jsonl"
    table_path = out_dir / "ctgov_table.csv"

    class_nodes = PubChemClassificationClient()
    pug_view = PubChemPugViewClient()
    ctgov = CTGovClient()

    hnids = [args.hnid] + _parse_csv_list(args.extra_hnids)

    # 1) HNID -> CIDs
    cids: List[int] = []
    for hnid in hnids:
        cids.extend(class_nodes.get_cids(int(hnid), fmt="TXT"))

    # de-dup
    seen_cids: Set[int] = set()
    deduped: List[int] = []
    for cid in cids:
        if cid in seen_cids:
            continue
        seen_cids.add(cid)
        deduped.append(cid)
    cids = deduped

    if args.limit:
        cids = cids[: args.limit]

    cids_path.parent.mkdir(parents=True, exist_ok=True)
    cids_path.write_text("\n".join(str(c) for c in cids) + "\n", encoding="utf-8")

    # resume state
    processed_cids: Set[int] = set()
    existing_studies: Dict[str, Tuple[str, str]] = {}
    if args.resume:
        processed_cids = _load_existing_links(links_path)
        existing_studies = _load_existing_studies(studies_path)

    # outputs
    _write_table_header(table_path)

    fields = _parse_csv_list(args.ctgov_fields)

    for cid in cids:
        if cid in processed_cids:
            continue
        nct_ids = pug_view.nct_ids_for_cid(cid)

        _write_jsonl(
            links_path,
            [
                {
                    "cid": cid,
                    "nct_ids": nct_ids,
                    "n_nct": len(nct_ids),
                    "source": "PubChem PUG-View annotations",
                }
            ],
        )

        for nct in nct_ids:
            if nct in existing_studies:
                title, phase = existing_studies[nct]
            else:
                study = ctgov.get_study(nct, fields=fields or None)
                _write_jsonl(studies_path, [study])
                title, phase = _extract_title_phase(study)
                existing_studies[nct] = (title, phase)

            with table_path.open("a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([cid, nct, title, phase])

    print(f"hnids: {','.join(str(h) for h in hnids)}")
    print(f"cids: {len(cids)}")
    print(f"links: {links_path}")
    print(f"studies: {studies_path}")
    print(f"table: {table_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
