#!/usr/bin/env python3
"""
utils_embeddings.py - Generate embeddings for text chunks using sentence-transformers

Supports semantic search for RAG pipeline.
"""

from typing import List, Dict, Optional
import numpy as np


class EmbeddingGenerator:
    """Generate embeddings for text chunks using sentence-transformers"""

    def __init__(self, model_name: str = "all-mpnet-base-v2", device: Optional[str] = None):
        """
        Initialize embedding model.

        Args:
            model_name: Hugging Face model name (default: all-mpnet-base-v2)
            device: Device to use ('cuda', 'cpu', or None for auto-detect)
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers not installed. Install with: pip install sentence-transformers"
            )

        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device=device)
        self.dimension = self.model.get_sentence_embedding_dimension()

        print(f"   📊 Loaded embedding model: {model_name}")
        print(f"   📐 Embedding dimension: {self.dimension}")

    def generate(self, text: str, normalize: bool = True) -> np.ndarray:
        """
        Generate embedding for single text.

        Args:
            text: Input text
            normalize: Normalize to unit vector (recommended for cosine similarity)

        Returns:
            Numpy array of shape (dimension,)
        """
        return self.model.encode(
            text,
            normalize_embeddings=normalize,
            convert_to_numpy=True
        )

    def generate_batch(
        self,
        texts: List[str],
        batch_size: int = 32,
        show_progress: bool = True,
        normalize: bool = True
    ) -> np.ndarray:
        """
        Generate embeddings for batch of texts.

        Args:
            texts: List of input texts
            batch_size: Batch size for encoding
            show_progress: Show progress bar
            normalize: Normalize to unit vectors

        Returns:
            Numpy array of shape (num_texts, dimension)
        """
        return self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            normalize_embeddings=normalize,
            convert_to_numpy=True
        )

    def add_embeddings_to_chunks(
        self,
        chunks: List[Dict],
        batch_size: int = 32,
        show_progress: bool = True
    ) -> List[Dict]:
        """
        Add embeddings to JSONL chunks (in-place).

        Args:
            chunks: List of JSONL chunk dicts
            batch_size: Batch size for encoding
            show_progress: Show progress bar

        Returns:
            Chunks with 'embedding' field added
        """
        # Extract texts
        texts = [chunk['text'] for chunk in chunks]

        # Generate embeddings
        embeddings = self.generate_batch(
            texts,
            batch_size=batch_size,
            show_progress=show_progress
        )

        # Add to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding.tolist()  # Convert to list for JSON serialization

        return chunks


def format_embedding_stats(chunks: List[Dict]) -> str:
    """
    Format embedding statistics for logging.

    Args:
        chunks: List of chunks with embeddings

    Returns:
        Formatted string
    """
    chunks_with_embeddings = sum(1 for c in chunks if 'embedding' in c and c['embedding'])

    if chunks_with_embeddings == 0:
        return "No embeddings generated"

    # Get dimension from first embedding
    first_embedding = next((c['embedding'] for c in chunks if 'embedding' in c), None)
    dimension = len(first_embedding) if first_embedding else 0

    return f"Generated {chunks_with_embeddings}/{len(chunks)} embeddings (dim: {dimension})"
