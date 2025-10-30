#!/usr/bin/env python3
"""
Simple test script to verify parallel processing speedup after optimization.

Tests sequential vs parallel processing with 2 and 4 workers.
"""

import sys
import time
from pathlib import Path

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

from utils_config import load_config, get_storage_paths
from utils_processor import process_batch

def run_test(num_workers: int, test_files: int = 10):
    """Run processing test with specified number of workers."""

    config = load_config()
    paths = get_storage_paths(config)

    # Read digital PDFs from inventory
    import csv
    inventory_path = paths["inventory_dir"] / "inventory.csv"

    digital_pdfs = []
    with inventory_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("classification_type") == "pdf_digital" and row.get("allowed") == "True":
                pdf_path = row["file_path"].strip('"')
                digital_pdfs.append(Path(pdf_path))
                if len(digital_pdfs) >= test_files:
                    break

    if not digital_pdfs:
        print("❌ No digital PDFs found")
        return None

    # Update config with worker count
    config["processors"]["digital_pdf_workers"] = num_workers

    print(f"\n{'='*70}")
    print(f"🧪 Testing with {num_workers} workers, {len(digital_pdfs)} files")
    print(f"{'='*70}\n")

    # Run processing
    start_time = time.time()
    result = process_batch(
        digital_pdfs,
        config,
        batch_id=f"parallel_test_{num_workers}w",
        skip_enrichment=False  # Include entities + embeddings
    )
    duration = time.time() - start_time

    print(f"\n✅ Test Complete")
    print(f"   Duration: {duration:.1f}s")
    print(f"   Files/sec: {len(digital_pdfs)/duration:.2f}")
    print(f"   Successful: {result['successful']}/{result['total_files']}")

    return duration


if __name__ == "__main__":
    print("\n" + "="*70)
    print("📊 PARALLEL PROCESSING SPEEDUP TEST")
    print("="*70)

    num_files = 10

    # Test 1: Sequential (1 worker)
    print("\n🔹 TEST 1: Sequential (1 worker)")
    seq_time = run_test(num_workers=1, test_files=num_files)

    if seq_time is None:
        sys.exit(1)

    # Test 2: Parallel (2 workers)
    print("\n🔹 TEST 2: Parallel (2 workers)")
    par2_time = run_test(num_workers=2, test_files=num_files)

    # Test 3: Parallel (4 workers)
    print("\n🔹 TEST 3: Parallel (4 workers)")
    par4_time = run_test(num_workers=4, test_files=num_files)

    # Summary
    print("\n" + "="*70)
    print("📊 RESULTS SUMMARY")
    print("="*70)
    print(f"\nSequential (1 worker):  {seq_time:.1f}s")
    print(f"Parallel (2 workers):   {par2_time:.1f}s  (speedup: {seq_time/par2_time:.2f}x)")
    print(f"Parallel (4 workers):   {par4_time:.1f}s  (speedup: {seq_time/par4_time:.2f}x)")

    # Check if targets met
    speedup_2w = seq_time / par2_time
    speedup_4w = seq_time / par4_time

    print(f"\n🎯 TARGET VALIDATION:")
    print(f"   2 workers: {speedup_2w:.2f}x {'✅' if speedup_2w >= 1.6 else '❌'} (target: ≥1.6x)")
    print(f"   4 workers: {speedup_4w:.2f}x {'✅' if speedup_4w >= 2.5 else '❌'} (target: ≥2.5x)")

    print("\n" + "="*70)
    print("Test complete!")
    print("="*70 + "\n")
