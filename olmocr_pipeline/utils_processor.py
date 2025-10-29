#!/usr/bin/env python3
"""
utils_processor.py - Unified batch processing orchestrator

Integrates all handlers (PDF digital/scanned, DOCX, XLSX, Images) with
classification, routing, retry logic, and quarantine handling.
"""

import time
from pathlib import Path
from typing import Dict, List

from utils_config import load_config, get_storage_paths
from utils_classify import classify_pdf, validate_file_type, SUPPORTED_EXTENSIONS, compute_file_hash
from utils_quarantine import quarantine_file, should_retry, write_quarantine_csv
from utils_manifest import write_manifest_csv, write_success_marker
from handlers import (
    process_digital_pdf,
    process_scanned_pdf,
    process_docx,
    process_xlsx,
    process_image
)


def process_file_with_retry(
    file_path: Path,
    output_dir: Path,
    config: Dict,
    batch_id: str,
    apply_preprocessing: bool = False
) -> Dict:
    """
    Process single file with automatic retry and quarantine logic.

    Routes to appropriate handler based on file type and PDF classification.
    Retries transient errors up to 2 times.
    Quarantines permanent failures.

    Args:
        file_path: Path to input file
        output_dir: Base output directory
        config: Configuration dictionary
        batch_id: Batch identifier
        apply_preprocessing: Apply preprocessing to scanned PDFs

    Returns:
        Processing result dictionary with metadata
    """
    # Validate file type
    valid, file_type = validate_file_type(file_path, SUPPORTED_EXTENSIONS)

    if not valid:
        return {
            "success": False,
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": "unsupported",
            "processor": None,
            "error": f"Unsupported file type: {file_path.suffix}",
            "quarantined": True
        }

    retry_count = 0
    max_retries = config.get("processors", {}).get("retry_attempts", 2)
    last_error = None

    print(f"\n📄 Processing: {file_path.name}")

    while retry_count <= max_retries:
        try:
            # Route based on file type
            if file_type == "pdf":
                # Classify PDF first
                classification = classify_pdf(file_path, config)

                if not classification["allowed"]:
                    # Rejected (e.g., >200 pages)
                    return {
                        "success": False,
                        "file_path": str(file_path),
                        "file_name": file_path.name,
                        "file_type": "pdf",
                        "processor": None,
                        "error": classification["rejection_reason"],
                        "quarantined": True
                    }

                # Route to digital or scanned handler
                if classification["type"] == "pdf_digital":
                    result = process_digital_pdf(file_path, output_dir, config, batch_id)
                else:  # pdf_scanned
                    result = process_scanned_pdf(
                        file_path, output_dir, config, batch_id,
                        apply_preprocessing=apply_preprocessing
                    )

            elif file_type == "docx":
                result = process_docx(file_path, output_dir, config, batch_id)

            elif file_type in ["xlsx", "csv"]:
                result = process_xlsx(file_path, output_dir, config, batch_id)

            elif file_type in ["jpg", "jpeg", "png", "tif", "tiff"]:
                result = process_image(file_path, output_dir, config, batch_id)

            else:
                raise ValueError(f"Unsupported file type: {file_type}")

            # Add file metadata
            result["file_path"] = str(file_path)
            result["file_name"] = file_path.name
            result["file_type"] = file_type

            # Compute file hash for deduplication (matches inventory hash method)
            file_hash = compute_file_hash(file_path)
            result["hash_sha256"] = file_hash

            # If successful, write success marker
            if result["success"] and result.get("jsonl_path"):
                write_success_marker(
                    result["jsonl_path"],
                    {
                        "file_hash": file_hash,
                        "chunks": result.get("chunk_count", 0),
                        "processor": result.get("processor", ""),
                        "processing_duration_ms": result.get("processing_duration_ms", 0),
                        "config_version": config.get("metadata", {}).get("config_version", "")
                    }
                )

            return result

        except Exception as e:
            last_error = e
            retry_count += 1

            print(f"   ⚠️  Error (attempt {retry_count}/{max_retries + 1}): {e}")

            # Check if should retry
            if retry_count <= max_retries and should_retry(e, retry_count - 1, max_retries):
                print(f"   🔄 Retrying...")
                delay = config.get("processors", {}).get("retry_delay_seconds", 5)
                time.sleep(delay)
            else:
                break

    # All retries exhausted - quarantine
    return {
        "success": False,
        "file_path": str(file_path),
        "file_name": file_path.name,
        "file_type": file_type,
        "processor": None,
        "error": str(last_error),
        "quarantined": True,
        "retry_count": retry_count - 1
    }


def process_batch(
    file_paths: List[Path],
    config: Dict,
    batch_id: str,
    apply_preprocessing: bool = False
) -> Dict:
    """
    Process batch of files with unified handling.

    Args:
        file_paths: List of file paths to process
        config: Configuration dictionary
        batch_id: Batch identifier
        apply_preprocessing: Apply preprocessing to scanned PDFs

    Returns:
        Batch results dictionary:
        {
            "total_files": int,
            "successful": int,
            "failed": int,
            "quarantined": int,
            "results": list[dict],
            "manifest_path": Path,
            "quarantine_csv_path": Path | None
        }
    """
    paths = get_storage_paths(config)
    output_dir = paths["rag_staging"]

    results = []
    quarantine_records = []

    print(f"\n{'='*70}")
    print(f"🚀 Processing Batch: {batch_id}")
    print(f"   Files: {len(file_paths)}")
    print(f"{'='*70}")

    for idx, file_path in enumerate(file_paths, 1):
        print(f"\n[{idx}/{len(file_paths)}]")

        result = process_file_with_retry(
            file_path,
            output_dir,
            config,
            batch_id,
            apply_preprocessing
        )

        results.append(result)

        # Handle quarantine
        if result.get("quarantined"):
            quarantine_dir = paths["quarantine_dir"]
            quarantine_location = quarantine_file(
                file_path,
                quarantine_dir,
                result.get("error", "Unknown error"),
                retry_count=result.get("retry_count", 0),
                processor_attempted=result.get("processor")
            )

            quarantine_records.append({
                "file_path": str(file_path),
                "file_name": file_path.name,
                "file_type": result.get("file_type", "unknown"),
                "attempted_processor": result.get("processor", "unknown"),
                "error_message": result.get("error", ""),
                "retry_count": result.get("retry_count", 0),
                "quarantine_location": str(quarantine_location)
            })

    # Write manifest
    manifest_dir = paths["manifest_dir"]
    manifest_path = manifest_dir / f"manifest_{batch_id}.csv"
    write_manifest_csv(manifest_path, results, config)

    # Write quarantine CSV if any failures
    quarantine_csv_path = None
    if quarantine_records:
        quarantine_csv_path = paths["quarantine_dir"] / "quarantine.csv"
        write_quarantine_csv(quarantine_csv_path, quarantine_records)

    # Compute summary
    successful = sum(1 for r in results if r.get("success"))
    failed = len(results) - successful
    quarantined = len(quarantine_records)

    print(f"\n{'='*70}")
    print(f"📊 Batch Complete: {batch_id}")
    print(f"   Total: {len(results)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Quarantined: {quarantined}")
    print(f"{'='*70}\n")

    return {
        "total_files": len(results),
        "successful": successful,
        "failed": failed,
        "quarantined": quarantined,
        "results": results,
        "manifest_path": manifest_path,
        "quarantine_csv_path": quarantine_csv_path
    }
