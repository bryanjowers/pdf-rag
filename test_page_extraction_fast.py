#!/usr/bin/env python3
"""Test page extraction from existing OlmOCR JSONL output (no reprocessing needed)"""

import sys
import json
from pathlib import Path

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

from utils_olmocr import olmocr_jsonl_to_markdown_with_pages, olmocr_to_jsonl
from utils_classify import compute_file_hash
import yaml

print("=" * 70)
print("FAST PAGE EXTRACTION TEST (using existing OlmOCR output)")
print("=" * 70)
print()

# Use existing OlmOCR JSONL
olmocr_jsonl = Path("test_output/bbox_fix_test/olmocr_staging/results/output_c0c43b4cea29f38834a866c1fc85eb530deb8b96.jsonl")
source_pdf = Path("pdf_input/SDTO_170.0 ac 12-5-2022.pdf")

if not olmocr_jsonl.exists():
    print(f"❌ OlmOCR JSONL not found: {olmocr_jsonl}")
    sys.exit(1)

print(f"📄 Source PDF: {source_pdf.name}")
print(f"📊 OlmOCR JSONL: {olmocr_jsonl.name}")
print()

# Load config
with open("config/default.yaml") as f:
    config = yaml.safe_load(f)

# Step 1: Extract markdown + page mapping from OlmOCR JSONL
print("🔍 Extracting page mappings from OlmOCR JSONL...")
markdown_content, page_map = olmocr_jsonl_to_markdown_with_pages(olmocr_jsonl)

print(f"   Markdown length: {len(markdown_content):,} chars")
print(f"   Page ranges found: {len(page_map)}")
print(f"   Sample ranges: {list(page_map.items())[:3]}")
print()

# Step 2: Convert to JSONL chunks
print("📦 Converting to JSONL chunks...")
chunks = olmocr_to_jsonl(
    markdown_content,
    source_pdf,
    config,
    batch_id="fast_test",
    page_mapping=page_map
)

print(f"   Total chunks: {len(chunks)}")
print()

# Step 3: Analyze bbox coverage
print("📊 Analyzing bbox coverage...")
chunks_with_bbox = 0
pages_found = set()

for chunk in chunks:
    bbox = chunk['attrs'].get('bbox')
    if bbox and bbox.get('page') is not None:
        chunks_with_bbox += 1
        pages_found.add(bbox['page'])

coverage_pct = 100 * chunks_with_bbox / len(chunks) if chunks else 0

print(f"   Chunks with page data: {chunks_with_bbox}/{len(chunks)} ({coverage_pct:.1f}%)")
print(f"   Pages found: {sorted(pages_found)}")
print(f"   Page range: {min(pages_found) if pages_found else 'N/A'} - {max(pages_found) if pages_found else 'N/A'}")
print()

# Step 4: Show sample chunks
print("📄 Sample chunks:")
for i, chunk in enumerate(chunks[:3]):
    bbox = chunk['attrs'].get('bbox')
    page = bbox['page'] if bbox and bbox.get('page') is not None else 'None'
    text_preview = chunk['text'][:80].replace('\n', ' ')
    print(f"   Chunk {i}: Page {page} - \"{text_preview}...\"")
print()

# Verdict
if chunks_with_bbox == 0:
    print("❌ FAILED - No page data extracted!")
    sys.exit(1)
elif chunks_with_bbox < len(chunks) * 0.8:
    print(f"⚠️  PARTIAL - Only {coverage_pct:.1f}% coverage (expected >80%)")
    sys.exit(1)
else:
    print(f"✅ SUCCESS - {coverage_pct:.1f}% of chunks have page data!")
    print(f"✅ Page extraction working correctly!")
    sys.exit(0)
