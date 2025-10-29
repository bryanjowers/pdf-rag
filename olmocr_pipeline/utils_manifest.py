#!/usr/bin/env python3
"""
utils_manifest.py - Manifest CSV generation for batch processing

Writes per-batch manifest CSV files with processing metadata for audit trails.
"""

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def write_manifest_csv(
    manifest_path: Path,
    records: List[Dict],
    config: Dict
) -> None:
    """
    Write batch manifest CSV with processing metadata.

    Args:
        manifest_path: Path to write manifest CSV
        records: List of processing result dictionaries
        config: Configuration dictionary

    CSV Schema:
        - doc_id: Document identifier (hash prefix)
        - file_path: Original file path
        - file_name: Original filename
        - file_type: File type (pdf, docx, xlsx, etc.)
        - processor: Processor used (docling, olmocr, python-docx, etc.)
        - status: Processing status (success, failed, quarantined)
        - page_count: Number of pages (PDFs and images only, null otherwise)
        - chunks_created: Number of chunks generated
        - processing_duration_ms: Processing time in milliseconds
        - char_count: Character count of output
        - estimated_tokens: Estimated token count
        - hash_sha256: SHA256 hash of input file
        - batch_id: Batch identifier
        - processed_at: ISO timestamp
        - warnings: Comma-separated warnings
        - error: Error message (if failed)
        - confidence_score: Processing confidence (0.0-1.0)
    """
    # Ensure parent directory exists
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    # Define CSV columns
    fieldnames = [
        "doc_id",
        "file_path",
        "file_name",
        "file_type",
        "processor",
        "status",
        "page_count",
        "chunks_created",
        "processing_duration_ms",
        "char_count",
        "estimated_tokens",
        "hash_sha256",
        "batch_id",
        "processed_at",
        "warnings",
        "error",
        "confidence_score"
    ]

    # Write CSV
    with manifest_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for record in records:
            # Extract doc_id from hash if available
            doc_id = record.get("doc_id") or record.get("hash_sha256", "unknown")[:16]

            # Determine status
            if record.get("success"):
                status = "success"
            elif record.get("quarantined"):
                status = "quarantined"
            else:
                status = "failed"

            # Format warnings
            warnings_list = record.get("warnings", [])
            warnings_str = "; ".join(warnings_list) if warnings_list else ""

            row = {
                "doc_id": doc_id,
                "file_path": record.get("file_path", ""),
                "file_name": record.get("file_name", ""),
                "file_type": record.get("file_type", ""),
                "processor": record.get("processor", ""),
                "status": status,
                "page_count": record.get("page_count", ""),  # Empty string for null
                "chunks_created": record.get("chunk_count", 0),
                "processing_duration_ms": record.get("processing_duration_ms", 0),
                "char_count": record.get("char_count", 0),
                "estimated_tokens": record.get("estimated_tokens", 0),
                "hash_sha256": record.get("hash_sha256", ""),
                "batch_id": record.get("batch_id", ""),
                "processed_at": record.get("processed_at", datetime.utcnow().isoformat() + "Z"),
                "warnings": warnings_str,
                "error": record.get("error", ""),
                "confidence_score": record.get("confidence_score", 1.0)
            }

            writer.writerow(row)


def write_success_marker(
    output_path: Path,
    metadata: Dict
) -> None:
    """
    Write _SUCCESS marker file with processing metadata.

    Args:
        output_path: Path to output file (marker will be named {output_path}_SUCCESS)
        metadata: Metadata dictionary to include in marker

    Marker format (JSON):
    {
        "timestamp": "2025-10-29T03:00:00Z",
        "file_hash": "abc123...",
        "chunks": 42,
        "processor": "docling",
        "processing_duration_ms": 1234,
        "config_version": "2.2.0"
    }
    """
    marker_path = output_path.parent / f"{output_path.stem}_SUCCESS"

    marker_data = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "file_path": str(output_path.resolve()),
        **metadata
    }

    marker_path.write_text(json.dumps(marker_data, indent=2), encoding="utf-8")


def check_success_marker(output_path: Path) -> bool:
    """
    Check if _SUCCESS marker exists for a file.

    Args:
        output_path: Path to output file

    Returns:
        True if marker exists, False otherwise
    """
    marker_path = output_path.parent / f"{output_path.stem}_SUCCESS"
    return marker_path.exists()


def read_success_marker(output_path: Path) -> Optional[Dict]:
    """
    Read _SUCCESS marker metadata.

    Args:
        output_path: Path to output file

    Returns:
        Metadata dictionary or None if marker doesn't exist
    """
    marker_path = output_path.parent / f"{output_path.stem}_SUCCESS"

    if not marker_path.exists():
        return None

    try:
        return json.loads(marker_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def generate_batch_summary(
    manifest_path: Path
) -> Dict:
    """
    Generate summary statistics from batch manifest CSV.

    Args:
        manifest_path: Path to manifest CSV

    Returns:
        Summary dictionary with batch statistics
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    # Load manifest
    with manifest_path.open("r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        records = list(reader)

    if not records:
        return {
            "total_files": 0,
            "successful": 0,
            "failed": 0,
            "quarantined": 0,
            "total_chunks": 0,
            "total_processing_time_ms": 0,
            "file_types": {},
            "processors": {}
        }

    # Compute statistics
    total_files = len(records)
    successful = sum(1 for r in records if r["status"] == "success")
    failed = sum(1 for r in records if r["status"] == "failed")
    quarantined = sum(1 for r in records if r["status"] == "quarantined")

    total_chunks = sum(int(r["chunks_created"]) for r in records if r["chunks_created"])
    total_time = sum(int(r["processing_duration_ms"]) for r in records if r["processing_duration_ms"])

    # Count by file type
    file_types = {}
    for record in records:
        ft = record["file_type"]
        file_types[ft] = file_types.get(ft, 0) + 1

    # Count by processor
    processors = {}
    for record in records:
        proc = record["processor"]
        if proc:
            processors[proc] = processors.get(proc, 0) + 1

    return {
        "total_files": total_files,
        "successful": successful,
        "failed": failed,
        "quarantined": quarantined,
        "total_chunks": total_chunks,
        "total_processing_time_ms": total_time,
        "avg_processing_time_ms": total_time // total_files if total_files > 0 else 0,
        "file_types": file_types,
        "processors": processors
    }


def print_batch_summary(summary: Dict) -> None:
    """
    Print human-readable batch summary.

    Args:
        summary: Result from generate_batch_summary()
    """
    print(f"\n📦 Batch Processing Summary")
    print(f"   Total files: {summary['total_files']}")
    print(f"   Successful: {summary['successful']}")
    print(f"   Failed: {summary['failed']}")
    print(f"   Quarantined: {summary['quarantined']}")
    print(f"   Total chunks: {summary['total_chunks']}")
    print(f"   Total time: {summary['total_processing_time_ms']/1000:.1f}s")
    print(f"   Avg time/file: {summary['avg_processing_time_ms']/1000:.1f}s")

    if summary['file_types']:
        print(f"\n   File types processed:")
        for ft, count in sorted(summary['file_types'].items()):
            print(f"      {ft.upper()}: {count}")

    if summary['processors']:
        print(f"\n   Processors used:")
        for proc, count in sorted(summary['processors'].items()):
            print(f"      {proc}: {count}")
