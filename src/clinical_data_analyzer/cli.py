# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

import argparse

from clinical_data_analyzer.ctgov.client import CTGovClient
from clinical_data_analyzer.pubchem.client import PubChemClient
from clinical_data_analyzer.pipeline.build_dataset import DatasetBuildConfig, build_dataset_for_cids


def main() -> int:
    p = argparse.ArgumentParser(prog="clinical-data-analyzer")
    p.add_argument("--name", help="Compound name to resolve via PubChem (e.g., aspirin)")
    p.add_argument("--cid", type=int, help="PubChem CID (optional)")
    p.add_argument("--out", default="out", help="Output directory")
    args = p.parse_args()

    pub = PubChemClient()
    ct = CTGovClient()

    cids = []
    if args.cid:
        cids = [args.cid]
    elif args.name:
        cids = pub.cids_by_name(args.name)[:1]
    else:
        p.error("Provide --name or --cid")

    cfg = DatasetBuildConfig(out_dir=args.out)
    out = build_dataset_for_cids(cids, pub, ct, config=cfg)
    for k, v in out.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
