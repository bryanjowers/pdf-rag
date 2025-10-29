#!/usr/bin/env python3
"""
utils_estimator.py - Processing time estimation from manifest data

Builds predictive models for processing time based on file characteristics.
Useful for batch planning and resource allocation.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, Optional


def analyze_manifest_data(manifest_dir: Path) -> pd.DataFrame:
    """
    Load and combine all manifest CSVs.

    Args:
        manifest_dir: Directory containing manifest CSV files

    Returns:
        Combined DataFrame with all manifest data
    """
    manifests = list(manifest_dir.glob("*.csv"))

    if not manifests:
        return pd.DataFrame()

    all_data = []
    for manifest in manifests:
        df = pd.read_csv(manifest)
        all_data.append(df)

    return pd.concat(all_data, ignore_index=True)


def build_time_estimators(df: pd.DataFrame) -> Dict:
    """
    Build time estimation models from manifest data.

    Uses simple linear regression: time = base + (rate * size_metric)

    Args:
        df: DataFrame with manifest data

    Returns:
        Dictionary of estimators by file type/processor
    """
    # Filter successful only
    df_success = df[df['status'] == 'success'].copy()

    if len(df_success) == 0:
        return {}

    estimators = {}

    # Group by file_type and processor
    for (file_type, processor), group in df_success.groupby(['file_type', 'processor']):
        if len(group) < 2:
            # Need at least 2 samples for estimation
            continue

        # Calculate metrics
        avg_time_ms = group['processing_duration_ms'].mean()
        avg_chars = group['char_count'].mean()
        avg_chunks = group['chunks_created'].mean()

        # Time per character (simple metric)
        ms_per_char = group['processing_duration_ms'] / group['char_count']
        avg_ms_per_char = ms_per_char.mean()

        # Time per chunk (alternative metric)
        ms_per_chunk = group['processing_duration_ms'] / group['chunks_created']
        avg_ms_per_chunk = ms_per_chunk.mean()

        # Time per page (for PDFs/DOCX with page_count)
        has_page_count = 'page_count' in group.columns and group['page_count'].notna().sum() > 0
        if has_page_count:
            group_with_pages = group[group['page_count'].notna() & (group['page_count'] > 0)]
            if len(group_with_pages) >= 2:
                ms_per_page = group_with_pages['processing_duration_ms'] / group_with_pages['page_count']
                avg_ms_per_page = ms_per_page.mean()
                avg_pages = group_with_pages['page_count'].mean()
            else:
                avg_ms_per_page = None
                avg_pages = None
        else:
            avg_ms_per_page = None
            avg_pages = None

        # Base overhead (y-intercept - minimum time even for small files)
        base_overhead_ms = max(0, group['processing_duration_ms'].min() - 1000)

        estimators[f"{file_type}_{processor}"] = {
            "file_type": file_type,
            "processor": processor,
            "sample_count": len(group),
            "avg_time_ms": avg_time_ms,
            "avg_chars": avg_chars,
            "avg_chunks": avg_chunks,
            "avg_pages": avg_pages,
            "ms_per_char": avg_ms_per_char,
            "ms_per_chunk": avg_ms_per_chunk,
            "ms_per_page": avg_ms_per_page,
            "base_overhead_ms": base_overhead_ms
        }

    return estimators


def estimate_processing_time(
    file_type: str,
    processor: str,
    estimated_chars: Optional[int] = None,
    estimated_chunks: Optional[int] = None,
    estimated_pages: Optional[int] = None,
    estimators: Optional[Dict] = None
) -> Dict:
    """
    Estimate processing time for a file.

    Args:
        file_type: Type of file (pdf, docx, xlsx)
        processor: Processor to use (docling, olmocr-2, openpyxl)
        estimated_chars: Estimated character count
        estimated_chunks: Estimated chunk count
        estimated_pages: Estimated page count (for PDFs/DOCX)
        estimators: Pre-computed estimators (from build_time_estimators)

    Returns:
        Estimation dictionary with time ranges
    """
    if estimators is None:
        return {"error": "No estimators available"}

    key = f"{file_type}_{processor}"
    if key not in estimators:
        return {"error": f"No data for {file_type} with {processor}"}

    est = estimators[key]

    # Prefer page_count for PDFs/DOCX (most reliable predictor)
    if estimated_pages and est["ms_per_page"] is not None:
        predicted_ms = est["base_overhead_ms"] + (est["ms_per_page"] * estimated_pages)
        predictor_used = "pages"
    elif estimated_chars:
        predicted_ms = est["base_overhead_ms"] + (est["ms_per_char"] * estimated_chars)
        predictor_used = "chars"
    elif estimated_chunks:
        predicted_ms = est["base_overhead_ms"] + (est["ms_per_chunk"] * estimated_chunks)
        predictor_used = "chunks"
    else:
        # Use average
        predicted_ms = est["avg_time_ms"]
        predictor_used = "average"

    # Add confidence interval (±30% based on variance)
    min_ms = predicted_ms * 0.7
    max_ms = predicted_ms * 1.3

    return {
        "file_type": file_type,
        "processor": processor,
        "estimated_time_ms": int(predicted_ms),
        "estimated_time_sec": predicted_ms / 1000,
        "min_time_sec": min_ms / 1000,
        "max_time_sec": max_ms / 1000,
        "predictor_used": predictor_used,
        "confidence": "medium" if est["sample_count"] >= 5 else "low",
        "based_on_samples": est["sample_count"]
    }


def estimate_batch_time(
    file_list: list[Dict],
    estimators: Dict,
    parallel_workers: int = 1
) -> Dict:
    """
    Estimate total time for batch processing.

    Args:
        file_list: List of file dicts with {file_type, processor, estimated_chars}
        estimators: Pre-computed estimators
        parallel_workers: Number of parallel workers

    Returns:
        Batch time estimation
    """
    total_time_ms = 0
    file_estimates = []

    for file_info in file_list:
        est = estimate_processing_time(
            file_info["file_type"],
            file_info["processor"],
            file_info.get("estimated_chars"),
            file_info.get("estimated_chunks"),
            estimators
        )
        if "error" not in est:
            total_time_ms += est["estimated_time_ms"]
            file_estimates.append(est)

    # Adjust for parallelism (simplified - assumes perfect scaling)
    if parallel_workers > 1:
        adjusted_time_ms = total_time_ms / parallel_workers
    else:
        adjusted_time_ms = total_time_ms

    return {
        "total_files": len(file_list),
        "sequential_time_sec": total_time_ms / 1000,
        "parallel_time_sec": adjusted_time_ms / 1000,
        "parallel_workers": parallel_workers,
        "file_estimates": file_estimates
    }


def print_estimators(estimators: Dict) -> None:
    """
    Print human-readable estimator summary.

    Args:
        estimators: Dictionary from build_time_estimators()
    """
    print("\n📊 Processing Time Estimators (from manifest data)")
    print("="*70)

    for key, est in sorted(estimators.items()):
        print(f"\n{est['file_type'].upper()} ({est['processor']}):")
        print(f"  Samples: {est['sample_count']}")
        print(f"  Avg time: {est['avg_time_ms']/1000:.1f}s")

        size_metrics = f"{est['avg_chars']:,.0f} chars, {est['avg_chunks']:.0f} chunks"
        if est['avg_pages'] is not None:
            size_metrics += f", {est['avg_pages']:.1f} pages"
        print(f"  Avg size: {size_metrics}")

        print(f"  Rate (chars): {est['ms_per_char']:.4f} ms/char ({1000/est['ms_per_char']:.0f} chars/sec)")

        if est['ms_per_page'] is not None:
            print(f"  Rate (pages): {est['ms_per_page']:.1f} ms/page ({60000/est['ms_per_page']:.1f} pages/min)")

        print(f"  Base overhead: {est['base_overhead_ms']/1000:.1f}s")

        # Example estimates (prefer page-based when available)
        if est['file_type'] == 'pdf':
            if est['ms_per_page']:
                example_time = (est['base_overhead_ms'] + est['ms_per_page'] * 30) / 1000
                print(f"  Example: 30-page PDF = {example_time:.1f}s")
            else:
                example_chars = 100000
                example_time = (est['base_overhead_ms'] + est['ms_per_char'] * example_chars) / 1000
                print(f"  Example: 30-page PDF (~100k chars) = {example_time:.1f}s")
        elif est['file_type'] == 'docx':
            if est['ms_per_page']:
                example_time = (est['base_overhead_ms'] + est['ms_per_page'] * 20) / 1000
                print(f"  Example: 20-page DOCX = {example_time:.1f}s")
            else:
                example_chars = 50000
                example_time = (est['base_overhead_ms'] + est['ms_per_char'] * example_chars) / 1000
                print(f"  Example: 20-page DOCX (~50k chars) = {example_time:.1f}s")
        elif est['file_type'] == 'xlsx':
            example_chars = 10000  # ~500 rows
            example_time = (est['base_overhead_ms'] + est['ms_per_char'] * example_chars) / 1000
            print(f"  Example: 500-row XLSX (~10k chars) = {example_time:.1f}s")

    print("\n" + "="*70)


def print_estimate(estimate: Dict) -> None:
    """
    Print human-readable time estimate.

    Args:
        estimate: Dictionary from estimate_processing_time()
    """
    if "error" in estimate:
        print(f"⚠️  {estimate['error']}")
        return

    print(f"\n⏱️  Estimated Time: {estimate['estimated_time_sec']:.1f}s")
    print(f"   Range: {estimate['min_time_sec']:.1f}s - {estimate['max_time_sec']:.1f}s")
    print(f"   Confidence: {estimate['confidence']} (based on {estimate['based_on_samples']} samples)")
