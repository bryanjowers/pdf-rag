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


def olmocr_to_jsonl(
    markdown_content: str,
    source_path: Path,
    config: Dict,
    batch_id: str
) -> List[Dict]:
    """
    Convert OlmOCR markdown output to JSONL chunks.

    Reuses chunking logic from pdf_digital handler but applies to
    OlmOCR outputs (scanned PDFs, images).

    Args:
        markdown_content: Markdown text from OlmOCR
        source_path: Original source file path
        config: Configuration dictionary
        batch_id: Batch identifier

    Returns:
        List of JSONL record dictionaries
    """
    from datetime import datetime
    from utils_classify import compute_file_hash, get_mime_type

    # Compute source file hash
    file_hash = compute_file_hash(source_path)
    mime_type = get_mime_type(source_path)

    # Generate doc_id from hash
    doc_id = file_hash[:16]

    # Simple chunking by paragraphs
    paragraphs = [p.strip() for p in markdown_content.split('\n\n') if p.strip()]

    # Get chunking config
    chunking_config = config.get("chunking", {})
    token_target = chunking_config.get("token_target", 1400)
    token_max = chunking_config.get("token_max", 2000)

    # Combine paragraphs into chunks
    chunks = []
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
                "page_span": None,  # TODO: Extract from OlmOCR output
                "sections": [],
                "table": "| " in chunk_text and chunk_text.count("|") >= 3,
                "token_count": chunk_tokens
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
