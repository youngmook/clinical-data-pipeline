# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Set, Tuple
import re


NCT_RE = re.compile(r"\bNCT\d{8}\b", flags=re.IGNORECASE)

SDQ_COLLECTION_CLINICALTRIALS = "clinicaltrials"
SDQ_COLLECTION_EU_REGISTER = "clinicaltrials_eu"
SDQ_COLLECTION_JAPAN_NIPH = "clinicaltrials_jp"

SDQ_COLLECTION_LABELS = {
    SDQ_COLLECTION_CLINICALTRIALS: "ClinicalTrials.gov",
    SDQ_COLLECTION_EU_REGISTER: "EU Clinical Trials Register",
    SDQ_COLLECTION_JAPAN_NIPH: "NIPH Clinical Trials Search of Japan",
}


class PubChemWebFallbackError(RuntimeError):
    pass


def _walk(obj: Any) -> Iterable[Any]:
    if isinstance(obj, dict):
        for v in obj.values():
            yield v
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield v
            yield from _walk(v)


def extract_nct_ids_from_html(html: str) -> List[str]:
    ncts: Set[str] = {m.group(0).upper() for m in NCT_RE.finditer(html or "")}
    return sorted(ncts)


def extract_nct_ids_from_sdq_payload(payload: Dict[str, Any]) -> List[str]:
    ncts: Set[str] = set()
    for x in _walk(payload):
        if isinstance(x, str):
            for m in NCT_RE.finditer(x):
                ncts.add(m.group(0).upper())
    return sorted(ncts)


def extract_sdq_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    output_set = payload.get("SDQOutputSet")
    if not isinstance(output_set, list) or not output_set:
        return []
    first = output_set[0]
    if not isinstance(first, dict):
        return []
    rows = first.get("rows")
    if not isinstance(rows, list):
        return []
    return [r for r in rows if isinstance(r, dict)]


def normalize_sdq_trial_row(row: Dict[str, Any], *, collection: str) -> Dict[str, Any]:
    if collection == SDQ_COLLECTION_EU_REGISTER:
        trial_id = row.get("eudractnumber") or row.get("ctid")
    else:
        trial_id = row.get("ctid") or row.get("eudractnumber")

    date_val = row.get("date")
    if date_val is None:
        date_val = row.get("updatedate")

    link_val = row.get("id_url") or row.get("link")

    return {
        "collection": SDQ_COLLECTION_LABELS.get(collection, collection),
        "collection_code": collection,
        "id": trial_id,
        "title": row.get("title"),
        "phase": row.get("phase"),
        "status": row.get("status"),
        "date": date_val,
        "id_url": link_val,
        "cids": row.get("cids"),
    }


def normalize_sdq_trial_row_union(row: Dict[str, Any], *, collection: str) -> Dict[str, Any]:
    out = normalize_sdq_trial_row(row, collection=collection)
    for k, v in row.items():
        if k not in out:
            out[k] = v
    return out


def align_rows_to_union_schema(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[str]]:
    if not rows:
        return [], []
    keys: Set[str] = set()
    for r in rows:
        keys.update(r.keys())
    ordered_keys = sorted(keys)
    aligned: List[Dict[str, Any]] = []
    for r in rows:
        aligned.append({k: r.get(k) for k in ordered_keys})
    return aligned, ordered_keys
