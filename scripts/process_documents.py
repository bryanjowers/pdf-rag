#!/usr/bin/env python3
"""
process_documents.py — Multi-format document processing router (Phase 2)

Unified entrypoint for processing PDFs (scanned/digital), DOCX, XLSX, and images.
Routes to appropriate handlers based on file type and PDF classification.

Usage:
  # Manual mode
  python process_documents.py path/to/*.pdf --summary
  python process_documents.py path/to/file.docx path/to/file.xlsx --summary

  # Auto mode - discover from GCS bucket
  python process_documents.py --auto --summary
  python process_documents.py --auto --file-types pdf,docx --batch-size 10

  # Watch mode
  python process_documents.py --auto --watch --watch-interval 300

  # Dry run
  python process_documents.py --auto --dry-run
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add olmocr_pipeline directory to path to support relative imports
sys.path.insert(0, str(Path(__file__).parent.parent / "olmocr_pipeline"))

# Local imports - using relative imports from olmocr_pipeline
from utils_config import load_config, print_config_summary, get_storage_paths
from utils_classify import validate_file_type, SUPPORTED_EXTENSIONS, FILE_TYPE_HANDLERS
from utils_inventory import (
    build_inventory,
    load_inventory,
    filter_inventory,
    print_inventory_summary
)
from utils_batch import (
    acquire_process_lock,
    release_process_lock,
    verify_gcs_mount
)


def validate_inputs(paths: List[str], allowed_exts: set[str]) -> List[Path]:
    """
    Validate input paths and return list of valid files.

    Args:
        paths: List of path strings from command line
        allowed_exts: Set of allowed extensions (e.g., {'.pdf', '.docx'})

    Returns:
        List of validated Path objects
    """
    valid_paths = []
    invalid_count = 0

    for p in paths:
        path = Path(p)

        if not path.exists():
            print(f"⚠️  File not found: {p}")
            invalid_count += 1
            continue

        valid, file_type = validate_file_type(path, allowed_exts)
        if not valid:
            print(f"⚠️  Unsupported file type: {p}")
            invalid_count += 1
            continue

        valid_paths.append(path)

    if invalid_count > 0:
        print(f"   Skipped {invalid_count} invalid file(s)\n")

    return valid_paths


def ensure_directories(config: dict) -> None:
    """
    Ensure all required output directories exist.

    Args:
        config: Configuration dictionary
    """
    paths = get_storage_paths(config)

    # Create all output directories
    for key in ['rag_staging', 'html_output', 'markdown_output', 'jsonl_output',
                'log_dir', 'report_dir', 'manifest_dir', 'inventory_dir', 'quarantine_dir']:
        paths[key].mkdir(parents=True, exist_ok=True)


def main() -> None:
    """Main entry point for multi-format document processing."""
    parser = argparse.ArgumentParser(
        description="Process multiple document formats with unified pipeline (Phase 2)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Manual mode
  python process_documents.py sample.pdf sample.docx --summary
  python process_documents.py path/to/*.pdf --batch-size 5

  # Auto mode - discover from input bucket
  python process_documents.py --auto --summary
  python process_documents.py --auto --file-types pdf,docx --limit 20

  # Filter PDFs by classification
  python process_documents.py --auto --file-types pdf --pdf-type scanned --limit 100
  python process_documents.py --auto --file-types pdf --pdf-type digital --limit 100

  # Pipeline separation
  python process_documents.py --auto --ingest-only --file-types pdf --pdf-type scanned
  python process_documents.py --auto --enrich-only --limit 50

  # Watch mode - continuous processing
  python process_documents.py --auto --watch --watch-interval 300

  # Dry run - preview only
  python process_documents.py --auto --dry-run

Supported file types: PDF (scanned/digital), DOCX, XLSX, CSV, JPG, PNG, TIF
        """
    )

    # Input source
    parser.add_argument("files", nargs="*",
                        help="Path(s) to input file(s) - not required with --auto")
    parser.add_argument("--auto", action="store_true",
                        help="Auto-discover files from GCS input bucket")

    # File type filtering
    parser.add_argument("--file-types", type=str, default=None,
                        help="Comma-separated file types to process (e.g., 'pdf,docx,xlsx')")
    parser.add_argument("--pdf-type", type=str, choices=["digital", "scanned"], default=None,
                        help="For PDFs only: filter by type (digital or scanned)")

    # Batch processing
    parser.add_argument("--batch-size", type=int, default=5,
                        help="Number of files to process per batch (default: 5)")
    parser.add_argument("--sort-by", choices=["name", "mtime", "mtime_desc"], default="name",
                        help="Sort order for auto mode")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit total number of files to process")

    # Watch mode
    parser.add_argument("--watch", action="store_true",
                        help="Watch mode: continuously poll for new files (requires --auto)")
    parser.add_argument("--watch-interval", type=int, default=60,
                        help="Seconds between scans in watch mode (default: 60)")

    # Processing options
    parser.add_argument("--summary", action="store_true",
                        help="Generate summary JSON after processing each file")
    parser.add_argument("--preprocess", action="store_true",
                        help="Apply image cleanup before OCR (scanned PDFs only)")
    parser.add_argument("--workers", type=int, default=6,
                        help="Parallel workers for processing (default: 6)")

    # Pipeline separation flags
    parser.add_argument("--ingest-only", action="store_true",
                        help="Ingest only: extract text/markdown but skip entities and embeddings")
    parser.add_argument("--enrich-only", action="store_true",
                        help="Enrich only: process existing markdown files with entities and embeddings")

    # Utility flags
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview files without processing")
    parser.add_argument("--rebuild-inventory", action="store_true",
                        help="Force rebuild inventory even if it exists")
    parser.add_argument("--no-skip-processed", action="store_false", dest="skip_processed",
                        help="Disable skipping of already-processed files")
    parser.add_argument("--reprocess-all", action="store_true",
                        help="Clear all success markers and reprocess all files")
    parser.set_defaults(skip_processed=True)
    parser.add_argument("--reprocess-hash", type=str, metavar="HASH",
                        help="Reprocess specific file by hash (prefix match supported)")

    args = parser.parse_args()

    # Validate arguments
    if args.watch and not args.auto:
        parser.error("--watch requires --auto mode")

    if args.ingest_only and args.enrich_only:
        parser.error("Cannot use both --ingest-only and --enrich-only together")

    if args.pdf_type and (not args.file_types or 'pdf' not in args.file_types.lower()):
        parser.error("--pdf-type requires --file-types to include 'pdf'")

    if not args.auto and not args.files:
        parser.error("Either provide file paths or use --auto")

    if args.auto and args.files:
        print("⚠️  Ignoring manual file arguments when --auto is enabled\n")

    # Load configuration
    try:
        config = load_config()
        print_config_summary(config)
    except Exception as e:
        print(f"❌ Failed to load configuration: {e}")
        return

    # Get storage paths
    paths = get_storage_paths(config)

    # Handle --enrich-only mode (process existing markdown files)
    if args.enrich_only:
        print("🔄 Enrich-only mode: Processing existing markdown files\n")
        import subprocess
        cmd = [
            "python",
            str(Path(__file__).parent / "enrich_from_markdown.py"),
            "--auto"
        ]
        if args.file_types:
            cmd.extend(["--file-types", args.file_types])
        if args.limit:
            cmd.extend(["--limit", str(args.limit)])

        result = subprocess.run(cmd)
        return

    # Acquire single-instance lock
    try:
        lock = acquire_process_lock(paths["lock_file"])
    except Exception as e:
        print(f"❌ Failed to acquire process lock: {e}")
        print(f"   Another instance may be running, or lock file is stale.")
        return

    try:
        start_time = time.time()
        ensure_directories(config)

        # Verify GCS mount health
        verify_gcs_mount(paths["gcs_mount_base"])

        # Handle reprocessing flags
        if args.reprocess_all or args.reprocess_hash:
            from utils_state import clear_processed_state

            if args.reprocess_all:
                print("🔄 Clearing all success markers for reprocessing...\n")
                cleared = clear_processed_state(paths["jsonl_output"])
                print(f"   Cleared {cleared} success marker(s)\n")
            elif args.reprocess_hash:
                print(f"🔄 Clearing success marker for hash {args.reprocess_hash}...\n")
                cleared = clear_processed_state(paths["jsonl_output"], hash_sha256=args.reprocess_hash)
                if cleared > 0:
                    print(f"   Cleared {cleared} success marker(s)\n")
                else:
                    print(f"   ⚠️  No file found with hash starting with '{args.reprocess_hash}'\n")

        # Auto mode: build/load inventory
        if args.auto:
            input_bucket = paths["input_bucket"]
            inventory_path = paths["inventory_dir"] / "inventory.csv"

            # Build or load inventory
            if args.rebuild_inventory or not inventory_path.exists():
                print(f"📋 Building inventory from {input_bucket}...")
                build_inventory(input_bucket, config, output_path=inventory_path, sort_by=args.sort_by)
            else:
                print(f"📋 Loading existing inventory from {inventory_path}")
                print(f"   (Use --rebuild-inventory to force refresh)\n")

            # Load inventory
            inventory = load_inventory(inventory_path)
            print_inventory_summary(inventory)

            # Filter by file types if specified
            if args.file_types:
                requested_types = [ft.strip().lower() for ft in args.file_types.split(',')]
                filtered = []
                for file_type in requested_types:
                    filtered.extend(filter_inventory(inventory, file_type=file_type, allowed_only=True))
                inventory = filtered
                print(f"   Filtered to {len(inventory)} file(s) matching types: {', '.join(requested_types)}\n")
            else:
                # Only allowed files
                inventory = filter_inventory(inventory, allowed_only=True)

            # Filter PDFs by classification type if specified
            if args.pdf_type:
                classification = f"pdf_{args.pdf_type}"  # Convert "digital" -> "pdf_digital"
                inventory = filter_inventory(inventory, classification_type=classification)
                print(f"   Filtered to {len(inventory)} {args.pdf_type} PDF(s)\n")

            # Filter out already-processed files (unless disabled)
            if args.skip_processed and not args.reprocess_all:
                from utils_state import get_processed_hashes, filter_unprocessed_files

                processed_hashes = get_processed_hashes(
                    jsonl_dir=paths["jsonl_output"],
                    use_cache=True,
                    cache_path=paths["gcs_mount_base"] / "state" / "processed_hashes.json"
                )

                original_count = len(inventory)
                inventory = filter_unprocessed_files(inventory, processed_hashes)

                if original_count > len(inventory):
                    skipped_count = original_count - len(inventory)
                    print(f"   Skipping {skipped_count} already-processed file(s)")
                    print(f"   Remaining unprocessed: {len(inventory)}\n")

            # Extract file paths
            file_paths = [Path(record["file_path"]) for record in inventory]

        else:
            # Manual mode: validate provided paths
            print("📋 Validating input files...")
            file_paths = validate_inputs(args.files, SUPPORTED_EXTENSIONS)

        # Apply limit
        if args.limit:
            file_paths = file_paths[:args.limit]
            print(f"   Limited to first {args.limit} file(s)")

        if not file_paths:
            print("❌ No valid files to process. Exiting.")
            return

        print(f"   Found {len(file_paths)} valid file(s) to process\n")

        # Dry run mode
        if args.dry_run:
            print("🔍 DRY RUN MODE - No processing will occur\n")
            print("="*70)
            for i, file_path in enumerate(file_paths, 1):
                valid, file_type = validate_file_type(file_path, SUPPORTED_EXTENSIONS)
                handler = FILE_TYPE_HANDLERS.get(file_type, "unknown")
                print(f"[{i}/{len(file_paths)}] {file_path.name}")
                print(f"   Type: {file_type.upper():<6} | Handler: {handler}")
            print("="*70)
            print(f"\nTotal files: {len(file_paths)}")
            print(f"Batches ({args.batch_size} files each): {(len(file_paths) + args.batch_size - 1) // args.batch_size}")
            return

        # TODO: Implement watch mode
        if args.watch:
            print("⚠️  Watch mode not yet implemented (deferred to production)")
            return

        # Process files using unified batch processor
        from utils_processor import process_batch
        from utils_batch import generate_batch_id

        batch_id = generate_batch_id()

        # Process batch
        batch_result = process_batch(
            file_paths,
            config,
            batch_id,
            apply_preprocessing=args.preprocess,
            skip_enrichment=args.ingest_only
        )

        # Print summary
        from utils_manifest import generate_batch_summary, print_batch_summary
        summary = generate_batch_summary(batch_result["manifest_path"])
        print_batch_summary(summary)

        # Print quarantine summary if any
        if batch_result.get("quarantine_csv_path"):
            from utils_quarantine import get_quarantine_stats, print_quarantine_summary
            quar_stats = get_quarantine_stats(batch_result["quarantine_csv_path"])
            print_quarantine_summary(quar_stats)

        elapsed = time.time() - start_time
        print(f"\n⏱️  Total elapsed: {elapsed:.1f}s")

    finally:
        # Release lock
        release_process_lock(lock)


if __name__ == "__main__":
    main()
