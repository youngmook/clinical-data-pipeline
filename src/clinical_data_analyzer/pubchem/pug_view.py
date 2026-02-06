# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Set
import re

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class PubChemPugViewError(RuntimeError):
    pass


NCT_RE = re.compile(r"\bNCT\d{8}\b", flags=re.IGNORECASE)
CTGOV_HOST_RE = re.compile(r"clinicaltrials\.gov", flags=re.IGNORECASE)


def _walk(obj: Any) -> Iterable[Any]:
    if isinstance(obj, dict):
        for v in obj.values():
            yield v
            yield from _walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield v
            yield from _walk(v)


def _extract_urls(value: Any) -> Iterable[str]:
    for x in _walk(value):
        if isinstance(x, dict) and "URL" in x and isinstance(x["URL"], str):
            yield x["URL"]


def _extract_nct_ids_from_text(text: str) -> Set[str]:
    return {m.group(0).upper() for m in NCT_RE.finditer(text or "")}


@dataclass(frozen=True)
class PubChemPugViewClient:
    base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"
    timeout: float = 60.0
    user_agent: str = "clinical-data-pipeline/0.1 (magicai-labs)"

    def _session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({"User-Agent": self.user_agent})
        return s

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type((requests.RequestException,)),
    )
    def get_compound_record(self, cid: int) -> Dict[str, Any]:
        url = f"{self.base_url}/data/compound/{cid}/JSON/?response_type=display"
        with self._session() as s:
            r = s.get(url, timeout=self.timeout)
            try:
                r.raise_for_status()
            except requests.HTTPError as e:
                raise PubChemPugViewError(f"HTTP {r.status_code} for {url}: {r.text[:500]}") from e
            return r.json()

    def nct_ids_for_cid(self, cid: int) -> List[str]:
        payload = self.get_compound_record(cid)

        ncts: Set[str] = set()

        for url in _extract_urls(payload):
            if CTGOV_HOST_RE.search(url):
                ncts |= _extract_nct_ids_from_text(url)

        for x in _walk(payload):
            if isinstance(x, str) and ("nct" in x.lower() or "clinicaltrials.gov" in x.lower()):
                ncts |= _extract_nct_ids_from_text(x)

        return sorted(ncts)
