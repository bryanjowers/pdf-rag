#!/usr/bin/env python3
"""
Debug script to identify performance regression in inventory building.
"""

import sys
import time
from pathlib import Path
from multiprocessing import Pool, cpu_count
from concurrent.futures import ThreadPoolExecutor

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

from utils_config import load_config
from utils_classify import classify_pdf
from utils_inventory import discover_files, _classify_single_file

def test_sequential(files, config, timestamp):
    """Sequential processing."""
    print("\n1. Sequential Processing:")
    print("-" * 70)
    start = time.time()

    for idx, file_path in enumerate(files[:20], 1):  # Test first 20
        _classify_single_file((file_path, config, timestamp))
        if idx % 5 == 0:
            print(f"   Processed {idx}/20...", end="\r")

    elapsed = time.time() - start
    print(f"\n   Time: {elapsed:.2f}s for 20 files")
    print(f"   Rate: {20/elapsed:.2f} files/sec")
    return elapsed


def test_multiprocessing(files, config, timestamp):
    """Multiprocessing with Pool."""
    print("\n2. Multiprocessing (Pool):")
    print("-" * 70)

    num_workers = 4
    args_list = [(f, config, timestamp) for f in files[:20]]

    start = time.time()
    with Pool(processes=num_workers) as pool:
        results = list(pool.imap(_classify_single_file, args_list))
    elapsed = time.time() - start

    print(f"   Workers: {num_workers}")
    print(f"   Time: {elapsed:.2f}s for 20 files")
    print(f"   Rate: {20/elapsed:.2f} files/sec")
    return elapsed


def test_threadpool(files, config, timestamp):
    """ThreadPoolExecutor."""
    print("\n3. ThreadPoolExecutor:")
    print("-" * 70)

    num_workers = 4
    args_list = [(f, config, timestamp) for f in files[:20]]

    start = time.time()
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(_classify_single_file, args) for args in args_list]
        results = [f.result() for f in futures]
    elapsed = time.time() - start

    print(f"   Workers: {num_workers}")
    print(f"   Time: {elapsed:.2f}s for 20 files")
    print(f"   Rate: {20/elapsed:.2f} files/sec")
    return elapsed


def main():
    print("=" * 70)
    print("Inventory Building Performance Debug")
    print("=" * 70)

    config = load_config()
    input_dir = Path(config.get("storage", {}).get("input_bucket", "/mnt/gcs/legal-ocr-pdf-input"))

    print(f"\nDiscovering files in: {input_dir}")
    files = discover_files(input_dir, sort_by="name")
    print(f"Found: {len(files)} files")

    timestamp = "2025-10-30T00:00:00Z"

    # Test each method
    t_seq = test_sequential(files, config, timestamp)
    t_multi = test_multiprocessing(files, config, timestamp)
    t_thread = test_threadpool(files, config, timestamp)

    # Summary
    print("\n" + "=" * 70)
    print("Performance Comparison (20 files)")
    print("=" * 70)
    print(f"Sequential:       {t_seq:8.2f}s  ({20/t_seq:6.2f} files/sec)")
    print(f"Multiprocessing:  {t_multi:8.2f}s  ({20/t_multi:6.2f} files/sec) - {t_seq/t_multi:.2f}x speedup")
    print(f"ThreadPool:       {t_thread:8.2f}s  ({20/t_thread:6.2f} files/sec) - {t_seq/t_thread:.2f}x speedup")
    print("=" * 70)

    if t_thread > t_multi:
        print(f"\n⚠️  ThreadPool is SLOWER than Multiprocessing by {t_thread/t_multi:.2f}x")
        print("   Recommendation: Revert to multiprocessing.Pool")
    else:
        print(f"\n✅ ThreadPool is faster than Multiprocessing by {t_multi/t_thread:.2f}x")


if __name__ == "__main__":
    main()
