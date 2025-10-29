#!/usr/bin/env python3
"""Test page number extraction from OlmOCR output"""

import sys
from pathlib import Path

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

from handlers.pdf_scanned import process_scanned_pdf
import yaml

# Load config
config_path = Path("config/default.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Test PDF
pdf_path = Path("pdf_input/SDTO_170.0 ac 12-5-2022.pdf")
output_dir = Path("test_output/page_extraction_test")
output_dir.mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("TESTING PAGE EXTRACTION FROM OLMOCR")
print("=" * 70)
print()

# Process
result = process_scanned_pdf(
    pdf_path=pdf_path,
    output_dir=output_dir,
    config=config,
    batch_id="page_test"
)

if result["success"]:
    print(f"\n✅ Processing successful")
    print(f"   JSONL: {result['jsonl_path']}")

    # Check bbox page coverage
    import json
    chunks_with_bbox = 0
    total_chunks = 0
    pages_found = set()

    with open(result['jsonl_path']) as f:
        for line in f:
            chunk = json.loads(line)
            total_chunks += 1
            bbox = chunk['attrs'].get('bbox')
            if bbox and bbox.get('page') is not None:
                chunks_with_bbox += 1
                pages_found.add(bbox['page'])

    print(f"\n📊 Results:")
    print(f"   Total chunks: {total_chunks}")
    print(f"   Chunks with page data: {chunks_with_bbox}")
    print(f"   Coverage: {chunks_with_bbox}/{total_chunks} ({100*chunks_with_bbox/total_chunks:.1f}%)")
    print(f"   Pages found: {sorted(pages_found)}")

    if chunks_with_bbox == 0:
        print(f"\n❌ NO PAGE DATA - Bug still present!")
        sys.exit(1)
    elif chunks_with_bbox < total_chunks * 0.8:
        print(f"\n⚠️  Low coverage - some chunks missing page data")
        sys.exit(1)
    else:
        print(f"\n✅ Good coverage - page extraction working!")
        sys.exit(0)
else:
    print(f"\n❌ Processing failed: {result['error']}")
    sys.exit(1)
