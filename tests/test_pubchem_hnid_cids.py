# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from clinical_data_analyzer.pubchem import PubChemClassificationClient

def test_hnid_to_cids_smoke():
    hnid = 1856916  # Clinical Trials
    c = PubChemClassificationClient()
    cids = c.get_cids(hnid)
    assert len(cids) > 0
    assert isinstance(cids[0], int)
