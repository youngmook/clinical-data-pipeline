# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple
import re


def _norm_text(s: str) -> str:
    s = s.casefold()
    s = re.sub(r"\s+", " ", s).strip()
    return s


@dataclass(frozen=True)
class LinkEvidence:
    term: str
    query_mode: str  # "intr" or "term"
    score: int
    reasons: List[str]


@dataclass(frozen=True)
class LinkResult:
    cid: int
    nct_id: str
    evidence: LinkEvidence


@dataclass(frozen=True)
class LinkerConfig:
    max_synonyms: int = 20
    ctgov_page_size: int = 100
    ctgov_max_pages_per_term: int = 2
    min_score: int = 2
    max_links_per_cid: int = 50


class CompoundTrialLinker:
    def __init__(self, pubchem_client, ctgov_client, config: Optional[LinkerConfig] = None):
        self.pubchem = pubchem_client
        self.ctgov = ctgov_client
        self.config = config or LinkerConfig()

    def _extract_nct_id(self, study_obj: Dict[str, Any]) -> Optional[str]:
        ps = study_obj.get("protocolSection") or {}
        ident = ps.get("identificationModule") or {}
        nct = ident.get("nctId")
        if isinstance(nct, str) and nct.strip():
            return nct.strip()
        for k in ("nctId", "NCTId", "nct_id"):
            v = study_obj.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
        return None

    def _extract_text_blob(self, study_obj: Dict[str, Any]) -> str:
        ps = study_obj.get("protocolSection") or {}

        ident = ps.get("identificationModule") or {}
        title = ident.get("briefTitle") or ""
        official = ident.get("officialTitle") or ""

        status = (ps.get("statusModule") or {}).get("overallStatus") or ""

        conditions = (ps.get("conditionsModule") or {}).get("conditions") or []
        if not isinstance(conditions, list):
            conditions = []

        im = ps.get("interventionsModule") or {}
        interventions = im.get("interventions") or []
        names: List[str] = []
        if isinstance(interventions, list):
            for it in interventions:
                if not isinstance(it, dict):
                    continue
                name = it.get("name")
                if isinstance(name, str):
                    names.append(name)

        pieces = [title, official, status, " ".join([c for c in conditions if isinstance(c, str)]), " ".join(names)]
        return _norm_text(" ".join([p for p in pieces if isinstance(p, str)]))

    def _score(self, term: str, study_obj: Dict[str, Any]) -> Tuple[int, List[str]]:
        reasons: List[str] = []
        blob = self._extract_text_blob(study_obj)

        t = _norm_text(term)
        score = 0

        if t and t in blob:
            score += 2
            reasons.append("term_found_in_core_fields(+2)")

        if t:
            pattern = r"(^|[^a-z0-9])" + re.escape(t) + r"([^a-z0-9]|$)"
            if re.search(pattern, blob):
                score += 1
                reasons.append("term_whole_word_match(+1)")

        return score, reasons

    def _iter_ctgov_by_term(self, term: str) -> Iterable[Tuple[str, Dict[str, Any]]]:
        for s in self.ctgov.iter_studies(
            intr=term,
            page_size=self.config.ctgov_page_size,
            max_pages=self.config.ctgov_max_pages_per_term,
        ):
            yield "intr", s

        for s in self.ctgov.iter_studies(
            term=term,
            page_size=self.config.ctgov_page_size,
            max_pages=self.config.ctgov_max_pages_per_term,
        ):
            yield "term", s

    def link_cid(self, cid: int) -> List[LinkResult]:
        syns = self.pubchem.synonyms(cid, max_items=self.config.max_synonyms)
        props = self.pubchem.compound_properties(cid)

        iupac = props.get("IUPACName")
        if isinstance(iupac, str) and iupac.strip():
            if len(iupac) <= 40 and iupac not in syns:
                syns.insert(0, iupac.strip())

        results: List[LinkResult] = []
        seen_pairs = set()

        for term in syns:
            term = term.strip()
            if not term:
                continue

            for mode, study in self._iter_ctgov_by_term(term):
                nct = self._extract_nct_id(study)
                if not nct:
                    continue

                score, reasons = self._score(term, study)
                if score < self.config.min_score:
                    continue

                key = (cid, nct)
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)

                ev = LinkEvidence(term=term, query_mode=mode, score=score, reasons=reasons)
                results.append(LinkResult(cid=cid, nct_id=nct, evidence=ev))

                if len(results) >= self.config.max_links_per_cid:
                    return results

        return results
