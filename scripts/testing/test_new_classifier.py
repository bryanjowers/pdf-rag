#!/usr/bin/env python3
"""
Test script for improved PDF classifier with image detection.
Tests the problem PDF to verify it now classifies as scanned.
"""

import sys
from pathlib import Path

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

from utils_config import load_config
from utils_classify import classify_pdf

def test_classifier():
    """Test new classifier on the problem PDF."""

    # Load config
    config = load_config()

    # Problem PDF path
    problem_pdf = Path("/mnt/gcs/legal-ocr-pdf-input/Lewis Unit - Panola Co, TX/Tract 4/Scan Docs/1947_11_04_248_208.pdf")

    if not problem_pdf.exists():
        print(f"❌ Problem PDF not found: {problem_pdf}")
        return

    print("="*70)
    print("Testing New PDF Classifier with Image Detection")
    print("="*70)
    print(f"\nTest PDF: {problem_pdf.name}")
    print(f"Location: Scan Docs/")
    print(f"Expected: Should classify as 'pdf_scanned' (pre-OCR'd scan)")
    print("\n" + "-"*70)
    print("Running classification...")
    print("-"*70 + "\n")

    # Classify
    result = classify_pdf(problem_pdf, config)

    # Display results
    print("Classification Results:")
    print("="*70)
    print(f"Type:                {result['type']}")
    print(f"Confidence:          {result['confidence']}")
    print(f"Total Pages:         {result['total_pages']}")
    print(f"Digital Pages:       {result['digital_pages']}")
    print(f"Percent Digital:     {result['percent_digital']:.1%}")
    print(f"Allowed:             {result['allowed']}")
    print(f"Rejection Reason:    {result.get('rejection_reason', 'None')}")
    print(f"Classification Reason: {result.get('classification_reason', 'None')}")

    # Image detection details
    if 'image_detection' in result:
        img = result['image_detection']
        print("\nImage Detection:")
        print("-"*70)
        print(f"Has Full-Page Scans: {img['has_full_page_scans']}")
        print(f"Sampled Pages:       {img['sampled_pages']}")
        print(f"Scan Pages:          {img['scan_pages']}")
        print(f"Scan Percentage:     {img['scan_percentage']:.0f}%")

    print("\n" + "="*70)

    # Verify expected result
    if result['type'] == 'pdf_scanned':
        print("✅ SUCCESS: PDF correctly classified as SCANNED")
        print("   This pre-OCR'd PDF will now go through OlmOCR-2")
    else:
        print("❌ FAILURE: PDF still classified as DIGITAL")
        print("   This is a problem - it should be scanned!")
        return False

    print("="*70 + "\n")
    return True


if __name__ == "__main__":
    success = test_classifier()
    sys.exit(0 if success else 1)
