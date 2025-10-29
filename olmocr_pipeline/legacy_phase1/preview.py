#!/usr/bin/env python3
"""
preview.py — Simple browser preview tool for OCR or RAG output files
(OlmOCR Markdown or HTML).

Usage:
  python preview.py <path-to-md-or-html-file>

Example:
  python preview.py "rag_staging/markdown_merged/2023004079_Assn_Legacy_Reserves.merged.md"
"""

import sys
import subprocess
import tempfile
import webbrowser
from pathlib import Path

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
def convert_md_to_html(md_text: str, title: str = "Preview") -> str:
    """Convert Markdown to HTML using pandoc if available, else fallback."""
    try:
        html = subprocess.check_output(
            ["pandoc", "--from", "markdown", "--to", "html"],
            input=md_text.encode("utf-8"),
            stderr=subprocess.DEVNULL,
        ).decode("utf-8")
    except (FileNotFoundError, subprocess.CalledProcessError):
        # Fallback mini converter
        import markdown
        html = markdown.markdown(md_text, extensions=["tables", "fenced_code"])

    style = """
    <style>
      body { font-family: system-ui, serif; margin: 2em; line-height: 1.5; }
      section { margin-bottom: 3em; }
      table { border-collapse: collapse; width: 100%; margin-top: 1em; }
      th, td { border: 1px solid #999; padding: 4px; vertical-align: top; }
      h1, h2, h3 { border-bottom: 1px solid #ccc; padding-bottom: 4px; }
      @media print {
        @page { size: auto; margin: 1in; }
        section { page-break-after: always; }
      }
    </style>
    """
    return f"<!DOCTYPE html><html><head><meta charset='utf-8'><title>{title}</title>{style}</head><body>{html}</body></html>"


def open_in_browser(html: str, name: str):
    """Write HTML to temp file and open in browser."""
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as f:
        f.write(html)
        temp_path = f.name
    webbrowser.open_new_tab(f"file://{temp_path}")
    print(f"🌐 Preview opened in browser: {temp_path}")


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python preview.py <path-to-md-or-html-file>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"❌ File not found: {path}")
        sys.exit(1)

    if path.suffix.lower() == ".html":
        html = path.read_text(encoding="utf-8")
        open_in_browser(html, path.stem)
    elif path.suffix.lower() in {".md", ".markdown"}:
        md_text = path.read_text(encoding="utf-8")
        html = convert_md_to_html(md_text, path.stem)
        open_in_browser(html, path.stem)
    else:
        print("⚠️  Unsupported file type. Use .md or .html")

if __name__ == "__main__":
    main()
