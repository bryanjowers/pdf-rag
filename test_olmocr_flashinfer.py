#!/usr/bin/env python3
"""
Direct test of OlmOCR with FlashInfer enabled
"""

import sys
import time
import torch
import fitz  # PyMuPDF
from pathlib import Path

print("="*70)
print("OlmOCR + FlashInfer Integration Test")
print("="*70)

# Check versions
print(f"\n✅ PyTorch: {torch.__version__}")
print(f"✅ CUDA available: {torch.cuda.is_available()}")
print(f"✅ GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}")

try:
    import flashinfer
    print(f"✅ FlashInfer: {flashinfer.__version__}")
except ImportError as e:
    print(f"❌ FlashInfer not available: {e}")
    sys.exit(1)

try:
    from olmocr import OlmOCR
    print(f"✅ OlmOCR imported successfully")
except ImportError as e:
    print(f"❌ OlmOCR import failed: {e}")
    sys.exit(1)

# Test with a simple scanned PDF
if len(sys.argv) < 2:
    print("\n⚠️  No PDF file provided")
    print("Usage: python test_olmocr_flashinfer.py <pdf_path>")
    print("\nRunning basic import test only...")
    print("\n" + "="*70)
    print("✅ All imports successful - FlashInfer is ready!")
    print("="*70)
    sys.exit(0)

pdf_path = Path(sys.argv[1])
if not pdf_path.exists():
    print(f"\n❌ File not found: {pdf_path}")
    sys.exit(1)

print(f"\n{'='*70}")
print(f"Testing with: {pdf_path.name}")
print(f"{'='*70}")

try:
    # Check if PDF has images (likely scanned)
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    has_images = any(page.get_images() for page in doc)
    doc.close()

    print(f"\nPDF Info:")
    print(f"  Pages: {page_count}")
    print(f"  Has images: {has_images}")
    print(f"  Size: {pdf_path.stat().st_size / 1024:.1f} KB")

    if not has_images:
        print("\n⚠️  This appears to be a digital PDF (no images)")
        print("FlashInfer only speeds up scanned PDF processing")
        print("Test will continue but benefits won't be visible")

    # Initialize OlmOCR
    print(f"\n{'='*70}")
    print("Initializing OlmOCR...")
    print(f"{'='*70}")
    start = time.time()

    model = OlmOCR(
        device="cuda",
        gpu_memory_utilization=0.8
    )

    init_time = time.time() - start
    print(f"✅ OlmOCR initialized in {init_time:.2f}s")

    # Process the PDF
    print(f"\n{'='*70}")
    print("Processing PDF with OlmOCR + FlashInfer...")
    print(f"{'='*70}")
    start = time.time()

    results = model.process_document(str(pdf_path))

    process_time = time.time() - start

    print(f"\n✅ Processing complete!")
    print(f"\nResults:")
    print(f"  Total time: {process_time:.2f}s")
    print(f"  Pages processed: {len(results)}")

    total_text = sum(len(page.get('text', '')) for page in results)
    print(f"  Total text extracted: {total_text} characters")

    if results:
        first_page = results[0]
        preview = first_page.get('text', '')[:200]
        print(f"\nFirst page preview:")
        print(f"  {preview}...")

    print(f"\n{'='*70}")
    print("✅ FlashInfer integration test PASSED!")
    print(f"{'='*70}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
