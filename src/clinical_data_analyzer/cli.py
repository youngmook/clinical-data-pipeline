# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, List, Optional

from clinical_data_analyzer.ctgov.client import CTGovClient
from clinical_data_analyzer.pubchem.client import PubChemClient
from clinical_data_analyzer.pubchem.classification_nodes import PubChemClassificationClient
from clinical_data_analyzer.pubchem.pug_view import PubChemPugViewClient
from clinical_data_analyzer.pipeline.build_dataset import DatasetBuildConfig, build_dataset_for_cids
from clinical_data_analyzer.pipeline.cid_to_nct import CidToNctConfig, export_cids_nct_dataset


def _write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> List[dict]:
    out: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(json.loads(line))
    return out


def _parse_fields(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    parts = [p.strip() for p in value.split(",")]
    return [p for p in parts if p]


def _add_legacy_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--name", help="Compound name to resolve via PubChem (e.g., aspirin)")
    p.add_argument("--cid", type=int, help="PubChem CID (optional)")
    p.add_argument("--out", default="out", help="Output directory")


def main() -> int:
    p = argparse.ArgumentParser(prog="clinical-data-analyzer")
    sub = p.add_subparsers(dest="command")

    # Legacy single-compound dataset build (default when no subcommand)
    _add_legacy_args(p)

    # Subcommand: hnid-cids
    p_hnid = sub.add_parser("hnid-cids", help="Download PubChem CIDs for a given HNID")
    p_hnid.add_argument("--hnid", type=int, required=True, help="PubChem HNID")
    p_hnid.add_argument("--out", required=True, help="Output file path (TXT)")

    # Subcommand: collect-ctgov
    p_collect = sub.add_parser(
        "collect-ctgov", help="HNID -> CID -> NCT -> ClinicalTrials.gov dataset"
    )
    p_collect.add_argument("--hnid", type=int, required=True, help="PubChem HNID")
    p_collect.add_argument("--limit", type=int, default=None, help="Limit number of CIDs")
    p_collect.add_argument("--out", default="out_ctgov", help="Output directory")
    p_collect.add_argument(
        "--ctgov-fields",
        default=None,
        help="Comma-separated CT.gov fields to request (optional)",
    )

    args = p.parse_args()

    if args.command == "hnid-cids":
        class_nodes = PubChemClassificationClient()
        cids = class_nodes.get_cids(args.hnid, fmt="TXT")
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(str(c) for c in cids) + "\n", encoding="utf-8")
        print(f"cids: {len(cids)}")
        print(f"out: {out_path}")
        return 0

    if args.command == "collect-ctgov":
        class_nodes = PubChemClassificationClient()
        pub = PubChemClient()
        pug_view = PubChemPugViewClient()
        ct = CTGovClient()

        cids = class_nodes.get_cids(args.hnid, fmt="TXT")
        if args.limit:
            cids = cids[: args.limit]

        cfg = CidToNctConfig(out_dir=args.out, write_jsonl=True, include_compound_props=True)
        outputs = export_cids_nct_dataset(cids, config=cfg, pubchem=pub, pug_view=pug_view)

        links_path = outputs.get("cid_nct_links")
        if links_path:
            link_rows = _read_jsonl(links_path)
            nct_ids = sorted({nct for r in link_rows for nct in r.get("nct_ids", [])})
        else:
            nct_ids = []

        fields = _parse_fields(args.ctgov_fields)
        studies_rows = [ct.get_study(nct, fields=fields) for nct in nct_ids]
        studies_path = Path(args.out) / "studies.jsonl"
        _write_jsonl(studies_path, studies_rows)

        print(f"cids: {len(cids)}")
        print(f"nct_ids: {len(nct_ids)}")
        for k, v in outputs.items():
            print(f"{k}: {v}")
        print(f"studies: {studies_path}")
        return 0

    # Legacy path: build dataset by name or cid
    pub = PubChemClient()
    ct = CTGovClient()

    cids: List[int] = []
    if args.cid:
        cids = [args.cid]
    elif args.name:
        cids = pub.cids_by_name(args.name)[:1]
    else:
        p.error("Provide --name or --cid, or use a subcommand")

    cfg = DatasetBuildConfig(out_dir=args.out)
    out = build_dataset_for_cids(cids, pub, ct, config=cfg)
    for k, v in out.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
