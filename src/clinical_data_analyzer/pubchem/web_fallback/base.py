# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence
import json

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .common import (
    PubChemWebFallbackError,
    SDQ_COLLECTION_CLINICALTRIALS,
    SDQ_COLLECTION_EU_REGISTER,
    SDQ_COLLECTION_JAPAN_NIPH,
)


@dataclass(frozen=True)
class PubChemWebFallbackBaseClient:
    base_url: str = "https://pubchem.ncbi.nlm.nih.gov"
    timeout: float = 60.0
    user_agent: str = "clinical-data-pipeline/0.1 (magicai-labs)"

    def _session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({"User-Agent": self.user_agent})
        return s

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((requests.RequestException,)),
    )
    def get_compound_page_html(self, cid: int) -> str:
        url = f"{self.base_url}/compound/{cid}"
        with self._session() as s:
            r = s.get(url, timeout=self.timeout)
            try:
                r.raise_for_status()
            except requests.HTTPError as e:
                raise PubChemWebFallbackError(f"HTTP {r.status_code} for {url}: {r.text[:500]}") from e
            return r.text

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((requests.RequestException,)),
    )
    def get_sdq_payload(
        self,
        cid: int,
        *,
        collection: str = SDQ_COLLECTION_CLINICALTRIALS,
        limit: int = 200,
        order: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        if order is None:
            order = (
                ["date,desc"]
                if collection in (SDQ_COLLECTION_EU_REGISTER, SDQ_COLLECTION_JAPAN_NIPH)
                else ["updatedate,desc"]
            )
        query_obj = {
            "select": "*",
            "collection": collection,
            "order": list(order),
            "start": 1,
            "limit": int(limit),
            "nullatbottom": 1,
            "where": {"ands": [{"cid": str(cid)}]},
            "width": 1000000,
        }
        url = f"{self.base_url}/sdq/sphinxql.cgi"
        params = {
            "infmt": "json",
            "outfmt": "json",
            "query": json.dumps(query_obj, separators=(",", ":")),
        }
        with self._session() as s:
            r = s.get(url, params=params, timeout=self.timeout)
            try:
                r.raise_for_status()
            except requests.HTTPError as e:
                raise PubChemWebFallbackError(f"HTTP {r.status_code} for {url}: {r.text[:500]}") from e
            try:
                return r.json()
            except json.JSONDecodeError as e:
                raise PubChemWebFallbackError(f"Invalid JSON response for {url}: {r.text[:500]}") from e
