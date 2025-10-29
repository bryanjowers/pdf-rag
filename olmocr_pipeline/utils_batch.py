#!/usr/bin/env python3
"""
utils_batch.py — Batch processing utilities for OlmOCR pipeline

Provides:
- Single-instance file locking
- Enhanced GCS mount verification
- PDF discovery with sorting options
- Unique batch ID generation
- Output file relocation
"""

import os
import random
import shutil
import string
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from filelock import FileLock, Timeout


def acquire_process_lock(lock_file: Path, timeout: float = 1.0) -> Optional[FileLock]:
    """
    Acquire single-instance lock to prevent concurrent process_pdf.py runs.

    Args:
        lock_file: Path to lock file
        timeout: Timeout in seconds

    Returns:
        FileLock object if acquired, None otherwise

    Raises:
        SystemExit: If another instance is already running
    """
    lock = FileLock(lock_file, timeout=timeout)

    try:
        lock.acquire(timeout=timeout)
        print(f"✅ Process lock acquired: {lock_file}")
        return lock
    except Timeout:
        print(f"❌ Another instance is already running")
        print(f"   Lock file: {lock_file}")
        print(f"   If you're sure no other process is running, delete the lock file and retry.")
        sys.exit(1)


def release_process_lock(lock: FileLock) -> None:
    """Release process lock."""
    if lock and lock.is_locked:
        lock.release()
        print("✅ Process lock released")


def verify_gcs_mount(mount_base: Path) -> None:
    """
    Verify that GCS mount is writable.
    Uses PID and timestamp to avoid conflicts with concurrent processes.

    Args:
        mount_base: Base path of GCS mount

    Raises:
        SystemExit: If mount is not writable
    """
    test_file = mount_base / f".mount_test_{os.getpid()}_{int(time.time())}.tmp"

    try:
        # Create parent directory if it doesn't exist
        mount_base.mkdir(parents=True, exist_ok=True)

        # Write test file
        test_file.write_text("ok", encoding="utf-8")

        # Verify it exists
        if not test_file.exists():
            raise IOError("Write test failed (file not created)")

        # Cleanup
        test_file.unlink()

        print(f"✅ GCS mount healthy: {mount_base}")

    except Exception as e:
        print(f"❌ GCS mount check FAILED: {e}")
        print(f"   Mount point: {mount_base}")
        print(f"   Ensure the GCS bucket is mounted with gcsfuse and writable.")
        sys.exit(1)
    finally:
        # Ensure cleanup even on exceptions
        if test_file.exists():
            try:
                test_file.unlink()
            except Exception:
                pass  # Best effort cleanup


def discover_pdfs(input_dir: Path, sort_by: str = "name") -> list[Path]:
    """
    Discover all PDFs in input directory with optional sorting.

    Args:
        input_dir: Directory to scan for PDFs
        sort_by: Sorting method:
                 - "name": Alphabetical (default)
                 - "mtime": Oldest first (by modification time)
                 - "mtime_desc": Newest first (by modification time)

    Returns:
        List of PDF file paths

    Raises:
        FileNotFoundError: If input directory doesn't exist
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")

    if not input_dir.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {input_dir}")

    # Find all PDFs
    pdfs = list(input_dir.glob("*.pdf"))

    # Sort based on method
    if sort_by == "mtime":
        return sorted(pdfs, key=lambda p: p.stat().st_mtime)
    elif sort_by == "mtime_desc":
        return sorted(pdfs, key=lambda p: p.stat().st_mtime, reverse=True)
    else:  # "name" or any other value defaults to alphabetical
        return sorted(pdfs)


def generate_batch_id() -> str:
    """
    Generate unique batch identifier with timestamp and random suffix.

    Returns:
        Batch ID string in format: YYYYMMDD_HHMMSS_XXXX
        where XXXX is a random alphanumeric suffix
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{timestamp}_{random_suffix}"


def relocate_outputs_batch(
    pdf_paths: list[Path],
    markdown_output_dir: Path,
    jsonl_source_dir: Path,
    jsonl_dest_dir: Path
) -> dict:
    """
    Relocate generated markdown and JSONL files to canonical locations.

    Args:
        pdf_paths: List of PDF paths that were processed
        markdown_output_dir: Target directory for markdown files
        jsonl_source_dir: Source directory where OlmOCR writes JSONL (rag_staging/results)
        jsonl_dest_dir: Destination directory for JSONL files (rag_staging/jsonl)

    Returns:
        Dictionary with relocation statistics:
        {
            'markdown_moved': int,
            'markdown_missing': int,
            'jsonl_moved': int
        }
    """
    stats = {
        'markdown_moved': 0,
        'markdown_missing': 0,
        'jsonl_moved': 0
    }

    # Ensure target directories exist
    markdown_output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_dest_dir.mkdir(parents=True, exist_ok=True)

    # Move Markdown files generated next to PDFs
    for pdf in pdf_paths:
        # OlmOCR generates markdown files in the same directory as the PDF
        # with pattern: {pdf_stem}*.md
        possible_md = list(pdf.parent.glob(f"{pdf.stem}*.md"))

        if not possible_md:
            print(f"   ⚠️  No Markdown found for {pdf.name}")
            stats['markdown_missing'] += 1
            continue

        for src_md in possible_md:
            dest_md = markdown_output_dir / src_md.name

            try:
                # Move file
                shutil.move(str(src_md), str(dest_md))
                print(f"   📦 {src_md.name} → {dest_md.relative_to(dest_md.parent.parent)}")
                stats['markdown_moved'] += 1
            except Exception as e:
                print(f"   ⚠️  Failed to move {src_md.name}: {e}")

    # Move JSONL files from rag_staging/results/ to rag_staging/jsonl/
    if jsonl_source_dir.exists():
        for jsonl_file in jsonl_source_dir.glob("*.jsonl"):
            dest = jsonl_dest_dir / jsonl_file.name

            try:
                shutil.move(str(jsonl_file), str(dest))
                print(f"   📦 {jsonl_file.name} → {dest.relative_to(dest.parent.parent)}")
                stats['jsonl_moved'] += 1
            except Exception as e:
                print(f"   ⚠️  Failed to move {jsonl_file.name}: {e}")

    return stats
