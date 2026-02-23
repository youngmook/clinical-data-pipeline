# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class PubChemError(RuntimeError):
    pass


@dataclass(frozen=True)
class PubChemClient:
    base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
    timeout: float = 30.0
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
    def _get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._session() as s:
            r = s.get(url, params=params, timeout=self.timeout)
            try:
                r.raise_for_status()
            except requests.HTTPError as e:
                raise PubChemError(f"HTTP {r.status_code} for {url}: {r.text[:500]}") from e
            return r.json()

    def cids_by_name(self, name: str) -> List[int]:
        url = f"{self.base_url}/compound/name/{requests.utils.quote(name)}/cids/JSON"
        data = self._get_json(url)
        cids = data.get("IdentifierList", {}).get("CID", []) or []
        return [int(x) for x in cids]

    def compound_properties(self, cid: int) -> Dict[str, Any]:
        props = "CanonicalSMILES,ConnectivitySMILES,InChIKey,IUPACName"
        url = f"{self.base_url}/compound/cid/{cid}/property/{props}/JSON"
        data = self._get_json(url)
        rows = data.get("PropertyTable", {}).get("Properties", []) or []
        if not rows:
            raise PubChemError(f"No properties for CID {cid}")
        row = rows[0]
        # Some CIDs return ConnectivitySMILES only. Normalize to CanonicalSMILES key.
        if isinstance(row, dict) and not row.get("CanonicalSMILES") and row.get("ConnectivitySMILES"):
            row["CanonicalSMILES"] = row.get("ConnectivitySMILES")
        return row

    def synonyms(self, cid: int, max_items: int = 50) -> List[str]:
        url = f"{self.base_url}/compound/cid/{cid}/synonyms/JSON"
        data = self._get_json(url)
        info = data.get("InformationList", {}).get("Information", [])
        if not info:
            return []
        arr = info[0].get("Synonym", []) or []

        seen = set()
        out: List[str] = []
        for s in arr:
            if not isinstance(s, str):
                continue
            t = s.strip()
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(t)
            if len(out) >= max_items:
                break
        return out
