#!/usr/bin/env python3
"""
utils_inventory.py - File discovery and inventory management

Recursively discovers files, classifies PDFs, and builds inventory.csv
for batch processing with provenance tracking.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, Optional
from multiprocessing import Pool, cpu_count

from utils_classify import (
    classify_pdf,
    compute_file_hash,
    validate_file_type,
    get_mime_type,
    SUPPORTED_EXTENSIONS
)


def _classify_single_file(args):
    """
    Helper function for parallel classification of a single file.

    Args:
        args: Tuple of (file_path, config, timestamp)

    Returns:
        Inventory record dictionary
    """
    file_path, config, timestamp = args

    try:
        # Basic file info
        valid, file_type = validate_file_type(file_path, SUPPORTED_EXTENSIONS)
        mime_type = get_mime_type(file_path)
        size_bytes = file_path.stat().st_size
        file_hash = compute_file_hash(file_path)

        # Initialize record
        record = {
            "file_path": str(file_path.resolve()),
            "file_name": file_path.name,
            "file_type": file_type,
            "mime_type": mime_type,
            "size_bytes": size_bytes,
            "hash_sha256": file_hash,
            "detected_at": timestamp,
            "total_pages": None,
            "digital_pages": None,
            "percent_digital": None,
            "classification_type": None,
            "classification_confidence": None,
            "classification_reason": None,
            "allowed": None,
            "rejection_reason": None
        }

        # Classify PDFs
        if file_type == "pdf":
            try:
                classification = classify_pdf(file_path, config)
                record.update({
                    "total_pages": classification["total_pages"],
                    "digital_pages": classification["digital_pages"],
                    "percent_digital": f"{classification['percent_digital']:.4f}",
                    "classification_type": classification["type"],
                    "classification_confidence": classification["confidence"],
                    "classification_reason": classification.get("classification_reason"),
                    "allowed": classification["allowed"],
                    "rejection_reason": classification.get("rejection_reason")
                })
            except Exception as e:
                record["rejection_reason"] = f"Classification failed: {e}"
                record["allowed"] = False
        else:
            # Non-PDF files are always allowed
            record["allowed"] = True

        return record

    except Exception as e:
        # Return error record
        return {
            "file_path": str(file_path.resolve()),
            "file_name": file_path.name,
            "file_type": "unknown",
            "mime_type": "unknown",
            "size_bytes": 0,
            "hash_sha256": "",
            "detected_at": timestamp,
            "total_pages": None,
            "digital_pages": None,
            "percent_digital": None,
            "classification_type": None,
            "classification_confidence": None,
            "classification_reason": None,
            "allowed": False,
            "rejection_reason": f"Processing failed: {e}"
        }


def discover_files(
    input_dir: Path,
    sort_by: Literal["name", "mtime", "mtime_desc"] = "name"
) -> List[Path]:
    """
    Recursively discover all supported files in input directory.

    Args:
        input_dir: Directory to search
        sort_by: Sorting strategy
            - "name": Alphabetical by filename
            - "mtime": Oldest first (modification time)
            - "mtime_desc": Newest first (modification time descending)

    Returns:
        List of Path objects for supported files

    Raises:
        FileNotFoundError: If input_dir doesn't exist
        NotADirectoryError: If input_dir is not a directory
    """
    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory not found: {input_dir}")

    if not input_dir.is_dir():
        raise NotADirectoryError(f"Not a directory: {input_dir}")

    # Recursively find all files
    all_files = [f for f in input_dir.rglob("*") if f.is_file()]

    # Filter to supported extensions
    supported_files = []
    for f in all_files:
        valid, _ = validate_file_type(f, SUPPORTED_EXTENSIONS)
        if valid:
            supported_files.append(f)

    # Sort according to strategy
    if sort_by == "name":
        supported_files.sort(key=lambda f: f.name.lower())
    elif sort_by == "mtime":
        supported_files.sort(key=lambda f: f.stat().st_mtime)  # Oldest first
    elif sort_by == "mtime_desc":
        supported_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)  # Newest first

    return supported_files


def build_inventory(
    input_dir: Path,
    config: Dict,
    output_path: Optional[Path] = None,
    sort_by: Literal["name", "mtime", "mtime_desc"] = "name",
    parallel: bool = True
) -> Path:
    """
    Build comprehensive inventory of all input files with classification.

    Args:
        input_dir: Directory to scan
        config: Configuration dictionary
        output_path: Path to write inventory.csv (default: inventory/inventory.csv)
        sort_by: File sorting strategy
        parallel: Use parallel processing for classification (default: True)

    Returns:
        Path to written inventory.csv

    Raises:
        FileNotFoundError: If input_dir doesn't exist
    """
    # Discover files
    files = discover_files(input_dir, sort_by=sort_by)

    if not files:
        print(f"⚠️  No supported files found in {input_dir}")
        return None

    # Default output path
    if output_path is None:
        storage = config.get("storage", {})
        base = Path(storage.get("gcs_mount_base", "/mnt/gcs/legal-ocr-results"))
        inventory_dir = base / storage.get("inventory_dir", "inventory")
        inventory_dir.mkdir(parents=True, exist_ok=True)
        output_path = inventory_dir / "inventory.csv"

    # Build inventory records
    timestamp = datetime.utcnow().isoformat() + "Z"

    print(f"📋 Building inventory for {len(files)} files...")

    if parallel and len(files) > 5:  # Only parallelize if >5 files
        # ⚡ OPTIMIZATION 5: Multiprocessing for parallel classification
        # Testing showed multiprocessing.Pool is 1.24x faster than ThreadPoolExecutor
        num_workers = config.get("classification", {}).get("parallel_workers", 8)
        num_workers = min(num_workers, cpu_count(), len(files))  # Don't exceed CPU count or file count

        print(f"   Using {num_workers} parallel workers...")

        # Prepare args for parallel processing
        args_list = [(f, config, timestamp) for f in files]

        # Process in parallel with progress indicator
        with Pool(processes=num_workers) as pool:
            inventory_records = []
            for idx, record in enumerate(pool.imap(_classify_single_file, args_list), 1):
                inventory_records.append(record)
                if idx % 10 == 0 or idx == len(files):
                    print(f"   Processed {idx}/{len(files)} files...", end="\r")

        print()  # New line after progress

    else:
        # Sequential processing (for small batches or when parallel disabled)
        inventory_records = []
        for idx, file_path in enumerate(files, 1):
            record = _classify_single_file((file_path, config, timestamp))
            inventory_records.append(record)

            # Progress indicator
            if idx % 10 == 0 or idx == len(files):
                print(f"   Processed {idx}/{len(files)} files...", end="\r")

        print()  # New line after progress

    # Write CSV
    if inventory_records:
        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=inventory_records[0].keys())
            writer.writeheader()
            writer.writerows(inventory_records)

        print(f"✅ Inventory written: {output_path}")
        print(f"   Total files: {len(inventory_records)}")
        print(f"   Allowed: {sum(1 for r in inventory_records if r['allowed'])}")
        print(f"   Rejected: {sum(1 for r in inventory_records if not r['allowed'])}")

        return output_path

    return None


def load_inventory(inventory_path: Path) -> List[Dict]:
    """
    Load inventory from CSV file.

    Args:
        inventory_path: Path to inventory.csv

    Returns:
        List of inventory records as dictionaries

    Raises:
        FileNotFoundError: If inventory file doesn't exist
    """
    if not inventory_path.exists():
        raise FileNotFoundError(f"Inventory not found: {inventory_path}")

    with inventory_path.open("r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)


def filter_inventory(
    inventory: List[Dict],
    file_type: Optional[str] = None,
    allowed_only: bool = True,
    classification_type: Optional[str] = None
) -> List[Dict]:
    """
    Filter inventory records by criteria.

    Args:
        inventory: List of inventory records
        file_type: Filter by file type (pdf, docx, xlsx, etc.)
        allowed_only: If True, only return allowed files
        classification_type: For PDFs, filter by classification (pdf_digital, pdf_scanned, rejected)

    Returns:
        Filtered list of inventory records
    """
    filtered = inventory

    if allowed_only:
        filtered = [r for r in filtered if r.get("allowed") == "True"]

    if file_type:
        filtered = [r for r in filtered if r.get("file_type") == file_type]

    if classification_type:
        filtered = [r for r in filtered if r.get("classification_type") == classification_type]

    return filtered


def get_inventory_stats(inventory: List[Dict]) -> Dict:
    """
    Compute summary statistics from inventory.

    Args:
        inventory: List of inventory records

    Returns:
        Dictionary with statistics
    """
    total = len(inventory)
    allowed = sum(1 for r in inventory if r.get("allowed") == "True")
    rejected = total - allowed

    # Count by file type
    file_types = {}
    for record in inventory:
        ft = record.get("file_type", "unknown")
        file_types[ft] = file_types.get(ft, 0) + 1

    # PDF-specific stats
    pdfs = [r for r in inventory if r.get("file_type") == "pdf"]
    digital_pdfs = sum(1 for r in pdfs if r.get("classification_type") == "pdf_digital")
    scanned_pdfs = sum(1 for r in pdfs if r.get("classification_type") == "pdf_scanned")

    return {
        "total_files": total,
        "allowed": allowed,
        "rejected": rejected,
        "file_types": file_types,
        "pdf_digital": digital_pdfs,
        "pdf_scanned": scanned_pdfs
    }


def print_inventory_summary(inventory: List[Dict]) -> None:
    """
    Print human-readable inventory summary.

    Args:
        inventory: List of inventory records
    """
    stats = get_inventory_stats(inventory)

    print(f"\n📊 Inventory Summary")
    print(f"   Total files: {stats['total_files']}")
    print(f"   Allowed: {stats['allowed']}")
    print(f"   Rejected: {stats['rejected']}")
    print(f"\n   File types:")
    for ft, count in sorted(stats['file_types'].items()):
        print(f"      {ft.upper()}: {count}")

    if stats['pdf_digital'] or stats['pdf_scanned']:
        print(f"\n   PDF classification:")
        print(f"      Digital: {stats['pdf_digital']}")
        print(f"      Scanned: {stats['pdf_scanned']}")
    print()
