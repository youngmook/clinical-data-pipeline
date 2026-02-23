# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from clinical_data_analyzer.pubchem.client import PubChemClient


def test_pubchem_basic():
    p = PubChemClient()
    cids = p.cids_by_name("aspirin")
    assert len(cids) > 0
    props = p.compound_properties(cids[0])
    assert "InChIKey" in props
