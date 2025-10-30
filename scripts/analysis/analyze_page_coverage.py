#!/usr/bin/env python3
"""Analyze which pages are actually covered in the scanned output"""

import json
from pathlib import Path

# Read the scanned JSONL
jsonl_path = Path('/home/bryanjowers/pdf-rag/test_output/validation_test/scanned_output/jsonl/scanned_temp.jsonl')

print('='*70)
print('DETAILED PAGE COVERAGE ANALYSIS')
print('='*70)

chunks = []
with open(jsonl_path) as f:
    for line in f:
        chunks.append(json.loads(line))

print(f'\nTotal chunks: {len(chunks)}')

# Analyze each chunk
print(f'\nChunk Details:')
print(f'{"Chunk":<8} {"ID":<25} {"Chars":<10} {"Bbox?":<8} {"Page"}')
print('-'*70)

for i, chunk in enumerate(chunks, 1):
    chunk_id = chunk.get('id', 'N/A')
    text_len = len(chunk.get('text', ''))
    bbox = chunk.get('attrs', {}).get('bbox')
    has_bbox = 'Yes' if bbox else 'No'
    page_num = bbox.get('page', 'N/A') if bbox else 'N/A'

    print(f'{i:<8} {chunk_id:<25} {text_len:<10} {has_bbox:<8} {page_num}')

total_chars = sum(len(c.get('text', '')) for c in chunks)
chunks_with_bbox = sum(1 for c in chunks if c.get('attrs', {}).get('bbox'))

print(f'\n' + '='*70)
print('SUMMARY')
print('='*70)
print(f'Total characters: {total_chars:,}')
print(f'Chunks with bbox: {chunks_with_bbox}/{len(chunks)}')

# Now let's look at the actual text to see what sections are covered
print(f'\n' + '='*70)
print('CONTENT COVERAGE CHECK')
print('='*70)

# Read the markdown to see where it ends
md_path = Path('/home/bryanjowers/pdf-rag/test_output/validation_test/scanned_temp.md')
with open(md_path) as f:
    md_content = f.read()

# Check for key sections (from the table of contents)
sections_to_check = [
    ('TABLE OF CONTENTS', 'page 1-2'),
    ('SUBJECT PROPERTY', 'page 3-4'),
    ('MATERIALS EXAMINED', 'page 4-5'),
    ('OWNERSHIP OF THE SUBJECT PROPERTY', 'page 5-7'),
    ('OIL AND GAS LEASE ANALYSIS', 'page 8-9'),
    ('OIL AND GAS LEASE ASSIGNMENTS', 'page 10-13'),
    ('EASEMENTS AND RIGHTS-OF-WAY', 'page 15'),
    ('COMMENTS AND REQUIREMENTS', 'page 16-27'),
    ('1. AFFIDAVITS OF USE AND POSSESSION', 'page 16'),
    ('10. MEMORANDUM OF GAS GATHERING AGREEMENT', 'page ~20'),
    ('15. AUTHORITY OF TRUSTEE', 'page ~22'),
    ('20. AD VALOREM TAXES', 'page ~25'),
    ('24. MISCELLANEOUS LIMITATIONS', 'page ~26'),
    ('EXHIBIT', 'page 28'),
]

print(f'\n{"Section":<50} {"Found?":<10} {"Expected Page"}')
print('-'*70)

for section, page_ref in sections_to_check:
    found = 'YES' if section in md_content else 'NO'
    print(f'{section:<50} {found:<10} {page_ref}')

# Check the last line
last_lines = md_content.strip().split('\n')[-5:]
print(f'\n' + '='*70)
print('LAST 5 LINES OF MARKDOWN:')
print('='*70)
for line in last_lines:
    print(line[:100])  # First 100 chars of each line
