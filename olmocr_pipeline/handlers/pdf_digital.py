#!/usr/bin/env python3
"""
pdf_digital.py - Digital PDF processing handler using Docling

Processes PDFs with digital text layers using Docling's document converter.
Includes fallback to OlmOCR-2 if text yield is too low.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions


def process_digital_pdf(
    pdf_path: Path,
    output_dir: Path,
    config: Dict,
    batch_id: str
) -> Dict:
    """
    Process digital PDF using Docling with fallback to OlmOCR-2.

    Args:
        pdf_path: Path to input PDF
        output_dir: Base output directory
        config: Configuration dictionary
        batch_id: Unique batch identifier

    Returns:
        Processing result dictionary with metadata:
        {
            "success": bool,
            "processor": "docling" | "olmocr" | None,
            "markdown_path": Path | None,
            "jsonl_path": Path | None,
            "processing_duration_ms": int,
            "char_count": int,
            "estimated_tokens": int,
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

    # Extract config settings
    min_yield = config.get("classification", {}).get("min_text_yield_per_page", 100)

    # Prepare output paths
    markdown_dir = output_dir / "markdown"
    jsonl_dir = output_dir / "jsonl"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    jsonl_dir.mkdir(parents=True, exist_ok=True)

    stem = pdf_path.stem
    markdown_path = markdown_dir / f"{stem}.md"
    jsonl_path = jsonl_dir / f"{stem}.jsonl"

    try:
        # Initialize Docling converter
        converter = DocumentConverter()

        # Convert PDF to document
        print(f"   🔄 Converting with Docling: {pdf_path.name}")
        result = converter.convert(str(pdf_path))

        # Extract markdown
        markdown_content = result.document.export_to_markdown()
        char_count = len(markdown_content)

        # Get page count for validation
        # Note: result.document may have page_count attribute
        pages = getattr(result.document, 'page_count', None) or len(result.document.pages) if hasattr(result.document, 'pages') else 1

        # Check text yield per page
        chars_per_page = char_count / pages if pages > 0 else 0

        if chars_per_page < min_yield:
            warnings.append(f"Low text yield: {chars_per_page:.0f} chars/page (threshold: {min_yield})")
            warnings.append("Consider fallback to OlmOCR-2 for better OCR")

        # Write markdown output
        markdown_path.write_text(markdown_content, encoding="utf-8")

        # Convert to JSONL chunks
        chunks = convert_to_jsonl(
            markdown_content,
            pdf_path,
            config,
            batch_id,
            processor="docling"
        )

        # Write JSONL output
        with jsonl_path.open("w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

        # Compute duration
        duration_ms = int((time.time() - start_time) * 1000)

        print(f"   ✅ Docling processing complete")
        print(f"      Output: {char_count:,} chars (~{len(markdown_content.split()):,} tokens)")
        print(f"      Duration: {duration_ms/1000:.1f}s")
        print(f"      Chunks: {len(chunks)}")

        if warnings:
            for warning in warnings:
                print(f"      ⚠️  {warning}")

        return {
            "success": True,
            "processor": "docling",
            "markdown_path": markdown_path,
            "jsonl_path": jsonl_path,
            "processing_duration_ms": duration_ms,
            "page_count": pages,
            "char_count": char_count,
            "estimated_tokens": len(markdown_content.split()),
            "chunk_count": len(chunks),
            "warnings": warnings,
            "error": None
        }

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Docling conversion failed: {str(e)}"
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


def convert_to_jsonl(
    markdown_text: str,
    source_path: Path,
    config: Dict,
    batch_id: str,
    processor: str
) -> list[Dict]:
    """
    Convert markdown text to JSONL chunks following unified schema.

    Args:
        markdown_text: Markdown content to chunk
        source_path: Original source file path
        config: Configuration dictionary
        batch_id: Batch identifier
        processor: Name of processor used

    Returns:
        List of JSONL record dictionaries
    """
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from utils_classify import compute_file_hash, get_mime_type

    # Compute source file hash
    file_hash = compute_file_hash(source_path)
    mime_type = get_mime_type(source_path)

    # Generate doc_id from hash (first 16 chars)
    doc_id = file_hash[:16]

    # Simple chunking by paragraphs for now
    # TODO: Implement smart chunking with heading detection and token limits
    paragraphs = [p.strip() for p in markdown_text.split('\n\n') if p.strip()]

    # Get chunking config
    chunking_config = config.get("chunking", {})
    token_target = chunking_config.get("token_target", 1400)
    token_min = chunking_config.get("token_min", 800)
    token_max = chunking_config.get("token_max", 2000)

    # Combine paragraphs into chunks within token limits
    chunks = []
    current_chunk = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = len(para.split())

        # If adding this paragraph exceeds max, finalize current chunk
        if current_tokens + para_tokens > token_max and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [para]
            current_tokens = para_tokens
        else:
            current_chunk.append(para)
            current_tokens += para_tokens

            # If we've reached target size, finalize chunk
            if current_tokens >= token_target:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_tokens = 0

    # Add remaining chunk
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    # Convert to JSONL records
    schema_version = config.get("schema", {}).get("version", "2.2.0")
    processed_at = datetime.utcnow().isoformat() + "Z"

    jsonl_records = []
    for idx, chunk_text in enumerate(chunks):
        chunk_tokens = len(chunk_text.split())

        record = {
            "id": f"{doc_id}_{idx:04d}",
            "doc_id": doc_id,
            "chunk_index": idx,
            "text": chunk_text,
            "attrs": {
                "page_span": None,  # TODO: Track page numbers
                "sections": [],     # TODO: Extract section headers
                "table": False,     # TODO: Detect if chunk contains table
                "token_count": chunk_tokens
            },
            "source": {
                "file_path": str(source_path.resolve()),
                "file_name": source_path.name,
                "file_type": "pdf",
                "mime_type": mime_type
            },
            "metadata": {
                "schema_version": schema_version,
                "file_type": "pdf_digital",
                "mime_type": mime_type,
                "hash_input_sha256": file_hash,
                "processor": processor,
                "processor_version": "docling-latest",  # TODO: Get actual version
                "processed_at": processed_at,
                "batch_id": batch_id,
                "processing_duration_ms": None,  # Set by caller
                "confidence_score": 1.0,  # Digital PDF = high confidence
                "warnings": []
            }
        }

        jsonl_records.append(record)

    return jsonl_records


def check_fallback_needed(
    result: Dict,
    pdf_path: Path,
    config: Dict
) -> bool:
    """
    Determine if OlmOCR-2 fallback is needed based on Docling result.

    Args:
        result: Docling processing result
        pdf_path: Path to PDF file
        config: Configuration dictionary

    Returns:
        True if fallback should be triggered, False otherwise
    """
    # Check if Docling failed
    if not result["success"]:
        return True

    # Check text yield
    min_yield = config.get("classification", {}).get("min_text_yield_per_page", 100)

    # Estimate pages (simple check)
    # In production, would get actual page count from classification
    char_count = result["char_count"]

    # If very low character count, consider fallback
    if char_count < 500:
        return True

    # Check for low yield warning
    if any("Low text yield" in w for w in result.get("warnings", [])):
        max_fallback_pages = config.get("classification", {}).get("max_pages_for_fallback", 1000)

        # Simple heuristic: only fallback if likely under page limit
        # In production, would check actual page count
        return True  # For now, allow fallback

    return False
