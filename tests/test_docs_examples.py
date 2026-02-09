# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

from typing import Any, Dict, List

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
from clinical_data_analyzer.pipeline.build_dataset import build_dataset_for_cids


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
