#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

import argparse
from pathlib import Path

from mvp_pipeline_lib import (
    fetch_ctgov_studies,
    load_nct_ids_from_links,
    parse_csv_list,
)


def main() -> int:
    p = argparse.ArgumentParser(prog="fetch-ctgov-docs")
    p.add_argument("--links-file", default="out_mvp/cid_nct_links.jsonl", help="CID-NCT links JSONL")
    p.add_argument("--out-path", default="out_mvp/studies.jsonl", help="Output studies JSONL")
    p.add_argument(
        "--ctgov-fields",
        default=None,
        help="Comma-separated CT.gov study fields (optional)",
    )
    p.add_argument("--resume", action="store_true", help="Skip NCT IDs already in output")
    p.add_argument("--limit", type=int, default=None, help="Limit number of NCT IDs to fetch")
    args = p.parse_args()

    nct_ids = load_nct_ids_from_links(Path(args.links_file))
    stats = fetch_ctgov_studies(
        nct_ids,
        out_path=Path(args.out_path),
        fields=parse_csv_list(args.ctgov_fields) or None,
        resume=args.resume,
        limit=args.limit,
    )

    print(f"nct_ids_total: {len(nct_ids)}")
    print(f"requested: {stats['requested']}")
    print(f"fetched: {stats['fetched']}")
    print(f"existing: {stats['existing']}")
    print(f"studies: {args.out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
