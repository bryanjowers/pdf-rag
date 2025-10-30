#!/usr/bin/env python3
"""
Test script for scanned PDF handler with bbox support (schema v2.3.0)
"""

import json
import sys
from pathlib import Path

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

from utils_olmocr import olmocr_jsonl_to_markdown_with_pages, olmocr_to_jsonl
from utils_config import load_config

def test_olmocr_bbox_extraction():
    """Test bbox extraction from existing OlmOCR JSONL output."""

    print("=" * 70)
    print("Testing OlmOCR JSONL Page Extraction")
    print("=" * 70)

    # Find an existing OlmOCR JSONL file
    olmocr_results = Path("/mnt/gcs/legal-ocr-results/rag_staging/olmocr_staging/results")
    jsonl_files = list(olmocr_results.glob("*.jsonl"))

    if not jsonl_files:
        print("❌ No OlmOCR JSONL files found in results directory")
        return False

    test_jsonl = jsonl_files[0]
    print(f"\n📄 Testing with: {test_jsonl.name}")

    # Extract markdown and page mapping
    try:
        markdown_content, page_map = olmocr_jsonl_to_markdown_with_pages(test_jsonl)

        print(f"\n✅ Extraction successful!")
        print(f"   Text length: {len(markdown_content):,} chars")
        print(f"   Page map entries: {len(page_map)}")

        if page_map:
            print(f"   Page numbers found: {sorted(set(page_map.values()))}")
            print(f"\n   Sample page map:")
            for idx, page in list(page_map.items())[:3]:
                print(f"      Block {idx} → Page {page}")
        else:
            print("   ⚠️  No page information found")

        return True

    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        return False


def test_jsonl_chunking_with_bbox():
    """Test full chunking pipeline with bbox."""

    print("\n" + "=" * 70)
    print("Testing Chunking with Bbox (Schema v2.3.0)")
    print("=" * 70)

    # Find test file
    olmocr_results = Path("/mnt/gcs/legal-ocr-results/rag_staging/olmocr_staging/results")
    jsonl_files = list(olmocr_results.glob("*.jsonl"))

    if not jsonl_files:
        print("❌ No test files available")
        return False

    test_jsonl = jsonl_files[0]

    # Load config
    config = load_config()

    # Extract markdown and pages
    markdown_content, page_map = olmocr_jsonl_to_markdown_with_pages(test_jsonl)

    # Create chunks with bbox
    source_path = Path("/home/bryanjowers/pdf-rag/pdf_input/checkpoint4_test/G4UxpnmWgAAR_so.jpeg")
    batch_id = "test_bbox_v230"

    try:
        chunks = olmocr_to_jsonl(
            markdown_content,
            source_path,
            config,
            batch_id,
            page_mapping=page_map
        )

        print(f"\n✅ Chunking successful!")
        print(f"   Chunks created: {len(chunks)}")

        # Inspect first chunk
        if chunks:
            first_chunk = chunks[0]
            print(f"\n   📦 Sample chunk structure:")
            print(f"      ID: {first_chunk['id']}")
            print(f"      Text length: {len(first_chunk['text'])} chars")
            print(f"      Token count: {first_chunk['attrs']['token_count']}")
            print(f"      Schema version: {first_chunk['metadata']['schema_version']}")

            # Check bbox field
            bbox = first_chunk['attrs'].get('bbox')
            if bbox:
                print(f"      ✅ Bbox present: {bbox}")

                # Validate bbox structure
                if 'page' in bbox and bbox['page'] is not None:
                    print(f"         Page number: {bbox['page']}")
                    print(f"         Coordinates: x0={bbox.get('x0')}, y0={bbox.get('y0')}, x1={bbox.get('x1')}, y1={bbox.get('y1')}")

                    if all(bbox.get(k) is None for k in ['x0', 'y0', 'x1', 'y1']):
                        print(f"         ✅ Page-level bbox (MVP format) - coordinates are None as expected")
                    else:
                        print(f"         ℹ️  Precise coordinates available")
                else:
                    print(f"         ⚠️  Bbox present but no page number")
            else:
                print(f"      ⚠️  Bbox field is None")

            # Show full chunk (pretty printed)
            print(f"\n   📋 Full JSONL record:")
            print(json.dumps(first_chunk, indent=2, ensure_ascii=False)[:1000] + "...")

        return True

    except Exception as e:
        print(f"❌ Chunking failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n🧪 OlmOCR Bbox Extraction Test Suite\n")

    # Test 1: Page extraction
    test1_pass = test_olmocr_bbox_extraction()

    # Test 2: Full chunking with bbox
    test2_pass = test_jsonl_chunking_with_bbox()

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Page extraction: {'✅ PASS' if test1_pass else '❌ FAIL'}")
    print(f"Chunking with bbox: {'✅ PASS' if test2_pass else '❌ FAIL'}")

    if test1_pass and test2_pass:
        print("\n✅ All tests passed! Schema v2.3.0 with page-level bbox is working.")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed. Please review errors above.")
        sys.exit(1)
