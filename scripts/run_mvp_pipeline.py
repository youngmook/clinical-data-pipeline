#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

import argparse
from pathlib import Path

from mvp_pipeline_lib import (
    build_cid_nct_map,
    build_clinical_dataset,
    fetch_cids_by_hnids,
    fetch_ctgov_studies,
    load_nct_ids_from_links,
    parse_csv_list,
    read_cids,
)


def main() -> int:
    p = argparse.ArgumentParser(prog="run-mvp-pipeline")
    p.add_argument(
        "--hnid",
        type=int,
        default=3647573,
        help="Primary PubChem HNID (default: 3647573, ClinicalTrials.gov)",
    )
    p.add_argument(
        "--extra-hnids",
        default=None,
        help="Comma-separated extra HNIDs (e.g., 1856916,3647574,3647575)",
    )
    p.add_argument("--limit-cids", type=int, default=None, help="Limit CID count after de-dup")
    p.add_argument("--limit-ncts", type=int, default=None, help="Limit NCT fetch count")
    p.add_argument("--out-dir", default="out_mvp", help="Pipeline output directory")
    p.add_argument(
        "--ctgov-fields",
        default=None,
        help="Comma-separated CT.gov study fields (optional)",
    )
    p.add_argument("--resume", action="store_true", help="Resume CTGov study fetch")
    args = p.parse_args()

    out_dir = Path(args.out_dir)
    hnids = [args.hnid] + [int(x) for x in parse_csv_list(args.extra_hnids)]

    step1 = fetch_cids_by_hnids(hnids, out_dir=out_dir, limit=args.limit_cids)
    cids = read_cids(step1["cids_txt"])

    step2 = build_cid_nct_map(cids, out_dir=out_dir, include_compound_props=True)
    nct_ids = load_nct_ids_from_links(step2["cid_nct_links"])

    ctgov_stats = fetch_ctgov_studies(
        nct_ids,
        out_path=out_dir / "studies.jsonl",
        fields=parse_csv_list(args.ctgov_fields) or None,
        resume=args.resume,
        limit=args.limit_ncts,
    )

    final_outputs = build_clinical_dataset(
        links_path=step2["cid_nct_links"],
        studies_path=out_dir / "studies.jsonl",
        compounds_path=step2.get("compounds"),
        out_dir=out_dir / "final",
    )

    print(f"hnids: {','.join(str(h) for h in hnids)}")
    print(f"cids: {len(cids)}")
    print(f"nct_ids_total: {len(nct_ids)}")
    print(f"nct_requested: {ctgov_stats['requested']}")
    print(f"nct_fetched: {ctgov_stats['fetched']}")
    for key, value in step1.items():
        print(f"{key}: {value}")
    for key, value in step2.items():
        print(f"{key}: {value}")
    print(f"studies: {out_dir / 'studies.jsonl'}")
    for key, value in final_outputs.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
