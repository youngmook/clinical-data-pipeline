# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
import re

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from .web_fallback import PubChemWebFallbackClient, PubChemWebFallbackError


class PubChemPugViewError(RuntimeError):
    pass


NCT_RE = re.compile(r"\bNCT\d{8}\b", flags=re.IGNORECASE)
CTGOV_HOST_RE = re.compile(r"clinicaltrials\.gov", flags=re.IGNORECASE)
CLINICAL_TRIALS_RE = re.compile(r"clinical\s*trials?(\.gov)?", flags=re.IGNORECASE)
DRUG_MED_INFO_RE = re.compile(
    r"drug(?:\s|-|&|and)+medication(?:\s|-)+information",
    flags=re.IGNORECASE,
)


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


def _extract_nct_ids_from_payload(payload: Any) -> Set[str]:
    ncts: Set[str] = set()

    for url in _extract_urls(payload):
        if CTGOV_HOST_RE.search(url):
            ncts |= _extract_nct_ids_from_text(url)

    for x in _walk(payload):
        if isinstance(x, str) and ("nct" in x.lower() or "clinicaltrials.gov" in x.lower()):
            ncts |= _extract_nct_ids_from_text(x)

    return ncts


def _has_external_clinical_trials_ref(payload: Any) -> bool:
    for x in _walk(payload):
        if isinstance(x, dict):
            name = x.get("ExternalTableName")
            if isinstance(name, str) and CLINICAL_TRIALS_RE.search(name):
                return True
    return False


def _candidate_clinical_headings(payload: Any) -> Set[str]:
    out: Set[str] = set()
    out.update(
        {
            "ClinicalTrials.gov",
            "Clinical Trials",
            "ClinicalTrials",
            "Drug and Medication Information",
            "Drug-and-Medication-Information",
        }
    )

    for x in _walk(payload):
        if not isinstance(x, dict):
            continue
        for key in ("TOCHeading", "Name", "Heading", "Title"):
            val = x.get(key)
            if isinstance(val, str) and (
                CLINICAL_TRIALS_RE.search(val) or DRUG_MED_INFO_RE.search(val)
            ):
                out.add(val.strip())
    return out


@dataclass(frozen=True)
class PubChemPugViewClient:
    base_url: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view"
    timeout: float = 60.0
    user_agent: str = "clinical-data-pipeline/0.1 (magicai-labs)"
    use_web_fallback: bool = True

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

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        retry=retry_if_exception_type((requests.RequestException,)),
    )
    def get_compound_record_by_heading(self, cid: int, heading: str) -> Dict[str, Any]:
        enc = requests.utils.quote(heading, safe="")
        url = f"{self.base_url}/data/compound/{cid}/JSON/?heading={enc}&response_type=display"
        with self._session() as s:
            r = s.get(url, timeout=self.timeout)
            try:
                r.raise_for_status()
            except requests.HTTPError as e:
                raise PubChemPugViewError(f"HTTP {r.status_code} for {url}: {r.text[:500]}") from e
            return r.json()

    def nct_ids_for_cid_with_source(
        self,
        cid: int,
        *,
        web_fallback_client: Optional[PubChemWebFallbackClient] = None,
    ) -> Tuple[List[str], str]:
        payload = self.get_compound_record(cid)
        ncts = _extract_nct_ids_from_payload(payload)
        source = "PubChem PUG-View annotations"

        # Some compounds reference ClinicalTrials data via external tables.
        # In those cases, direct NCT IDs may be absent in the default payload.
        needs_heading_lookup = (not ncts) or _has_external_clinical_trials_ref(payload)
        if needs_heading_lookup:
            for heading in sorted(_candidate_clinical_headings(payload)):
                try:
                    section_payload = self.get_compound_record_by_heading(cid, heading)
                except PubChemPugViewError:
                    continue
                ncts |= _extract_nct_ids_from_payload(section_payload)

        if not ncts and self.use_web_fallback:
            fallback = web_fallback_client or PubChemWebFallbackClient(
                timeout=self.timeout,
                user_agent=self.user_agent,
            )
            try:
                if hasattr(fallback, "nct_ids_for_cid_with_source"):
                    fallback_ncts, fallback_source = fallback.nct_ids_for_cid_with_source(cid)
                else:
                    fallback_ncts = fallback.nct_ids_for_cid(cid)
                    fallback_source = "PubChem web fallback (compound page HTML)"
                ncts |= set(fallback_ncts)
            except PubChemWebFallbackError:
                pass
            if ncts:
                source = fallback_source

        return sorted(ncts), source

    def nct_ids_for_cid(self, cid: int) -> List[str]:
        ncts, _ = self.nct_ids_for_cid_with_source(cid)
        return ncts
