#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from clinical_data_analyzer.pipeline import CollectCtgovDocsConfig, collect_ctgov_docs


def _parse_csv_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def main() -> int:
    p = argparse.ArgumentParser(
        prog="collect-ctgov-docs-first1",
        description="Quick smoke run: first 1 CID and first 1 NCT document",
    )
    p.add_argument("--hnid", type=int, default=3647573)
    p.add_argument("--extra-hnids", default=None)
    p.add_argument("--out-root", default="out")
    p.add_argument("--folder-name", default="ctgov_docs_first1")
    p.add_argument("--ctgov-fields", default=None)
    p.add_argument("--use-ctgov-fallback", action="store_true")
    p.add_argument("--resume", action="store_true")
    args = p.parse_args()

    out_dir = Path(args.out_root) / args.folder_name
    hnids = [args.hnid] + [int(x) for x in _parse_csv_list(args.extra_hnids)]

    print("[quick-test] Starting first1 smoke run")
    print("[quick-test] fixed limits: limit_cids=1, limit_ncts=1")
    print(f"[setup] output: {out_dir}")
    print(f"[setup] hnids: {','.join(str(h) for h in hnids)}")

    cfg = CollectCtgovDocsConfig(
        hnids=hnids,
        out_dir=str(out_dir),
        limit_cids=1,
        limit_ncts=1,
        ctgov_fields=_parse_csv_list(args.ctgov_fields) or None,
        use_ctgov_fallback=args.use_ctgov_fallback,
        resume=args.resume,
        progress_every=1,
    )
    result = collect_ctgov_docs(cfg, progress_cb=print)

    print("[done] first1 smoke run finished")
    print(f"out_dir: {result.out_dir}")
    print(f"cids: {result.cids_count}")
    print(f"nct_requested: {result.nct_requested}")
    print(f"nct_fetched: {result.nct_fetched}")
    print(f"elapsed_sec: {result.elapsed_sec:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
