from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional, Sequence, Union

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


class CTGovError(RuntimeError):
    pass


def _normalize_fields(fields: Optional[Union[str, Sequence[str]]]) -> Optional[str]:
    if not fields:
        return None
    if isinstance(fields, str):
        val = fields.strip()
        return val or None
    cleaned = [f.strip() for f in fields if isinstance(f, str) and f.strip()]
    if not cleaned:
        return None
    # Preserve order, drop duplicates
    seen = set()
    unique: list[str] = []
    for f in cleaned:
        if f in seen:
            continue
        seen.add(f)
        unique.append(f)
    return ",".join(unique)


def _merge_query(params: Dict[str, Any], query: Optional[Dict[str, str]]) -> None:
    if not query:
        return
    for k, v in query.items():
        if not k or v is None:
            continue
        key = f"query.{k}" if not k.startswith("query.") else k
        if key not in params:
            params[key] = v
@dataclass(frozen=True)
class CTGovClient:
    base_url: str = "https://clinicaltrials.gov/api/v2"
    timeout: float = 30.0
    user_agent: str = "clinical-data-pipeline/0.1 (magicai-labs)"
    max_page_size: int = 1000

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
        filter: Optional[str] = None,
        fmt: Optional[str] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        query: Optional[Dict[str, str]] = None,
        sort: Optional[str] = None,
        page_size: int = 50,
        page_token: Optional[str] = None,
        count_total: bool = False,
    ) -> Dict[str, Any]:
        page_size = max(1, min(page_size, self.max_page_size))
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
        if query:
            _merge_query(params, query)
        if sort:
            params["sort"] = sort
        if filter:
            params["filter"] = filter
        if fmt:
            params["format"] = fmt
        if fields:
            val = _normalize_fields(fields)
            if val:
                params["fields"] = val
        if page_token:
            params["pageToken"] = page_token
        return self._get("/studies", params=params)

    def iter_studies(
        self,
        *,
        cond: Optional[str] = None,
        intr: Optional[str] = None,
        term: Optional[str] = None,
        fields: Optional[Union[str, Sequence[str]]] = None,
        query: Optional[Dict[str, str]] = None,
        sort: Optional[str] = None,
        filter: Optional[str] = None,
        fmt: Optional[str] = None,
        page_size: int = 100,
        max_pages: Optional[int] = None,
        max_results: Optional[int] = None,
        start_page_token: Optional[str] = None,
        raise_on_empty: bool = False,
        count_total: bool = False,
    ) -> Iterator[Dict[str, Any]]:
        """Yield study objects from paginated results."""
        token: Optional[str] = start_page_token
        pages = 0
        yielded = 0
        while True:
            payload = self.search_studies(
                cond=cond,
                intr=intr,
                term=term,
                fields=fields,
                query=query,
                sort=sort,
                filter=filter,
                fmt=fmt,
                page_size=page_size,
                page_token=token,
                count_total=count_total,
            )
            studies = payload.get("studies", []) or []
            if raise_on_empty and not studies and pages == 0:
                raise CTGovError("No studies found for query")
            for s in studies:
                yield s
                yielded += 1
                if max_results is not None and yielded >= max_results:
                    return

            token = payload.get("nextPageToken")
            pages += 1
            if not token:
                break
            if max_pages is not None and pages >= max_pages:
                break

    def get_study(
        self,
        nct_id: str,
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        fmt: Optional[str] = None,
    ) -> Dict[str, Any]:
        params: Optional[Dict[str, Any]] = None
        val = _normalize_fields(fields)
        if val:
            params = {"fields": val}
        if fmt:
            if params is None:
                params = {}
            params["format"] = fmt
        return self._get(f"/studies/{nct_id}", params=params)
