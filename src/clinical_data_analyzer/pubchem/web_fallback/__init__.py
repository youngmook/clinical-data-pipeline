# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from .base import PubChemWebFallbackBaseClient
from .common import (
    PubChemWebFallbackError,
    SDQ_COLLECTION_CLINICALTRIALS,
    SDQ_COLLECTION_EU_REGISTER,
    SDQ_COLLECTION_JAPAN_NIPH,
    align_rows_to_union_schema,
    extract_nct_ids_from_html,
    extract_nct_ids_from_sdq_payload,
    extract_sdq_rows,
    normalize_sdq_trial_row,
    normalize_sdq_trial_row_union,
)
from .ctgov import get_ctgov_normalized_trials, get_ctgov_sdq_payload
from .eu_ctr import get_eu_normalized_trials, get_eu_sdq_payload
from .jp_niph import get_jp_normalized_trials, get_jp_sdq_payload


class PubChemWebFallbackClient(PubChemWebFallbackBaseClient):
    def get_clinicaltrials_sdq_payload(self, cid: int, *, limit: int = 200) -> Dict[str, Any]:
        return get_ctgov_sdq_payload(self, cid, limit=limit)

    def get_eu_register_sdq_payload(self, cid: int, *, limit: int = 200) -> Dict[str, Any]:
        return get_eu_sdq_payload(self, cid, limit=limit)

    def get_japan_niph_sdq_payload(self, cid: int, *, limit: int = 200) -> Dict[str, Any]:
        return get_jp_sdq_payload(self, cid, limit=limit)

    # Backward-compatible wrappers
    def get_clinicaltrials_eu_sdq_payload(self, cid: int, *, limit: int = 200) -> Dict[str, Any]:
        return self.get_eu_register_sdq_payload(cid, limit=limit)

    def get_clinicaltrials_jp_sdq_payload(self, cid: int, *, limit: int = 200) -> Dict[str, Any]:
        return self.get_japan_niph_sdq_payload(cid, limit=limit)

    def get_normalized_trials(
        self,
        cid: int,
        *,
        collection: str = SDQ_COLLECTION_CLINICALTRIALS,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        if collection == SDQ_COLLECTION_CLINICALTRIALS:
            return get_ctgov_normalized_trials(self, cid, limit=limit)
        if collection == SDQ_COLLECTION_EU_REGISTER:
            return get_eu_normalized_trials(self, cid, limit=limit)
        if collection == SDQ_COLLECTION_JAPAN_NIPH:
            return get_jp_normalized_trials(self, cid, limit=limit)

        payload = self.get_sdq_payload(cid, collection=collection, limit=limit)
        rows = extract_sdq_rows(payload)
        return [normalize_sdq_trial_row(r, collection=collection) for r in rows]

    def get_normalized_trials_union(
        self,
        cid: int,
        *,
        collections: Sequence[str] = (
            SDQ_COLLECTION_CLINICALTRIALS,
            SDQ_COLLECTION_EU_REGISTER,
            SDQ_COLLECTION_JAPAN_NIPH,
        ),
        limit_per_collection: int = 200,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        merged: List[Dict[str, Any]] = []
        for collection in collections:
            payload = self.get_sdq_payload(cid, collection=collection, limit=limit_per_collection)
            rows = extract_sdq_rows(payload)
            merged.extend(normalize_sdq_trial_row_union(r, collection=collection) for r in rows)
        return align_rows_to_union_schema(merged)

    def nct_ids_for_cid_with_source(self, cid: int) -> Tuple[List[str], str]:
        try:
            sdq_payload = self.get_clinicaltrials_sdq_payload(cid)
            sdq_ncts = extract_nct_ids_from_sdq_payload(sdq_payload)
            if sdq_ncts:
                return sdq_ncts, "PubChem web clinicaltrials endpoint fallback (sdq)"
        except PubChemWebFallbackError:
            pass

        try:
            eu_payload = self.get_eu_register_sdq_payload(cid)
            eu_ncts = extract_nct_ids_from_sdq_payload(eu_payload)
            if eu_ncts:
                return eu_ncts, "PubChem web EU Clinical Trials Register endpoint fallback (sdq)"
        except PubChemWebFallbackError:
            pass

        try:
            jp_payload = self.get_japan_niph_sdq_payload(cid)
            jp_ncts = extract_nct_ids_from_sdq_payload(jp_payload)
            if jp_ncts:
                return jp_ncts, "PubChem web NIPH Clinical Trials Search of Japan endpoint fallback (sdq)"
        except PubChemWebFallbackError:
            pass

        html = self.get_compound_page_html(cid)
        html_ncts = extract_nct_ids_from_html(html)
        if html_ncts:
            return html_ncts, "PubChem web compound page fallback (html)"
        return [], "PubChem web fallback (empty)"

    def nct_ids_for_cid(self, cid: int) -> List[str]:
        ncts, _ = self.nct_ids_for_cid_with_source(cid)
        return ncts


__all__ = [
    "PubChemWebFallbackClient",
    "PubChemWebFallbackError",
    "SDQ_COLLECTION_CLINICALTRIALS",
    "SDQ_COLLECTION_EU_REGISTER",
    "SDQ_COLLECTION_JAPAN_NIPH",
    "extract_nct_ids_from_html",
    "extract_nct_ids_from_sdq_payload",
    "extract_sdq_rows",
    "normalize_sdq_trial_row",
    "normalize_sdq_trial_row_union",
    "align_rows_to_union_schema",
]
