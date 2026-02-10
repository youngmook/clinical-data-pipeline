# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

from typing import Any, Dict, List
import json

import requests
import pytest

from clinical_data_analyzer.ctgov import (
    CTGOV_QUERY_KEYS,
    CTGovClient,
    CTGovError,
    CTGovSort,
    extract_study_compact,
)
from clinical_data_analyzer.pubchem.client import PubChemClient
from clinical_data_analyzer.pubchem import PubChemClassificationClient
from clinical_data_analyzer.pubchem import PubChemPugViewClient
from clinical_data_analyzer.pubchem.web_fallback import (
    PubChemWebFallbackClient,
    align_rows_to_union_schema,
    extract_sdq_rows,
    normalize_sdq_trial_row,
    normalize_sdq_trial_row_union,
    extract_nct_ids_from_sdq_payload,
    extract_nct_ids_from_html,
)
from clinical_data_analyzer.pipeline.build_dataset import build_dataset_for_cids
from clinical_data_analyzer.pipeline.cid_to_nct import CidToNctConfig, export_cids_nct_dataset


class _DummyResponse:
    def __init__(self, data: Dict[str, Any], status: int = 200, headers: Dict[str, str] | None = None):
        self._data = data
        self.status_code = status
        self.headers = headers or {}
        self.text = "dummy"

    def json(self) -> Dict[str, Any]:
        return self._data

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError("error")


class _DummySession:
    def __init__(self, responses: List[_DummyResponse]):
        self._responses = list(responses)
        self.headers: Dict[str, str] = {}

    def get(self, url: str, params: Dict[str, Any] | None = None, timeout: float | None = None):
        return self._responses.pop(0)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_ctgov_search_iter_and_compact(monkeypatch):
    payload = {
        "studies": [
            {
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT00000001", "briefTitle": "Test"},
                    "statusModule": {"overallStatus": "COMPLETED"},
                }
            }
        ]
    }
    responses = [_DummyResponse(payload)]

    client = CTGovClient()
    monkeypatch.setattr(CTGovClient, "_session", lambda self: _DummySession(responses))

    data = client.search_studies(term="aspirin", fields=["NCTId", "BriefTitle"], sort=CTGovSort.asc("NCTId"))
    assert "studies" in data

    studies = list(client.iter_studies(term="aspirin", max_results=1))
    assert studies[0]["protocolSection"]["identificationModule"]["nctId"] == "NCT00000001"

    compact = extract_study_compact(studies[0])
    assert compact["nct_id"] == "NCT00000001"


def test_ctgov_query_validation(monkeypatch):
    payload = {"studies": []}
    responses = [_DummyResponse(payload)]

    client = CTGovClient()
    monkeypatch.setattr(CTGovClient, "_session", lambda self: _DummySession(responses))

    ok = client.search_studies(query={"titles": "aspirin"}, validate_query_keys=True)
    assert "studies" in ok

    with pytest.raises(CTGovError):
        client.search_studies(query={"badkey": "x"}, validate_query_keys=True)

    assert "titles" in CTGOV_QUERY_KEYS


def test_pubchem_clients(monkeypatch):
    pub = PubChemClient()

    responses = [
        _DummyResponse({"IdentifierList": {"CID": [2244]}}),
        _DummyResponse(
            {
                "PropertyTable": {
                    "Properties": [
                        {
                            "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
                            "InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
                            "IUPACName": "2-acetyloxybenzoic acid",
                        }
                    ]
                }
            }
        ),
        _DummyResponse({"InformationList": {"Information": [{"Synonym": ["Aspirin"]}]}}),
    ]

    response_iter = iter(responses)
    monkeypatch.setattr(
        PubChemClient,
        "_session",
        lambda self: _DummySession([next(response_iter)]),
    )

    cids = pub.cids_by_name("aspirin")
    assert cids == [2244]

    props = pub.compound_properties(2244)
    assert props["InChIKey"].startswith("BSYNRY")

    syns = pub.synonyms(2244, max_items=10)
    assert "Aspirin" in syns


def test_pubchem_classification(monkeypatch):
    class DummyResponse:
        status_code = 200
        text = "101\n102\n"

        def json(self):
            return {"IdentifierList": {"CID": [101, 102]}}

    def fake_get(url, headers=None, timeout=None):
        return DummyResponse()

    monkeypatch.setattr(requests, "get", fake_get)

    client = PubChemClassificationClient()
    cids = client.get_cids(123, fmt="TXT")
    assert cids == [101, 102]


def test_pug_view_extracts_nct(monkeypatch):
    payload = {
        "Record": {
            "Section": [
                {
                    "Information": [
                        {"URL": "https://clinicaltrials.gov/study/NCT01234567"}
                    ]
                }
            ]
        }
    }

    pv = PubChemPugViewClient()
    monkeypatch.setattr(PubChemPugViewClient, "_session", lambda self: _DummySession([_DummyResponse(payload)]))

    ncts = pv.nct_ids_for_cid(2244)
    assert ncts == ["NCT01234567"]


def test_pug_view_heading_lookup_for_external_clinical_trials(monkeypatch):
    base_payload = {
        "Record": {
            "Section": [
                {
                    "Information": [
                        {"ExternalTableName": "clinicaltrials"},
                    ]
                }
            ]
        }
    }
    heading_payload = {
        "Record": {
            "Section": [
                {
                    "Information": [
                        {"StringValue": "Referenced study NCT76543210"},
                    ]
                }
            ]
        }
    }

    pv = PubChemPugViewClient()
    monkeypatch.setattr(PubChemPugViewClient, "get_compound_record", lambda self, cid: base_payload)
    monkeypatch.setattr(
        PubChemPugViewClient,
        "get_compound_record_by_heading",
        lambda self, cid, heading: heading_payload,
    )

    ncts = pv.nct_ids_for_cid(6)
    assert ncts == ["NCT76543210"]


def test_pug_view_heading_lookup_for_drug_medication_info(monkeypatch):
    base_payload = {"Record": {"Section": [{"TOCHeading": "Overview"}]}}

    def _by_heading(self, cid, heading):
        if heading == "Drug-and-Medication-Information":
            return {
                "Record": {
                    "Section": [
                        {"Information": [{"StringValue": "CTID: NCT01214278"}]}
                    ]
                }
            }
        return {"Record": {"Section": []}}

    pv = PubChemPugViewClient()
    monkeypatch.setattr(PubChemPugViewClient, "get_compound_record", lambda self, cid: base_payload)
    monkeypatch.setattr(PubChemPugViewClient, "get_compound_record_by_heading", _by_heading)

    ncts = pv.nct_ids_for_cid(38)
    assert ncts == ["NCT01214278"]


def test_extract_nct_ids_from_html():
    html = "<html><body>CTID: NCT01214278 and NCT00000001</body></html>"
    assert extract_nct_ids_from_html(html) == ["NCT00000001", "NCT01214278"]


def test_extract_nct_ids_from_sdq_payload():
    payload = {
        "SDQOutputSet": [
            {
                "rows": [
                    {"ctid": "NCT01214278"},
                    {"ctid": "NCT00000001"},
                ]
            }
        ]
    }
    assert extract_nct_ids_from_sdq_payload(payload) == ["NCT00000001", "NCT01214278"]


def test_web_fallback_uses_sdq_first():
    class DummyWebFallback(PubChemWebFallbackClient):
        def get_clinicaltrials_sdq_payload(self, cid: int, *, limit: int = 200):
            return {"rows": [{"ctid": "NCT01214278"}]}

        def get_compound_page_html(self, cid: int):
            raise AssertionError("html fallback should not be called when sdq has NCT")

    ncts, source = DummyWebFallback().nct_ids_for_cid_with_source(38)
    assert ncts == ["NCT01214278"]
    assert source.startswith("PubChem web clinicaltrials endpoint fallback")


def test_normalize_sdq_trial_row_ctgov_uses_date_alias():
    row = {
        "ctid": "NCT01561508",
        "title": "Trial",
        "phase": "Phase 2",
        "status": "Withdrawn",
        "updatedate": "2012-12-24",
        "link": "https://clinicaltrials.gov/study/NCT01561508",
    }
    out = normalize_sdq_trial_row(row, collection="clinicaltrials")
    assert out["id"] == "NCT01561508"
    assert out["date"] == "2012-12-24"
    assert out["id_url"] == "https://clinicaltrials.gov/study/NCT01561508"


def test_normalize_sdq_trial_row_eu_uses_eudract_as_id():
    row = {
        "eudractnumber": "2006-006023-39",
        "title": "EU Trial",
        "phase": "Phase 2",
        "status": "Completed",
        "date": "2007-09-24",
        "link": "https://www.clinicaltrialsregister.eu/ctr-search/search?query=2006-006023-39",
    }
    out = normalize_sdq_trial_row(row, collection="clinicaltrials_eu")
    assert out["id"] == "2006-006023-39"
    assert out["date"] == "2007-09-24"
    assert out["id_url"].startswith("https://www.clinicaltrialsregister.eu/")


def test_extract_sdq_rows_and_union_alignment():
    payload = {
        "SDQOutputSet": [
            {
                "rows": [
                    {"ctid": "NCT00000001", "updatedate": "2020-01-01", "title": "A"},
                    {"eudractnumber": "2006-006023-39", "date": "2007-09-24", "status": "Completed"},
                ]
            }
        ]
    }
    rows = extract_sdq_rows(payload)
    assert len(rows) == 2

    a = normalize_sdq_trial_row_union(rows[0], collection="clinicaltrials")
    b = normalize_sdq_trial_row_union(rows[1], collection="clinicaltrials_eu")
    aligned, keys = align_rows_to_union_schema([a, b])

    assert "id" in keys
    assert "date" in keys
    assert "eudractnumber" in keys
    assert "ctid" in keys
    assert aligned[0]["id"] == "NCT00000001"
    assert aligned[1]["id"] == "2006-006023-39"


def test_pug_view_uses_web_fallback_when_rest_empty(monkeypatch):
    pv = PubChemPugViewClient(use_web_fallback=True)
    monkeypatch.setattr(PubChemPugViewClient, "get_compound_record", lambda self, cid: {"Record": {}})
    monkeypatch.setattr(
        PubChemPugViewClient,
        "get_compound_record_by_heading",
        lambda self, cid, heading: {"Record": {"Section": []}},
    )

    class DummyWebFallback(PubChemWebFallbackClient):
        def nct_ids_for_cid_with_source(self, cid: int):
            return ["NCT01214278"], "PubChem web clinicaltrials endpoint fallback (sdq)"

    ncts, source = pv.nct_ids_for_cid_with_source(38, web_fallback_client=DummyWebFallback())
    assert ncts == ["NCT01214278"]
    assert source.startswith("PubChem web clinicaltrials endpoint fallback")


def test_cid_to_nct_ctgov_fallback(tmp_path):
    class DummyPubChem:
        def compound_properties(self, cid: int):
            return {"IUPACName": "aspirin"}

        def synonyms(self, cid: int, max_items: int = 30):
            return ["Aspirin"]

    class DummyPugView:
        def nct_ids_for_cid(self, cid: int):
            return []

    class DummyCTGov:
        def iter_studies(self, intr=None, term=None, page_size=100, max_pages=1):
            yield {
                "protocolSection": {
                    "identificationModule": {"nctId": "NCT00000042", "briefTitle": "Aspirin trial"}
                }
            }

    cfg = CidToNctConfig(
        out_dir=str(tmp_path),
        write_jsonl=True,
        include_compound_props=False,
        use_ctgov_fallback=True,
    )
    outputs = export_cids_nct_dataset(
        [2244],
        config=cfg,
        pubchem=DummyPubChem(),
        pug_view=DummyPugView(),
        ctgov=DummyCTGov(),
    )

    rows = [json.loads(line) for line in outputs["cid_nct_links"].read_text(encoding="utf-8").splitlines() if line]
    assert rows[0]["nct_ids"] == ["NCT00000042"]
    assert rows[0]["source"].startswith("CTGov term-link fallback")


def test_cid_to_nct_source_from_pug_view_fallback(tmp_path):
    class DummyPubChem:
        def compound_properties(self, cid: int):
            return {"IUPACName": "compound"}

    class DummyPugView:
        def nct_ids_for_cid_with_source(self, cid: int):
            return ["NCT01214278"], "PubChem web fallback (compound page HTML)"

    cfg = CidToNctConfig(
        out_dir=str(tmp_path),
        write_jsonl=True,
        include_compound_props=False,
        use_ctgov_fallback=False,
    )
    outputs = export_cids_nct_dataset(
        [38],
        config=cfg,
        pubchem=DummyPubChem(),
        pug_view=DummyPugView(),
    )

    rows = [json.loads(line) for line in outputs["cid_nct_links"].read_text(encoding="utf-8").splitlines() if line]
    assert rows[0]["nct_ids"] == ["NCT01214278"]
    assert rows[0]["source"].startswith("PubChem web fallback")


def test_cid_to_nct_non_fail_fast_on_errors(tmp_path):
    class DummyPubChem:
        def compound_properties(self, cid: int):
            raise RuntimeError("no pubchem")

    class DummyPugView:
        def nct_ids_for_cid(self, cid: int):
            raise RuntimeError("no pug_view")

    cfg = CidToNctConfig(
        out_dir=str(tmp_path),
        write_jsonl=True,
        include_compound_props=True,
        use_ctgov_fallback=False,
        fail_fast=False,
    )
    outputs = export_cids_nct_dataset(
        [38, 51],
        config=cfg,
        pubchem=DummyPubChem(),
        pug_view=DummyPugView(),
    )

    link_rows = [json.loads(line) for line in outputs["cid_nct_links"].read_text(encoding="utf-8").splitlines() if line]
    assert len(link_rows) == 2
    assert link_rows[0]["nct_ids"] == []
    assert "pug_view_error" in link_rows[0].get("error", "")

    comp_rows = [json.loads(line) for line in outputs["compounds"].read_text(encoding="utf-8").splitlines() if line]
    assert len(comp_rows) == 2
    assert "compound_props_error" in comp_rows[0].get("error", "")


def test_pipeline_build_dataset(monkeypatch, tmp_path):
    class DummyPubChem:
        def compound_properties(self, cid: int):
            return {"InChIKey": "KEY", "CanonicalSMILES": "SMI", "IUPACName": "IUPAC"}

        def synonyms(self, cid: int, max_items: int = 30):
            return ["Aspirin"]

    class DummyCTGov:
        def get_study(self, nct_id: str):
            return {"protocolSection": {"identificationModule": {"nctId": nct_id}}}

    from clinical_data_analyzer.pipeline.linker import LinkEvidence, LinkResult, CompoundTrialLinker

    class DummyLinker(CompoundTrialLinker):
        def link_cid(self, cid: int):
            ev = LinkEvidence(term="Aspirin", query_mode="term", score=3, reasons=["ok"])
            return [LinkResult(cid=cid, nct_id="NCT00000001", evidence=ev)]

    pub = DummyPubChem()
    ct = DummyCTGov()

    out = build_dataset_for_cids([2244], pub, ct, linker=DummyLinker(pub, ct), config=None)
    assert "compounds" in out
    assert "links" in out
    assert "studies" in out
