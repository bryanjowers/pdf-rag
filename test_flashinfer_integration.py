#!/usr/bin/env python3
"""
Quick test to verify FlashInfer integration with OlmOCR pipeline
"""

import sys
import time
from pathlib import Path

# Test imports
print("Testing imports...")
try:
    import torch
    print(f"✅ PyTorch: {torch.__version__}")
    print(f"✅ CUDA available: {torch.cuda.is_available()}")

    import flashinfer
    print(f"✅ FlashInfer: {flashinfer.__version__}")

    import olmocr
    print(f"✅ OlmOCR imported successfully")

    from olmocr_pipeline.utils_classify import classify_document
    from olmocr_pipeline.utils_processor import process_document
    print(f"✅ Pipeline utilities imported successfully")

except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Test document processing
if len(sys.argv) < 2:
    print("\nUsage: python test_flashinfer_integration.py <pdf_path>")
    print("\nSkipping document processing test (no file provided)")
    sys.exit(0)

pdf_path = Path(sys.argv[1])
if not pdf_path.exists():
    print(f"❌ File not found: {pdf_path}")
    sys.exit(1)

print(f"\n{'='*60}")
print(f"Testing document processing with FlashInfer enabled")
print(f"{'='*60}")
print(f"File: {pdf_path.name}")
print(f"Size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB")

try:
    # Classify document
    print("\n1. Classifying document...")
    start_time = time.time()
    doc_type = classify_document(str(pdf_path))
    classify_time = time.time() - start_time
    print(f"   Type: {doc_type}")
    print(f"   Time: {classify_time:.2f}s")

    # Process document
    print("\n2. Processing document...")
    start_time = time.time()
    result = process_document(str(pdf_path))
    process_time = time.time() - start_time

    if result:
        print(f"   ✅ Success!")
        print(f"   Time: {process_time:.2f}s")
        print(f"   Pages: {result.get('page_count', 'N/A')}")
        print(f"   Text length: {len(result.get('text', ''))}")
        print(f"   Entities: {len(result.get('entities', []))}")
    else:
        print(f"   ❌ Processing failed")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"✅ FlashInfer integration test PASSED!")
    print(f"{'='*60}")

except Exception as e:
    print(f"\n❌ Error during processing: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
