#!/usr/bin/env python3
"""
pdf_scanned.py - Scanned PDF processing handler using OlmOCR-2

Processes PDFs without digital text layers using OlmOCR-2 OCR.
Optionally applies preprocessing (image cleanup) before OCR.
Reuses OlmOCR logic from utils_olmocr.py.
"""

import json
import time
from pathlib import Path
from typing import Dict
import fitz  # PyMuPDF for page count

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils_olmocr import (
    run_olmocr_batch,
    get_olmocr_jsonl_path,
    olmocr_jsonl_to_markdown,
    olmocr_to_jsonl
)


def process_scanned_pdf(
    pdf_path: Path,
    output_dir: Path,
    config: Dict,
    batch_id: str,
    apply_preprocessing: bool = False
) -> Dict:
    """
    Process scanned PDF using OlmOCR-2 OCR.

    Args:
        pdf_path: Path to input scanned PDF
        output_dir: Base output directory
        config: Configuration dictionary
        batch_id: Unique batch identifier
        apply_preprocessing: If True, apply image cleanup before OCR

    Returns:
        Processing result dictionary with metadata:
        {
            "success": bool,
            "processor": "olmocr-2" | None,
            "markdown_path": Path | None,
            "jsonl_path": Path | None,
            "processing_duration_ms": int,
            "char_count": int,
            "estimated_tokens": int,
            "chunk_count": int,
            "warnings": list[str],
            "error": str | None
        }

    Raises:
        FileNotFoundError: If PDF doesn't exist
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    start_time = time.time()
    warnings = []
    processed_pdf_path = pdf_path

    # Optional preprocessing
    if apply_preprocessing:
        try:
            from utils_preprocess import preprocess_pdf
            print(f"   🧹 Applying preprocessing...")
            processed_pdf_path = preprocess_pdf(pdf_path)
            print(f"      Preprocessed: {processed_pdf_path.name}")
        except Exception as e:
            warnings.append(f"Preprocessing failed: {e}")
            print(f"   ⚠️  Preprocessing failed: {e}")
            print(f"      Continuing with original PDF...")

    # Prepare output directories
    olmocr_staging = output_dir / "olmocr_staging"
    markdown_dir = output_dir / "markdown"
    jsonl_dir = output_dir / "jsonl"
    log_dir = output_dir / "logs"

    for d in [olmocr_staging, markdown_dir, jsonl_dir, log_dir]:
        d.mkdir(parents=True, exist_ok=True)

    stem = pdf_path.stem  # Use original stem
    log_file = log_dir / f"olmocr_{stem}.log"

    try:
        print(f"   🔄 Processing with OlmOCR-2: {pdf_path.name}")

        # Run OlmOCR batch
        run_olmocr_batch(
            file_paths=[processed_pdf_path],
            output_dir=olmocr_staging,
            config=config,
            log_file=log_file
        )

        # Get OlmOCR JSONL output (v0.4.2+ format)
        jsonl_path_olmocr = get_olmocr_jsonl_path(pdf_path, olmocr_staging)

        # Check if JSONL was created
        if jsonl_path_olmocr is None or not jsonl_path_olmocr.exists():
            raise FileNotFoundError(f"OlmOCR did not produce JSONL output for: {pdf_path.name}")

        # Convert JSONL to markdown
        markdown_content = olmocr_jsonl_to_markdown(jsonl_path_olmocr)
        char_count = len(markdown_content)

        # Get page count from PDF
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
        except Exception:
            page_count = 1  # Fallback if PDF can't be opened
            warnings.append("Could not determine page count from PDF")

        # Check for low yield (OCR might have failed on some pages)
        chars_per_page = char_count / page_count if page_count > 0 else 0
        if chars_per_page < 100:
            warnings.append(f"Low text yield: {chars_per_page:.0f} chars/page")

        # Copy markdown to final location
        final_md_path = markdown_dir / f"{stem}.md"
        final_md_path.write_text(markdown_content, encoding="utf-8")

        # Convert to JSONL
        chunks = olmocr_to_jsonl(markdown_content, pdf_path, config, batch_id)

        # Write JSONL
        jsonl_path = jsonl_dir / f"{stem}.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

        # Compute duration
        duration_ms = int((time.time() - start_time) * 1000)

        print(f"   ✅ OlmOCR-2 processing complete")
        print(f"      Output: {char_count:,} chars (~{len(markdown_content.split()):,} tokens)")
        print(f"      Duration: {duration_ms/1000:.1f}s")
        print(f"      Chunks: {len(chunks)}")

        if warnings:
            for warning in warnings:
                print(f"      ⚠️  {warning}")

        return {
            "success": True,
            "processor": "olmocr-2",
            "markdown_path": final_md_path,
            "jsonl_path": jsonl_path,
            "processing_duration_ms": duration_ms,
            "page_count": page_count,
            "char_count": char_count,
            "estimated_tokens": len(markdown_content.split()),
            "chunk_count": len(chunks),
            "warnings": warnings,
            "error": None
        }

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"OlmOCR-2 failed: {str(e)}"
        print(f"   ❌ {error_msg}")

        return {
            "success": False,
            "processor": None,
            "markdown_path": None,
            "jsonl_path": None,
            "processing_duration_ms": duration_ms,
            "char_count": 0,
            "estimated_tokens": 0,
            "chunk_count": 0,
            "warnings": warnings,
            "error": error_msg
        }
