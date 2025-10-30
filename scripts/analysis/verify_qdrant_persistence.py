#!/usr/bin/env python3
"""
Verify Qdrant data persistence.

This script checks if data persists in Qdrant without reloading.
"""

from olmocr_pipeline.utils_qdrant import QdrantLoader
from olmocr_pipeline.utils_embeddings import EmbeddingGenerator


def main():
    print("="*70)
    print("VERIFY QDRANT PERSISTENCE")
    print("="*70)

    # Connect to existing collection (don't recreate)
    loader = QdrantLoader(
        collection_name="legal_docs_v2_3",
        host="localhost",
        port=6333,
        in_memory=False
    )

    # Get collection info
    info = loader.get_collection_info()

    print(f"\n{'='*70}")
    print("COLLECTION STATUS")
    print(f"{'='*70}")
    print(f"   Collection: {info.get('name')}")
    print(f"   Points: {info.get('points_count')}")
    print(f"   Status: {info.get('status')}")

    if info.get('points_count', 0) > 0:
        print("\n✅ Data persists! Collection has data.")

        # Test a search
        print(f"\n{'='*70}")
        print("TEST SEARCH")
        print(f"{'='*70}")

        embedding_gen = EmbeddingGenerator(model_name="all-mpnet-base-v2")

        query = "Who are the parties involved?"
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
                page = result.payload.get('page')
                print(f"   {i}. Score: {score:.3f} | Page: {page} | {text_preview}...")
            print("\n✅ Search working!")
        else:
            print("   ⚠️  No results found")

    else:
        print("\n❌ No data found! Collection is empty.")
        print("\nRun: python setup_persistent_qdrant.py")


if __name__ == "__main__":
    main()
