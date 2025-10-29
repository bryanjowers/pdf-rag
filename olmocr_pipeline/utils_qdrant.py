#!/usr/bin/env python3
"""
utils_qdrant.py - Qdrant vector database loader for RAG pipeline

Uploads chunks with embeddings to Qdrant for semantic search.
"""

from typing import List, Dict, Optional
from pathlib import Path
import json


class QdrantLoader:
    """Load chunks with embeddings into Qdrant vector database"""

    def __init__(
        self,
        collection_name: str = "legal_docs",
        host: str = "localhost",
        port: int = 6333,
        in_memory: bool = False
    ):
        """
        Initialize Qdrant client.

        Args:
            collection_name: Name of Qdrant collection
            host: Qdrant host (default: localhost)
            port: Qdrant port (default: 6333)
            in_memory: Use in-memory storage (for testing)
        """
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http import models
        except ImportError:
            raise ImportError(
                "qdrant-client not installed. Install with: pip install qdrant-client"
            )

        self.collection_name = collection_name

        if in_memory:
            self.client = QdrantClient(":memory:")
            print(f"   💾 Using in-memory Qdrant (data will not persist)")
        else:
            try:
                self.client = QdrantClient(host=host, port=port)
                # Test connection
                self.client.get_collections()
                print(f"   ✅ Connected to Qdrant at {host}:{port}")
            except Exception as e:
                print(f"   ⚠️  Could not connect to Qdrant at {host}:{port}")
                print(f"   ⚠️  Falling back to in-memory mode")
                print(f"   Error: {e}")
                self.client = QdrantClient(":memory:")

        self.models = models

    def create_collection(self, vector_size: int = 768, force_recreate: bool = False):
        """
        Create Qdrant collection if it doesn't exist.

        Args:
            vector_size: Embedding dimension (must match embedding model)
            force_recreate: Delete and recreate if exists
        """
        try:
            self.client.get_collection(self.collection_name)

            if force_recreate:
                print(f"   🗑️  Deleting existing collection '{self.collection_name}'")
                self.client.delete_collection(self.collection_name)
            else:
                print(f"   ✅ Collection '{self.collection_name}' already exists")
                return
        except:
            pass  # Collection doesn't exist, will create

        # Create collection
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=self.models.VectorParams(
                size=vector_size,
                distance=self.models.Distance.COSINE  # Cosine similarity for semantic search
            )
        )
        print(f"   ✅ Created collection '{self.collection_name}' (dim: {vector_size})")

    def upload_chunks(self, chunks: List[Dict], batch_size: int = 100) -> int:
        """
        Upload chunks with embeddings to Qdrant.

        Args:
            chunks: List of JSONL chunks with 'embedding' field
            batch_size: Batch size for upload

        Returns:
            Number of chunks uploaded
        """
        points = []

        for chunk in chunks:
            # Skip chunks without embeddings
            embedding = chunk.get('embedding')
            if not embedding:
                continue

            # Prepare payload (all metadata except embedding)
            payload = {
                "doc_id": chunk.get("doc_id"),
                "chunk_index": chunk.get("chunk_index"),
                "text": chunk.get("text"),
                "text_length": len(chunk.get("text", "")),
                "token_count": chunk.get("token_count"),
                "source_filename": chunk.get("source", {}).get("filename"),
                "source_file_type": chunk.get("source", {}).get("file_type"),
                "page": chunk.get("attrs", {}).get("bbox", {}).get("page"),
                "processed_at": chunk.get("processed_at"),
                "batch_id": chunk.get("batch_id")
            }

            # Add entities if present
            entities_data = chunk.get("entities", {})
            if entities_data and "extracted_entities" in entities_data:
                payload["has_entities"] = True
                payload["entity_count"] = len(entities_data["extracted_entities"])
                # Store entity types for filtering
                entity_types = list(set(e.get("type") for e in entities_data["extracted_entities"]))
                payload["entity_types"] = entity_types
            else:
                payload["has_entities"] = False
                payload["entity_count"] = 0

            # Create point
            # Use chunk ID as point ID (must be hashable string/int)
            point_id = abs(hash(chunk.get("id", f"{chunk.get('doc_id')}_{chunk.get('chunk_index')}"))) % (10**10)

            point = self.models.PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            points.append(point)

        # Upload in batches
        uploaded = 0
        for i in range(0, len(points), batch_size):
            batch = points[i:i+batch_size]
            self.client.upsert(
                collection_name=self.collection_name,
                points=batch
            )
            uploaded += len(batch)

        print(f"   ✅ Uploaded {uploaded} chunks to Qdrant collection '{self.collection_name}'")
        return uploaded

    def search(
        self,
        query_text: str,
        embedding_generator,
        limit: int = 5,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict] = None
    ) -> List:
        """
        Semantic search in Qdrant.

        Args:
            query_text: Search query
            embedding_generator: EmbeddingGenerator instance
            limit: Max results to return
            score_threshold: Minimum similarity score (0-1)
            filter_conditions: Qdrant filter dict (optional)

        Returns:
            List of search results with payload and score
        """
        # Generate query embedding
        query_embedding = embedding_generator.generate(query_text)

        # Search
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=limit,
            score_threshold=score_threshold,
            query_filter=filter_conditions,
            with_payload=True
        )

        return results

    def get_collection_info(self) -> Dict:
        """Get collection statistics"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "status": info.status
            }
        except Exception as e:
            return {"error": str(e)}
