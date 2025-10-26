#!/usr/bin/env python3
"""
process_pdf.py — Modernized OlmOCR-2 + QA pipeline (Milestone #2)

Usage examples:
  python process_pdf.py app/samples/*.pdf --summary
  python process_pdf.py app/samples/*.pdf --preprocess --summary
  python process_pdf.py app/samples/*.pdf --qa
"""

import argparse
import os
import time
from pathlib import Path
from datetime import datetime
import json
import webbrowser

# Local imports
from qa_summary import summarize_output
from utils_preprocess import preprocess_pdf

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------
OUTPUT_DIR = Path("olmocr_pipeline/data/processed_html")
LOG_DIR = Path("olmocr_pipeline/data/logs")
MODEL_ID = "allenai/olmOCR-2-7B-1025-FP8"

# ---------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------
def ensure_dirs():
    for d in [OUTPUT_DIR, LOG_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def run_olmocr_single(pdf_path: Path, model=None) -> Path:
    """Run OlmOCR-2 on one PDF and save HTML output."""
    from olmocr import OlmOCR

    if model is None:
        print(f"🧠 Loading model {MODEL_ID} ...")
        model = OlmOCR.from_pretrained(MODEL_ID, device="cuda")

    html_output = model.run(pdf_path, output_format="html")
    out_path = OUTPUT_DIR / f"{pdf_path.stem}.html"
    out_path.write_text(html_output, encoding="utf-8")
    print(f"✅ {pdf_path.name} → {out_path.name}")
    return out_path


def save_summary(pdf_path: Path, html_path: Path, start_time: float):
    summary = summarize_output(pdf_path, html_path, start_time)
    summary_file = LOG_DIR / f"{pdf_path.stem}_summary.json"
    summary_file.write_text(json.dumps(summary, indent=2))
    print(f"📈 Summary saved → {summary_file}")


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Run OlmOCR-2 on one or more PDFs.")
    parser.add_argument("pdfs", nargs="+", help="Path(s) to input PDF(s)")
    parser.add_argument("--preprocess", action="store_true", help="Apply image cleanup before OCR")
    parser.add_argument("--summary", action="store_true", help="Generate summary JSON after each run")
    parser.add_argument("--qa", action="store_true", help="Open resulting HTML in browser for inspection")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of PDFs processed")
    args = parser.parse_args()

    ensure_dirs()
    start_time = time.time()

    from olmocr import OlmOCR
    print(f"🚀 Initializing model {MODEL_ID} (FP8) on CUDA ...")
    model = OlmOCR.from_pretrained(MODEL_ID, device="cuda")

    pdf_paths = [Path(p) for p in args.pdfs]
    if args.limit:
        pdf_paths = pdf_paths[: args.limit]

    for pdf_path in pdf_paths:
        print(f"\n📄 Processing {pdf_path.name} ...")

        if args.preprocess:
            print("🧹 Running preprocessing step ...")
            pdf_path = preprocess_pdf(pdf_path)

        try:
            html_path = run_olmocr_single(pdf_path, model=model)

            if args.summary:
                save_summary(pdf_path, html_path, start_time)

            if args.qa:
                webbrowser.open(f"file://{html_path.resolve()}")

        except Exception as e:
            print(f"⚠️  Error processing {pdf_path.name}: {e}")

    print("\n🎯 Done. All outputs written to:", OUTPUT_DIR.resolve())


if __name__ == "__main__":
    main()
