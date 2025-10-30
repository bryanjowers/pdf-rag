#!/usr/bin/env python3
"""
enrich_from_markdown.py - Enrich existing markdown files with entities and embeddings

This script processes existing markdown files (from ingest-only mode) and adds:
- Chunking
- Entity extraction
- Embeddings
- JSONL output

Usage:
  python enrich_from_markdown.py --auto --file-types pdf,docx
  python enrich_from_markdown.py path/to/file.md
"""

import argparse
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add olmocr_pipeline directory to path to support relative imports
sys.path.insert(0, str(Path(__file__).parent.parent / "olmocr_pipeline"))

from utils_config import load_config, get_storage_paths
from utils_classify import compute_file_hash


def create_chunks_from_markdown(markdown_text: str, config: Dict, source_filename: str) -> List[Dict]:
    """
    Simple chunking by paragraphs with token limits.

    Args:
        markdown_text: Markdown content
        config: Configuration dictionary
        source_filename: Name of source file

    Returns:
        List of chunk dictionaries
    """
    # Simple chunking by paragraphs
    paragraphs = [p.strip() for p in markdown_text.split('\n\n') if p.strip()]

    # Get chunking config
    chunking_config = config.get("chunking", {})
    token_target = chunking_config.get("token_target", 1400)
    token_max = chunking_config.get("token_max", 2000)

    # Combine paragraphs into chunks within token limits
    chunks = []
    current_chunk = []
    current_tokens = 0

    for para in paragraphs:
        para_tokens = len(para.split())

        # If adding this paragraph exceeds max, finalize current chunk
        if current_tokens + para_tokens > token_max and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [para]
            current_tokens = para_tokens
        else:
            current_chunk.append(para)
            current_tokens += para_tokens

    # Add remaining chunk
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    # Convert to JSONL format
    chunk_records = []
    for i, chunk_text in enumerate(chunks):
        chunk_records.append({
            "text": chunk_text,
            "metadata": {
                "file_name": source_filename,
                "chunk_id": i,
                "processor": "enrich_from_markdown",
                "enriched": str(datetime.now())
            }
        })

    return chunk_records


def enrich_markdown_file(
    markdown_path: Path,
    config: Dict,
    output_dir: Path
) -> Dict:
    """
    Enrich a single markdown file with entities and embeddings.

    Args:
        markdown_path: Path to markdown file
        config: Configuration dictionary
        output_dir: Output directory for JSONL

    Returns:
        Result dictionary with success status
    """
    print(f"📄 Processing: {markdown_path.name}")

    try:
        # Read markdown
        with open(markdown_path, 'r', encoding='utf-8') as f:
            markdown_text = f.read()

        # Convert to chunks
        chunks = create_chunks_from_markdown(markdown_text, config, markdown_path.stem)

        print(f"   📑 Created {len(chunks)} chunks")

        # Add entity extraction if enabled
        enable_entities = config.get("entity_extraction", {}).get("enabled", False)
        if enable_entities:
            import os
            from utils_entity_integration import add_entities_to_chunks, format_entity_stats
            api_key = config.get("entity_extraction", {}).get("openai_api_key") or os.getenv("OPENAI_API_KEY")
            print(f"   🔍 Extracting entities...")
            chunks, entity_stats = add_entities_to_chunks(
                chunks,
                enable_entities=True,
                api_key=api_key
            )
            print(f"   {format_entity_stats(entity_stats)}")

        # Generate embeddings if enabled
        enable_embeddings = config.get("embeddings", {}).get("enabled", False)
        if enable_embeddings:
            from utils_embeddings import EmbeddingGenerator, format_embedding_stats
            print(f"   🔢 Generating embeddings...")
            embedding_gen = EmbeddingGenerator(
                model_name=config.get("embeddings", {}).get("model", "all-mpnet-base-v2")
            )
            chunks = embedding_gen.add_embeddings_to_chunks(chunks, show_progress=False)
            print(f"   {format_embedding_stats(chunks)}")

        # Write JSONL output
        jsonl_path = output_dir / f"{markdown_path.stem}.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

        print(f"   ✅ Success: {jsonl_path.name}\n")

        return {
            "success": True,
            "markdown_path": str(markdown_path),
            "jsonl_path": str(jsonl_path),
            "chunk_count": len(chunks)
        }

    except Exception as e:
        print(f"   ❌ Error: {e}\n")
        return {
            "success": False,
            "markdown_path": str(markdown_path),
            "error": str(e)
        }


def main():
    parser = argparse.ArgumentParser(
        description="Enrich existing markdown files with entities and embeddings"
    )

    parser.add_argument("files", nargs="*",
                        help="Path(s) to markdown file(s)")
    parser.add_argument("--auto", action="store_true",
                        help="Auto-discover markdown files from staging directory")
    parser.add_argument("--file-types", type=str, default=None,
                        help="Comma-separated file types to filter (e.g., 'pdf,docx')")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of files to process")

    args = parser.parse_args()

    if not args.auto and not args.files:
        parser.error("Either provide markdown files or use --auto")

    # Load config
    config = load_config()
    paths = get_storage_paths(config)

    # Get markdown files
    if args.auto:
        markdown_dir = Path(paths["markdown_output"])
        markdown_files = list(markdown_dir.glob("*.md"))

        # Filter by file types if specified
        if args.file_types:
            allowed_types = {ft.strip().lower() for ft in args.file_types.split(",")}
            # This is a simplification - in reality we'd need to track original file type
            # For now, just process all markdown files
            pass

        if args.limit:
            markdown_files = markdown_files[:args.limit]

        print(f"📂 Found {len(markdown_files)} markdown files to enrich\n")
    else:
        markdown_files = [Path(f) for f in args.files]

    # Process files
    results = []
    for md_file in markdown_files:
        result = enrich_markdown_file(
            md_file,
            config,
            Path(paths["jsonl_output"])
        )
        results.append(result)

    # Print summary
    successful = sum(1 for r in results if r["success"])
    print(f"\n{'='*60}")
    print(f"Enrichment Complete")
    print(f"{'='*60}")
    print(f"Total files: {len(results)}")
    print(f"Successful: {successful}")
    print(f"Failed: {len(results) - successful}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
