# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional
import json

from clinical_data_analyzer.ctgov import CTGovClient
from clinical_data_analyzer.pipeline.linker import CompoundTrialLinker, LinkerConfig
from clinical_data_analyzer.pubchem import PubChemClient, PubChemPugViewClient


@dataclass(frozen=True)
class CidToNctConfig:
    out_dir: str = "out_nct"
    write_jsonl: bool = True
    include_compound_props: bool = True  # InChIKey/SMILES/IUPACName 포함 여부
    use_ctgov_fallback: bool = False
    fallback_max_synonyms: int = 12
    fallback_ctgov_page_size: int = 50
    fallback_ctgov_max_pages_per_term: int = 1
    fallback_min_score: int = 2
    fallback_max_links_per_cid: int = 30
    fail_fast: bool = False


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
    ctgov: Optional[CTGovClient] = None,
    progress_every: int = 0,
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
    ctgov = ctgov or CTGovClient()
    linker: Optional[CompoundTrialLinker] = None
    if cfg.use_ctgov_fallback:
        linker = CompoundTrialLinker(
            pubchem,
            ctgov,
            config=LinkerConfig(
                max_synonyms=cfg.fallback_max_synonyms,
                ctgov_page_size=cfg.fallback_ctgov_page_size,
                ctgov_max_pages_per_term=cfg.fallback_ctgov_max_pages_per_term,
                min_score=cfg.fallback_min_score,
                max_links_per_cid=cfg.fallback_max_links_per_cid,
            ),
        )

    links_rows: List[dict] = []
    compounds_rows: List[dict] = []

    total = len(cids)
    for idx, cid in enumerate(cids, start=1):
        rec = map_cid_to_nct_record(
            cid,
            config=cfg,
            pubchem=pubchem,
            pug_view=pug_view,
            ctgov=ctgov,
        )
        links_rows.append(rec["link"])
        if cfg.include_compound_props and "compound" in rec:
            compounds_rows.append(rec["compound"])

        if progress_every > 0 and (idx % progress_every == 0 or idx == total):
            print(f"[cid->nct] processed {idx}/{total} CIDs")

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


def map_cid_to_nct_record(
    cid: int,
    *,
    config: Optional[CidToNctConfig] = None,
    pubchem: Optional[PubChemClient] = None,
    pug_view: Optional[PubChemPugViewClient] = None,
    ctgov: Optional[CTGovClient] = None,
) -> Dict[str, dict]:
    """
    Build a single CID mapping record and optional compound properties record.

    Returns:
      {
        "link": {...},
        "compound": {...}   # only when include_compound_props=True
      }
    """
    cfg = config or CidToNctConfig()
    pubchem = pubchem or PubChemClient()
    pug_view = pug_view or PubChemPugViewClient()
    ctgov = ctgov or CTGovClient()

    linker: Optional[CompoundTrialLinker] = None
    if cfg.use_ctgov_fallback:
        linker = CompoundTrialLinker(
            pubchem,
            ctgov,
            config=LinkerConfig(
                max_synonyms=cfg.fallback_max_synonyms,
                ctgov_page_size=cfg.fallback_ctgov_page_size,
                ctgov_max_pages_per_term=cfg.fallback_ctgov_max_pages_per_term,
                min_score=cfg.fallback_min_score,
                max_links_per_cid=cfg.fallback_max_links_per_cid,
            ),
        )

    source = "PubChem PUG-View annotations"
    nct_ids: List[str] = []
    link_error: Optional[str] = None

    try:
        if hasattr(pug_view, "nct_ids_for_cid_with_source"):
            nct_ids, source = pug_view.nct_ids_for_cid_with_source(cid)
        else:
            nct_ids = pug_view.nct_ids_for_cid(cid)
    except Exception as e:
        link_error = f"pug_view_error:{type(e).__name__}:{e}"
        if cfg.fail_fast:
            raise

    if not nct_ids and linker is not None:
        try:
            link_results = linker.link_cid(cid)
            nct_ids = sorted({lr.nct_id for lr in link_results})
            if nct_ids:
                source = "CTGov term-link fallback (no PUG-View NCT IDs)"
        except Exception as e:
            fallback_error = f"ctgov_fallback_error:{type(e).__name__}:{e}"
            link_error = f"{link_error}|{fallback_error}" if link_error else fallback_error
            if cfg.fail_fast:
                raise

    link_row: Dict[str, object] = {
        "cid": cid,
        "nct_ids": nct_ids,
        "n_nct": len(nct_ids),
        "source": source,
    }
    if link_error:
        link_row["error"] = link_error

    out: Dict[str, dict] = {"link": link_row}  # type: ignore[assignment]

    if cfg.include_compound_props:
        props: Dict[str, Optional[str]] = {}
        comp_error: Optional[str] = None
        try:
            props = pubchem.compound_properties(cid)
        except Exception as e:
            comp_error = f"compound_props_error:{type(e).__name__}:{e}"
            if cfg.fail_fast:
                raise
        comp_row = {
            "cid": cid,
            "inchikey": props.get("InChIKey"),
            "canonical_smiles": props.get("CanonicalSMILES"),
            "iupac_name": props.get("IUPACName"),
            **({"error": comp_error} if comp_error else {}),
        }
        out["compound"] = comp_row

    return out
