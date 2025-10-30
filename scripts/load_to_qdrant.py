#!/usr/bin/env python3
"""
load_to_qdrant.py - Load processed documents into Qdrant vector database

This is a critical component of the RAG pipeline that bridges document processing
and query capabilities. Run this after processing documents to make them searchable.

Usage:
    python load_to_qdrant.py                    # Append new documents
    python load_to_qdrant.py --recreate         # Wipe and reload everything
    python load_to_qdrant.py --stats-only       # Just show what would be loaded
"""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from olmocr_pipeline.utils_qdrant import QdrantLoader


def load_jsonl_files(jsonl_dir: Path, pattern="*.jsonl"):
    """Load all JSONL files from directory"""
    all_chunks = []
    file_stats = []

    for jsonl_path in sorted(jsonl_dir.glob(pattern)):
        chunks = []
        with open(jsonl_path) as f:
            for line in f:
                if line.strip():
                    chunks.append(json.loads(line))

        # Check if chunks have embeddings and entities
        with_embeddings = sum(1 for c in chunks if 'embedding' in c)
        with_entities = sum(1 for c in chunks if 'entities' in c and c['entities'].get('extracted_entities'))

        file_stats.append({
            'file': jsonl_path.name,
            'total_chunks': len(chunks),
            'with_embeddings': with_embeddings,
            'with_entities': with_entities
        })

        all_chunks.extend(chunks)

    return all_chunks, file_stats


def main():
    parser = argparse.ArgumentParser(
        description="Load processed documents into Qdrant vector database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python load_to_qdrant.py                    # Append new documents (default)
  python load_to_qdrant.py --recreate         # Wipe collection and reload all
  python load_to_qdrant.py --stats-only       # Preview without loading
  python load_to_qdrant.py --collection test  # Use different collection name
        """
    )

    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete existing collection and recreate (WARNING: deletes all data)"
    )

    parser.add_argument(
        "--stats-only",
        action="store_true",
        help="Show statistics without loading to Qdrant"
    )

    parser.add_argument(
        "--collection",
        type=str,
        default="legal_docs_v2_3",
        help="Qdrant collection name (default: legal_docs_v2_3)"
    )

    parser.add_argument(
        "--jsonl-dir",
        type=Path,
        default=Path("/mnt/gcs/legal-ocr-results/rag_staging/jsonl"),
        help="Directory containing JSONL files"
    )

    args = parser.parse_args()

    print("="*70)
    print("LOAD DOCUMENTS TO QDRANT")
    print("="*70)

    # Load documents
    print(f"\n1. Loading JSONL files from {args.jsonl_dir}")
    if not args.jsonl_dir.exists():
        print(f"❌ Directory not found: {args.jsonl_dir}")
        return 1

    all_chunks, file_stats = load_jsonl_files(args.jsonl_dir)

    print(f"\n📊 Files Found:")
    for stat in file_stats:
        print(f"   {stat['file']:<50} "
              f"Chunks: {stat['total_chunks']:>3} | "
              f"Embeddings: {stat['with_embeddings']:>3} | "
              f"Entities: {stat['with_entities']:>3}")

    # Filter to chunks with embeddings
    chunks_with_embeddings = [c for c in all_chunks if 'embedding' in c]
    chunks_with_entities = [c for c in chunks_with_embeddings if 'entities' in c and c['entities'].get('extracted_entities')]

    print(f"\n2. Summary:")
    print(f"   Total files: {len(file_stats)}")
    print(f"   Total chunks: {len(all_chunks)}")
    print(f"   Chunks with embeddings: {len(chunks_with_embeddings)}")
    print(f"   Chunks with entities: {len(chunks_with_entities)}")

    if not chunks_with_embeddings:
        print("\n❌ No chunks with embeddings found!")
        return 1

    if args.stats_only:
        print("\n📊 Stats-only mode - exiting without loading")
        return 0

    # Connect to Qdrant
    print(f"\n3. Connecting to Qdrant...")
    loader = QdrantLoader(
        collection_name=args.collection,
        host="localhost",
        port=6333,
        in_memory=False
    )

    # Create or verify collection
    if args.recreate:
        print(f"\n⚠️  RECREATE mode - deleting existing collection!")
        confirm = input("   Type 'yes' to confirm: ")
        if confirm.lower() != 'yes':
            print("   Aborted.")
            return 1

        print(f"\n4. Recreating collection...")
        loader.create_collection(vector_size=768, force_recreate=True)
    else:
        print(f"\n4. Verifying collection exists (creating if needed)...")
        try:
            loader.create_collection(vector_size=768, force_recreate=False)
        except:
            print(f"   Collection doesn't exist, creating...")
            loader.create_collection(vector_size=768, force_recreate=True)

    # Upload
    print(f"\n5. Uploading {len(chunks_with_embeddings)} chunks...")
    uploaded_count = loader.upload_chunks(chunks_with_embeddings)

    # Verify
    print(f"\n6. Verifying...")
    info = loader.get_collection_info()

    print(f"\n{'='*70}")
    print("COLLECTION INFO")
    print(f"{'='*70}")
    print(f"   Collection: {info.get('name')}")
    print(f"   Points: {info.get('points_count')}")
    print(f"   Status: {info.get('status')}")

    print(f"\n{'='*70}")
    print("✅ LOAD COMPLETE")
    print(f"{'='*70}")
    print(f"Uploaded {uploaded_count} chunks to Qdrant")
    print(f"Chunks with entities: {len(chunks_with_entities)}")
    print(f"\nReady to query: python query_cli.py")

    return 0


if __name__ == "__main__":
    sys.exit(main())
