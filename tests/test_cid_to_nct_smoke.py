# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from clinical_data_analyzer.pipeline.cid_to_nct import cid_to_nct_ids

def test_cid_to_nct_smoke():
    # 값이 0일 수도 있으니 "리스트 반환"만 보장
    ncts = cid_to_nct_ids(2244)
    assert isinstance(ncts, list)
