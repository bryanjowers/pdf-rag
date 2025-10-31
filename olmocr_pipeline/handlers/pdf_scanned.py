#!/usr/bin/env python3
"""
pdf_scanned.py - Scanned PDF processing handler using OlmOCR-2

Processes PDFs without digital text layers using OlmOCR-2 OCR.
Optionally applies preprocessing (image cleanup) before OCR.
Reuses OlmOCR logic from utils_olmocr.py.
"""

import json
import shutil
import time
from pathlib import Path
from typing import Dict, List
import fitz  # PyMuPDF for page count

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils_olmocr import (
    run_olmocr_batch,
    get_olmocr_jsonl_path,
    olmocr_jsonl_to_markdown_with_pages,
    olmocr_to_jsonl
)


def process_scanned_pdf(
    pdf_path: Path,
    output_dir: Path,
    config: Dict,
    batch_id: str,
    apply_preprocessing: bool = False,
    skip_enrichment: bool = False
) -> Dict:
    """
    Process scanned PDF using OlmOCR-2 OCR.

    Args:
        pdf_path: Path to input scanned PDF
        output_dir: Base output directory
        config: Configuration dictionary
        batch_id: Unique batch identifier
        apply_preprocessing: If True, apply image cleanup before OCR

    Returns:
        Processing result dictionary with metadata:
        {
            "success": bool,
            "processor": "olmocr-2" | None,
            "markdown_path": Path | None,
            "jsonl_path": Path | None,
            "processing_duration_ms": int,
            "char_count": int,
            "estimated_tokens": int,
            "chunk_count": int,
            "warnings": list[str],
            "error": str | None
        }

    Raises:
        FileNotFoundError: If PDF doesn't exist
    """
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    start_time = time.time()
    warnings = []
    processed_pdf_path = pdf_path

    # Optional preprocessing
    if apply_preprocessing:
        try:
            from utils_preprocess import preprocess_pdf
            print(f"   🧹 Applying preprocessing...")
            processed_pdf_path = preprocess_pdf(pdf_path)
            print(f"      Preprocessed: {processed_pdf_path.name}")
        except Exception as e:
            warnings.append(f"Preprocessing failed: {e}")
            print(f"   ⚠️  Preprocessing failed: {e}")
            print(f"      Continuing with original PDF...")

    # Prepare output directories
    olmocr_staging = output_dir / "olmocr_staging"
    markdown_dir = output_dir / "markdown"
    jsonl_dir = output_dir / "jsonl"
    log_dir = output_dir / "logs"

    for d in [olmocr_staging, markdown_dir, jsonl_dir, log_dir]:
        d.mkdir(parents=True, exist_ok=True)

    stem = pdf_path.stem  # Use original stem
    log_file = log_dir / f"olmocr_{stem}.log"

    try:
        print(f"   🔄 Processing with OlmOCR-2: {pdf_path.name}")

        # Run OlmOCR batch
        run_olmocr_batch(
            file_paths=[processed_pdf_path],
            output_dir=olmocr_staging,
            config=config,
            log_file=log_file
        )

        # Get OlmOCR JSONL output (v0.4.2+ format)
        jsonl_path_olmocr = get_olmocr_jsonl_path(pdf_path, olmocr_staging)

        # Check if JSONL was created
        if jsonl_path_olmocr is None or not jsonl_path_olmocr.exists():
            raise FileNotFoundError(f"OlmOCR did not produce JSONL output for: {pdf_path.name}")

        # Check for OlmOCR-generated markdown file (created with --markdown flag)
        # OlmOCR creates markdown in different locations depending on path type:
        # - Absolute path input: Creates .md in same directory as source PDF
        # - Relative path input: Creates .md in workspace/markdown/
        # Try source directory first (most common with absolute paths)
        olmocr_md_path = pdf_path.with_suffix('.md')

        # If not found, try workspace markdown directory (for relative paths)
        if not olmocr_md_path.exists():
            olmocr_md_path = olmocr_staging / "markdown" / pdf_path.name.replace('.pdf', '.md')

        if olmocr_md_path.exists():
            # Use OlmOCR's markdown (properly formatted with line breaks)
            print(f"      📄 Using OlmOCR markdown: {olmocr_md_path.name}")
            markdown_content = olmocr_md_path.read_text(encoding="utf-8")
            char_count = len(markdown_content)

            # Extract page mapping from JSONL for bbox tracking
            _, page_map = olmocr_jsonl_to_markdown_with_pages(jsonl_path_olmocr)
            print(f"      📍 Extracted page info for {len(page_map)} text blocks")
        else:
            # Fallback: Convert JSONL to markdown (for image inputs)
            print(f"      ⚠️  No markdown file found, using JSONL text")
            markdown_content, page_map = olmocr_jsonl_to_markdown_with_pages(jsonl_path_olmocr)
            char_count = len(markdown_content)
            print(f"      📍 Extracted page info for {len(page_map)} text blocks")

        # Get page count from PDF
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
        except Exception:
            page_count = 1  # Fallback if PDF can't be opened
            warnings.append("Could not determine page count from PDF")

        # Check for low yield (OCR might have failed on some pages)
        chars_per_page = char_count / page_count if page_count > 0 else 0
        if chars_per_page < 100:
            warnings.append(f"Low text yield: {chars_per_page:.0f} chars/page")

        # Copy markdown to final location
        final_md_path = markdown_dir / f"{stem}.md"
        final_md_path.write_text(markdown_content, encoding="utf-8")

        # Convert to JSONL with page mapping
        chunks = olmocr_to_jsonl(
            markdown_content,
            pdf_path,
            config,
            batch_id,
            page_mapping=page_map
        )

        # Add entity extraction and embeddings (unless skipped for ingest-only mode)
        if not skip_enrichment:
            import os
            enable_entities = config.get("entity_extraction", {}).get("enabled", False)
            if enable_entities:
                from utils_entity_integration import add_entities_to_chunks, format_entity_stats
                api_key = config.get("entity_extraction", {}).get("openai_api_key") or os.getenv("OPENAI_API_KEY")
                print(f"   🔍 Extracting entities...")
                chunks, entity_stats = add_entities_to_chunks(
                    chunks,
                    enable_entities=True,
                    api_key=api_key
                )
                print(format_entity_stats(entity_stats))

            enable_embeddings = config.get("embeddings", {}).get("enabled", False)
            if enable_embeddings:
                from utils_embeddings import EmbeddingGenerator, format_embedding_stats
                print(f"   🔢 Generating embeddings...")
                embedding_gen = EmbeddingGenerator(
                    model_name=config.get("embeddings", {}).get("model", "all-mpnet-base-v2")
                )
                chunks = embedding_gen.add_embeddings_to_chunks(chunks, show_progress=False)
                print(f"   {format_embedding_stats(chunks)}")

        # Write JSONL
        jsonl_path = jsonl_dir / f"{stem}.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

        # Compute duration
        duration_ms = int((time.time() - start_time) * 1000)

        print(f"   ✅ OlmOCR-2 processing complete")
        print(f"      Output: {char_count:,} chars (~{len(markdown_content.split()):,} tokens)")
        print(f"      Duration: {duration_ms/1000:.1f}s")
        print(f"      Chunks: {len(chunks)}")

        if warnings:
            for warning in warnings:
                print(f"      ⚠️  {warning}")

        return {
            "success": True,
            "processor": "olmocr-2",
            "markdown_path": final_md_path,
            "jsonl_path": jsonl_path,
            "processing_duration_ms": duration_ms,
            "page_count": page_count,
            "char_count": char_count,
            "estimated_tokens": len(markdown_content.split()),
            "chunk_count": len(chunks),
            "warnings": warnings,
            "error": None
        }

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"OlmOCR-2 failed: {str(e)}"
        print(f"   ❌ {error_msg}")

        return {
            "success": False,
            "processor": None,
            "markdown_path": None,
            "jsonl_path": None,
            "processing_duration_ms": duration_ms,
            "char_count": 0,
            "estimated_tokens": 0,
            "chunk_count": 0,
            "warnings": warnings,
            "error": error_msg
        }


def process_scanned_pdf_batch(
    pdf_paths: List[Path],
    output_dir: Path,
    config: Dict,
    batch_id: str,
    apply_preprocessing: bool = False,
    skip_enrichment: bool = False
) -> List[Dict]:
    """
    Process multiple scanned PDFs in a single OlmOCR batch for 2-3x speedup.

    This function groups multiple PDFs and processes them together,
    amortizing OlmOCR model startup/teardown costs across all files.

    Args:
        pdf_paths: List of scanned PDF paths to process
        output_dir: Output directory
        config: Configuration dictionary
        batch_id: Batch identifier
        apply_preprocessing: Whether to apply preprocessing
        skip_enrichment: Whether to skip enrichment

    Returns:
        List of result dictionaries (one per PDF)
    """
    start_time = time.time()

    # Prepare output directories
    olmocr_staging = output_dir / "olmocr_staging"
    markdown_dir = output_dir / "markdown"
    jsonl_dir = output_dir / "jsonl"
    log_dir = output_dir / "logs"

    for d in [olmocr_staging, markdown_dir, jsonl_dir, log_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Create batch log file
    log_file = log_dir / f"olmocr_batch_{batch_id}_{len(pdf_paths)}files.log"

    print(f"   🔄 Processing {len(pdf_paths)} scanned PDFs with OlmOCR-2 batch")

    # Apply preprocessing if needed (for all files)
    processed_paths = []
    for pdf_path in pdf_paths:
        if apply_preprocessing:
            try:
                from utils_preprocess import preprocess_pdf
                processed_path = preprocess_pdf(pdf_path)
            except Exception as e:
                print(f"   ⚠️  Preprocessing failed for {pdf_path.name}: {e}")
                processed_path = pdf_path
        else:
            processed_path = pdf_path
        processed_paths.append(processed_path)

    try:
        # ✨ KEY CHANGE: Pass ALL files to OlmOCR at once!
        run_olmocr_batch(
            file_paths=processed_paths,  # ← MULTIPLE FILES!
            output_dir=olmocr_staging,
            config=config,
            log_file=log_file
        )

        # Process results for each file
        results = []
        for pdf_path in pdf_paths:
            result = _process_single_olmocr_output(
                pdf_path=pdf_path,
                olmocr_staging=olmocr_staging,
                markdown_dir=markdown_dir,
                jsonl_dir=jsonl_dir,
                config=config,
                batch_id=batch_id,
                skip_enrichment=skip_enrichment
            )
            results.append(result)

        batch_duration = time.time() - start_time
        print(f"   ✅ Batch complete: {len(pdf_paths)} files in {batch_duration:.1f}s ({batch_duration/len(pdf_paths):.1f}s/file avg)")

        return results

    except Exception as e:
        # Handle batch failure - return failure results for all files
        print(f"   ❌ Batch processing failed: {e}")
        return [
            {
                "success": False,
                "file_path": str(pdf_path),
                "file_name": pdf_path.name,
                "file_type": "pdf",
                "processor": "olmocr",
                "error": f"Batch processing failed: {e}",
                "quarantined": True,
                "retry_count": 0
            }
            for pdf_path in pdf_paths
        ]


def _process_single_olmocr_output(
    pdf_path: Path,
    olmocr_staging: Path,
    markdown_dir: Path,
    jsonl_dir: Path,
    config: Dict,
    batch_id: str,
    skip_enrichment: bool
) -> Dict:
    """
    Extract and process OlmOCR output for a single PDF from batch results.

    This function handles the post-processing after OlmOCR has completed
    a batch run containing this PDF.

    Args:
        pdf_path: Original PDF path
        olmocr_staging: OlmOCR staging directory
        markdown_dir: Output markdown directory
        jsonl_dir: Output JSONL directory
        config: Configuration dictionary
        batch_id: Batch identifier
        skip_enrichment: Whether to skip enrichment

    Returns:
        Result dictionary for this PDF
    """
    start_time = time.time()
    stem = pdf_path.stem
    warnings = []

    try:
        # Get OlmOCR JSONL output
        jsonl_path_olmocr = get_olmocr_jsonl_path(pdf_path, olmocr_staging)

        if jsonl_path_olmocr is None or not jsonl_path_olmocr.exists():
            raise FileNotFoundError(f"OlmOCR did not produce JSONL output for: {pdf_path.name}")

        # Get OlmOCR markdown output
        olmocr_md_path = pdf_path.with_suffix('.md')
        if not olmocr_md_path.exists():
            olmocr_md_path = olmocr_staging / "markdown" / f"{stem}.md"

        if olmocr_md_path.exists():
            # Use OlmOCR's markdown
            markdown_content = olmocr_md_path.read_text(encoding="utf-8")
            char_count = len(markdown_content)

            # Extract page mapping from JSONL (filter by this file for batched results)
            _, page_map = olmocr_jsonl_to_markdown_with_pages(jsonl_path_olmocr, filter_source_file=pdf_path)
        else:
            # Fallback: Convert JSONL to markdown (filter by this file for batched results)
            markdown_content, page_map = olmocr_jsonl_to_markdown_with_pages(jsonl_path_olmocr, filter_source_file=pdf_path)
            char_count = len(markdown_content)
            warnings.append("No markdown file found, used JSONL text")

        # Get page count from PDF
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
        except Exception:
            page_count = 1
            warnings.append("Could not determine page count from PDF")

        # Check for low yield
        chars_per_page = char_count / page_count if page_count > 0 else 0
        if chars_per_page < 100:
            warnings.append(f"Low text yield: {chars_per_page:.0f} chars/page")

        # Copy markdown to final location
        final_md_path = markdown_dir / f"{stem}.md"
        final_md_path.write_text(markdown_content, encoding="utf-8")

        # Convert to JSONL with page mapping
        chunks = olmocr_to_jsonl(
            markdown_content,
            pdf_path,
            config,
            batch_id,
            page_mapping=page_map
        )

        # Add entity extraction and embeddings (unless skipped)
        if not skip_enrichment:
            import os
            enable_entities = config.get("entity_extraction", {}).get("enabled", False)
            if enable_entities:
                from utils_entity_integration import add_entities_to_chunks, format_entity_stats
                api_key = config.get("entity_extraction", {}).get("openai_api_key") or os.getenv("OPENAI_API_KEY")
                chunks, entity_stats = add_entities_to_chunks(
                    chunks,
                    enable_entities=True,
                    api_key=api_key
                )

            enable_embeddings = config.get("embeddings", {}).get("enabled", False)
            if enable_embeddings:
                from utils_embeddings import EmbeddingGenerator
                embedding_gen = EmbeddingGenerator(
                    model_name=config.get("embeddings", {}).get("model", "all-mpnet-base-v2")
                )
                chunks = embedding_gen.add_embeddings_to_chunks(chunks, show_progress=False)

        # Write JSONL
        jsonl_path = jsonl_dir / f"{stem}.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

        duration_ms = int((time.time() - start_time) * 1000)

        print(f"      ✅ {pdf_path.name}: {char_count:,} chars, {len(chunks)} chunks ({duration_ms/1000:.1f}s)")

        return {
            "success": True,
            "file_path": str(pdf_path),
            "file_name": pdf_path.name,
            "file_type": "pdf",
            "processor": "olmocr-2",
            "output_markdown": str(final_md_path),
            "output_jsonl": str(jsonl_path),
            "page_count": page_count,
            "char_count": char_count,
            "estimated_tokens": len(markdown_content.split()),
            "chunk_count": len(chunks),
            "processing_duration_ms": duration_ms,
            "warnings": warnings
        }

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        error_msg = f"Failed to process OlmOCR output: {str(e)}"
        print(f"      ❌ {pdf_path.name}: {error_msg}")

        return {
            "success": False,
            "file_path": str(pdf_path),
            "file_name": pdf_path.name,
            "file_type": "pdf",
            "processor": "olmocr",
            "error": error_msg,
            "quarantined": True,
            "retry_count": 0,
            "processing_duration_ms": duration_ms
        }
