#!/usr/bin/env python3
"""
generate_ocr_dashboard.py — Render an interactive HTML dashboard
from the ocr_merge_summary.json report.

Usage:
  python utils/generate_ocr_dashboard.py
"""

import json
from pathlib import Path
from datetime import datetime

REPORT_PATH = Path("rag_staging/reports/ocr_merge_summary.json")
DASHBOARD_PATH = Path("rag_staging/reports/index.html")


def load_report() -> dict:
    if REPORT_PATH.exists():
        try:
            return json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"⚠️  Could not parse report: {e}")
            return {}
    print(f"⚠️  Report not found: {REPORT_PATH}")
    return {}


def render_dashboard(data: dict) -> str:
    rows = []
    for key, v in sorted(data.items(), key=lambda kv: kv[1]["timestamp"], reverse=True):
        pages = v.get("pages", 0)
        empties = v.get("empty_pages", 0)
        chars = v.get("characters", 0)
        html_path = v.get("html_output", "")
        md_path = v.get("markdown_output", "")
        ts = v.get("timestamp", "—")

        # Derived metrics
        pct_complete = 100 * (1 - (empties / pages)) if pages else 0
        density = f"{chars // max(pages,1):,}"
        bar_color = "#4caf50" if pct_complete > 95 else "#ffa726" if pct_complete > 80 else "#ef5350"

        rows.append(
            f"<tr>"
            f"<td>{key}</td>"
            f"<td>{pages}</td>"
            f"<td>{empties}</td>"
            f"<td><div class='bar'><div class='fill' style='width:{pct_complete:.1f}%;background:{bar_color}'></div></div>"
            f"{pct_complete:.1f}%</td>"
            f"<td>{density}</td>"
            f"<td>{ts}</td>"
            f"<td>"
            + (f"<a href='../../{html_path}' target='_blank'>HTML</a>" if html_path else "")
            + (" | " if html_path and md_path else "")
            + (f"<a href='../../{md_path}' target='_blank'>MD</a>" if md_path else "")
            + "</td></tr>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>OlmOCR QA Dashboard</title>
<style>
body {{ font-family:system-ui, sans-serif; margin:2em; background:#f8f9fa; }}
h1 {{ margin-bottom:0.2em; }}
table {{ width:100%; border-collapse:collapse; background:white; box-shadow:0 2px 6px rgba(0,0,0,0.1); }}
th,td {{ padding:10px 12px; border-bottom:1px solid #ddd; text-align:left; font-size:14px; }}
th {{ background:#e9ecef; cursor:pointer; }}
tr:hover {{ background:#f1f3f5; }}
.bar {{ background:#ddd; width:120px; height:10px; border-radius:5px; overflow:hidden; display:inline-block; vertical-align:middle; margin-right:5px; }}
.fill {{ height:10px; }}
tfoot td {{ font-weight:bold; }}
</style>
<script>
function sortTable(n) {{
  var table=document.getElementById("ocrTable");
  var switching=true, dir="desc", switchcount=0;
  while(switching){{
    switching=false; var rows=table.rows;
    for(var i=1;i<rows.length-1;i++){{
      var shouldSwitch=false;
      var x=rows[i].getElementsByTagName("TD")[n];
      var y=rows[i+1].getElementsByTagName("TD")[n];
      if(dir=="asc" ? x.innerText.toLowerCase()>y.innerText.toLowerCase()
                    : x.innerText.toLowerCase()<y.innerText.toLowerCase()){{
        shouldSwitch=true; break;
      }}
    }}
    if(shouldSwitch){{ rows[i].parentNode.insertBefore(rows[i+1], rows[i]); switching=true; switchcount++; }}
    else if(switchcount==0 && dir=="asc"){{ dir="desc"; switching=true; }}
  }}
}}
</script>
</head>
<body>
<h1>🧾 OlmOCR QA Dashboard</h1>
<p>Last updated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

<table id="ocrTable">
<thead>
<tr>
  <th onclick="sortTable(0)">Document</th>
  <th onclick="sortTable(1)">Pages</th>
  <th onclick="sortTable(2)">Empty</th>
  <th onclick="sortTable(3)">Completeness</th>
  <th onclick="sortTable(4)">Chars/Page</th>
  <th onclick="sortTable(5)">Timestamp</th>
  <th>Links</th>
</tr>
</thead>
<tbody>
{''.join(rows) if rows else "<tr><td colspan='7'>No data available</td></tr>"}
</tbody>
</table>
</body></html>"""


def main():
    data = load_report()
    html = render_dashboard(data)
    DASHBOARD_PATH.write_text(html, encoding="utf-8")
    print(f"✅ Dashboard generated: {DASHBOARD_PATH}")


if __name__ == "__main__":
    main()
