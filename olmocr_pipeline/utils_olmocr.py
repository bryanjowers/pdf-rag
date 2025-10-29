#!/usr/bin/env python3
"""
utils_olmocr.py - Reusable OlmOCR-2 processing utilities

Extracted from process_pdf.py for composability and reuse across
scanned PDF and image handlers.
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional


def get_olmocr_module() -> str:
    """
    Determine the correct OlmOCR module path with fallback support.

    Returns:
        str: Module path to use with -m flag

    Raises:
        ImportError: If neither module variant is available
    """
    try:
        import olmocr.pipeline
        return "olmocr.pipeline"
    except ImportError:
        try:
            import olmocr.cli
            return "olmocr.cli"
        except ImportError:
            raise ImportError(
                "OlmOCR module not found. Please ensure olmocr is installed "
                "and you are in the correct virtual environment."
            )


def run_olmocr_batch(
    file_paths: List[Path],
    output_dir: Path,
    config: Dict,
    log_file: Path,
    workers: Optional[int] = None
) -> None:
    """
    Run OlmOCR CLI pipeline on batch of files (PDFs or images).

    Supports both PDF and image inputs (JPG, PNG, TIF).
    Produces HTML + Markdown outputs in output_dir.

    Args:
        file_paths: List of input file paths (PDFs or images)
        output_dir: Base output directory for OlmOCR staging
        config: Configuration dictionary
        log_file: Path to write log output
        workers: Number of parallel workers (default from config)

    Raises:
        subprocess.CalledProcessError: If OlmOCR pipeline fails
        ImportError: If OlmOCR module not found
    """
    # Get OlmOCR settings from config
    olmocr_config = config.get("processors", {}).get("olmocr", {})
    model_id = olmocr_config.get("model_id", "allenai/olmOCR-2-7B-1025-FP8")
    target_dim = olmocr_config.get("target_image_dim", "1288")
    gpu_util = olmocr_config.get("gpu_memory_utilization", 0.8)
    workers = workers or olmocr_config.get("default_workers", 6)

    # Convert paths to strings
    file_path_strings = [str(p.resolve()) for p in file_paths]

    # Dynamically determine module path
    try:
        module_path = get_olmocr_module()
    except ImportError as e:
        print(f"❌ {e}")
        raise

    # Build command
    command = [
        sys.executable,
        "-m", module_path,
        str(output_dir),
        "--markdown",
        "--model", model_id,
        "--workers", str(workers),
        "--target_longest_image_dim", target_dim,
        "--gpu-memory-utilization", str(gpu_util),
        "--pdfs", *file_path_strings
    ]

    print(f"🚀 Starting OlmOCR batch for {len(file_paths)} file(s)...")
    print(f"   Module: {module_path}")
    print(f"   Workspace: {output_dir.resolve()}")
    print(f"   Workers: {workers}")
    print(f"   Log file: {log_file}\n")

    # Run OlmOCR with live output streaming
    with log_file.open("w", encoding="utf-8") as lf:
        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1
        ) as proc:
            # Stream output live
            if proc.stdout:
                for line in proc.stdout:
                    line = line.rstrip("\n")
                    print(f"   [olmocr] {line}")
                    lf.write(line + "\n")

            # Wait for completion
            proc.wait()

            # Check return code
            if proc.returncode != 0:
                print(f"\n⚠️  OlmOCR pipeline FAILED with exit code {proc.returncode}")
                print(f"   Check log: {log_file}")
                print(f"   Common issues: GPU memory, invalid file, missing dependencies")
                raise subprocess.CalledProcessError(proc.returncode, command)

    print("✅ OlmOCR batch completed successfully.\n")


def get_olmocr_jsonl_path(
    input_path: Path,
    output_dir: Path
) -> Optional[Path]:
    """
    Find the JSONL output file produced by OlmOCR v0.4.2+.

    OlmOCR v0.4.2+ outputs JSONL files in results/ directory with hash-based names.
    This function reads the mapping file to find the correct JSONL output.

    Args:
        input_path: Original input file path
        output_dir: OlmOCR output directory (olmocr_staging)

    Returns:
        Path to JSONL file, or None if not found
    """
    import zstandard as zstd
    import csv
    import hashlib

    # Compute file hash (same method OlmOCR uses)
    file_hash = hashlib.sha256(str(input_path.resolve()).encode()).hexdigest()

    # Check if JSONL exists directly
    results_dir = output_dir / "results"
    jsonl_path = results_dir / f"output_{file_hash}.jsonl"

    if jsonl_path.exists():
        return jsonl_path

    # Fallback: read mapping file
    mapping_file = output_dir / "work_index_list.csv.zstd"
    if not mapping_file.exists():
        return None

    try:
        with open(mapping_file, "rb") as f:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(f) as reader:
                text_stream = reader.read().decode('utf-8')
                for row in csv.reader(text_stream.splitlines()):
                    if len(row) == 2:
                        hash_val, file_path = row
                        if Path(file_path) == input_path.resolve():
                            jsonl_path = results_dir / f"output_{hash_val}.jsonl"
                            if jsonl_path.exists():
                                return jsonl_path
    except Exception:
        pass

    return None


def get_olmocr_output_paths(
    input_path: Path,
    output_dir: Path
) -> tuple[Path, Path]:
    """
    Compute expected HTML and Markdown paths from OlmOCR (DEPRECATED).

    NOTE: OlmOCR v0.4.2+ outputs JSONL files instead of markdown.
    Use get_olmocr_jsonl_path() for newer OlmOCR versions.

    Args:
        input_path: Original input file path
        output_dir: OlmOCR output directory

    Returns:
        Tuple of (html_path, markdown_path)
    """
    stem = input_path.stem

    html_dir = output_dir / "html"
    markdown_dir = output_dir / "markdown"

    html_path = html_dir / f"{stem}.html"
    md_path = markdown_dir / f"{stem}.md"

    return html_path, md_path


def olmocr_jsonl_to_markdown(jsonl_path: Path) -> str:
    """
    Convert OlmOCR JSONL output to markdown format.

    OlmOCR v0.4.2+ outputs JSONL files with extracted text.
    This function reads the JSONL and extracts the text field.

    Args:
        jsonl_path: Path to JSONL file

    Returns:
        Markdown-formatted text content

    Raises:
        FileNotFoundError: If JSONL doesn't exist
        ValueError: If JSONL is empty or malformed
    """
    import json

    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL not found: {jsonl_path}")

    markdown_parts = []

    try:
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    text = data.get("text", "")
                    if text:
                        markdown_parts.append(text)
                except json.JSONDecodeError as e:
                    raise ValueError(f"Malformed JSON on line {line_num}: {e}")

        if not markdown_parts:
            raise ValueError(f"JSONL file is empty or contains no text: {jsonl_path}")

        # Join with double newlines to separate pages/sections
        return "\n\n".join(markdown_parts)

    except Exception as e:
        raise ValueError(f"Failed to read JSONL: {e}")


def olmocr_jsonl_to_markdown_with_pages(jsonl_path: Path) -> tuple[str, Dict[str, int]]:
    """
    Convert OlmOCR JSONL output to markdown with character-based page mapping.

    OlmOCR v0.4.2+ outputs JSONL files with page numbers in attributes.pdf_page_numbers.
    Format: [[start_char, end_char, page_num], ...]

    Args:
        jsonl_path: Path to JSONL file

    Returns:
        Tuple of (markdown_content, page_ranges) where page_ranges maps character positions to pages
        page_ranges format: {char_range: page_num} where char_range is "start-end"

    Raises:
        FileNotFoundError: If JSONL doesn't exist
        ValueError: If JSONL is empty or malformed
    """
    import json

    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL not found: {jsonl_path}")

    markdown_parts = []
    page_ranges = []  # List of (start_char_in_full_text, end_char_in_full_text, page_num)
    current_char_pos = 0

    try:
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                    text = data.get("text", "")

                    if text:
                        markdown_parts.append(text)

                        # Extract page ranges from attributes.pdf_page_numbers
                        # Format: [[start_char, end_char, page_num], ...]
                        attrs = data.get("attributes", {})
                        pdf_pages = attrs.get("pdf_page_numbers", [])

                        if pdf_pages:
                            # Convert OlmOCR's local character positions to global positions
                            for page_range in pdf_pages:
                                if len(page_range) >= 3:
                                    local_start, local_end, page_num = page_range
                                    global_start = current_char_pos + local_start
                                    global_end = current_char_pos + local_end
                                    page_ranges.append((global_start, global_end, page_num))

                        # Update character position (text + 2 chars for "\n\n")
                        current_char_pos += len(text) + 2

                except json.JSONDecodeError as e:
                    raise ValueError(f"Malformed JSON on line {line_num}: {e}")

        if not markdown_parts:
            raise ValueError(f"JSONL file is empty or contains no text: {jsonl_path}")

        # Join with double newlines to separate pages/sections
        markdown_content = "\n\n".join(markdown_parts)

        # Convert page_ranges list to a lookup-friendly dict
        page_map = {}
        for start, end, page_num in page_ranges:
            page_map[f"{start}-{end}"] = page_num

        return markdown_content, page_map

    except Exception as e:
        raise ValueError(f"Failed to read JSONL: {e}")


def _get_page_for_char_position(char_pos: int, page_mapping: Dict[str, int]) -> Optional[int]:
    """
    Find which page a character position falls into.

    Args:
        char_pos: Character position in the text
        page_mapping: Dict mapping "start-end" ranges to page numbers

    Returns:
        Page number, or None if not found
    """
    for range_str, page_num in page_mapping.items():
        start, end = map(int, range_str.split('-'))
        if start <= char_pos < end:
            return page_num
    return None


def olmocr_to_jsonl(
    markdown_content: str,
    source_path: Path,
    config: Dict,
    batch_id: str,
    page_mapping: Optional[Dict[str, int]] = None
) -> List[Dict]:
    """
    Convert OlmOCR markdown output to JSONL chunks (schema v2.3.0).

    Reuses chunking logic from pdf_digital handler but applies to
    OlmOCR outputs (scanned PDFs, images).

    Args:
        markdown_content: Markdown text from OlmOCR
        source_path: Original source file path
        config: Configuration dictionary
        batch_id: Batch identifier
        page_mapping: Optional dict mapping character ranges ("start-end") to page numbers

    Returns:
        List of JSONL record dictionaries (schema v2.3.0 with page-level bbox)
    """
    from datetime import datetime
    from utils_classify import compute_file_hash, get_mime_type

    # Compute source file hash
    file_hash = compute_file_hash(source_path)
    mime_type = get_mime_type(source_path)

    # Generate doc_id from hash
    doc_id = file_hash[:16]

    # Try paragraph-based chunking first
    paragraphs = [p.strip() for p in markdown_content.split('\n\n') if p.strip()]

    # Get chunking config
    chunking_config = config.get("chunking", {})
    token_target = chunking_config.get("token_target", 1400)
    token_max = chunking_config.get("token_max", 2000)

    # Detect if this is continuous text (OlmOCR JSONL) vs structured markdown (Docling)
    # If we have very few paragraphs, use sentence-based chunking instead
    use_sentence_chunking = len(paragraphs) < 3

    chunks = []

    if use_sentence_chunking:
        # OlmOCR produces continuous text - use sentence-based chunking
        import re

        # Split by sentences (basic approach)
        sentences = re.split(r'(?<=[.!?])\s+', markdown_content)

        current_chunk = []
        current_tokens = 0

        for sent in sentences:
            sent_tokens = len(sent.split())

            if current_tokens + sent_tokens > token_max and current_chunk:
                chunks.append(' '.join(current_chunk))
                current_chunk = [sent]
                current_tokens = sent_tokens
            else:
                current_chunk.append(sent)
                current_tokens += sent_tokens

                if current_tokens >= token_target:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

        # Add remaining
        if current_chunk:
            chunks.append(' '.join(current_chunk))

    else:
        # Structured markdown (Docling) - use paragraph-based chunking
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = len(para.split())

            # If adding exceeds max, finalize current chunk
            if current_tokens + para_tokens > token_max and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = [para]
                current_tokens = para_tokens
            else:
                current_chunk.append(para)
                current_tokens += para_tokens

                # If reached target, finalize
                if current_tokens >= token_target:
                    chunks.append("\n\n".join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

        # Add remaining
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

    # Determine file type
    ext = source_path.suffix.lower()
    if ext == '.pdf':
        file_type = 'pdf_scanned'
    elif ext in ['.jpg', '.jpeg']:
        file_type = 'image_jpg'
    elif ext == '.png':
        file_type = 'image_png'
    elif ext in ['.tif', '.tiff']:
        file_type = 'image_tiff'
    else:
        file_type = 'unknown'

    # Convert to JSONL records (schema v2.3.0)
    schema_version = config.get("schema", {}).get("version", "2.3.0")
    processed_at = datetime.utcnow().isoformat() + "Z"

    jsonl_records = []
    for idx, chunk_text in enumerate(chunks):
        chunk_tokens = len(chunk_text.split())

        # Get page number by finding this chunk's position in the markdown
        page_num = None
        if page_mapping and chunk_text:
            # Find where this chunk appears in the markdown
            char_pos = markdown_content.find(chunk_text[:100])  # Use first 100 chars for matching
            if char_pos != -1:
                page_num = _get_page_for_char_position(char_pos, page_mapping)

        # Page-level bbox (MVP: coordinates as None, page number only)
        chunk_bbox = None
        if page_num is not None:
            chunk_bbox = {
                "page": page_num,
                "x0": None,  # Precise coordinates not available from OlmOCR
                "y0": None,
                "x1": None,
                "y1": None
            }

        record = {
            "id": f"{doc_id}_{idx:04d}",
            "doc_id": doc_id,
            "chunk_index": idx,
            "text": chunk_text,
            "attrs": {
                "page_span": None,  # TODO: Extract from OlmOCR output
                "sections": [],
                "table": "| " in chunk_text and chunk_text.count("|") >= 3,
                "token_count": chunk_tokens,
                "bbox": chunk_bbox  # NEW in v2.3.0: page-level bbox
            },
            "source": {
                "file_path": str(source_path.resolve()),
                "file_name": source_path.name,
                "file_type": ext.lstrip('.'),
                "mime_type": mime_type
            },
            "metadata": {
                "schema_version": schema_version,
                "file_type": file_type,
                "mime_type": mime_type,
                "hash_input_sha256": file_hash,
                "processor": "olmocr-2",
                "processor_version": "olmocr-2-7b",
                "processed_at": processed_at,
                "batch_id": batch_id,
                "processing_duration_ms": None,  # Set by caller
                "confidence_score": 0.85,  # Lower than digital (OCR uncertainty)
                "warnings": []
            }
        }

        jsonl_records.append(record)

    return jsonl_records
