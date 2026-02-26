#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
from typing import List, Optional, Sequence

from clinical_data_analyzer.pubchem import PubChemClassificationClient


def _parse_csv_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def _dedupe(values: Sequence[int]) -> List[int]:
    seen = set()
    out: List[int] = []
    for v in values:
        if v in seen:
            continue
        seen.add(v)
        out.append(v)
    return out


def _read_cids(path: Path) -> List[int]:
    vals: List[int] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s and s.isdigit():
            vals.append(int(s))
    return vals


def _write_cids(path: Path, cids: Sequence[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{x}\n" for x in cids), encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(prog="prefetch-hnid-cids")
    p.add_argument("--hnid", type=int, required=True, help="Primary PubChem HNID")
    p.add_argument("--extra-hnids", default=None, help="Comma-separated extra HNIDs")
    p.add_argument("--out-file", required=True, help="Output CID txt path")
    p.add_argument("--fallback-file", default=None, help="Fallback CID txt path when API fetch fails")
    p.add_argument(
        "--update-fallback",
        action="store_true",
        help="On successful API fetch, also update fallback-file",
    )
    args = p.parse_args()

    hnids = [args.hnid] + [int(x) for x in _parse_csv_list(args.extra_hnids)]
    out_file = Path(args.out_file)
    fallback_file = Path(args.fallback_file) if args.fallback_file else None

    source = "pubchem"
    client = PubChemClassificationClient()

    try:
        cids: List[int] = []
        for hnid in hnids:
            cids.extend(client.get_cids(hnid, fmt="TXT"))
        cids = _dedupe(cids)
    except Exception as exc:
        if fallback_file and fallback_file.exists():
            cids = _dedupe(_read_cids(fallback_file))
            if not cids:
                raise RuntimeError(f"fallback cids file is empty: {fallback_file}") from exc
            source = f"fallback:{fallback_file}"
            print(f"[prefetch] API fetch failed, using fallback ({fallback_file}): {type(exc).__name__}: {exc}")
        else:
            raise

    _write_cids(out_file, cids)

    if source == "pubchem" and args.update_fallback and fallback_file:
        fallback_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_file, fallback_file)

    print(f"[prefetch] source={source}")
    print(f"[prefetch] hnids={hnids}")
    print(f"[prefetch] cids={len(cids)}")
    print(f"[prefetch] out={out_file}")
    if fallback_file:
        print(f"[prefetch] fallback={fallback_file}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
