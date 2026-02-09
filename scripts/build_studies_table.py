#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Young-Mook Kang, Magic AI Research Association

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import shutil
from typing import List


def _read_csv_rows(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def _write_json(path: Path, rows: List[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False)


def _write_html(path: Path, title: str) -> None:
    html = f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f5f7fb;
      --card: #ffffff;
      --text: #1f2937;
      --muted: #6b7280;
      --line: #d1d5db;
      --accent: #0f766e;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: var(--bg); color: var(--text); }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 20px; }}
    .card {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; }}
    .head {{ padding: 16px 18px; border-bottom: 1px solid var(--line); }}
    h1 {{ margin: 0; font-size: 1.1rem; }}
    .meta {{ margin-top: 6px; font-size: 0.9rem; color: var(--muted); }}
    .controls {{ display: grid; grid-template-columns: 1fr auto; gap: 8px; padding: 12px 16px; border-bottom: 1px solid var(--line); }}
    input[type=search] {{ width: 100%; border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; }}
    .badge {{ align-self: center; color: var(--accent); font-weight: 600; font-size: 0.9rem; }}
    .table-wrap {{ overflow: auto; max-height: 70vh; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
    thead th {{ position: sticky; top: 0; background: #f9fafb; border-bottom: 1px solid var(--line); padding: 10px 8px; text-align: left; white-space: nowrap; }}
    tbody td {{ border-bottom: 1px solid #eef2f7; padding: 8px; vertical-align: top; }}
    tbody tr:hover {{ background: #f8fbff; }}
    a {{ color: #0369a1; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
  </style>
</head>
<body>
  <div class=\"wrap\">
    <div class=\"card\">
      <div class=\"head\">
        <h1>{title}</h1>
        <div class=\"meta\">Generated from <code>clinical_compound_trials.csv</code></div>
      </div>
      <div class=\"controls\">
        <input id=\"q\" type=\"search\" placeholder=\"Search by CID, NCT ID, title, phase, condition...\" />
        <div id=\"count\" class=\"badge\">0 rows</div>
      </div>
      <div class=\"table-wrap\">
        <table>
          <thead>
            <tr>
              <th>CID</th>
              <th>NCT ID</th>
              <th>Phase</th>
              <th>Status</th>
              <th>Title</th>
              <th>Conditions</th>
              <th>Interventions</th>
              <th>Targets</th>
              <th>Last Update</th>
              <th>Source</th>
            </tr>
          </thead>
          <tbody id=\"tbody\"></tbody>
        </table>
      </div>
    </div>
  </div>

  <script>
    const escapeHtml = (s) => String(s ?? '').replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');

    function renderRows(rows) {{
      const tbody = document.getElementById('tbody');
      const count = document.getElementById('count');
      tbody.innerHTML = rows.map(r => `
        <tr>
          <td>${{escapeHtml(r.cid)}}</td>
          <td>${{escapeHtml(r.nct_id)}}</td>
          <td>${{escapeHtml(r.phase)}}</td>
          <td>${{escapeHtml(r.overall_status)}}</td>
          <td>${{escapeHtml(r.title)}}</td>
          <td>${{escapeHtml(r.conditions)}}</td>
          <td>${{escapeHtml(r.interventions)}}</td>
          <td>${{escapeHtml(r.targets)}}</td>
          <td>${{escapeHtml(r.last_update_date)}}</td>
          <td><a href="${{escapeHtml(r.source_url)}}" target="_blank" rel="noreferrer">link</a></td>
        </tr>
      `).join('');
      count.textContent = `${{rows.length}} rows`;
    }}

    async function main() {{
      const rows = await fetch('./studies.json').then(r => r.json());
      const q = document.getElementById('q');
      const hay = rows.map(r => [
        r.cid, r.nct_id, r.phase, r.overall_status, r.title,
        r.conditions, r.interventions, r.targets, r.last_update_date
      ].join(' ').toLowerCase());

      function apply() {{
        const k = q.value.trim().toLowerCase();
        if (!k) {{
          renderRows(rows);
          return;
        }}
        const filtered = rows.filter((_, i) => hay[i].includes(k));
        renderRows(filtered);
      }}

      q.addEventListener('input', apply);
      renderRows(rows);
    }}

    main();
  </script>
</body>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(prog="build-studies-table")
    p.add_argument(
        "--dataset-csv",
        default="out/ctgov_docs_run1/final/clinical_compound_trials.csv",
        help="Input normalized CSV (from scripts/build_clinical_dataset.py)",
    )
    p.add_argument("--out-dir", default="docs/data", help="Output directory for page assets")
    p.add_argument("--title", default="Clinical Compound Trials Table")
    args = p.parse_args()

    dataset_csv = Path(args.dataset_csv)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not dataset_csv.exists():
      raise FileNotFoundError(f"dataset csv not found: {dataset_csv}")

    rows = _read_csv_rows(dataset_csv)

    out_csv = out_dir / "studies.csv"
    out_json = out_dir / "studies.json"
    out_html = out_dir / "index.html"

    shutil.copy2(dataset_csv, out_csv)
    _write_json(out_json, rows)
    _write_html(out_html, args.title)

    print(f"rows: {len(rows)}")
    print(f"csv: {out_csv}")
    print(f"json: {out_json}")
    print(f"html: {out_html}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
