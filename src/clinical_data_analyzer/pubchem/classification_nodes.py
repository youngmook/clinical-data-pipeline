# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

from dataclasses import dataclass
from typing import List
import requests
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential


class PubChemClassificationError(RuntimeError):
    pass


@dataclass(frozen=True)
class PubChemClassificationClient:
    base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/classification"
    timeout: float = 60.0
    user_agent: str = "clinical-data-pipeline/0.1 (magicai-labs)"

    def _headers(self) -> dict:
        return {"User-Agent": self.user_agent}

    @retry(
        stop=stop_after_attempt(6),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        retry=retry_if_exception_type((requests.RequestException,)),
        reraise=True,
    )
    def _get_with_retry(self, url: str) -> requests.Response:
        r = requests.get(url, headers=self._headers(), timeout=self.timeout)
        # Retry only for transient/server-busy classes.
        if r.status_code in (429, 500, 502, 503, 504):
            raise requests.RequestException(f"Transient HTTP {r.status_code} for {url}: {r.text[:300]}")
        return r

    def get_ids(self, hnid: int, id_type: str = "cids", fmt: str = "TXT") -> List[int]:
        """
        Generic: HNID -> list of IDs (as integers when possible).
        For compounds: id_type should be 'cids' or 'cid' (case-insensitive).

        Examples:
          hnid/1856916/cids/TXT
          hnid/4501233/patents/JSON   (not int IDs; you may want separate parsing)
        """
        id_type = id_type.lower()
        fmt = fmt.upper()
        url = f"{self.base_url}/hnid/{hnid}/{id_type}/{fmt}"

        r = self._get_with_retry(url)
        if r.status_code != 200:
            raise PubChemClassificationError(f"HTTP {r.status_code} for {url}: {r.text[:300]}")

        if fmt == "TXT":
            # For cids this returns one per line
            vals = []
            for x in r.text.split():
                x = x.strip()
                if x.isdigit():
                    vals.append(int(x))
            return vals

        if fmt == "JSON":
            # Common structure for CID list: {"IdentifierList": {"CID":[...]}}
            data = r.json()
            key = "CID" if "cid" in id_type else None
            if key:
                ids = data.get("IdentifierList", {}).get(key, []) or []
                return [int(x) for x in ids]
            # If not CID-like, return empty or raise depending on your needs
            raise PubChemClassificationError(f"JSON parsing for id_type={id_type} not implemented")

        raise ValueError(f"Unsupported format: {fmt}")

    def get_cids(self, hnid: int, fmt: str = "TXT") -> List[int]:
        """HNID -> CID list (compound IDs)."""
        return self.get_ids(hnid=hnid, id_type="cids", fmt=fmt)
