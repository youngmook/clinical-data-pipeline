# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
import json

from clinical_data_analyzer.pipeline.linker import CompoundTrialLinker, LinkResult


@dataclass(frozen=True)
class DatasetBuildConfig:
    out_dir: str = "out"
    write_jsonl: bool = True
    max_synonyms_in_compound: int = 30


def _safe_mkdir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def build_dataset_for_cids(
    cids: List[int],
    pubchem_client,
    ctgov_client,
    *,
    linker: Optional[CompoundTrialLinker] = None,
    config: Optional[DatasetBuildConfig] = None,
) -> Dict[str, Path]:
    cfg = config or DatasetBuildConfig()
    out_dir = Path(cfg.out_dir)
    _safe_mkdir(out_dir)

    linker = linker or CompoundTrialLinker(pubchem_client, ctgov_client)

    compounds: List[Dict[str, Any]] = []
    studies: Dict[str, Dict[str, Any]] = {}
    links: List[Dict[str, Any]] = []

    for cid in cids:
        props = pubchem_client.compound_properties(cid)
        syns = pubchem_client.synonyms(cid, max_items=cfg.max_synonyms_in_compound)

        compounds.append(
            {
                "cid": cid,
                "inchikey": props.get("InChIKey"),
                "canonical_smiles": props.get("CanonicalSMILES"),
                "iupac_name": props.get("IUPACName"),
                "synonyms": syns,
            }
        )

        link_results: List[LinkResult] = linker.link_cid(cid)
        for lr in link_results:
            links.append(
                {
                    "cid": lr.cid,
                    "nct_id": lr.nct_id,
                    "match_term": lr.evidence.term,
                    "query_mode": lr.evidence.query_mode,
                    "score": lr.evidence.score,
                    "reasons": lr.evidence.reasons,
                }
            )

            if lr.nct_id not in studies:
                studies[lr.nct_id] = ctgov_client.get_study(lr.nct_id)

    outputs: Dict[str, Path] = {}
    if cfg.write_jsonl:
        p_comp = out_dir / "compounds.jsonl"
        p_links = out_dir / "links.jsonl"
        p_stud = out_dir / "studies.jsonl"
        _write_jsonl(p_comp, compounds)
        _write_jsonl(p_links, links)
        _write_jsonl(p_stud, studies.values())
        outputs.update({"compounds": p_comp, "links": p_links, "studies": p_stud})

    return outputs
