# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
from clinical_data_analyzer.pubchem.classification_nodes import PubChemClassificationClient


# Provided HNIDs (hid=72)
HNID_CLINICAL_TRIALS = 1856916
HNID_CLINICALTRIALS_GOV = 3647573
HNID_EU_CLINICAL_TRIALS_REGISTER = 3647574
HNID_JAPAN_NIPH_CLINICAL_TRIALS = 3647575


@dataclass(frozen=True)
class ClinicalTrialsNodeSet:
    clinical_trials: int = HNID_CLINICAL_TRIALS
    clinicaltrials_gov: int = HNID_CLINICALTRIALS_GOV
    eu_register: int = HNID_EU_CLINICAL_TRIALS_REGISTER
    japan_niph: int = HNID_JAPAN_NIPH_CLINICAL_TRIALS


def save_cids_txt(cids: List[int], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        for cid in cids:
            f.write(f"{cid}\n")
    return p


def download_cids_for_hnid(hnid: int, *, out_path: str | Path | None = None) -> List[int]:
    client = PubChemClassificationClient()
    cids = client.get_cids(hnid, fmt="TXT")
    if out_path:
        save_cids_txt(cids, out_path)
    return cids


def download_clinical_trials_cids(
    *,
    out_dir: str | Path = "out_hnid",
    include_sources: bool = True,
) -> Dict[str, List[int]]:
    """
    Download CID lists for clinical-trial related nodes and optionally save them.

    Returns a dict:
      - "clinical_trials"
      - "clinicaltrials_gov"
      - "eu_register"
      - "japan_niph"
    """
    nodes = ClinicalTrialsNodeSet()
    client = PubChemClassificationClient()
    out_dir = Path(out_dir)

    results: Dict[str, List[int]] = {}

    mapping = {
        "clinical_trials": nodes.clinical_trials,
        "clinicaltrials_gov": nodes.clinicaltrials_gov,
    }
    if include_sources:
        mapping.update(
            {
                "eu_register": nodes.eu_register,
                "japan_niph": nodes.japan_niph,
            }
        )

    for name, hnid in mapping.items():
        cids = client.get_cids(hnid, fmt="TXT")
        results[name] = cids
        save_cids_txt(cids, out_dir / f"{name}_cids.txt")

    return results
