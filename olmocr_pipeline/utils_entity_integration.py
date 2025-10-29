#!/usr/bin/env python3
"""
utils_entity_integration.py - Helper functions for integrating entity extraction

Provides clean integration of entity extraction into PDF processing pipelines.
Handles errors gracefully to avoid breaking document processing.
"""

import os
from typing import Dict, List, Optional, Tuple


def add_entities_to_chunks(
    chunks: List[Dict],
    enable_entities: bool = True,
    api_key: Optional[str] = None,
    extractor: str = "gpt-4o-mini",
    normalize: bool = True,
    track_costs: bool = True
) -> Tuple[List[Dict], Dict]:
    """
    Add entity extraction to JSONL chunks.

    Args:
        chunks: List of JSONL chunk dictionaries
        enable_entities: If False, skip entity extraction
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        extractor: Extractor to use ("gpt-4o-mini", "gliner", "spacy")
        normalize: If True, normalize and deduplicate entities
        track_costs: If True, track token usage and costs

    Returns:
        Tuple of (enriched_chunks, aggregate_stats):
        - enriched_chunks: Chunks with "entities" field added
        - aggregate_stats: Dict with extraction statistics

    Notes:
        - Does not fail pipeline if extraction fails
        - Sets entities.error field if extraction fails for a chunk
        - Accumulates costs across all chunks
    """
    if not enable_entities:
        return chunks, {
            "entities_extracted": False,
            "reason": "Entity extraction disabled in config"
        }

    # Import entity extraction (only if needed)
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent))
        from utils_entity import extract_entities
    except ImportError as e:
        # Return chunks unchanged if import fails
        return chunks, {
            "entities_extracted": False,
            "error": f"Failed to import utils_entity: {e}"
        }

    # Get API key
    api_key = api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return chunks, {
            "entities_extracted": False,
            "error": "OpenAI API key not found (set OPENAI_API_KEY environment variable)"
        }

    # Process each chunk
    total_cost = 0.0
    total_entities = 0
    total_tokens_in = 0
    total_tokens_out = 0
    chunks_with_entities = 0
    chunks_with_errors = 0

    for i, chunk in enumerate(chunks):
        try:
            # Extract entities from chunk text
            result = extract_entities(
                text=chunk["text"],
                extractor=extractor,
                normalize=normalize,
                api_key=api_key,
                track_costs=track_costs
            )

            # Add entities to chunk
            chunk["entities"] = {
                "extracted_entities": result.get("entities", []),
                "extraction_metadata": {
                    "model": result.get("model"),
                    "tokens_in": result.get("tokens_in"),
                    "tokens_out": result.get("tokens_out"),
                    "cost": result.get("cost"),
                    "extracted_at": result.get("extracted_at")
                }
            }

            # Accumulate stats
            total_cost += result.get("cost", 0.0)
            total_entities += len(result.get("entities", []))
            total_tokens_in += result.get("tokens_in", 0)
            total_tokens_out += result.get("tokens_out", 0)
            chunks_with_entities += 1

        except Exception as e:
            # Don't fail pipeline - just mark chunk as having extraction error
            chunk["entities"] = {
                "error": str(e),
                "extraction_metadata": None
            }
            chunks_with_errors += 1

    # Aggregate statistics
    stats = {
        "entities_extracted": True,
        "extractor": extractor,
        "total_entities": total_entities,
        "total_chunks_processed": len(chunks),
        "chunks_with_entities": chunks_with_entities,
        "chunks_with_errors": chunks_with_errors,
        "total_tokens_in": total_tokens_in,
        "total_tokens_out": total_tokens_out,
        "total_cost_usd": round(total_cost, 6)
    }

    return chunks, stats


def format_entity_stats(stats: Dict) -> str:
    """
    Format entity extraction statistics for logging.

    Args:
        stats: Statistics dict from add_entities_to_chunks()

    Returns:
        Formatted string for logging
    """
    if not stats.get("entities_extracted"):
        reason = stats.get("reason") or stats.get("error", "Unknown reason")
        return f"Entity extraction skipped: {reason}"

    lines = [
        f"   🔍 Entity Extraction Summary:",
        f"      Extractor: {stats.get('extractor', 'unknown')}",
        f"      Entities found: {stats.get('total_entities', 0)}",
        f"      Chunks processed: {stats.get('chunks_with_entities', 0)}/{stats.get('total_chunks_processed', 0)}",
        f"      Tokens: {stats.get('total_tokens_in', 0):,} in, {stats.get('total_tokens_out', 0):,} out",
        f"      Cost: ${stats.get('total_cost_usd', 0.0):.4f}"
    ]

    if stats.get("chunks_with_errors", 0) > 0:
        lines.append(f"      ⚠️  Errors: {stats['chunks_with_errors']} chunks failed")

    return "\n".join(lines)


# Export for use in handlers
__all__ = [
    "add_entities_to_chunks",
    "format_entity_stats"
]
