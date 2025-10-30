#!/usr/bin/env python3
"""Quick script to inspect bbox data in JSONL files"""

import json
from pathlib import Path

def inspect_jsonl(file_path, label):
    print(f"\n{'='*70}")
    print(f"{label}")
    print(f"{'='*70}")
    print(f"File: {file_path}\n")

    with open(file_path) as f:
        for i, line in enumerate(f, 1):
            chunk = json.loads(line)
            bbox = chunk.get('attrs', {}).get('bbox')
            text_preview = chunk.get('text', '')[:100].replace('\n', ' ')

            print(f"Chunk {i}:")
            print(f"  ID: {chunk.get('id')}")
            print(f"  Text length: {len(chunk.get('text', ''))} chars")
            print(f"  Text preview: {text_preview}...")
            print(f"  Bbox: {bbox}")
            print()

if __name__ == "__main__":
    base = Path("/home/bryanjowers/pdf-rag/test_output/validation_test")

    digital_jsonl = base / "digital_output/jsonl/SDTO_170.0 ac 12-5-2022.jsonl"
    scanned_jsonl = base / "scanned_output/jsonl/scanned_temp.jsonl"

    inspect_jsonl(digital_jsonl, "DIGITAL PIPELINE (Docling) - Element-Level Bbox")
    inspect_jsonl(scanned_jsonl, "SCANNED PIPELINE (OlmOCR) - Page-Level Bbox")

    # Summary comparison
    print(f"\n{'='*70}")
    print("SUMMARY COMPARISON")
    print(f"{'='*70}")

    with open(digital_jsonl) as f:
        digital_chunks = [json.loads(line) for line in f]

    with open(scanned_jsonl) as f:
        scanned_chunks = [json.loads(line) for line in f]

    digital_chars = sum(len(c.get('text', '')) for c in digital_chunks)
    scanned_chars = sum(len(c.get('text', '')) for c in scanned_chunks)

    digital_with_bbox = sum(1 for c in digital_chunks if c.get('attrs', {}).get('bbox') is not None)
    scanned_with_bbox = sum(1 for c in scanned_chunks if c.get('attrs', {}).get('bbox') is not None)

    print(f"Digital: {len(digital_chunks)} chunks, {digital_chars:,} chars, {digital_with_bbox}/{len(digital_chunks)} with bbox")
    print(f"Scanned: {len(scanned_chunks)} chunks, {scanned_chars:,} chars, {scanned_with_bbox}/{len(scanned_chunks)} with bbox")
    print(f"Coverage: {scanned_chars/digital_chars*100:.1f}% of digital content")
    print()
