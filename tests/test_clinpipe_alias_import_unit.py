from __future__ import annotations


def test_clinpipe_alias_top_level_exports():
    from clinical_data_analyzer import CTGovClient as A_CTGovClient
    from clinical_data_analyzer import PubChemClient as A_PubChemClient
    from clinpipe import CTGovClient as B_CTGovClient
    from clinpipe import PubChemClient as B_PubChemClient

    assert B_CTGovClient is A_CTGovClient
    assert B_PubChemClient is A_PubChemClient


def test_clinpipe_alias_subpackages_exports():
    from clinical_data_analyzer.ctgov import CTGovClient as A_CTGovClient
    from clinical_data_analyzer.pubchem import PubChemClient as A_PubChemClient
    from clinical_data_analyzer.pipeline import build_dataset_for_cids as A_build

    from clinpipe.ctgov import CTGovClient as B_CTGovClient
    from clinpipe.pubchem import PubChemClient as B_PubChemClient
    from clinpipe.pipeline import build_dataset_for_cids as B_build

    assert B_CTGovClient is A_CTGovClient
    assert B_PubChemClient is A_PubChemClient
    assert B_build is A_build


def test_clinpipe_cli_wrapper_main():
    from clinpipe.cli import main

    assert callable(main)
