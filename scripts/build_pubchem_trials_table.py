#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 Magic AI Research Association

from __future__ import annotations

import argparse
from pathlib import Path


def _html_vanilla(title: str, json_filename: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title} (Vanilla)</title>
  <style>
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: #f6f8fc; color: #1f2937; }}
    .wrap {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
    .card {{ background: #fff; border: 1px solid #d1d5db; border-radius: 12px; overflow: hidden; }}
    .head {{ padding: 16px 18px; border-bottom: 1px solid #d1d5db; }}
    h1 {{ margin: 0; font-size: 1.1rem; }}
    .meta {{ margin-top: 6px; font-size: 0.9rem; color: #6b7280; }}
    .controls {{ display: grid; grid-template-columns: 1fr auto auto; gap: 8px; padding: 12px 16px; border-bottom: 1px solid #d1d5db; }}
    input[type=search], select {{ border: 1px solid #d1d5db; border-radius: 8px; padding: 8px 10px; background: #fff; }}
    .badge {{ align-self: center; color: #0f766e; font-weight: 600; font-size: 0.9rem; }}
    .table-wrap {{ overflow: auto; max-height: 72vh; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
    thead th {{ position: sticky; top: 0; background: #f9fafb; border-bottom: 1px solid #d1d5db; padding: 10px 8px; text-align: left; white-space: nowrap; }}
    tbody td {{ border-bottom: 1px solid #eef2f7; padding: 8px; vertical-align: top; }}
    tbody tr:hover {{ background: #f8fbff; }}
    a {{ color: #0369a1; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .img-cell img {{ width: 88px; height: 88px; object-fit: contain; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <div class="head">
        <h1>{title} (Vanilla)</h1>
        <div class="meta">Generated from <code>{json_filename}</code></div>
      </div>
      <div class="controls">
        <input id="q" type="search" placeholder="Search by CID, ID, title, phase, status, collection..." />
        <select id="pageSize">
          <option value="25">25 / page</option>
          <option value="50" selected>50 / page</option>
          <option value="100">100 / page</option>
        </select>
        <div id="count" class="badge">0 rows</div>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>2D</th><th>CID</th><th>Collection</th><th>ID</th><th>Date</th><th>Phase</th><th>Status</th><th>Title</th><th>SMILES</th>
            </tr>
          </thead>
          <tbody id="tbody"></tbody>
        </table>
      </div>
    </div>
  </div>
  <script>
    const DATA_JSON = "./{json_filename}";
    const esc = (s) => String(s ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
    const attr = (s) => String(s ?? "").replaceAll('"', "&quot;");
    async function main() {{
      const rows = await fetch(DATA_JSON).then(r => r.json());
      const tbody = document.getElementById("tbody");
      const q = document.getElementById("q");
      const pageSizeEl = document.getElementById("pageSize");
      const count = document.getElementById("count");
      let filtered = rows.slice();
      let page = 1;
      let pageSize = Number(pageSizeEl.value || 50);
      const hay = rows.map(r => [r.cid, r.collection, r.id, r.title, r.phase, r.status, r.date, r.smiles].join(" ").toLowerCase());
      function render() {{
        const start = (page - 1) * pageSize;
        const view = filtered.slice(start, start + pageSize);
        tbody.innerHTML = view.map(r => {{
          const idCell = r.id_url ? `<a href="${{attr(r.id_url)}}" target="_blank" rel="noreferrer">${{esc(r.id)}}</a>` : esc(r.id);
          const img = r.image_base64 ? `<img alt="cid-${{esc(r.cid)}}" src="${{attr(r.image_base64)}}" loading="lazy" />` : "";
          return `<tr><td class="img-cell">${{img}}</td><td>${{esc(r.cid)}}</td><td>${{esc(r.collection)}}</td><td>${{idCell}}</td><td>${{esc(r.date)}}</td><td>${{esc(r.phase)}}</td><td>${{esc(r.status)}}</td><td>${{esc(r.title)}}</td><td>${{esc(r.smiles)}}</td></tr>`;
        }}).join("");
        count.textContent = `${{filtered.length}} rows`;
      }}
      q.addEventListener("input", () => {{
        const k = q.value.trim().toLowerCase();
        filtered = k ? rows.filter((_, i) => hay[i].includes(k)) : rows.slice();
        page = 1;
        render();
      }});
      pageSizeEl.addEventListener("change", () => {{
        pageSize = Number(pageSizeEl.value || 50);
        page = 1;
        render();
      }});
      render();
    }}
    main();
  </script>
</body>
</html>
"""


def _html_datatables(title: str, json_filename: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title} (DataTables)</title>
  <link rel="stylesheet" href="https://cdn.datatables.net/1.13.8/css/jquery.dataTables.min.css" />
  <style>
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: #f6f8fc; color: #1f2937; }}
    .wrap {{ max-width: 1500px; margin: 0 auto; padding: 20px; }}
    .card {{ background: #fff; border: 1px solid #d1d5db; border-radius: 12px; padding: 16px; }}
    h1 {{ margin: 0 0 6px 0; font-size: 1.1rem; }}
    .meta {{ margin: 0 0 12px 0; color: #6b7280; font-size: 0.9rem; }}
    td.img-cell img {{ width: 72px; height: 72px; object-fit: contain; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }}
    table.dataTable td {{ vertical-align: top; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>{title} (DataTables)</h1>
      <p class="meta">Generated from <code>{json_filename}</code></p>
      <table id="tbl" class="display" style="width:100%">
        <thead>
          <tr>
            <th>2D</th><th>CID</th><th>Collection</th><th>ID</th><th>Date</th><th>Phase</th><th>Status</th><th>Title</th><th>SMILES</th>
          </tr>
        </thead>
      </table>
    </div>
  </div>
  <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
  <script src="https://cdn.datatables.net/1.13.8/js/jquery.dataTables.min.js"></script>
  <script>
    const DATA_JSON = "./{json_filename}";
    const esc = (s) => String(s ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
    const attr = (s) => String(s ?? "").replaceAll('"', "&quot;");
    fetch(DATA_JSON)
      .then(r => r.json())
      .then(rows => {{
        $("#tbl").DataTable({{
          data: rows,
          pageLength: 25,
          columns: [
            {{
              data: "image_base64",
              className: "img-cell",
              render: (v, type, row) => v ? `<img alt="cid-${{esc(row.cid)}}" src="${{attr(v)}}" loading="lazy" />` : ""
            }},
            {{ data: "cid" }},
            {{ data: "collection" }},
            {{
              data: "id",
              render: (v, type, row) => row.id_url ? `<a href="${{attr(row.id_url)}}" target="_blank" rel="noreferrer">${{esc(v)}}</a>` : esc(v)
            }},
            {{ data: "date" }},
            {{ data: "phase" }},
            {{ data: "status" }},
            {{ data: "title" }},
            {{ data: "smiles" }}
          ],
          order: [[1, "asc"]],
        }});
      }})
      .catch(err => {{
        document.body.insertAdjacentHTML("beforeend", `<pre>Failed to load data: ${{esc(err?.message || String(err))}}</pre>`);
      }});
  </script>
</body>
</html>
"""


def _html_tabulator(title: str, json_filename: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>{title} (Tabulator)</title>
  <link href="https://unpkg.com/tabulator-tables@6.2.5/dist/css/tabulator.min.css" rel="stylesheet">
  <style>
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif; background: #f6f8fc; color: #1f2937; }}
    .wrap {{ max-width: 1500px; margin: 0 auto; padding: 20px; }}
    .card {{ background: #fff; border: 1px solid #d1d5db; border-radius: 12px; padding: 16px; }}
    h1 {{ margin: 0 0 6px 0; font-size: 1.1rem; }}
    .meta {{ margin: 0 0 12px 0; color: #6b7280; font-size: 0.9rem; }}
    #tbl {{ border: 1px solid #d1d5db; border-radius: 8px; }}
    .img-cell img {{ width: 72px; height: 72px; object-fit: contain; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1>{title} (Tabulator)</h1>
      <p class="meta">Generated from <code>{json_filename}</code></p>
      <div id="tbl"></div>
    </div>
  </div>
  <script src="https://unpkg.com/tabulator-tables@6.2.5/dist/js/tabulator.min.js"></script>
  <script>
    const DATA_JSON = "./{json_filename}";
    const esc = (s) => String(s ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
    const attr = (s) => String(s ?? "").replaceAll('"', "&quot;");
    fetch(DATA_JSON)
      .then(r => r.json())
      .then(rows => {{
        new Tabulator("#tbl", {{
          data: rows,
          layout: "fitDataStretch",
          height: "72vh",
          pagination: true,
          paginationSize: 25,
          initialSort: [{{column:"cid", dir:"asc"}}],
          columns: [
            {{
              title: "2D", field: "image_base64", headerSort: false,
              formatter: (cell) => {{
                const v = cell.getValue();
                return v ? `<div class="img-cell"><img alt="cid-image" src="${{attr(v)}}" loading="lazy" /></div>` : "";
              }}
            }},
            {{title: "CID", field: "cid"}},
            {{title: "Collection", field: "collection"}},
            {{
              title: "ID", field: "id",
              formatter: (cell) => {{
                const row = cell.getData();
                const v = cell.getValue();
                return row.id_url ? `<a href="${{attr(row.id_url)}}" target="_blank" rel="noreferrer">${{esc(v)}}</a>` : esc(v);
              }}
            }},
            {{title: "Date", field: "date"}},
            {{title: "Phase", field: "phase"}},
            {{title: "Status", field: "status"}},
            {{title: "Title", field: "title", width: 420}},
            {{title: "SMILES", field: "smiles", width: 280}},
          ],
        }});
      }})
      .catch(err => {{
        document.body.insertAdjacentHTML("beforeend", `<pre>Failed to load data: ${{esc(err?.message || String(err))}}</pre>`);
      }});
  </script>
</body>
</html>
"""


def _write(path: Path, html: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(prog="build-pubchem-trials-table")
    p.add_argument("--in-json", default="out/pubchem_trials_dataset/trials.json", help="Input trials JSON array")
    p.add_argument("--out-html", default=None, help="Output HTML path for single mode")
    p.add_argument("--title", default="PubChem Clinical Trials Table", help="HTML title")
    p.add_argument(
        "--mode",
        default="vanilla",
        choices=("vanilla", "datatables", "tabulator"),
        help="Single output mode",
    )
    p.add_argument("--all", action="store_true", help="Write all variants: vanilla, datatables, tabulator")
    args = p.parse_args()

    in_json = Path(args.in_json)
    if not in_json.exists():
        raise FileNotFoundError(f"Input file not found: {in_json}")

    parent = in_json.parent
    stem = "index"
    generated: list[Path] = []

    if args.all:
        targets = [
            (parent / f"{stem}.vanilla.html", _html_vanilla(args.title, in_json.name)),
            (parent / f"{stem}.datatables.html", _html_datatables(args.title, in_json.name)),
            (parent / f"{stem}.tabulator.html", _html_tabulator(args.title, in_json.name)),
        ]
        for out, html in targets:
            _write(out, html)
            generated.append(out)
    else:
        out_html = Path(args.out_html) if args.out_html else parent / "index.html"
        if args.mode == "vanilla":
            html = _html_vanilla(args.title, in_json.name)
        elif args.mode == "datatables":
            html = _html_datatables(args.title, in_json.name)
        else:
            html = _html_tabulator(args.title, in_json.name)
        _write(out_html, html)
        generated.append(out_html)

    print(f"json: {in_json}")
    for pth in generated:
        print(f"html: {pth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

