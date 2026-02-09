#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

import argparse
from pathlib import Path

from mvp_pipeline_lib import build_cid_nct_map, read_cids


def main() -> int:
    p = argparse.ArgumentParser(prog="map-cid-to-nct")
    p.add_argument("--cids-file", default="out_mvp/cids.txt", help="Input CID TXT file")
    p.add_argument("--out-dir", default="out_mvp", help="Output directory")
    p.add_argument(
        "--no-compound-props",
        action="store_true",
        help="Do not request compound properties (InChIKey/SMILES/IUPACName)",
    )
    args = p.parse_args()

    cids = read_cids(Path(args.cids_file))
    outputs = build_cid_nct_map(
        cids,
        out_dir=Path(args.out_dir),
        include_compound_props=not args.no_compound_props,
    )

    print(f"cids: {len(cids)}")
    for key, value in outputs.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
