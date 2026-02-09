#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from clinical_data_analyzer.pipeline import CollectCtgovDocsConfig, collect_ctgov_docs


def _friendly_error_reason(exc: Exception) -> str:
    msg = str(exc).lower()
    if "failed to resolve" in msg or "nodename nor servname provided" in msg:
        return "DNS/네트워크 문제로 호스트를 찾지 못했습니다. 인터넷/DNS/방화벽을 확인하세요."
    if "max retries exceeded" in msg:
        return "외부 API 재시도 한도를 초과했습니다. 네트워크 또는 대상 서버 상태를 확인하세요."
    if "429" in msg or "rate" in msg:
        return "요청 제한(레이트 리밋) 가능성이 있습니다. 잠시 후 재시도하세요."
    if "timeout" in msg:
        return "요청 시간 초과가 발생했습니다. 네트워크 상태를 확인하세요."
    return "알 수 없는 오류입니다. 아래 원본 에러 메시지를 확인하세요."


def _parse_csv_list(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def main() -> int:
    p = argparse.ArgumentParser(
        prog="collect-ctgov-docs",
        description="Step1-3 only: HNID -> CID -> NCT -> CTGov studies",
    )
    p.add_argument("--hnid", type=int, default=3647573)
    p.add_argument("--extra-hnids", default=None)
    p.add_argument("--limit-cids", type=int, default=None)
    p.add_argument("--limit-ncts", type=int, default=None)
    p.add_argument("--out-root", default="out")
    p.add_argument("--folder-name", required=True)
    p.add_argument("--ctgov-fields", default=None)
    p.add_argument("--use-ctgov-fallback", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--show-progress", action="store_true")
    p.add_argument("--progress-every", type=int, default=50)
    args = p.parse_args()

    hnids = [args.hnid] + [int(x) for x in _parse_csv_list(args.extra_hnids)]
    out_dir = Path(args.out_root) / args.folder_name
    progress_every = max(1, args.progress_every) if args.show_progress else 0

    print("[setup] Starting CTGov document collection pipeline (steps 1-3)")
    print(f"[setup] Preparing output directory: {out_dir}")
    print(f"[setup] HNIDs to query: {','.join(str(h) for h in hnids)}")
    print(f"[setup] CTGov fallback enabled: {'yes' if args.use_ctgov_fallback else 'no'}")
    print(f"[setup] Resume enabled: {'yes' if args.resume else 'no'}")
    if args.limit_cids is not None:
        print(f"[setup] CID limit: {args.limit_cids}")
    if args.limit_ncts is not None:
        print(f"[setup] NCT limit: {args.limit_ncts}")
    if args.ctgov_fields:
        print(f"[setup] CTGov fields: {args.ctgov_fields}")
    if args.show_progress:
        print(f"[setup] Progress interval: every {progress_every} items")

    cfg = CollectCtgovDocsConfig(
        hnids=hnids,
        out_dir=str(out_dir),
        limit_cids=args.limit_cids,
        limit_ncts=args.limit_ncts,
        ctgov_fields=_parse_csv_list(args.ctgov_fields) or None,
        use_ctgov_fallback=args.use_ctgov_fallback,
        resume=args.resume,
        progress_every=progress_every,
    )

    try:
        result = collect_ctgov_docs(cfg, progress_cb=print)
    except Exception as e:
        print("[error] Pipeline failed.")
        print(f"        reason: {_friendly_error_reason(e)}")
        print(f"        raw_error: {type(e).__name__}: {e}")
        return 2

    print("[done] Pipeline finished.")
    print(f"out_dir: {result.out_dir}")
    print(f"cids: {result.cids_count}")
    print(f"nct_ids_total_mapped: {result.nct_ids_total_mapped}")
    print(f"nct_unique_seen: {result.nct_unique_seen}")
    print(f"nct_requested: {result.nct_requested}")
    print(f"nct_fetched: {result.nct_fetched}")
    print(f"nct_existing_before_resume: {result.nct_existing_before_resume}")
    for k, v in result.paths.items():
        print(f"{k}: {v}")
    print(f"elapsed_sec: {result.elapsed_sec:.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
