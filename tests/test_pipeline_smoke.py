from clinical_data_analyzer.ctgov.client import CTGovClient
from clinical_data_analyzer.pubchem.client import PubChemClient
from clinical_data_analyzer.pipeline.build_dataset import DatasetBuildConfig, build_dataset_for_cids


def test_pipeline_smoke(tmp_path):
    pub = PubChemClient()
    ct = CTGovClient()
    cids = pub.cids_by_name("aspirin")[:1]

    cfg = DatasetBuildConfig(out_dir=str(tmp_path), write_jsonl=True, max_synonyms_in_compound=5)
    out = build_dataset_for_cids(cids, pub, ct, config=cfg)

    assert (tmp_path / "compounds.jsonl").exists()
    assert (tmp_path / "links.jsonl").exists()
    assert (tmp_path / "studies.jsonl").exists()
    assert len(out) == 3
