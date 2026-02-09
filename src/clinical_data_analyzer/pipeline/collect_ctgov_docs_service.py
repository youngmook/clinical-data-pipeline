# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

from dataclasses import dataclass
import csv
import json
from pathlib import Path
import time
from typing import Callable, Dict, List, Optional, Sequence, Set

from clinical_data_analyzer.ctgov import CTGovClient
from clinical_data_analyzer.pipeline.cid_to_nct import CidToNctConfig, map_cid_to_nct_record
from clinical_data_analyzer.pubchem import PubChemClassificationClient, PubChemClient, PubChemPugViewClient


@dataclass(frozen=True)
class CollectCtgovDocsConfig:
    hnids: Sequence[int]
    out_dir: str
    limit_cids: Optional[int] = None
    limit_ncts: Optional[int] = None
    ctgov_fields: Optional[Sequence[str]] = None
    use_ctgov_fallback: bool = False
    resume: bool = False
    progress_every: int = 0


@dataclass(frozen=True)
class CollectCtgovDocsResult:
    out_dir: Path
    cids_count: int
    nct_ids_total_mapped: int
    nct_unique_seen: int
    nct_requested: int
    nct_fetched: int
    nct_existing_before_resume: int
    elapsed_sec: float
    paths: Dict[str, Path]


def _write_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_jsonl_rows(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _load_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    out: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _load_processed_cids(path: Path) -> Set[int]:
    seen: Set[int] = set()
    for obj in _load_jsonl(path):
        cid = obj.get("cid")
        if isinstance(cid, int):
            seen.add(cid)
    return seen


def _extract_nct_id(study_obj: dict) -> Optional[str]:
    return (
        study_obj.get("protocolSection", {})
        .get("identificationModule", {})
        .get("nctId")
    )


def _load_study_cache_by_nct(path: Path) -> Dict[str, dict]:
    cache: Dict[str, dict] = {}
    for obj in _load_jsonl(path):
        nct = _extract_nct_id(obj)
        if isinstance(nct, str) and nct and nct not in cache:
            cache[nct] = obj
    return cache


def _fetch_cids_by_hnids(hnids: Sequence[int], out_dir: Path, limit: Optional[int]) -> Dict[str, Path]:
    class_nodes = PubChemClassificationClient()
    cid_to_hnids: Dict[int, Set[int]] = {}
    ordered_cids: List[int] = []

    for hnid in hnids:
        for cid in class_nodes.get_cids(int(hnid), fmt="TXT"):
            if cid not in cid_to_hnids:
                cid_to_hnids[cid] = set()
                ordered_cids.append(cid)
            cid_to_hnids[cid].add(int(hnid))

    if limit is not None:
        ordered_cids = ordered_cids[:limit]

    out_dir.mkdir(parents=True, exist_ok=True)
    cids_txt = out_dir / "cids.txt"
    cids_jsonl = out_dir / "cids.jsonl"
    cids_txt.write_text("\n".join(str(c) for c in ordered_cids) + "\n", encoding="utf-8")
    _write_jsonl_rows(
        cids_jsonl,
        [{"cid": cid, "source_hnids": sorted(cid_to_hnids.get(cid, set()))} for cid in ordered_cids],
    )
    return {"cids_txt": cids_txt, "cids_jsonl": cids_jsonl}


def collect_ctgov_docs(
    config: CollectCtgovDocsConfig,
    *,
    progress_cb: Optional[Callable[[str], None]] = None,
) -> CollectCtgovDocsResult:
    log = progress_cb or (lambda _: None)
    t0 = time.time()

    out_dir = Path(config.out_dir)
    links_path = out_dir / "cid_nct_links.jsonl"
    compounds_path = out_dir / "compounds.jsonl"
    map_csv_path = out_dir / "cid_nct_map.csv"
    studies_path = out_dir / "studies.jsonl"

    log(f"[1/3] Loading CIDs from HNIDs: {','.join(str(h) for h in config.hnids)}")
    step1 = _fetch_cids_by_hnids(config.hnids, out_dir=out_dir, limit=config.limit_cids)
    cids = [int(x.strip()) for x in step1["cids_txt"].read_text(encoding="utf-8").splitlines() if x.strip()]
    log(f"      done: {len(cids)} CIDs")

    if not map_csv_path.exists():
        map_csv_path.parent.mkdir(parents=True, exist_ok=True)
        with map_csv_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["cid", "nct_id"])

    processed_cids = _load_processed_cids(links_path) if config.resume else set()
    study_cache = _load_study_cache_by_nct(studies_path) if config.resume else {}
    existing_ncts = set(study_cache.keys())
    existing_ncts_before = len(existing_ncts)

    pubchem = PubChemClient()
    pug_view = PubChemPugViewClient()
    ctgov = CTGovClient()
    cid_cfg = CidToNctConfig(
        out_dir=str(out_dir),
        write_jsonl=True,
        include_compound_props=True,
        use_ctgov_fallback=config.use_ctgov_fallback,
    )

    nct_fetch_limit = config.limit_ncts if config.limit_ncts is not None else 10**9
    nct_requested = 0
    nct_fetched = 0
    nct_total_mapped = 0
    total_cids = len(cids)

    log("[2/3 + 3/3] Streaming CID -> NCT -> CTGov documents")
    for idx, cid in enumerate(cids, start=1):
        if cid in processed_cids:
            if config.progress_every > 0 and (idx % config.progress_every == 0 or idx == total_cids):
                log(f"[stream] CID {idx}/{total_cids} skipped (resume): cid={cid}")
            continue

        rec = map_cid_to_nct_record(
            cid,
            config=cid_cfg,
            pubchem=pubchem,
            pug_view=pug_view,
            ctgov=ctgov,
        )
        link_row = rec["link"]
        nct_ids = [n for n in link_row.get("nct_ids", []) if isinstance(n, str)]
        nct_total_mapped += len(nct_ids)

        _write_jsonl(links_path, link_row)
        if "compound" in rec:
            _write_jsonl(compounds_path, rec["compound"])

        with map_csv_path.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for nct in nct_ids:
                w.writerow([cid, nct])

        for nct in nct_ids:
            study_obj = study_cache.get(nct)
            if study_obj is None and nct not in existing_ncts:
                if nct_requested >= nct_fetch_limit:
                    break
                nct_requested += 1
                study_obj = ctgov.get_study(nct, fields=list(config.ctgov_fields) if config.ctgov_fields else None)
                study_cache[nct] = study_obj
                existing_ncts.add(nct)
                nct_fetched += 1
            if study_obj is None:
                continue

            out_study = dict(study_obj)
            out_study["cid"] = cid
            _write_jsonl(studies_path, out_study)

        if config.progress_every > 0 and (idx % config.progress_every == 0 or idx == total_cids):
            log(
                f"[stream] CID {idx}/{total_cids} processed: "
                f"cid={cid}, nct_found={len(nct_ids)}, nct_fetched_total={nct_fetched}"
            )

    elapsed = time.time() - t0
    return CollectCtgovDocsResult(
        out_dir=out_dir,
        cids_count=len(cids),
        nct_ids_total_mapped=nct_total_mapped,
        nct_unique_seen=len(existing_ncts),
        nct_requested=nct_requested,
        nct_fetched=nct_fetched,
        nct_existing_before_resume=existing_ncts_before,
        elapsed_sec=elapsed,
        paths={
            "cids_txt": step1["cids_txt"],
            "cids_jsonl": step1["cids_jsonl"],
            "cid_nct_links": links_path,
            "cid_nct_map_csv": map_csv_path,
            "compounds": compounds_path,
            "studies": studies_path,
        },
    )
