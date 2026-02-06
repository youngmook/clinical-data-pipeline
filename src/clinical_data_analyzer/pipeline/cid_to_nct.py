# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
import json

from clinical_data_analyzer.pubchem import PubChemClient, PubChemPugViewClient


@dataclass(frozen=True)
class CidToNctConfig:
    out_dir: str = "out_nct"
    write_jsonl: bool = True
    include_compound_props: bool = True  # InChIKey/SMILES/IUPACName 포함 여부


def _ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def cid_to_nct_ids(
    cid: int,
    *,
    pug_view: Optional[PubChemPugViewClient] = None,
) -> List[str]:
    """
    Return ClinicalTrials.gov NCT IDs for a single CID using PubChem PUG-View annotations.
    """
    pug_view = pug_view or PubChemPugViewClient()
    return pug_view.nct_ids_for_cid(cid)


def cids_to_nct_ids(
    cids: List[int],
    *,
    pubchem: Optional[PubChemClient] = None,
    pug_view: Optional[PubChemPugViewClient] = None,
) -> Dict[int, List[str]]:
    """
    Return mapping: CID -> [NCT IDs]
    """
    pubchem = pubchem or PubChemClient()
    pug_view = pug_view or PubChemPugViewClient()

    mapping: Dict[int, List[str]] = {}
    for cid in cids:
        mapping[cid] = pug_view.nct_ids_for_cid(cid)
    return mapping


def export_cids_nct_dataset(
    cids: List[int],
    *,
    config: Optional[CidToNctConfig] = None,
    pubchem: Optional[PubChemClient] = None,
    pug_view: Optional[PubChemPugViewClient] = None,
) -> Dict[str, Path]:
    """
    Export JSONL files:
      - cid_nct_links.jsonl: CID -> NCT IDs
      - compounds.jsonl (optional): CID -> basic compound properties
    """
    cfg = config or CidToNctConfig()
    out_dir = Path(cfg.out_dir)
    _ensure_dir(out_dir)

    pubchem = pubchem or PubChemClient()
    pug_view = pug_view or PubChemPugViewClient()

    links_rows: List[dict] = []
    compounds_rows: List[dict] = []

    for cid in cids:
        nct_ids = pug_view.nct_ids_for_cid(cid)

        links_rows.append(
            {
                "cid": cid,
                "nct_ids": nct_ids,
                "n_nct": len(nct_ids),
                "source": "PubChem PUG-View annotations",
            }
        )

        if cfg.include_compound_props:
            props = pubchem.compound_properties(cid)
            compounds_rows.append(
                {
                    "cid": cid,
                    "inchikey": props.get("InChIKey"),
                    "canonical_smiles": props.get("CanonicalSMILES"),
                    "iupac_name": props.get("IUPACName"),
                }
            )

    outputs: Dict[str, Path] = {}
    if cfg.write_jsonl:
        p_links = out_dir / "cid_nct_links.jsonl"
        _write_jsonl(p_links, links_rows)
        outputs["cid_nct_links"] = p_links

        if cfg.include_compound_props:
            p_comp = out_dir / "compounds.jsonl"
            _write_jsonl(p_comp, compounds_rows)
            outputs["compounds"] = p_comp

    return outputs
