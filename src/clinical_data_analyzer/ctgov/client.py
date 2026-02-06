from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Iterator

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class CTGovError(RuntimeError):
    pass


@dataclass(frozen=True)
class CTGovClient:
    base_url: str = "https://clinicaltrials.gov/api/v2"
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
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        with self._session() as s:
            r = s.get(url, params=params, timeout=self.timeout)
            try:
                r.raise_for_status()
            except requests.HTTPError as e:
                raise CTGovError(f"HTTP {r.status_code} for {url}: {r.text[:500]}") from e
            return r.json()

    def search_studies(
        self,
        *,
        cond: Optional[str] = None,
        intr: Optional[str] = None,
        term: Optional[str] = None,
        page_size: int = 50,
        page_token: Optional[str] = None,
        count_total: bool = True,
    ) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "pageSize": page_size,
            "countTotal": str(count_total).lower(),
        }
        if cond:
            params["query.cond"] = cond
        if intr:
            params["query.intr"] = intr
        if term:
            params["query.term"] = term
        if page_token:
            params["pageToken"] = page_token
        return self._get("/studies", params=params)

    def iter_studies(
        self,
        *,
        cond: Optional[str] = None,
        intr: Optional[str] = None,
        term: Optional[str] = None,
        page_size: int = 100,
        max_pages: Optional[int] = None,
    ) -> Iterator[Dict[str, Any]]:
        """Yield study objects from paginated results."""
        token: Optional[str] = None
        pages = 0
        while True:
            payload = self.search_studies(cond=cond, intr=intr, term=term, page_size=page_size, page_token=token)
            studies = payload.get("studies", []) or []
            for s in studies:
                yield s

            token = payload.get("nextPageToken")
            pages += 1
            if not token:
                break
            if max_pages is not None and pages >= max_pages:
                break

    def get_study(self, nct_id: str) -> Dict[str, Any]:
        return self._get(f"/studies/{nct_id}")
