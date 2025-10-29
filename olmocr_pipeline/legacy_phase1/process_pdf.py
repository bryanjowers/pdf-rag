#!/usr/bin/env python3
"""
process_pdf.py — LEGACY Phase 1 OlmOCR-2 pipeline (DEPRECATED)

⚠️  DEPRECATION NOTICE:
    This script is from Phase 1 and processes ONLY scanned PDFs using OlmOCR-2.
    For Phase 2+ (multi-format support), use process_documents.py instead:

    NEW: python process_documents.py --auto --batch-size 10
    OLD: python process_pdf.py --auto --batch-size 5

    Phase 2 supports: PDF (digital/scanned), DOCX, XLSX, images
    Phase 1 supports: PDF (scanned only)

This script is kept for backwards compatibility and specific Phase 1 use cases:
  - --merge flag (combine per-page JSONL → single HTML/MD)
  - Direct OlmOCR-2 CLI invocation for debugging

Usage (Legacy):
  python process_pdf.py app/samples/*.pdf --summary
  python process_pdf.py app/samples/*.pdf --preprocess --summary
  python process_pdf.py app/samples/*.pdf --merge
"""

import argparse
import hashlib
import inspect
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Local imports
from qa_summary import summarize_output
from utils_preprocess import preprocess_pdf
from utils_batch import (
    acquire_process_lock,
    release_process_lock,
    verify_gcs_mount,
    discover_pdfs,
    generate_batch_id,
    relocate_outputs_batch
)

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------

GCS_MOUNT_BASE = Path("/mnt/gcs/legal-ocr-results")
GCS_INPUT_BUCKET = Path("/mnt/gcs/legal-ocr-pdf-input")

RAG_STAGING_DIR = GCS_MOUNT_BASE / "rag_staging"
HTML_OUTPUT_DIR = RAG_STAGING_DIR / "html"
MARKDOWN_OUTPUT_DIR = RAG_STAGING_DIR / "markdown"
LOG_DIR = GCS_MOUNT_BASE / "logs"
REPORT_DIR = GCS_MOUNT_BASE / "reports"

LOCK_FILE = GCS_MOUNT_BASE / ".process_pdf.lock"

MODEL_ID = "allenai/olmOCR-2-7B-1025-FP8"  # intentionally hardcoded
TARGET_IMAGE_DIM = "1288"  # Optimized for L4 GPUs
GPU_MEMORY_UTIL = "0.8"    # 80% utilization for stability
DEFAULT_WORKERS = 6
DEFAULT_BATCH_SIZE = 5
DEFAULT_WATCH_INTERVAL = 60  # seconds


# ---------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------
def ensure_dirs() -> None:
    """Ensure required directories exist on GCS mount."""
    for d in [RAG_STAGING_DIR, HTML_OUTPUT_DIR, MARKDOWN_OUTPUT_DIR, LOG_DIR, REPORT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


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


def run_olmocr_batch(pdf_paths: list[Path], workers: int, log_file: Path) -> None:
    """
    Run the OlmOCR CLI pipeline ONCE over all PDFs with dual (HTML + Markdown) output.
    Streams stdout live and persists to log_file.
    
    Args:
        pdf_paths: List of PDF file paths to process
        workers: Number of parallel workers
        log_file: Path to write log output
        
    Raises:
        subprocess.CalledProcessError: If OlmOCR pipeline fails
        ImportError: If OlmOCR module cannot be found
    """
    pdf_path_strings = [str(p.resolve()) for p in pdf_paths]
    
    # Dynamically determine the correct module path
    try:
        module_path = get_olmocr_module()
    except ImportError as e:
        print(f"❌ {e}")
        raise

    command = [
        sys.executable,
        "-m", module_path,
        str(RAG_STAGING_DIR),
        "--markdown",
        "--model", MODEL_ID,
        "--workers", str(workers),
        "--target_longest_image_dim", TARGET_IMAGE_DIM,
        "--gpu-memory-utilization", GPU_MEMORY_UTIL,
        "--pdfs", *pdf_path_strings
    ]

    print(f"🚀 Starting OlmOCR batch for {len(pdf_paths)} document(s)...")
    print(f"   Module: {module_path}")
    print(f"   Workspace: {RAG_STAGING_DIR.resolve()}")
    print(f"   Log file: {log_file}\n")

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
            
            # Wait for process to complete
            proc.wait()
            
            # Check return code within context
            if proc.returncode != 0:
                print(f"\n⚠️  OlmOCR pipeline FAILED with exit code {proc.returncode}")
                print(f"   Check the log file for details: {log_file}")
                print(f"   Common issues: GPU memory, invalid PDF, missing dependencies")
                raise subprocess.CalledProcessError(proc.returncode, command)

    print("✅ OlmOCR batch completed successfully.\n")


def get_output_paths(pdf_path: Path) -> tuple[Path, Path]:
    """
    Compute expected .html and .md paths for a given PDF.
    OlmOCR preserves original PDF filenames in outputs, so we do the same.
    """
    # Use original PDF filename stem (OlmOCR preserves it)
    stem = pdf_path.stem

    html_path = HTML_OUTPUT_DIR / f"{stem}.html"
    md_path   = MARKDOWN_OUTPUT_DIR / f"{stem}.md"
    return html_path, md_path



def summarize_with_mode(pdf_path: Path, output_path: Path, start_time: float):
    """
    Call summarize_output() with auto-detected mode (html/markdown).
    Uses introspection to check if the function accepts 'mode' parameter.
    
    Args:
        pdf_path: Original PDF file path
        output_path: Path to OCR output file
        start_time: Start time for elapsed calculation
        
    Returns:
        Summary dictionary from summarize_output()
    """
    mode = "html" if output_path.suffix.lower() == ".html" else "markdown"
    
    # Use introspection to check if 'mode' parameter is supported
    sig = inspect.signature(summarize_output)
    if 'mode' in sig.parameters:
        return summarize_output(pdf_path, output_path, start_time, mode=mode)
    else:
        # Fall back to older signature without mode support
        return summarize_output(pdf_path, output_path, start_time)


def validate_pdf_inputs(paths: list[str]) -> list[Path]:
    """
    Validate input paths and return list of valid PDF files.
    
    Args:
        paths: List of path strings from command line
        
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
            
        if path.suffix.lower() != '.pdf':
            print(f"⚠️  Not a PDF file: {p}")
            invalid_count += 1
            continue
            
        valid_paths.append(path)
    
    if invalid_count > 0:
        print(f"   Skipped {invalid_count} invalid file(s)\n")
    
    return valid_paths


# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main() -> None:
    """Main entry point for the PDF processing pipeline."""
    parser = argparse.ArgumentParser(
        description="Run OlmOCR-2 on PDFs with auto-discovery and batch processing.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Manual mode (original behavior)
  python process_pdf.py path/to/*.pdf --summary

  # Auto mode - discover and process all PDFs from GCS bucket
  python process_pdf.py --auto --summary

  # Auto mode with custom batch size
  python process_pdf.py --auto --batch-size 10 --workers 4

  # Watch mode - poll for new files every 5 minutes
  python process_pdf.py --auto --watch --watch-interval 300

  # Dry run - preview what would be processed
  python process_pdf.py --auto --dry-run --sort-by mtime_desc

  # Process with preprocessing and merge at end
  python process_pdf.py --auto --preprocess --merge --summary

  # Limit processing to first 20 PDFs
  python process_pdf.py --auto --limit 20 --batch-size 5

Note: This script runs on a headless VM - browser QA features have been removed.
      Review outputs manually in the markdown/html directories after processing.
        """
    )

    # Input source
    parser.add_argument("pdfs", nargs="*",
                        help="Path(s) to input PDF(s) - not required with --auto")
    parser.add_argument("--auto", action="store_true",
                        help=f"Auto-discover PDFs from GCS input bucket ({GCS_INPUT_BUCKET})")

    # Batch processing
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
                        help=f"Number of PDFs to process per batch (default: {DEFAULT_BATCH_SIZE})")
    parser.add_argument("--sort-by", choices=["name", "mtime", "mtime_desc"], default="name",
                        help="Sort order for auto mode: name (alphabetical), mtime (oldest first), mtime_desc (newest first)")

    # Watch mode
    parser.add_argument("--watch", action="store_true",
                        help="Watch mode: continuously poll for new PDFs (requires --auto)")
    parser.add_argument("--watch-interval", type=int, default=DEFAULT_WATCH_INTERVAL,
                        help=f"Seconds between scans in watch mode (default: {DEFAULT_WATCH_INTERVAL})")

    # Utility flags
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview PDFs that would be processed without running OCR")

    # Processing options
    parser.add_argument("--preprocess", action="store_true",
                        help="Apply image cleanup before OCR")
    parser.add_argument("--summary", action="store_true",
                        help="Generate summary JSON after processing each PDF")
    parser.add_argument("--merge", action="store_true",
                        help="After all processing, merge JSONL outputs into combined HTML/Markdown")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit total number of PDFs to process (applied before batching)")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"Parallel workers for OlmOCR CLI (default: {DEFAULT_WORKERS})")

    args = parser.parse_args()

    # ⚠️ DEPRECATION WARNING
    print("=" * 70)
    print("⚠️  DEPRECATION WARNING: This is a Phase 1 legacy script")
    print("   For Phase 2+ multi-format support, use process_documents.py instead:")
    print("   python olmocr_pipeline/process_documents.py --auto --batch-size 10")
    print("=" * 70)
    print()

    # Validate arguments
    if args.watch and not args.auto:
        parser.error("--watch requires --auto mode")

    if not args.auto and not args.pdfs:
        parser.error("Either provide PDF paths or use --auto")

    if args.auto and args.pdfs:
        print("⚠️  Ignoring manual PDF arguments when --auto is enabled\n")

    # Acquire single-instance lock
    lock = acquire_process_lock(LOCK_FILE)

    try:
        t0 = time.time()
        ensure_dirs()

        # Verify GCS mount health
        verify_gcs_mount(GCS_MOUNT_BASE)

        # Discover or validate PDFs
        if args.auto:
            print(f"📋 Auto-discovering PDFs from {GCS_INPUT_BUCKET}")
            print(f"   Sort order: {args.sort_by}\n")
            try:
                pdf_paths = discover_pdfs(GCS_INPUT_BUCKET, args.sort_by)
            except (FileNotFoundError, NotADirectoryError) as e:
                print(f"❌ {e}")
                return
        else:
            print("📋 Validating input files...")
            pdf_paths = validate_pdf_inputs(args.pdfs)

        # Apply limit
        if args.limit:
            pdf_paths = pdf_paths[:args.limit]
            print(f"   Limited to first {args.limit} file(s)")

        if not pdf_paths:
            print("❌ No valid PDF files to process. Exiting.")
            return

        print(f"   Found {len(pdf_paths)} valid PDF(s)\n")

        # Dry run mode
        if args.dry_run:
            print("🔍 DRY RUN MODE - No processing will occur\n")
            for i, pdf in enumerate(pdf_paths, 1):
                print(f"[{i}/{len(pdf_paths)}] Would process: {pdf.name}")
            print(f"\nTotal files: {len(pdf_paths)}")
            print(f"Batches ({args.batch_size} PDFs each): {(len(pdf_paths) + args.batch_size - 1) // args.batch_size}")
            return

        # Watch mode
        if args.watch:
            watch_mode_loop(args, t0)
            return

        # Single run mode (auto or manual)
        process_all_pdfs(pdf_paths, args, t0)

    finally:
        # Release lock
        release_process_lock(lock)


def watch_mode_loop(args, start_time: float) -> None:
    """
    Watch mode: continuously poll for new PDFs and process them.
    """
    print(f"👁️  WATCH MODE: Monitoring {GCS_INPUT_BUCKET}")
    print(f"   Interval: {args.watch_interval}s")
    print(f"   Press Ctrl-C to stop\n")

    cycle_count = 0

    while True:
        try:
            cycle_count += 1
            print(f"\n{'='*60}")
            print(f"🔄 Watch Cycle #{cycle_count}")
            print(f"{'='*60}\n")

            # Verify mount health before each cycle
            verify_gcs_mount(GCS_MOUNT_BASE)

            # Discover PDFs
            try:
                pdf_paths = discover_pdfs(GCS_INPUT_BUCKET, args.sort_by)
            except (FileNotFoundError, NotADirectoryError) as e:
                print(f"⚠️  {e}")
                print(f"   Waiting {args.watch_interval}s before retry...")
                time.sleep(args.watch_interval)
                continue

            # Apply limit
            if args.limit:
                pdf_paths = pdf_paths[:args.limit]

            if pdf_paths:
                print(f"🔔 Found {len(pdf_paths)} PDF(s) - starting processing...")
                process_all_pdfs(pdf_paths, args, start_time)
                print(f"\n✅ Cycle #{cycle_count} complete")
            else:
                print("   No PDFs found")

            # Wait for next cycle
            print(f"\n⏸️  Waiting {args.watch_interval}s until next scan...")
            time.sleep(args.watch_interval)

        except KeyboardInterrupt:
            print("\n\n🛑 Watch mode stopped by user")
            break
        except Exception as e:
            print(f"\n⚠️  Error in watch cycle: {e}")
            print(f"   Waiting {args.watch_interval}s before retry...")
            time.sleep(args.watch_interval)


def process_all_pdfs(pdf_paths: list[Path], args, start_time: float) -> None:
    """
    Process all PDFs in batches.
    """
    print(f"\n{'='*60}")
    print(f"🚀 Starting {'AUTO' if args.auto else 'MANUAL'} processing mode")
    print(f"   Total files: {len(pdf_paths)}")
    print(f"   Batch size: {args.batch_size}")
    print(f"{'='*60}\n")

    # Preprocessing (if requested)
    processed_paths: list[Path] = []
    failed_preprocessing: list[tuple[Path, str]] = []

    if args.preprocess:
        print("--- 🧹 Preprocessing Step ---")
        for p in pdf_paths:
            try:
                outp = preprocess_pdf(p)
                if outp.suffix.lower() != ".pdf":
                    raise RuntimeError(
                        f"Preprocessing output must be a .pdf file, got {outp.name}"
                    )
                processed_paths.append(outp)
                print(f"   ✅ {p.name} → {outp.name}")
            except Exception as e:
                print(f"   ⚠️  Error preprocessing {p.name}: {e}")
                failed_preprocessing.append((p, str(e)))
        
        if failed_preprocessing:
            print(f"\n⚠️  {len(failed_preprocessing)} file(s) failed preprocessing:")
            for failed_path, error in failed_preprocessing:
                print(f"   - {failed_path.name}: {error}")
        
        print("--- ✅ Preprocessing Done ---\n")
    else:
        processed_paths = pdf_paths

    if not processed_paths:
        print("❌ No PDFs to process after preprocessing. Exiting.")
        return

    # Split into batches
    total_batches = (len(processed_paths) + args.batch_size - 1) // args.batch_size
    successful_batches = 0
    failed_batches = []
    total_processed = 0
    total_summary_errors = 0
    total_missing_outputs = 0

    for batch_num in range(total_batches):
        batch_start = batch_num * args.batch_size
        batch_end = min(batch_start + args.batch_size, len(processed_paths))
        batch = processed_paths[batch_start:batch_end]

        print(f"\n{'='*60}")
        print(f"📦 Batch {batch_num + 1}/{total_batches}: {len(batch)} PDFs")
        print(f"{'='*60}\n")

        # Verify GCS mount health before each batch
        verify_gcs_mount(GCS_MOUNT_BASE)

        try:
            # Run OlmOCR on batch
            batch_id = generate_batch_id()
            log_file = LOG_DIR / f"olmocr_batch{batch_num + 1}_{len(batch)}files_{batch_id}.log"

            print(f"🚀 Running OlmOCR on batch {batch_num + 1}...")
            run_olmocr_batch(batch, workers=args.workers, log_file=log_file)

            # Relocate outputs
            print("\n--- 🧩 Normalizing OlmOCR outputs ---")
            stats = relocate_outputs_batch(
                batch,
                MARKDOWN_OUTPUT_DIR,
                RAG_STAGING_DIR / "results",
                RAG_STAGING_DIR / "jsonl"
            )

            # Post-processing: summaries
            if args.summary:
                print("\n--- 📈 Generating Summaries ---")
                for pdf_path in batch:
                    html_path, md_path = get_output_paths(pdf_path)
                    have_any = html_path.exists() or md_path.exists()

                    if not have_any:
                        print(f"   ⚠️  No output found for {pdf_path.name}")
                        total_missing_outputs += 1
                        continue

                    total_processed += 1

                    try:
                        out_for_summary = md_path if md_path.exists() else html_path
                        summary = summarize_with_mode(pdf_path, out_for_summary, start_time)
                        summary_file = LOG_DIR / f"{pdf_path.stem}_summary.json"
                        summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
                        print(f"   ✅ {pdf_path.name} → {summary_file.name}")
                    except Exception as e:
                        print(f"   ⚠️  Error summarizing {pdf_path.name}: {e}")
                        total_summary_errors += 1
            else:
                # Just count processed files
                for pdf_path in batch:
                    html_path, md_path = get_output_paths(pdf_path)
                    if html_path.exists() or md_path.exists():
                        total_processed += 1
                    else:
                        total_missing_outputs += 1

            successful_batches += 1
            print(f"\n✅ Batch {batch_num + 1} complete")

        except KeyboardInterrupt:
            print("\n\n🛑 Interrupted by user - stopping gracefully")
            break
        except subprocess.CalledProcessError as e:
            print(f"\n❌ OlmOCR failed for batch {batch_num + 1}")
            print(f"   Log file: {log_file}")
            failed_batches.append((batch_num + 1, "OlmOCR error"))
        except Exception as e:
            print(f"\n❌ Unexpected error in batch {batch_num + 1}: {e}")
            failed_batches.append((batch_num + 1, str(e)))

    # Optional JSONL merge at end
    if args.merge:
        print(f"\n{'='*60}")
        print("--- 🧩 Merging all JSONL outputs ---")
        print(f"{'='*60}\n")
        try:
            # Get all JSONL files explicitly
            jsonl_dir = RAG_STAGING_DIR / "jsonl"
            jsonl_files = list(jsonl_dir.glob("*.jsonl"))

            if not jsonl_files:
                print("⚠️  No JSONL files found to merge")
            else:
                cmd = [
                    sys.executable,
                    "olmocr_pipeline/utils/combine_olmocr_outputs.py"
                ] + [str(f) for f in jsonl_files] + ["--html", "--md"]

                subprocess.run(cmd, check=False)
                print("✅ Merge complete")
        except Exception as e:
            print(f"⚠️  Merge failed: {e}")

    # Footer with statistics
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print("🎯 Processing Complete")
    print(f"{'='*60}")
    print(f"📦 Batches: {successful_batches}/{total_batches} successful")
    print(f"✅ Documents processed: {total_processed}/{len(processed_paths)}")

    if failed_batches:
        print(f"\n❌ Failed batches: {len(failed_batches)}")
        for batch_num, error in failed_batches:
            print(f"   Batch {batch_num}: {error}")

    if total_missing_outputs > 0:
        print(f"⚠️  Missing outputs: {total_missing_outputs}")
    if total_summary_errors > 0:
        print(f"⚠️  Summary errors: {total_summary_errors}")
    if failed_preprocessing:
        print(f"⚠️  Preprocessing failures: {len(failed_preprocessing)}")

    print(f"\n📁 Output locations:")
    print(f"   HTML:     {HTML_OUTPUT_DIR.resolve()}")
    print(f"   Markdown: {MARKDOWN_OUTPUT_DIR.resolve()}")
    print(f"   Logs:     {LOG_DIR.resolve()}")
    print(f"\n⏱️  Total elapsed: {elapsed:.1f}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()