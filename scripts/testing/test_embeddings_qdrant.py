#!/usr/bin/env python3
"""Test embeddings + Qdrant integration"""

import sys
import json
from pathlib import Path

# Add olmocr_pipeline to path
sys.path.insert(0, str(Path(__file__).parent / "olmocr_pipeline"))

from utils_embeddings import EmbeddingGenerator, format_embedding_stats
from utils_qdrant import QdrantLoader

print("=" * 70)
print("EMBEDDINGS + QDRANT INTEGRATION TEST")
print("=" * 70)
print()

# Step 1: Load existing JSONL chunks
jsonl_path = Path("test_output/entity_retest/SDTO_170.0 ac 12-5-2022.jsonl")

if not jsonl_path.exists():
    print(f"❌ JSONL not found: {jsonl_path}")
    print("   Run entity extraction test first")
    sys.exit(1)

print(f"📄 Loading chunks from: {jsonl_path.name}")
chunks = []
with open(jsonl_path) as f:
    for line in f:
        chunks.append(json.loads(line))

print(f"   Loaded {len(chunks)} chunks")
print()

# Step 2: Generate embeddings
print("🔢 Generating embeddings...")
gen = EmbeddingGenerator(model_name="all-mpnet-base-v2")
chunks = gen.add_embeddings_to_chunks(chunks, show_progress=True)
print(f"   {format_embedding_stats(chunks)}")
print()

# Step 3: Initialize Qdrant (in-memory for testing)
print("💾 Initializing Qdrant (in-memory)...")
loader = QdrantLoader(collection_name="test_legal_docs", in_memory=True)
loader.create_collection(vector_size=gen.dimension, force_recreate=True)
print()

# Step 4: Upload chunks
print("⬆️  Uploading chunks to Qdrant...")
uploaded = loader.upload_chunks(chunks)
print()

# Step 5: Test semantic search
print("🔍 Testing semantic search...")
print()

queries = [
    "Who are the grantors and grantees?",
    "What are the property parcels?",
    "When was this recorded?",
    "What are the monetary amounts?"
]

for query in queries:
    print(f"Query: \"{query}\"")
    results = loader.search(query, gen, limit=2, score_threshold=0.3)

    if not results:
        print("   No results found")
    else:
        for i, result in enumerate(results, 1):
            score = result.score
            text_preview = result.payload['text'][:100].replace('\n', ' ')
            page = result.payload.get('page', '?')
            print(f"   {i}. [Score: {score:.3f}] [Page: {page}]")
            print(f"      {text_preview}...")
    print()

# Step 6: Collection info
print("📊 Collection Statistics:")
info = loader.get_collection_info()
for key, value in info.items():
    print(f"   {key}: {value}")
print()

print("✅ Test complete!")
print()
print("Next steps:")
print("  1. Integrate into pdf_digital.py and pdf_scanned.py handlers")
print("  2. Add embeddings/qdrant config to config/default.yaml")
print("  3. Test with full pipeline")
