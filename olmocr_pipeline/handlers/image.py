#!/usr/bin/env python3
"""
image.py - Image file processing handler using OlmOCR-2

Processes JPG, PNG, TIF images using OlmOCR-2 OCR.
Reuses olmOCR logic from utils_olmocr.py for composability.
"""

import json
import time
from pathlib import Path
from typing import Dict

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils_olmocr import run_olmocr_batch, get_olmocr_jsonl_path, olmocr_jsonl_to_markdown, olmocr_to_jsonl


def process_image(
    image_path: Path,
    output_dir: Path,
    config: Dict,
    batch_id: str
) -> Dict:
    """
    Process image file using OlmOCR-2 OCR.

    Supported formats: JPG, JPEG, PNG, TIF, TIFF

    Args:
        image_path: Path to input image file
        output_dir: Base output directory
        config: Configuration dictionary
        batch_id: Unique batch identifier

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
        FileNotFoundError: If image doesn't exist
    """
    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    start_time = time.time()
    warnings = []

    # Prepare output directories
    olmocr_staging = output_dir / "olmocr_staging"
    markdown_dir = output_dir / "markdown"
    jsonl_dir = output_dir / "jsonl"
    log_dir = output_dir / "logs"

    for d in [olmocr_staging, markdown_dir, jsonl_dir, log_dir]:
        d.mkdir(parents=True, exist_ok=True)

    stem = image_path.stem
    log_file = log_dir / f"olmocr_{stem}.log"

    try:
        print(f"   🔄 Processing with OlmOCR-2: {image_path.name}")

        # Run OlmOCR batch (single image)
        run_olmocr_batch(
            file_paths=[image_path],
            output_dir=olmocr_staging,
            config=config,
            log_file=log_file
        )

        # Get OlmOCR JSONL output (v0.4.2+ format)
        jsonl_path_olmocr = get_olmocr_jsonl_path(image_path, olmocr_staging)

        # Check if JSONL was created
        if not jsonl_path_olmocr or not jsonl_path_olmocr.exists():
            raise FileNotFoundError(f"OlmOCR did not produce JSONL output")

        # Convert JSONL to markdown
        markdown_content = olmocr_jsonl_to_markdown(jsonl_path_olmocr)
        char_count = len(markdown_content)

        # Check for low yield
        if char_count < 50:
            warnings.append(f"Very low text yield: {char_count} chars")

        # Copy markdown to final location
        final_md_path = markdown_dir / f"{stem}.md"
        final_md_path.write_text(markdown_content, encoding="utf-8")

        # Convert to JSONL
        chunks = olmocr_to_jsonl(markdown_content, image_path, config, batch_id)

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
            "page_count": 1,  # Images are always single page
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
