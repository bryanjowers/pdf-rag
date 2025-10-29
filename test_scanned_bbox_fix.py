#!/usr/bin/env python3
"""Quick test to verify markdown path bug fix"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

from handlers.pdf_scanned import process_scanned_pdf
import yaml

# Load config
config_path = Path(__file__).parent / "config" / "default.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

# Test PDF
test_pdf = Path("/home/bryanjowers/pdf-rag/pdf_input/SDTO_170.0 ac 12-5-2022.pdf")
output_dir = Path("/home/bryanjowers/pdf-rag/test_output/bbox_fix_test")
output_dir.mkdir(parents=True, exist_ok=True)

print("="*70)
print("TESTING MARKDOWN PATH BUG FIX")
print("="*70)
print(f"\nTest PDF: {test_pdf.name}")
print(f"Output: {output_dir}")

# Process
print("\n🔄 Processing with OlmOCR...")
result = process_scanned_pdf(
    pdf_path=test_pdf,
    output_dir=output_dir,
    config=config,
    batch_id="bbox_fix_test"
)

print("\n" + "="*70)
print("RESULTS")
print("="*70)
print(f"Success: {result['success']}")
print(f"Markdown: {result.get('markdown_path')}")
print(f"JSONL: {result.get('jsonl_path')}")
print(f"Chunks: {result.get('chunk_count', 0)}")
print(f"Chars: {result.get('char_count', 0):,}")

if result['success']:
    # Check bbox coverage
    import json
    jsonl_path = result['jsonl_path']

    chunks_with_bbox = 0
    total_chunks = 0

    with open(jsonl_path) as f:
        for line in f:
            chunk = json.loads(line)
            total_chunks += 1
            if chunk.get('attrs', {}).get('bbox'):
                chunks_with_bbox += 1

    print(f"\n📍 Bbox Coverage: {chunks_with_bbox}/{total_chunks} chunks")

    if chunks_with_bbox > 0:
        print("✅ BUG FIX SUCCESSFUL - Bbox data present!")
    else:
        print("⚠️  No bbox data found (may still need markdown file)")

print("\n" + "="*70)
