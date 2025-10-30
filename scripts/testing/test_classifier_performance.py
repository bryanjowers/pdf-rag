#!/usr/bin/env python3
"""
Performance test for optimized PDF classifier.
Compares processing speed on different PDF types.
"""

import sys
import time
from pathlib import Path

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

from utils_config import load_config
from utils_classify import classify_pdf

def test_single_pdf(pdf_path: Path, config: dict, description: str):
    """Test classification speed on a single PDF."""
    print(f"\n{description}")
    print("-" * 70)
    print(f"File: {pdf_path.name}")

    start = time.time()
    result = classify_pdf(pdf_path, config)
    elapsed = time.time() - start

    print(f"Type: {result['type']}")
    print(f"Reason: {result.get('classification_reason', 'N/A')}")
    print(f"Total Pages: {result['total_pages']}")
    print(f"Time: {elapsed:.3f} seconds")

    if 'image_detection' in result:
        img = result['image_detection']
        print(f"Image Detection: {img['sampled_pages']} pages sampled, {img['scan_pages']} scans found")

    return elapsed


def main():
    print("=" * 70)
    print("PDF Classifier Performance Test")
    print("=" * 70)

    config = load_config()

    # Test different PDF types
    tests = []

    # 1. Pre-OCR'd scanned PDF (should detect quickly with early exit)
    pdf1 = Path("/mnt/gcs/legal-ocr-pdf-input/Lewis Unit - Panola Co, TX/Tract 4/Scan Docs/1947_11_04_248_208.pdf")
    if pdf1.exists():
        t1 = test_single_pdf(pdf1, config, "TEST 1: Pre-OCR'd Scanned PDF (2 pages)")
        tests.append(("Pre-OCR'd Scan (2 pages)", t1))

    # 2. Find a true digital PDF
    digital_pdfs = list(Path("/mnt/gcs/legal-ocr-pdf-input").rglob("*.pdf"))
    for pdf in digital_pdfs[:20]:  # Check first 20
        try:
            result = classify_pdf(pdf, config)
            if result['type'] == 'pdf_digital' and result.get('classification_reason') == 'True digital PDF (no full-page scans detected)':
                t2 = test_single_pdf(pdf, config, "TEST 2: True Digital PDF")
                tests.append(("True Digital PDF", t2))
                break
        except:
            continue

    # 3. Find a raw scan (low text yield)
    for pdf in digital_pdfs[:50]:
        try:
            result = classify_pdf(pdf, config)
            if result['type'] == 'pdf_scanned' and 'Low text yield' in result.get('classification_reason', ''):
                t3 = test_single_pdf(pdf, config, "TEST 3: Raw Scan (Low Text Yield)")
                tests.append(("Raw Scan", t3))
                break
        except:
            continue

    # Summary
    print("\n" + "=" * 70)
    print("Performance Summary")
    print("=" * 70)
    for name, elapsed in tests:
        print(f"{name:30s} {elapsed:8.3f}s")

    print("\n" + "=" * 70)
    print("Key Optimizations Active:")
    print("=" * 70)
    print("✅ Metadata Pre-Scan: Check first 2-3 pages, early exit on <5% text")
    print("✅ Lightweight Images: get_images(full=False) for faster detection")
    print("✅ Early Exit Sampling: Stop after finding 3 scanned pages")
    print("✅ ThreadPoolExecutor: Better I/O performance for PDF operations")
    print("=" * 70)


if __name__ == "__main__":
    main()
