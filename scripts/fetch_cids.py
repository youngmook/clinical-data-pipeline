#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

import argparse
from pathlib import Path

from mvp_pipeline_lib import fetch_cids_by_hnids, parse_csv_list


def main() -> int:
    p = argparse.ArgumentParser(prog="fetch-cids")
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
    p.add_argument("--limit", type=int, default=None, help="Limit CID count after de-dup")
    p.add_argument("--out-dir", default="out_mvp", help="Output directory")
    args = p.parse_args()

    hnids = [args.hnid] + [int(x) for x in parse_csv_list(args.extra_hnids)]
    outputs = fetch_cids_by_hnids(hnids, out_dir=Path(args.out_dir), limit=args.limit)

    print(f"hnids: {','.join(str(h) for h in hnids)}")
    print(f"cids_txt: {outputs['cids_txt']}")
    print(f"cids_jsonl: {outputs['cids_jsonl']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
