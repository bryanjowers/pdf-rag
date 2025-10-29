#!/usr/bin/env python3
"""
rag_query.py - RAG Query API for legal document search

Provides semantic search with entity filtering for the legal RAG pipeline.
"""

from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json


class RAGQuery:
    """RAG query interface with semantic search and entity filtering"""

    def __init__(
        self,
        collection_name: str = "legal_docs_v2_3",
        host: str = "localhost",
        port: int = 6333,
        embedding_model: str = "all-mpnet-base-v2"
    ):
        """
        Initialize RAG query system.

        Args:
            collection_name: Qdrant collection name
            host: Qdrant host
            port: Qdrant port
            embedding_model: Embedding model name
        """
        from olmocr_pipeline.utils_qdrant import QdrantLoader
        from olmocr_pipeline.utils_embeddings import EmbeddingGenerator

        self.loader = QdrantLoader(
            collection_name=collection_name,
            host=host,
            port=port,
            in_memory=False
        )

        self.embedding_gen = EmbeddingGenerator(model_name=embedding_model)

        print(f"✅ RAG Query initialized")
        print(f"   Collection: {collection_name}")
        print(f"   Qdrant: {host}:{port}")
        print(f"   Embedding model: {embedding_model}")

    def semantic_search(
        self,
        query: str,
        limit: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[Dict]:
        """
        Semantic search across all documents.

        Args:
            query: Search query text
            limit: Max results to return
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of results with score and metadata
        """
        results = self.loader.search(
            query_text=query,
            embedding_generator=self.embedding_gen,
            limit=limit,
            score_threshold=score_threshold
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "score": result.score,
                "text": result.payload.get("text"),
                "doc_id": result.payload.get("doc_id"),
                "chunk_index": result.payload.get("chunk_index"),
                "source_filename": result.payload.get("source_filename"),
                "page": result.payload.get("page"),
                "has_entities": result.payload.get("has_entities", False),
                "entity_count": result.payload.get("entity_count", 0),
                "entity_types": result.payload.get("entity_types", [])
            })

        return formatted_results

    def search_with_entity_filter(
        self,
        query: str,
        entity_types: Optional[List[str]] = None,
        require_entities: bool = False,
        limit: int = 10,
        score_threshold: Optional[float] = None
    ) -> List[Dict]:
        """
        Semantic search with entity-based filtering.

        Args:
            query: Search query text
            entity_types: Filter by entity types (e.g., ["PERSON", "ORG"])
            require_entities: Only return chunks with entities
            limit: Max results to return
            score_threshold: Minimum similarity score

        Returns:
            List of filtered results
        """
        # Build Qdrant filter
        filter_conditions = None

        if require_entities or entity_types:
            from qdrant_client.http import models

            must_conditions = []

            if require_entities:
                must_conditions.append(
                    models.FieldCondition(
                        key="has_entities",
                        match=models.MatchValue(value=True)
                    )
                )

            if entity_types:
                must_conditions.append(
                    models.FieldCondition(
                        key="entity_types",
                        match=models.MatchAny(any=entity_types)
                    )
                )

            filter_conditions = models.Filter(must=must_conditions)

        # Search with filter
        results = self.loader.client.search(
            collection_name=self.loader.collection_name,
            query_vector=self.embedding_gen.generate(query).tolist(),
            limit=limit,
            score_threshold=score_threshold,
            query_filter=filter_conditions,
            with_payload=True
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                "score": result.score,
                "text": result.payload.get("text"),
                "doc_id": result.payload.get("doc_id"),
                "chunk_index": result.payload.get("chunk_index"),
                "source_filename": result.payload.get("source_filename"),
                "page": result.payload.get("page"),
                "has_entities": result.payload.get("has_entities", False),
                "entity_count": result.payload.get("entity_count", 0),
                "entity_types": result.payload.get("entity_types", [])
            })

        return formatted_results

    def search_by_document(
        self,
        query: str,
        doc_id: str,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search within a specific document.

        Args:
            query: Search query
            doc_id: Document ID to search within
            limit: Max results

        Returns:
            List of results from specified document
        """
        from qdrant_client.http import models

        filter_conditions = models.Filter(
            must=[
                models.FieldCondition(
                    key="doc_id",
                    match=models.MatchValue(value=doc_id)
                )
            ]
        )

        results = self.loader.client.search(
            collection_name=self.loader.collection_name,
            query_vector=self.embedding_gen.generate(query).tolist(),
            limit=limit,
            query_filter=filter_conditions,
            with_payload=True
        )

        formatted_results = []
        for result in results:
            formatted_results.append({
                "score": result.score,
                "text": result.payload.get("text"),
                "doc_id": result.payload.get("doc_id"),
                "chunk_index": result.payload.get("chunk_index"),
                "source_filename": result.payload.get("source_filename"),
                "page": result.payload.get("page"),
                "has_entities": result.payload.get("has_entities", False),
                "entity_count": result.payload.get("entity_count", 0),
                "entity_types": result.payload.get("entity_types", [])
            })

        return formatted_results

    def get_chunk_context(
        self,
        doc_id: str,
        chunk_index: int,
        context_window: int = 1
    ) -> Dict:
        """
        Get a chunk with surrounding context chunks.

        Args:
            doc_id: Document ID
            chunk_index: Chunk index
            context_window: Number of chunks before/after to include

        Returns:
            Dict with target chunk and context
        """
        from qdrant_client.http import models

        # Get target chunk and surrounding chunks
        min_index = max(0, chunk_index - context_window)
        max_index = chunk_index + context_window

        filter_conditions = models.Filter(
            must=[
                models.FieldCondition(
                    key="doc_id",
                    match=models.MatchValue(value=doc_id)
                ),
                models.FieldCondition(
                    key="chunk_index",
                    range=models.Range(
                        gte=min_index,
                        lte=max_index
                    )
                )
            ]
        )

        # Use scroll to get filtered results (not vector search)
        results, _ = self.loader.client.scroll(
            collection_name=self.loader.collection_name,
            scroll_filter=filter_conditions,
            limit=100,  # Should be more than enough
            with_payload=True
        )

        # Sort by chunk_index
        sorted_results = sorted(results, key=lambda x: x.payload.get("chunk_index", 0))

        chunks = []
        for result in sorted_results:
            chunks.append({
                "chunk_index": result.payload.get("chunk_index"),
                "text": result.payload.get("text"),
                "page": result.payload.get("page"),
                "is_target": result.payload.get("chunk_index") == chunk_index
            })

        return {
            "doc_id": doc_id,
            "target_chunk_index": chunk_index,
            "chunks": chunks,
            "context_window": context_window
        }

    def get_collection_stats(self) -> Dict:
        """Get collection statistics"""
        info = self.loader.get_collection_info()

        # Get entity statistics if available
        from qdrant_client.http import models

        # Count chunks with entities
        try:
            filter_with_entities = models.Filter(
                must=[
                    models.FieldCondition(
                        key="has_entities",
                        match=models.MatchValue(value=True)
                    )
                ]
            )

            # Use count endpoint
            count_result = self.loader.client.count(
                collection_name=self.loader.collection_name,
                count_filter=filter_with_entities
            )
            chunks_with_entities = count_result.count
        except:
            chunks_with_entities = "N/A"

        return {
            "collection_name": info.get("name"),
            "total_chunks": info.get("points_count"),
            "chunks_with_entities": chunks_with_entities,
            "status": info.get("status")
        }


def format_result(result: Dict, show_entities: bool = True) -> str:
    """Format a search result for display"""
    lines = []
    lines.append(f"Score: {result['score']:.3f}")
    lines.append(f"Source: {result.get('source_filename', 'N/A')}")

    if result.get('page'):
        lines.append(f"Page: {result['page']}")

    if show_entities and result.get('has_entities'):
        lines.append(f"Entities: {result['entity_count']} ({', '.join(result.get('entity_types', []))})")

    lines.append(f"\nText: {result['text'][:300]}...")

    return "\n".join(lines)
