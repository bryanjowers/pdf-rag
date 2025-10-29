#!/usr/bin/env python3
"""
utils_quarantine.py - File quarantine and error handling

Manages failed files with retry logic and quarantine CSV tracking.
Implements "fail closed, never silent" from PRD North Stars.
"""

import csv
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def quarantine_file(
    file_path: Path,
    quarantine_dir: Path,
    error_message: str,
    retry_count: int = 0,
    processor_attempted: Optional[str] = None
) -> Path:
    """
    Move file to quarantine directory and log error.

    Args:
        file_path: Original file path
        quarantine_dir: Quarantine directory
        error_message: Error description
        retry_count: Number of retry attempts made
        processor_attempted: Processor that failed

    Returns:
        Path to quarantined file

    Raises:
        OSError: If file cannot be quarantined
    """
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    # Create quarantine subdirectory with timestamp
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    quarantine_subdir = quarantine_dir / timestamp
    quarantine_subdir.mkdir(exist_ok=True)

    # Copy file to quarantine (don't move, preserve original)
    dest_path = quarantine_subdir / file_path.name

    try:
        shutil.copy2(file_path, dest_path)
        print(f"   🔒 Quarantined: {file_path.name} → {quarantine_subdir.name}/")
    except Exception as e:
        print(f"   ⚠️  Failed to quarantine {file_path.name}: {e}")
        raise

    # Write error log alongside file
    error_log = quarantine_subdir / f"{file_path.stem}_error.txt"
    error_log.write_text(
        f"File: {file_path}\n"
        f"Quarantined: {datetime.utcnow().isoformat()}Z\n"
        f"Processor: {processor_attempted or 'unknown'}\n"
        f"Retry Count: {retry_count}\n"
        f"Error:\n{error_message}\n",
        encoding="utf-8"
    )

    return dest_path


def write_quarantine_csv(
    quarantine_csv_path: Path,
    records: List[Dict]
) -> None:
    """
    Write or append to quarantine CSV log.

    Args:
        quarantine_csv_path: Path to quarantine.csv
        records: List of quarantine record dicts

    CSV Schema:
        file_path, file_name, file_type, attempted_processor,
        error_message, retry_count, quarantined_at, quarantine_location
    """
    quarantine_csv_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if file exists to determine if we need header
    write_header = not quarantine_csv_path.exists()

    fieldnames = [
        "file_path",
        "file_name",
        "file_type",
        "attempted_processor",
        "error_message",
        "retry_count",
        "quarantined_at",
        "quarantine_location"
    ]

    with quarantine_csv_path.open("a", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        if write_header:
            writer.writeheader()

        for record in records:
            writer.writerow({
                "file_path": record.get("file_path", ""),
                "file_name": record.get("file_name", ""),
                "file_type": record.get("file_type", ""),
                "attempted_processor": record.get("attempted_processor", ""),
                "error_message": record.get("error_message", "")[:500],  # Truncate long errors
                "retry_count": record.get("retry_count", 0),
                "quarantined_at": record.get("quarantined_at", datetime.utcnow().isoformat() + "Z"),
                "quarantine_location": record.get("quarantine_location", "")
            })


def should_retry(
    error: Exception,
    retry_count: int,
    max_retries: int = 2
) -> bool:
    """
    Determine if processing should be retried based on error type.

    Transient errors (network, timeout) → retry
    Permanent errors (file corrupt, unsupported) → quarantine

    Args:
        error: Exception that occurred
        retry_count: Current retry count
        max_retries: Maximum retries allowed

    Returns:
        True if should retry, False if should quarantine
    """
    if retry_count >= max_retries:
        return False

    # Classify error as transient or permanent
    error_str = str(error).lower()

    # Transient errors - worth retrying
    transient_keywords = [
        "timeout",
        "connection",
        "network",
        "temporary",
        "busy",
        "locked",
        "unavailable"
    ]

    # Permanent errors - don't retry
    permanent_keywords = [
        "corrupted",
        "invalid",
        "unsupported",
        "not found",
        "permission denied",
        "out of memory"
    ]

    # Check for transient errors
    for keyword in transient_keywords:
        if keyword in error_str:
            return True

    # Check for permanent errors
    for keyword in permanent_keywords:
        if keyword in error_str:
            return False

    # Default: retry once for unknown errors
    return retry_count == 0


def load_quarantine_log(quarantine_csv_path: Path) -> List[Dict]:
    """
    Load quarantine log CSV.

    Args:
        quarantine_csv_path: Path to quarantine.csv

    Returns:
        List of quarantine records
    """
    if not quarantine_csv_path.exists():
        return []

    with quarantine_csv_path.open("r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        return list(reader)


def get_quarantine_stats(quarantine_csv_path: Path) -> Dict:
    """
    Compute statistics from quarantine log.

    Args:
        quarantine_csv_path: Path to quarantine.csv

    Returns:
        Statistics dictionary
    """
    records = load_quarantine_log(quarantine_csv_path)

    if not records:
        return {
            "total_quarantined": 0,
            "by_file_type": {},
            "by_processor": {},
            "by_error_type": {}
        }

    # Count by file type
    by_file_type = {}
    for record in records:
        ft = record.get("file_type", "unknown")
        by_file_type[ft] = by_file_type.get(ft, 0) + 1

    # Count by processor
    by_processor = {}
    for record in records:
        proc = record.get("attempted_processor", "unknown")
        by_processor[proc] = by_processor.get(proc, 0) + 1

    # Classify errors
    by_error_type = {
        "timeout": 0,
        "corrupted": 0,
        "unsupported": 0,
        "other": 0
    }

    for record in records:
        error_msg = record.get("error_message", "").lower()
        if "timeout" in error_msg or "connection" in error_msg:
            by_error_type["timeout"] += 1
        elif "corrupt" in error_msg or "invalid" in error_msg:
            by_error_type["corrupted"] += 1
        elif "unsupported" in error_msg:
            by_error_type["unsupported"] += 1
        else:
            by_error_type["other"] += 1

    return {
        "total_quarantined": len(records),
        "by_file_type": by_file_type,
        "by_processor": by_processor,
        "by_error_type": by_error_type
    }


def print_quarantine_summary(stats: Dict) -> None:
    """
    Print human-readable quarantine summary.

    Args:
        stats: Result from get_quarantine_stats()
    """
    print(f"\n🔒 Quarantine Summary")
    print(f"   Total quarantined: {stats['total_quarantined']}")

    if stats['by_file_type']:
        print(f"\n   By file type:")
        for ft, count in sorted(stats['by_file_type'].items()):
            print(f"      {ft.upper()}: {count}")

    if stats['by_processor']:
        print(f"\n   By processor:")
        for proc, count in sorted(stats['by_processor'].items()):
            print(f"      {proc}: {count}")

    if stats['by_error_type']:
        print(f"\n   By error type:")
        for error_type, count in sorted(stats['by_error_type'].items()):
            if count > 0:
                print(f"      {error_type}: {count}")
