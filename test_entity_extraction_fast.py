#!/usr/bin/env python3
"""Fast entity extraction test - reuses existing chunks, only re-runs entity extraction"""

import os
import sys
import json
from pathlib import Path

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

import yaml

print("=" * 70)
print("FAST ENTITY EXTRACTION TEST (reusing existing chunks)")
print("=" * 70)
print()

# Check for API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("⚠️  OPENAI_API_KEY not set in environment")
    sys.exit(1)

print(f"✅ OpenAI API key found ({len(api_key)} chars)")
print()

# Load existing JSONL (without entities)
input_jsonl = Path("test_output/entity_test/jsonl/SDTO_170.0 ac 12-5-2022.jsonl")
if not input_jsonl.exists():
    print(f"❌ Input JSONL not found: {input_jsonl}")
    print("   Run the full test first: python test_entity_extraction.py")
    sys.exit(1)

output_jsonl = Path("test_output/entity_retest/SDTO_170.0 ac 12-5-2022.jsonl")
output_jsonl.parent.mkdir(parents=True, exist_ok=True)

print(f"📄 Input: {input_jsonl.name}")
print(f"📄 Output: {output_jsonl.name}")
print()

# Load config
with open("config/default.yaml") as f:
    config = yaml.safe_load(f)

config["entity_extraction"]["enabled"] = True
config["entity_extraction"]["openai_api_key"] = api_key

print("🔍 Re-running entity extraction with max_tokens=2500...")
print()

# Import entity extraction
from utils_entity_integration import add_entities_to_chunks

# Load chunks
chunks = []
with open(input_jsonl) as f:
    for line in f:
        chunk = json.loads(line)
        # Remove old entities field to start fresh
        if "entities" in chunk:
            del chunk["entities"]
        chunks.append(chunk)

print(f"   Loaded {len(chunks)} chunks")
print()

# Re-run entity extraction
enriched_chunks, entity_stats = add_entities_to_chunks(
    chunks,
    enable_entities=True,
    api_key=api_key
)

print()
print("✅ Entity extraction complete!")
print()

# Write output
with open(output_jsonl, "w") as f:
    for chunk in enriched_chunks:
        f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

print(f"📊 Statistics:")
print(f"   {entity_stats}")
print()

# Analyze results
total_chunks = len(enriched_chunks)
chunks_with_entities = 0
total_entities = 0
total_cost = 0.0
entity_type_counts = {}

for chunk in enriched_chunks:
    entities_data = chunk.get("entities", {})
    if entities_data and "extracted_entities" in entities_data:
        extracted = entities_data["extracted_entities"]
        if extracted:
            chunks_with_entities += 1
            total_entities += len(extracted)
            
            for entity in extracted:
                etype = entity.get("type", "UNKNOWN")
                entity_type_counts[etype] = entity_type_counts.get(etype, 0) + 1
            
            metadata = entities_data.get("extraction_metadata", {})
            if metadata and metadata.get("cost"):
                total_cost += metadata["cost"]

print("📈 Results:")
print(f"   Total chunks: {total_chunks}")
print(f"   Chunks with entities: {chunks_with_entities}")
print(f"   Total entities: {total_entities}")
print(f"   Cost: ${total_cost:.4f}")
print()

if entity_type_counts:
    print("📊 Entity types found:")
    for etype, count in sorted(entity_type_counts.items(), key=lambda x: -x[1]):
        print(f"   {etype}: {count}")
    print()

# Show sample entities from each chunk
print("🔍 Sample entities by chunk:")
for i, chunk in enumerate(enriched_chunks):
    entities_data = chunk.get("entities", {})
    if entities_data and entities_data.get("extracted_entities"):
        entities = entities_data["extracted_entities"][:3]  # First 3
        print(f"\n   Chunk {i} ({len(entities_data['extracted_entities'])} total):")
        for entity in entities:
            etype = entity.get("type", "?")
            text = entity.get("text", "?")
            role = entity.get("role", "")
            role_str = f" ({role})" if role and role != "null" else ""
            print(f"      [{etype}] {text}{role_str}")

print()

# Verdict
if total_entities == 0:
    print("❌ FAILED - No entities extracted!")
    sys.exit(1)
elif chunks_with_entities < total_chunks * 0.8:
    print(f"⚠️  Coverage: {chunks_with_entities}/{total_chunks} chunks ({100*chunks_with_entities/total_chunks:.0f}%)")
    print("✅ Entity extraction working but coverage could be better")
    sys.exit(0)
else:
    print(f"✅ SUCCESS - {chunks_with_entities}/{total_chunks} chunks have entities!")
    print(f"   Extracted {total_entities} entities across {len(entity_type_counts)} types")
    sys.exit(0)
