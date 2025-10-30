#!/usr/bin/env python3
"""
Setup persistent Qdrant collection and load test data.

This script:
1. Connects to persistent Qdrant server (localhost:6333)
2. Creates collection with correct schema
3. Loads processed test documents
4. Verifies data is persisted
"""

import json
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from olmocr_pipeline.utils_qdrant import QdrantLoader
from olmocr_pipeline.utils_embeddings import EmbeddingGenerator


def load_jsonl_chunks(jsonl_path: Path):
    """Load chunks from JSONL file"""
    chunks = []
    with open(jsonl_path) as f:
        for line in f:
            if line.strip():
                chunks.append(json.loads(line))
    return chunks


def main():
    print("="*70)
    print("PERSISTENT QDRANT SETUP")
    print("="*70)

    # 1. Connect to persistent Qdrant
    print("\n1. Connecting to Qdrant server...")
    loader = QdrantLoader(
        collection_name="legal_docs_v2_3",
        host="localhost",
        port=6333,
        in_memory=False  # Use persistent server
    )

    # 2. Create collection (768-dim for all-mpnet-base-v2)
    print("\n2. Creating collection...")
    loader.create_collection(vector_size=768, force_recreate=True)

    # 3. Find test documents with embeddings
    print("\n3. Looking for test documents...")
    test_files = [
        Path("test_output/entity_test/jsonl/SDTO_170.0 ac 12-5-2022.jsonl"),
        Path("test_output/bbox_fix_test/jsonl/SDTO_170.0 ac 12-5-2022.jsonl"),
    ]

    all_chunks = []
    for jsonl_path in test_files:
        if jsonl_path.exists():
            chunks = load_jsonl_chunks(jsonl_path)
            # Check if chunks have embeddings
            has_embeddings = any('embedding' in c for c in chunks)
            print(f"   📄 {jsonl_path.name}: {len(chunks)} chunks (embeddings: {has_embeddings})")
            all_chunks.extend(chunks)
        else:
            print(f"   ⚠️  {jsonl_path.name}: Not found")

    if not all_chunks:
        print("\n❌ No test documents found!")
        print("\nTo create test data, run:")
        print("  python test_embeddings_qdrant.py")
        return

    # Check if we need to generate embeddings
    chunks_with_embeddings = [c for c in all_chunks if 'embedding' in c]

    if not chunks_with_embeddings:
        print(f"\n4. Generating embeddings for {len(all_chunks)} chunks...")
        embedding_gen = EmbeddingGenerator(model_name="all-mpnet-base-v2")

        for i, chunk in enumerate(all_chunks):
            text = chunk.get('text', '')
            if text:
                embedding = embedding_gen.generate(text)
                chunk['embedding'] = embedding.tolist()

                if (i + 1) % 10 == 0:
                    print(f"   Generated {i+1}/{len(all_chunks)} embeddings...")

        print(f"   ✅ Generated {len(all_chunks)} embeddings")
        chunks_with_embeddings = all_chunks
    else:
        print(f"\n4. Found {len(chunks_with_embeddings)} chunks with embeddings")

    # 4. Upload to Qdrant
    print("\n5. Uploading to persistent Qdrant...")
    uploaded_count = loader.upload_chunks(chunks_with_embeddings)

    # 5. Verify
    print("\n6. Verifying collection...")
    info = loader.get_collection_info()

    print(f"\n{'='*70}")
    print("COLLECTION INFO")
    print(f"{'='*70}")
    print(f"   Collection: {info.get('name')}")
    print(f"   Points: {info.get('points_count')}")
    print(f"   Vectors: {info.get('vectors_count')}")
    print(f"   Status: {info.get('status')}")

    # 6. Test search
    print(f"\n{'='*70}")
    print("TEST SEARCH")
    print(f"{'='*70}")

    embedding_gen = EmbeddingGenerator(model_name="all-mpnet-base-v2")

    test_queries = [
        "Who are the grantors?",
        "What properties are involved?",
        "When was this executed?"
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = loader.search(
            query_text=query,
            embedding_generator=embedding_gen,
            limit=3
        )

        if results:
            for i, result in enumerate(results, 1):
                score = result.score
                text_preview = result.payload.get('text', '')[:100]
                print(f"   {i}. Score: {score:.3f} | {text_preview}...")
        else:
            print("   No results found")

    print(f"\n{'='*70}")
    print("✅ SETUP COMPLETE")
    print(f"{'='*70}")
    print(f"\nPersistent Qdrant collection 'legal_docs_v2_3' is ready!")
    print(f"Uploaded {uploaded_count} chunks with embeddings.")
    print(f"\nData will persist across server restarts.")
    print(f"Access Qdrant UI: http://localhost:6333/dashboard")


if __name__ == "__main__":
    main()
