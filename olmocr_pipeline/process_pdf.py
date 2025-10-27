#!/usr/bin/env python3
"""
process_pdf.py — Modernized OlmOCR-2 + QA pipeline (Milestone #2)
Runs the OlmOCR CLI once for batch processing with both HTML and Markdown output.
Optimized for NVIDIA L4 GPUs and browser-based QA.

Usage:
  python process_pdf.py app/samples/*.pdf --summary
  python process_pdf.py app/samples/*.pdf --preprocess --summary
  python process_pdf.py app/samples/*.pdf --qa
"""

import argparse
import hashlib
import inspect
import json
import os
import subprocess
import sys
import time
import urllib.parse
import webbrowser
from datetime import datetime
from pathlib import Path

# Local imports
from qa_summary import summarize_output
from utils_preprocess import preprocess_pdf

# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------
RAG_STAGING_DIR = Path("rag_staging")
HTML_OUTPUT_DIR = RAG_STAGING_DIR / "html"
MARKDOWN_OUTPUT_DIR = RAG_STAGING_DIR / "markdown"
LOG_DIR = Path("olmocr_pipeline/data/logs")
MODEL_ID = "allenai/olmOCR-2-7B-1025-FP8"  # intentionally hardcoded

# GPU and processing parameters
TARGET_IMAGE_DIM = "1288"  # Optimized for L4 GPUs
GPU_MEMORY_UTIL = "0.8"    # 80% utilization for stability
DEFAULT_WORKERS = 8


# ---------------------------------------------------------------------
# UTILITIES
# ---------------------------------------------------------------------
def ensure_dirs() -> None:
    """Ensure required directories exist before processing."""
    for d in [RAG_STAGING_DIR, HTML_OUTPUT_DIR, MARKDOWN_OUTPUT_DIR, LOG_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def _safe_file_url(path: Path) -> str:
    """Return a file:// URL that is safe for non-ASCII paths."""
    p = path.resolve()
    return "file://" + urllib.parse.quote(str(p))


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
        "--html", "--markdown",
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
    Mirrors relative structure when possible; otherwise creates a collision-safe fallback name.
    
    Args:
        pdf_path: Input PDF file path
        
    Returns:
        Tuple of (html_path, markdown_path)
    """
    try:
        rel_path = pdf_path.resolve().relative_to(Path.cwd())
    except ValueError:
        # Fallback: create unique filename using hash to prevent collisions
        path_str = str(pdf_path.resolve())
        path_hash = hashlib.md5(path_str.encode()).hexdigest()[:8]
        safe_name = f"{pdf_path.stem}_{path_hash}"
        rel_path = Path(safe_name)
    
    html_path = (HTML_OUTPUT_DIR / rel_path).with_suffix(".html")
    md_path = (MARKDOWN_OUTPUT_DIR / rel_path).with_suffix(".md")
    return html_path, md_path


def open_for_qa(html_path: Path, md_path: Path, qa_mode: str, qa_pages: int) -> None:
    """
    Open output files in browser for quality assurance.
    
    QA modes:
      - 'full': open HTML in browser (best visual fidelity; heavier on huge docs)
      - 'light': open Markdown in browser (faster load; good for spot-checks)
      
    Args:
        html_path: Path to HTML output
        md_path: Path to Markdown output
        qa_mode: Either 'full' or 'light'
        qa_pages: Page hint for light mode (informational only)
    """
    target_path = None
    mode_desc = ""
    
    if qa_mode == "full" and html_path.exists():
        target_path = html_path
        mode_desc = "HTML (full)"
    elif qa_mode == "light" and md_path.exists():
        target_path = md_path
        mode_desc = f"Markdown (light, first {qa_pages} pages implied)"
    else:
        # Fallback: open whatever is available
        target_path = html_path if html_path.exists() else md_path
        if target_path and target_path.exists():
            mode_desc = f"{target_path.suffix[1:].upper()} (available)"
    
    if target_path and target_path.exists():
        print(f"🔍 Opening {mode_desc}: {target_path.name}")
        url = _safe_file_url(target_path)
        
        try:
            success = webbrowser.open(url)
            if not success:
                print(f"   ⚠️  Could not open browser automatically.")
                print(f"   File available at: {target_path}")
                print(f"   URL: {url}")
        except Exception as e:
            print(f"   ⚠️  Browser error: {e}")
            print(f"   File available at: {target_path}")
            print(f"   URL: {url}")
    else:
        print("⚠️  QA skipped: no output file found to open.")


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
        description="Run OlmOCR-2 on one or more PDFs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python process_pdf.py app/samples/*.pdf --summary
  python process_pdf.py app/samples/*.pdf --preprocess --summary
  python process_pdf.py app/samples/*.pdf --qa --qa-mode light
        """
    )
    parser.add_argument("pdfs", nargs="+", help="Path(s) to input PDF(s)")
    parser.add_argument("--preprocess", action="store_true", 
                        help="Apply image cleanup before OCR")
    parser.add_argument("--summary", action="store_true", 
                        help="Generate summary JSON after each run")
    parser.add_argument("--qa", action="store_true", 
                        help="Open outputs in browser for inspection")
    parser.add_argument("--qa-mode", choices=["full", "light"], default="full",
                        help="QA mode: 'full' opens HTML (layout fidelity), "
                             "'light' opens Markdown (faster)")
    parser.add_argument("--qa-pages", type=int, default=10,
                        help="Light QA hint (first N pages) — informational; does not trim files")
    parser.add_argument("--limit", type=int, default=None, 
                        help="Limit number of PDFs processed")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"Parallel workers for OlmOCR CLI (default: {DEFAULT_WORKERS})")
    args = parser.parse_args()

    t0 = time.time()
    ensure_dirs()

    # Validate and normalize input list (preserve user order)
    print("📋 Validating input files...")
    pdf_paths = validate_pdf_inputs(args.pdfs)
    
    if args.limit:
        pdf_paths = pdf_paths[:args.limit]
        print(f"   Limited to first {args.limit} file(s)")

    if not pdf_paths:
        print("❌ No valid PDF files to process. Exiting.")
        return

    print(f"   Found {len(pdf_paths)} valid PDF(s)\n")

    # Optional preprocessing
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

    # --- Run OlmOCR Batch ---
    # We run all PDFs in a single, efficient batch.
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    batch_size = len(processed_paths)
    log_file = LOG_DIR / f"olmocr_batch_{batch_size}files_{timestamp}.log"
    
    try:
        run_olmocr_batch(processed_paths, workers=args.workers, log_file=log_file)
    except subprocess.CalledProcessError:
        print(f"❌ Batch job failed — see log: {log_file}")
        return  # Abort on failure
    except (FileNotFoundError, ImportError) as e:
        print(f"❌ CRITICAL ERROR: {e}")
        print("   Please ensure you are in the correct virtual environment.")
        return

    # --- Post-processing ---
    print("--- 📈 Post-processing Step ---")
    processed_count = 0
    summary_errors = 0
    missing_outputs = 0
    
    for i, pdf_path in enumerate(processed_paths, 1):
        print(f"[{i}/{len(processed_paths)}] Processing {pdf_path.name}...")
        
        html_path, md_path = get_output_paths(pdf_path)
        have_any = html_path.exists() or md_path.exists()
        
        if not have_any:
            print(f"   ⚠️  Output not found")
            missing_outputs += 1
            continue

        processed_count += 1

        # Generate summary
        if args.summary:
            try:
                # Prefer markdown for semantic counting; fall back to HTML
                out_for_summary = md_path if md_path.exists() else html_path
                print(f"   📈 Generating summary using {out_for_summary.suffix}...")
                summary = summarize_with_mode(pdf_path, out_for_summary, t0)
                summary_file = LOG_DIR / f"{pdf_path.stem}_summary.json"
                summary_file.write_text(json.dumps(summary, indent=2), encoding="utf-8")
                print(f"   ✅ Summary saved → {summary_file.name}")
            except Exception as e:
                print(f"   ⚠️  Error summarizing: {e}")
                summary_errors += 1

        # Open for QA (browser)
        if args.qa:
            open_for_qa(html_path, md_path, qa_mode=args.qa_mode, qa_pages=args.qa_pages)

    # Footer with statistics
    elapsed = time.time() - t0
    print("\n" + "="*60)
    print("🎯 Processing Complete")
    print("="*60)
    print(f"✅ Successfully processed: {processed_count}/{len(processed_paths)} documents")
    
    if missing_outputs > 0:
        print(f"⚠️  Missing outputs: {missing_outputs}")
    if summary_errors > 0:
        print(f"⚠️  Summary errors: {summary_errors}")
    if failed_preprocessing:
        print(f"⚠️  Preprocessing failures: {len(failed_preprocessing)}")
    
    print(f"\n📁 Output locations:")
    print(f"   HTML:     {HTML_OUTPUT_DIR.resolve()}")
    print(f"   Markdown: {MARKDOWN_OUTPUT_DIR.resolve()}")
    print(f"   Logs:     {LOG_DIR.resolve()}")
    print(f"\n⏱️  Total elapsed: {elapsed:.1f}s")
    print("="*60)


if __name__ == "__main__":
    main()