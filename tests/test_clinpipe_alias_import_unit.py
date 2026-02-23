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


def test_clinpipe_alias_submodule_imports():
    from clinpipe.ctgov.client import CTGovClient as A1
    from clinpipe.pubchem.client import PubChemClient as A2
    from clinpipe.pubchem.classification_nodes import PubChemClassificationClient as A3
    from clinpipe.pubchem.clinical_trials_nodes import download_clinical_trials_cids as A4
    from clinpipe.pubchem.pug_view import PubChemPugViewClient as A5
    from clinpipe.pipeline.build_dataset import build_dataset_for_cids as A6
    from clinpipe.pipeline.linker import CompoundTrialLinker as A7
    from clinpipe.pipeline.collect_ctgov_docs_service import collect_ctgov_docs as A8
    from clinpipe.pipeline.cid_to_nct import export_cids_nct_dataset as A9
    from clinpipe.pubchem.web_fallback import PubChemWebFallbackClient as A10

    assert callable(A4)
    for obj in (A1, A2, A3, A5, A6, A7, A8, A9, A10):
        assert obj is not None


def test_clinpipe_cli_wrapper_main():
    from clinpipe.cli import main

    assert callable(main)
