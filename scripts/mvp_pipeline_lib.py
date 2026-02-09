#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from clinical_data_analyzer.ctgov import CTGovClient
from clinical_data_analyzer.pipeline.cid_to_nct import CidToNctConfig, export_cids_nct_dataset
from clinical_data_analyzer.pubchem import PubChemClassificationClient


TARGET_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("EGFR", re.compile(r"\bEGFR\b", re.IGNORECASE)),
    ("HER2", re.compile(r"\bHER2\b", re.IGNORECASE)),
    ("PD-1", re.compile(r"\bPD-1\b", re.IGNORECASE)),
    ("PD-L1", re.compile(r"\bPD-L1\b", re.IGNORECASE)),
    ("CTLA-4", re.compile(r"\bCTLA-4\b", re.IGNORECASE)),
    ("VEGF", re.compile(r"\bVEGF\b", re.IGNORECASE)),
    ("VEGFR", re.compile(r"\bVEGFR\b", re.IGNORECASE)),
    ("BRAF", re.compile(r"\bBRAF\b", re.IGNORECASE)),
    ("ALK", re.compile(r"\bALK\b", re.IGNORECASE)),
    ("MET", re.compile(r"\bMET\b", re.IGNORECASE)),
    ("TNF", re.compile(r"\bTNF(?:-ALPHA|-Α)?\b", re.IGNORECASE)),
]


def parse_csv_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    rows: List[dict] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_cids(path: Path) -> List[int]:
    cids: List[int] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cids.append(int(line))
    return cids


def write_cids_txt(path: Path, cids: Sequence[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(str(cid) for cid in cids) + "\n", encoding="utf-8")


def fetch_cids_by_hnids(
    hnids: Sequence[int],
    *,
    out_dir: Path,
    limit: Optional[int] = None,
) -> Dict[str, Path]:
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

    ensure_dir(out_dir)
    cids_path = out_dir / "cids.txt"
    cids_jsonl_path = out_dir / "cids.jsonl"
    write_cids_txt(cids_path, ordered_cids)

    rows = [
        {"cid": cid, "source_hnids": sorted(cid_to_hnids.get(cid, set()))}
        for cid in ordered_cids
    ]
    write_jsonl(cids_jsonl_path, rows)

    return {"cids_txt": cids_path, "cids_jsonl": cids_jsonl_path}


def build_cid_nct_map(
    cids: Sequence[int],
    *,
    out_dir: Path,
    include_compound_props: bool = True,
    use_ctgov_fallback: bool = False,
    progress_every: int = 0,
) -> Dict[str, Path]:
    cfg = CidToNctConfig(
        out_dir=str(out_dir),
        write_jsonl=True,
        include_compound_props=include_compound_props,
        use_ctgov_fallback=use_ctgov_fallback,
    )
    outputs = export_cids_nct_dataset(list(cids), config=cfg, progress_every=progress_every)
    links_path = outputs["cid_nct_links"]

    csv_path = out_dir / "cid_nct_map.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cid", "nct_id"])
        for row in read_jsonl(links_path):
            cid = row.get("cid")
            nct_ids = row.get("nct_ids", []) or []
            if not isinstance(cid, int):
                continue
            for nct in nct_ids:
                if isinstance(nct, str) and nct:
                    w.writerow([cid, nct])

    outputs["cid_nct_map_csv"] = csv_path
    return outputs


def load_nct_ids_from_links(path: Path) -> List[str]:
    nct_ids: Set[str] = set()
    for row in read_jsonl(path):
        for nct in row.get("nct_ids", []) or []:
            if isinstance(nct, str) and nct:
                nct_ids.add(nct)
    return sorted(nct_ids)


def load_nct_ids_from_studies(path: Path) -> Set[str]:
    existing: Set[str] = set()
    for row in read_jsonl(path):
        nct = (
            row.get("protocolSection", {})
            .get("identificationModule", {})
            .get("nctId")
        )
        if isinstance(nct, str) and nct:
            existing.add(nct)
    return existing


def fetch_ctgov_studies(
    nct_ids: Sequence[str],
    *,
    out_path: Path,
    fields: Optional[Sequence[str]] = None,
    resume: bool = True,
    limit: Optional[int] = None,
    progress_every: int = 0,
) -> Dict[str, int]:
    ctgov = CTGovClient()
    existing = load_nct_ids_from_studies(out_path) if resume else set()
    queued: List[str] = [nct for nct in nct_ids if nct not in existing]
    if limit is not None:
        queued = queued[:limit]

    fetched = 0
    total = len(queued)
    for idx, nct in enumerate(queued, start=1):
        study = ctgov.get_study(nct, fields=list(fields) if fields else None)
        append_jsonl(out_path, [study])
        fetched += 1
        if progress_every > 0 and (idx % progress_every == 0 or idx == total):
            print(f"[ctgov-fetch] processed {idx}/{total} NCT IDs")

    return {"requested": len(queued), "fetched": fetched, "existing": len(existing)}


def _extract_study_core(study: dict) -> Dict[str, object]:
    ps = study.get("protocolSection") or {}
    ident = ps.get("identificationModule") or {}
    status = ps.get("statusModule") or {}
    design = ps.get("designModule") or {}
    conditions_mod = ps.get("conditionsModule") or {}
    interventions_mod = ps.get("interventionsModule") or {}

    phases = design.get("phases")
    if isinstance(phases, list):
        phase = ";".join([p for p in phases if isinstance(p, str) and p])
    elif isinstance(phases, str):
        phase = phases
    else:
        phase = ""

    conditions = conditions_mod.get("conditions") or []
    if not isinstance(conditions, list):
        conditions = []
    condition_vals = [c for c in conditions if isinstance(c, str) and c]

    interventions_raw = interventions_mod.get("interventions") or []
    if not isinstance(interventions_raw, list):
        interventions_raw = []
    intervention_names: List[str] = []
    intervention_texts: List[str] = []
    for item in interventions_raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name:
            intervention_names.append(name)
            intervention_texts.append(name)
        description = item.get("description")
        if isinstance(description, str) and description:
            intervention_texts.append(description)
        other_names = item.get("otherNames") or []
        if isinstance(other_names, list):
            for other in other_names:
                if isinstance(other, str) and other:
                    intervention_texts.append(other)

    targets: Set[str] = set()
    for text in intervention_texts:
        for label, pattern in TARGET_PATTERNS:
            if pattern.search(text):
                targets.add(label)

    return {
        "nct_id": ident.get("nctId"),
        "title": ident.get("briefTitle") or ident.get("officialTitle") or "",
        "phase": phase,
        "overall_status": status.get("overallStatus") or "",
        "start_date": (status.get("startDateStruct") or {}).get("date") or "",
        "completion_date": (status.get("completionDateStruct") or {}).get("date") or "",
        "last_update_date": (status.get("lastUpdatePostDateStruct") or {}).get("date") or "",
        "conditions": condition_vals,
        "interventions": intervention_names,
        "targets": sorted(targets),
    }


def build_clinical_dataset(
    *,
    links_path: Path,
    studies_path: Path,
    compounds_path: Optional[Path] = None,
    out_dir: Path,
) -> Dict[str, Path]:
    ensure_dir(out_dir)
    links = read_jsonl(links_path)
    studies_rows = read_jsonl(studies_path)
    compounds_rows = read_jsonl(compounds_path) if compounds_path and compounds_path.exists() else []

    study_by_nct: Dict[str, Dict[str, object]] = {}
    for s in studies_rows:
        core = _extract_study_core(s)
        nct = core.get("nct_id")
        if isinstance(nct, str) and nct:
            study_by_nct[nct] = core

    compound_by_cid: Dict[int, dict] = {}
    for row in compounds_rows:
        cid = row.get("cid")
        if isinstance(cid, int):
            compound_by_cid[cid] = row

    normalized_rows: List[dict] = []
    for row in links:
        cid = row.get("cid")
        if not isinstance(cid, int):
            continue
        nct_ids = row.get("nct_ids", []) or []
        for nct in nct_ids:
            if not isinstance(nct, str) or not nct:
                continue
            core = study_by_nct.get(nct, {})
            comp = compound_by_cid.get(cid, {})
            normalized_rows.append(
                {
                    "cid": cid,
                    "nct_id": nct,
                    "compound_name": comp.get("iupac_name") or "",
                    "title": core.get("title", ""),
                    "phase": core.get("phase", ""),
                    "overall_status": core.get("overall_status", ""),
                    "conditions": core.get("conditions", []),
                    "interventions": core.get("interventions", []),
                    "targets": core.get("targets", []),
                    "start_date": core.get("start_date", ""),
                    "completion_date": core.get("completion_date", ""),
                    "last_update_date": core.get("last_update_date", ""),
                    "ctgov_url": f"https://clinicaltrials.gov/study/{nct}",
                    "pubchem_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
                    # Backward-compatible alias for older consumers.
                    "source_url": f"https://clinicaltrials.gov/study/{nct}",
                }
            )

    jsonl_path = out_dir / "clinical_compound_trials.jsonl"
    csv_path = out_dir / "clinical_compound_trials.csv"
    write_jsonl(jsonl_path, normalized_rows)

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "cid",
                "nct_id",
                "compound_name",
                "title",
                "phase",
                "overall_status",
                "conditions",
                "interventions",
                "targets",
                "start_date",
                "completion_date",
                "last_update_date",
                "ctgov_url",
                "pubchem_url",
                "source_url",
            ]
        )
        for row in normalized_rows:
            w.writerow(
                [
                    row["cid"],
                    row["nct_id"],
                    row["compound_name"],
                    row["title"],
                    row["phase"],
                    row["overall_status"],
                    ";".join(row["conditions"]),
                    ";".join(row["interventions"]),
                    ";".join(row["targets"]),
                    row["start_date"],
                    row["completion_date"],
                    row["last_update_date"],
                    row["ctgov_url"],
                    row["pubchem_url"],
                    row["source_url"],
                ]
            )

    return {"dataset_jsonl": jsonl_path, "dataset_csv": csv_path}
