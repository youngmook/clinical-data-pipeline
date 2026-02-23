# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterator, Optional, Sequence, Union
import json
import logging
import time

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)

class CTGovError(RuntimeError):
    pass


class CTGovRateLimitError(CTGovError):
    pass


class CTGovSort:
    LAST_UPDATE_POST_DATE = "LastUpdatePostDate"

    @staticmethod
    def asc(field: str) -> str:
        return f"{field}:asc"

    @staticmethod
    def desc(field: str) -> str:
        return f"{field}:desc"


class CTGovFilterKey:
    OVERALL_STATUS = "overallStatus"
    GEO = "geo"
    IDS = "ids"
    ADVANCED = "advanced"


CTGOV_QUERY_KEYS = {
    "cond",
    "intr",
    "term",
    "titles",
    "locn",
    "spons",
    "lead",
    "outc",
    "id",
}
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


def _merge_query(
    params: Dict[str, Any],
    query: Optional[Dict[str, str]],
    *,
    validate: bool = False,
    allowed: Optional[set[str]] = None,
) -> None:
    if not query:
        return
    for k, v in query.items():
        if not k or v is None:
            continue
        key = f"query.{k}" if not k.startswith("query.") else k
        if validate:
            base_key = key[len("query.") :] if key.startswith("query.") else key
            allowed_keys = allowed or CTGOV_QUERY_KEYS
            if base_key not in allowed_keys:
                raise CTGovError(f"Invalid query key: {base_key}")
        if key not in params:
            params[key] = v


def extract_study_compact(study_obj: Dict[str, Any]) -> Dict[str, Any]:
    ps = study_obj.get("protocolSection") or {}
    ident = ps.get("identificationModule") or {}
    status = ps.get("statusModule") or {}
    conditions_mod = ps.get("conditionsModule") or {}
    interventions_mod = ps.get("interventionsModule") or {}
    sponsors_mod = ps.get("sponsorsModule") or {}

    conditions = conditions_mod.get("conditions") or []
    if not isinstance(conditions, list):
        conditions = []

    interventions = interventions_mod.get("interventions") or []
    intervention_names = [
        it.get("name")
        for it in interventions
        if isinstance(it, dict) and isinstance(it.get("name"), str)
    ]

    lead = sponsors_mod.get("leadSponsor") or {}
    collaborators = sponsors_mod.get("collaborators") or []
    collaborator_names = [
        c.get("name")
        for c in collaborators
        if isinstance(c, dict) and isinstance(c.get("name"), str)
    ]

    return {
        "nct_id": ident.get("nctId"),
        "brief_title": ident.get("briefTitle"),
        "official_title": ident.get("officialTitle"),
        "overall_status": status.get("overallStatus"),
        "start_date": status.get("startDateStruct", {}).get("date"),
        "completion_date": status.get("completionDateStruct", {}).get("date"),
        "conditions": [c for c in conditions if isinstance(c, str)],
        "interventions": intervention_names,
        "lead_sponsor": lead.get("name"),
        "collaborators": collaborator_names,
    }
@dataclass(frozen=True)
class CTGovClient:
    base_url: str = "https://clinicaltrials.gov/api/v2"
    timeout: float = 30.0
    user_agent: str = "clinical-data-pipeline/0.1 (magicai-labs)"
    max_page_size: int = 1000
    log_requests: bool = False
    request_id_headers: Sequence[str] = ("x-request-id", "x-requestid", "x-correlation-id")

    def _session(self) -> requests.Session:
        s = requests.Session()
        s.headers.update({"User-Agent": self.user_agent})
        return s

    @retry(
        reraise=True,
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=8),
        retry=retry_if_exception_type((requests.RequestException, CTGovRateLimitError)),
    )
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        with self._session() as s:
            r = s.get(url, params=params, timeout=self.timeout)
            if self.log_requests:
                request_id = None
                for h in self.request_id_headers:
                    request_id = r.headers.get(h)
                    if request_id:
                        break
                logger.info("CTGov GET %s status=%s request_id=%s", url, r.status_code, request_id)
            try:
                if r.status_code in (408, 429, 503, 504):
                    retry_after = r.headers.get("Retry-After")
                    if retry_after:
                        try:
                            time.sleep(float(retry_after))
                        except ValueError:
                            pass
                    raise CTGovRateLimitError(f"HTTP {r.status_code} for {url}: {r.text[:500]}")
                r.raise_for_status()
            except requests.HTTPError as e:
                raise CTGovError(f"HTTP {r.status_code} for {url}: {r.text[:500]}") from e
            try:
                return r.json()
            except json.JSONDecodeError as e:
                raise CTGovError(f"Invalid JSON response for {url}: {r.text[:500]}") from e

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
        validate_query_keys: bool = False,
        allowed_query_keys: Optional[Sequence[str]] = None,
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
            allowed = set(allowed_query_keys) if allowed_query_keys else None
            _merge_query(params, query, validate=validate_query_keys, allowed=allowed)
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
        validate_query_keys: bool = False,
        allowed_query_keys: Optional[Sequence[str]] = None,
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
                validate_query_keys=validate_query_keys,
                allowed_query_keys=allowed_query_keys,
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

    def get_study_compact(
        self,
        nct_id: str,
        *,
        fields: Optional[Union[str, Sequence[str]]] = None,
        fmt: Optional[str] = None,
    ) -> Dict[str, Any]:
        study = self.get_study(nct_id, fields=fields, fmt=fmt)
        return extract_study_compact(study)
