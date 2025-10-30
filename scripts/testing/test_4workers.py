#!/usr/bin/env python3
"""
Quick test script to verify 4-worker parallelization performance.
"""

import sys
import time
import csv
from pathlib import Path

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

from utils_config import load_config, get_storage_paths
from utils_processor import process_batch

def find_unprocessed_digital_pdfs(config, limit=10):
    """Find digital PDFs that haven't been processed yet."""
    paths = get_storage_paths(config)
    inventory_path = paths["inventory_dir"] / "inventory.csv"
    jsonl_dir = paths["rag_staging"] / "jsonl"

    unprocessed = []

    with inventory_path.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("classification_type") == "pdf_digital" and row.get("allowed") == "True":
                pdf_path = Path(row["file_path"].strip('"'))

                # Check if already processed
                stem = pdf_path.stem
                jsonl_path = jsonl_dir / f"{stem}.jsonl"

                if not jsonl_path.exists():
                    unprocessed.append(pdf_path)
                    if len(unprocessed) >= limit:
                        break

    return unprocessed


def run_test(num_workers: int, test_pdfs):
    """Run test with specified worker count."""
    config = load_config()
    config["processors"]["digital_pdf_workers"] = num_workers

    print(f"\n{'='*70}")
    print(f"🧪 Testing {num_workers} workers with {len(test_pdfs)} PDFs")
    print(f"{'='*70}\n")

    start = time.time()
    result = process_batch(
        test_pdfs,
        config,
        batch_id=f"test_{num_workers}w",
        skip_enrichment=False
    )
    duration = time.time() - start

    print(f"\n✅ Complete: {duration:.1f}s")
    print(f"   Per-file: {duration/len(test_pdfs):.1f}s")
    print(f"   Files/sec: {len(test_pdfs)/duration:.2f}")

    return duration


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🚀 4-WORKER PARALLELIZATION TEST")
    print("="*70)

    config = load_config()

    # Find unprocessed PDFs
    print("\n📋 Finding unprocessed digital PDFs...")
    pdfs = find_unprocessed_digital_pdfs(config, limit=12)

    if len(pdfs) < 12:
        print(f"⚠️  Only found {len(pdfs)} unprocessed PDFs (need 12 for comparison)")
        print("   Using what we have...\n")
    else:
        print(f"✅ Found {len(pdfs)} unprocessed PDFs\n")

    # Split into two groups for comparison
    group1 = pdfs[:len(pdfs)//2]
    group2 = pdfs[len(pdfs)//2:]

    # Test 1: 2 workers
    print("\n🔹 TEST 1: 2 Workers")
    time_2w = run_test(2, group1)

    # Test 2: 4 workers
    print("\n🔹 TEST 2: 4 Workers")
    time_4w = run_test(4, group2)

    # Comparison
    per_file_2w = time_2w / len(group1)
    per_file_4w = time_4w / len(group2)
    improvement = ((per_file_2w - per_file_4w) / per_file_2w) * 100

    print(f"\n{'='*70}")
    print("📊 COMPARISON")
    print(f"{'='*70}")
    print(f"\n2 workers: {per_file_2w:.1f}s per file")
    print(f"4 workers: {per_file_4w:.1f}s per file")
    print(f"\nImprovement: {improvement:.1f}%")

    if per_file_4w < per_file_2w:
        print(f"✅ 4 workers is faster!")
    else:
        print(f"⚠️  4 workers is not showing improvement")
        print(f"   This suggests we've hit a bottleneck (API rate limits, I/O, etc.)")

    print(f"\n{'='*70}\n")
