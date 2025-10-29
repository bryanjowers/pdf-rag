#!/usr/bin/env python3
"""
Quick spot check tool for entity extraction validation.
Shows source text + extracted entities side-by-side for manual review.
"""

import json
import random
from pathlib import Path
from textwrap import wrap

def truncate(text, max_len=100):
    """Truncate text with ellipsis"""
    if len(text) <= max_len:
        return text
    return text[:max_len-3] + "..."

def show_chunk_with_entities(chunk_idx, chunk):
    """Display chunk with entities for manual validation"""
    print("\n" + "="*80)
    print(f"CHUNK {chunk_idx}")
    print("="*80)

    # Show source text
    print("\n📄 SOURCE TEXT:")
    print("-" * 80)
    text = chunk['text']
    # Wrap text for readability
    lines = text.split('\n')
    for line in lines[:30]:  # First 30 lines
        if line.strip():
            for wrapped in wrap(line, width=78):
                print(wrapped)
    if len(lines) > 30:
        remaining = len(lines) - 30
        print(f"\n... [{remaining} more lines] ...")
    print("-" * 80)

    # Show extracted entities
    entities_data = chunk.get('entities', {})
    if not entities_data or 'extracted_entities' not in entities_data:
        print("\n⚠️  NO ENTITIES EXTRACTED")
        return

    entities = entities_data['extracted_entities']
    print(f"\n🔍 EXTRACTED ENTITIES ({len(entities)} total):")
    print("-" * 80)

    # Group by type
    by_type = {}
    for entity in entities:
        etype = entity.get('type', 'UNKNOWN')
        if etype not in by_type:
            by_type[etype] = []
        by_type[etype].append(entity)

    # Display by type
    for etype in ['ORG', 'PERSON', 'PARCEL', 'DATE', 'AMOUNT']:
        if etype in by_type:
            print(f"\n  {etype} ({len(by_type[etype])}):")
            for entity in by_type[etype]:
                text = entity.get('text', '?')
                role = entity.get('role', '')
                conf = entity.get('confidence', 0)

                # Check if entity text appears in source
                if entity.get('text') and entity['text'] in chunk['text']:
                    marker = "✅"
                elif entity.get('text') and entity['text'].lower() in chunk['text'].lower():
                    marker = "⚠️"  # Case mismatch but found
                else:
                    marker = "❌"  # POTENTIAL HALLUCINATION

                role_str = f" ({role})" if role and role != "null" else ""
                print(f"    {marker} {truncate(text, 60)}{role_str} [conf: {conf:.2f}]")

    print("\n" + "-" * 80)
    print("\nLEGEND:")
    print("  ✅ = Found exact match in source text")
    print("  ⚠️  = Found case-insensitive match")
    print("  ❌ = NOT FOUND (potential hallucination)")

def main():
    # Load JSONL
    jsonl_path = Path("test_output/entity_retest/SDTO_170.0 ac 12-5-2022.jsonl")

    if not jsonl_path.exists():
        print(f"❌ JSONL not found: {jsonl_path}")
        print("   Run entity extraction test first:")
        print("   python test_entity_extraction_fast.py")
        return

    # Load all chunks
    chunks = []
    with open(jsonl_path) as f:
        for line in f:
            chunks.append(json.loads(line))

    print("="*80)
    print("ENTITY EXTRACTION SPOT CHECK")
    print("="*80)
    print(f"\nTotal chunks: {len(chunks)}")
    print()

    # Sample 3 random chunks (or all if <3)
    sample_size = min(3, len(chunks))
    sampled_indices = random.sample(range(len(chunks)), sample_size)

    print(f"Reviewing {sample_size} randomly selected chunks:")
    print(f"Indices: {sampled_indices}")

    # Show each chunk
    for idx in sampled_indices:
        show_chunk_with_entities(idx, chunks[idx])

    # Summary
    print("\n" + "="*80)
    print("SPOT CHECK COMPLETE")
    print("="*80)
    print()
    print("🔍 VALIDATION CHECKLIST:")
    print()
    print("1. ❌ markers → Potential hallucinations (entity not in source)")
    print("2. Missing entities → Compare source text to extracted list")
    print("3. Wrong entity types → ORG vs PERSON vs PARCEL confusion")
    print("4. Wrong roles → Grantor/grantee misidentification")
    print("5. Date errors → Incorrect year/month/day")
    print()
    print("If issues found:")
    print("  - Document in docs/planning/ENTITY_EXTRACTION_ISSUES.md")
    print("  - Revise prompt in olmocr_pipeline/utils_entity.py")
    print("  - Retest with: python test_entity_extraction_fast.py")
    print()
    print("If looks good:")
    print("  ✅ Entity extraction validated - safe to proceed to Task 4")
    print()

if __name__ == "__main__":
    main()
