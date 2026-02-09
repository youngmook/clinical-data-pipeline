# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from clinical_data_analyzer.ctgov import CTGovClient

def test_ctgov_search_basic():
    c = CTGovClient()
    payload = c.search_studies(term="aspirin", page_size=1)
    assert "studies" in payload
