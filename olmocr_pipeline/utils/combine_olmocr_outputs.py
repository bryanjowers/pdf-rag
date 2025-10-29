#!/usr/bin/env python3
"""
combine_olmocr_outputs.py — Merge OlmOCR per-page JSONL outputs
into layout-preserving HTML/Markdown for Docling + generate QA report.

Usage:
  python utils/combine_olmocr_outputs.py rag_staging/jsonl/*.jsonl --html --md

Example:
  python utils/combine_olmocr_outputs.py rag_staging/jsonl/*.jsonl --html --md
"""

import argparse
import json
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------
GCS_MOUNT_BASE = Path("/mnt/gcs/legal-ocr-results")
RAG_STAGING_DIR = GCS_MOUNT_BASE / "rag_staging"

OUT_DIR_HTML = RAG_STAGING_DIR / "html"
OUT_DIR_MD = RAG_STAGING_DIR / "markdown_merged"
REPORT_PATH = RAG_STAGING_DIR / "reports" / "ocr_merge_summary.json"

for p in [OUT_DIR_HTML, OUT_DIR_MD, REPORT_PATH.parent]:
    p.mkdir(parents=True, exist_ok=True)


def merge_jsonl_to_html(jsonl_path: Path) -> tuple[str, int, int, int]:
    """Merge JSONL file to layout-preserving HTML. Return (html, total_pages, empty_pages, total_chars)."""
    pages, empty_count, char_count = [], 0, 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Support both old format (per-page) and new format (per-document)
            text = record.get("response", record.get("text", "")).strip()
            page_num = record.get("page_index", line_num)

            if not text:
                empty_count += 1
                continue

            char_count += len(text)
            pages.append(
                f'<section id="page-{page_num}" class="page">\n'
                f'  <h2>Page {page_num}</h2>\n'
                f'  <div class="page-content">\n{text}\n  </div>\n'
                f'</section>'
            )

    html = (
        "<!DOCTYPE html>\n<html lang='en'>\n<head>\n"
        f"<meta charset='utf-8'/>\n<title>{jsonl_path.stem}</title>\n"
        "<style>body{font-family:serif;line-height:1.5;margin:2em;}"
        "section.page{margin-bottom:3em;page-break-after:always;}"
        "h2{border-bottom:1px solid #ccc;padding-bottom:4px;}"
        "table{border-collapse:collapse;width:100%;margin-top:1em;}"
        "td,th{border:1px solid #999;padding:4px;vertical-align:top;}"
        "</style>\n</head>\n<body>\n"
        f"<h1>{jsonl_path.stem}</h1>\n"
        f"{''.join(pages)}\n</body>\n</html>"
    )
    return html, len(pages), empty_count, char_count


def merge_jsonl_to_markdown(jsonl_path: Path) -> tuple[str, int, int, int]:
    """Merge JSONL file to Markdown (preserving page headings)."""
    pages, empty_count, char_count = [], 0, 0
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Support both old format (per-page) and new format (per-document)
            text = record.get("response", record.get("text", "")).strip()
            page_num = record.get("page_index", line_num)

            if not text:
                empty_count += 1
                continue
            char_count += len(text)
            pages.append(f"## Page {page_num}\n\n{text}")
    md = "\n\n---\n\n".join(pages)
    return md, len(pages), empty_count, char_count


def load_existing_report() -> dict:
    if REPORT_PATH.exists():
        try:
            return json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def main():
    parser = argparse.ArgumentParser(description="Combine OlmOCR JSONL outputs into Docling-ready HTML/MD + QA report.")
    parser.add_argument("jsonl_files", nargs="+", help="Path(s) to OlmOCR JSONL file(s)")
    parser.add_argument("--html", action="store_true", help="Emit combined HTML file")
    parser.add_argument("--md", action="store_true", help="Emit combined Markdown file")
    args = parser.parse_args()

    report = load_existing_report()
    timestamp = datetime.now().isoformat(timespec="seconds")

    for fpath in args.jsonl_files:
        path = Path(fpath)
        if not path.exists() or not path.suffix == ".jsonl":
            print(f"⚠️  Skipping non-JSONL file: {path}")
            continue

        html, n_pages_html, empty_html, chars_html = merge_jsonl_to_html(path)
        md, n_pages_md, empty_md, chars_md = merge_jsonl_to_markdown(path)
        n_pages = max(n_pages_html, n_pages_md)
        empty_pages = max(empty_html, empty_md)
        total_chars = max(chars_html, chars_md)

        base = path.stem
        entry = {
            "timestamp": timestamp,
            "jsonl": str(path),
            "pages": n_pages,
            "empty_pages": empty_pages,
            "characters": total_chars,
            "html_output": None,
            "markdown_output": None,
        }

        if args.html:
            html_path = OUT_DIR_HTML / f"{base}.merged.html"
            html_path.write_text(html, encoding="utf-8")
            entry["html_output"] = str(html_path)
            print(f"✅ HTML: {html_path.name} ({n_pages} pages, {empty_pages} empty)")

        if args.md:
            md_path = OUT_DIR_MD / f"{base}.merged.md"
            md_path.write_text(md, encoding="utf-8")
            entry["markdown_output"] = str(md_path)
            print(f"✅ Markdown: {md_path.name} ({n_pages} pages, {empty_pages} empty)")

        report[base] = entry

    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n🧾 Summary report written to: {REPORT_PATH}\n")


if __name__ == "__main__":
    main()
