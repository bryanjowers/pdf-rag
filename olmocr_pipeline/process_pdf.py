#!/usr/bin/env python3
"""
process_pdf.py — OlmOCR + Docling OCR pipeline (Milestone #1)

Usage:
  python process_pdf.py <pdf_path> [--preprocess] [--summary] [--diff <prev_html>] [--qa] [--mock]
"""

import argparse
import json
import os
import time
from datetime import datetime
from pathlib import Path

# Local helper imports
from utils_preprocess import preprocess_pdf
from qa_summary import summarize_output, diff_outputs


def ensure_dirs(base_dir="data"):
    """Ensure required folders exist."""
    dirs = [
        f"{base_dir}/pdf_input",
        f"{base_dir}/processed_html",
        f"{base_dir}/logs"
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
    return dirs


def mock_ocr(pdf_path):
    """Mock OCR for local testing (no GPU)."""
    html_output = f"<html><body><h2>Mock OCR output for {pdf_path.name}</h2></body></html>"
    return html_output


def save_output(content, out_path):
    out_path.write_text(content, encoding="utf-8")
    print(f"✅ Saved output: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="OlmOCR + Docling PDF Processor")
    parser.add_argument("pdf_path", type=str, help="Path to the input PDF")
    parser.add_argument("--preprocess", action="store_true", help="Apply image cleanup before OCR")
    parser.add_argument("--summary", action="store_true", help="Generate post-run summary JSON")
    parser.add_argument("--diff", type=str, help="Compare this run’s HTML to a previous one")
    parser.add_argument("--qa", action="store_true", help="Open raw HTML in browser for inspection")
    parser.add_argument("--mock", action="store_true", help="Run in mock (no OCR) mode")
    args = parser.parse_args()

    start_time = time.time()
    ensure_dirs()
    pdf_path = Path(args.pdf_path)
    basename = pdf_path.stem
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    out_dir = Path("data/processed_html")
    html_out_path = out_dir / f"{basename}_raw.html"
    log_dir = Path("data/logs")
    summary_log_path = log_dir / f"{basename}_summary.json"

    # Step 1: Optional preprocessing
    if args.preprocess:
        print("🧹 Preprocessing PDF images...")
        pdf_path = preprocess_pdf(pdf_path)
        print("✅ Preprocessing complete.")

    # Step 2: OCR or Mock
    if args.mock:
        print("🔧 Running in mock mode...")
        html_content = mock_ocr(pdf_path)
    else:
        print("🚀 Running real OCR via OlmOCR...")

        from transformers import AutoProcessor, AutoModelForVision2Seq
        import torch
        from PIL import Image
        from pdf2image import convert_from_path

        model_id = "IlluinTechnology/OlmOCR"
        processor = AutoProcessor.from_pretrained(model_id)
        model = AutoModelForVision2Seq.from_pretrained(model_id, torch_dtype=torch.float16).to("cuda")

        pages = convert_from_path(str(pdf_path), dpi=300)
        html_outputs = []

        for page_idx, page in enumerate(pages):
            inputs = processor(images=page, return_tensors="pt").to("cuda", torch.float16)
            generated_ids = model.generate(**inputs, max_new_tokens=2048)
            html = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
            html_outputs.append(html)
            print(f"✅ Page {page_idx + 1} processed")

        html_content = "\n".join(html_outputs)

    save_output(html_content, html_out_path)

    # Step 3: Optional QA view
    if args.qa:
        import webbrowser
        webbrowser.open(f"file://{html_out_path.resolve()}")

    # Step 4: Optional diff
    if args.diff:
        diff_log = diff_outputs(html_out_path, Path(args.diff))
        print(f"📊 Diff results: {json.dumps(diff_log, indent=2)}")

    # Step 5: Optional summary
    if args.summary:
        summary = summarize_output(pdf_path, html_out_path, start_time)
        summary_log_path.write_text(json.dumps(summary, indent=2))
        print(f"📈 Summary saved: {summary_log_path}")

    print("🎯 Done.")


if __name__ == "__main__":
    main()
