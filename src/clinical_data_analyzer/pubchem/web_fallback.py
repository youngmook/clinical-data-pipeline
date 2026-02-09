# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Set, Tuple
import json
import re

import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


NCT_RE = re.compile(r"\bNCT\d{8}\b", flags=re.IGNORECASE)


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


@dataclass(frozen=True)
class PubChemWebFallbackClient:
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
        # Web fallback: parse rendered page source when REST payload misses NCT IDs.
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
    def get_clinicaltrials_sdq_payload(self, cid: int, *, limit: int = 200) -> Dict[str, Any]:
        query_obj = {
            "select": "*",
            "collection": "clinicaltrials",
            "order": ["updatedate,desc"],
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

    def nct_ids_for_cid_with_source(self, cid: int) -> Tuple[List[str], str]:
        # Priority 1: web clinicaltrials endpoint used by PubChem summary UI.
        try:
            sdq_payload = self.get_clinicaltrials_sdq_payload(cid)
            sdq_ncts = extract_nct_ids_from_sdq_payload(sdq_payload)
            if sdq_ncts:
                return sdq_ncts, "PubChem web clinicaltrials endpoint fallback (sdq)"
        except PubChemWebFallbackError:
            pass

        # Priority 2: HTML source fallback.
        html = self.get_compound_page_html(cid)
        html_ncts = extract_nct_ids_from_html(html)
        if html_ncts:
            return html_ncts, "PubChem web compound page fallback (html)"
        return [], "PubChem web fallback (empty)"

    def nct_ids_for_cid(self, cid: int) -> List[str]:
        ncts, _ = self.nct_ids_for_cid_with_source(cid)
        return ncts
