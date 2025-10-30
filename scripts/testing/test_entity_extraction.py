#!/usr/bin/env python3
"""Test entity extraction on validation document"""

import os
import sys
import json
from pathlib import Path

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

import yaml

print("=" * 70)
print("ENTITY EXTRACTION TEST")
print("=" * 70)
print()

# Check for API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("⚠️  OPENAI_API_KEY not set in environment")
    print()
    print("To run this test:")
    print("  export OPENAI_API_KEY='your-key-here'")
    print("  python test_entity_extraction.py")
    print()
    print("Or run with:")
    print("  OPENAI_API_KEY='your-key' python test_entity_extraction.py")
    print()
    sys.exit(1)

print(f"✅ OpenAI API key found ({len(api_key)} chars)")
print()

# Load config and enable entity extraction
config_path = Path("config/default.yaml")
with open(config_path) as f:
    config = yaml.safe_load(f)

# Enable entity extraction for this test
config["entity_extraction"]["enabled"] = True
config["entity_extraction"]["openai_api_key"] = api_key

print("📋 Entity extraction enabled:")
print(f"   Model: {config['entity_extraction']['extractor']}")
print(f"   Entity types: {', '.join(config['entity_extraction']['entity_types'])}")
print()

# Use existing processed document to save time
# We'll test on the scanned PDF since we have OlmOCR output
from handlers.pdf_scanned import process_scanned_pdf

pdf_path = Path("pdf_input/SDTO_170.0 ac 12-5-2022.pdf")
output_dir = Path("test_output/entity_test")
output_dir.mkdir(parents=True, exist_ok=True)

print(f"📄 Processing: {pdf_path.name}")
print(f"📁 Output: {output_dir}")
print()
print("🔄 Running OlmOCR + Entity Extraction...")
print()

result = process_scanned_pdf(
    pdf_path=pdf_path,
    output_dir=output_dir,
    config=config,
    batch_id="entity_test"
)

if not result["success"]:
    print(f"❌ Processing failed: {result['error']}")
    sys.exit(1)

print()
print("✅ Processing complete!")
print(f"   Duration: {result['processing_duration_ms']/1000:.1f}s")
print(f"   Chunks: {result['chunk_count']}")
print()

# Analyze entity extraction results
jsonl_path = result['jsonl_path']
print(f"📊 Analyzing entities in: {jsonl_path.name}")
print()

total_chunks = 0
chunks_with_entities = 0
total_entities = 0
total_cost = 0.0
entity_type_counts = {}

with open(jsonl_path) as f:
    for line in f:
        chunk = json.loads(line)
        total_chunks += 1

        entities_data = chunk.get("entities", {})
        if entities_data and "extracted_entities" in entities_data:
            extracted = entities_data["extracted_entities"]
            if extracted:
                chunks_with_entities += 1
                total_entities += len(extracted)

                # Count by type
                for entity in extracted:
                    etype = entity.get("type", "UNKNOWN")
                    entity_type_counts[etype] = entity_type_counts.get(etype, 0) + 1

                # Track cost
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

# Show sample entities
print("🔍 Sample entities (first chunk with entities):")
with open(jsonl_path) as f:
    for line in f:
        chunk = json.loads(line)
        entities_data = chunk.get("entities", {})
        if entities_data and entities_data.get("extracted_entities"):
            entities = entities_data["extracted_entities"][:5]  # First 5
            for i, entity in enumerate(entities, 1):
                etype = entity.get("type", "?")
                text = entity.get("text", "?")
                role = entity.get("role", "")
                role_str = f" ({role})" if role else ""
                print(f"   {i}. [{etype}] {text}{role_str}")
            break
print()

# Verdict
if total_entities == 0:
    print("❌ FAILED - No entities extracted!")
    sys.exit(1)
elif chunks_with_entities < total_chunks * 0.5:
    print(f"⚠️  LOW COVERAGE - Only {chunks_with_entities}/{total_chunks} chunks have entities")
    print("   This may be expected for documents with lots of tables/formatting")
    print()
    print("✅ Entity extraction is WORKING (but low coverage)")
    sys.exit(0)
else:
    print(f"✅ SUCCESS - Entity extraction working!")
    print(f"   Coverage: {chunks_with_entities}/{total_chunks} chunks")
    print(f"   Extracted {total_entities} entities across {len(entity_type_counts)} types")
    sys.exit(0)
