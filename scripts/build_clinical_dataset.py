#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

import argparse
from pathlib import Path

from mvp_pipeline_lib import build_clinical_dataset


def main() -> int:
    p = argparse.ArgumentParser(prog="build-clinical-dataset")
    p.add_argument("--links-file", default="out_mvp/cid_nct_links.jsonl", help="CID-NCT links JSONL")
    p.add_argument("--studies-file", default="out_mvp/studies.jsonl", help="CTGov studies JSONL")
    p.add_argument(
        "--compounds-file",
        default="out_mvp/compounds.jsonl",
        help="Optional compounds JSONL from map-cid-to-nct step",
    )
    p.add_argument("--out-dir", default="out_mvp/final", help="Output directory")
    args = p.parse_args()

    compounds_path = Path(args.compounds_file)
    outputs = build_clinical_dataset(
        links_path=Path(args.links_file),
        studies_path=Path(args.studies_file),
        compounds_path=compounds_path if compounds_path.exists() else None,
        out_dir=Path(args.out_dir),
    )

    for key, value in outputs.items():
        print(f"{key}: {value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
