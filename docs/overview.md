# Clinical Data Pipeline Documentation

This folder documents the clinical-data-pipeline project modules and their usage.

## Contents

- docs/overview.md: Project overview and architecture
- docs/ctgov.md: ClinicalTrials.gov v2 client API
- docs/pubchem.md: PubChem clients (REST, Classification, PUG-View)
- docs/pipeline.md: Linker and dataset builders
- docs/cli.md: CLI usage and examples

## Quick Architecture

The project pulls compound data from PubChem and links it to ClinicalTrials.gov studies.

High-level flow:

1. Resolve compound identifiers (CID) from PubChem
2. Fetch compound properties and synonyms
3. Link compounds to CT.gov trials via text matching OR PUG-View annotations
4. Export JSONL datasets

Key packages:

- clinical_data_analyzer.ctgov: ClinicalTrials.gov v2 API client
- clinical_data_analyzer.pubchem: PubChem REST and PUG-View clients
- clinical_data_analyzer.pipeline: Linker and dataset build logic

## Outputs (JSONL)

Typical outputs include:

- compounds.jsonl
- links.jsonl
- studies.jsonl
- cid_nct_links.jsonl

See docs/pipeline.md for the exact export formats.
