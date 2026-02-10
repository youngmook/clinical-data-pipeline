# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

from typing import Any, Dict, List

from .common import SDQ_COLLECTION_CLINICALTRIALS, extract_sdq_rows, normalize_sdq_trial_row


def get_ctgov_sdq_payload(client, cid: int, *, limit: int = 200) -> Dict[str, Any]:
    return client.get_sdq_payload(
        cid,
        collection=SDQ_COLLECTION_CLINICALTRIALS,
        limit=limit,
        order=["updatedate,desc"],
    )


def get_ctgov_normalized_trials(client, cid: int, *, limit: int = 200) -> List[Dict[str, Any]]:
    payload = get_ctgov_sdq_payload(client, cid, limit=limit)
    rows = extract_sdq_rows(payload)
    return [normalize_sdq_trial_row(r, collection=SDQ_COLLECTION_CLINICALTRIALS) for r in rows]
