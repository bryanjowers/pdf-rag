# Task 4: Embedding Generation + Qdrant Vector Database

**Goal:** Generate embeddings for JSONL chunks and load into Qdrant for semantic search

**Time Budget:** 1 hour (MVP implementation)

---

## Architecture Overview

```
JSONL Chunks (with bbox + entities)
    ↓
Embedding Model (sentence-transformers)
    ↓
Vector Embeddings (768-dim)
    ↓
Qdrant Vector Database
    ↓
Semantic Search API
```

---

## Task Breakdown

### 4a. Choose Embedding Model (5 min)

**Options:**

| Model | Dimensions | Speed | Quality | Use Case |
|-------|-----------|-------|---------|----------|
| **all-MiniLM-L6-v2** | 384 | ⚡⚡⚡ | Good | MVP (fast, small) |
| **all-mpnet-base-v2** | 768 | ⚡⚡ | Better | Production (balanced) |
| **instructor-large** | 768 | ⚡ | Best | Domain-specific (legal) |

**Recommendation:** **all-mpnet-base-v2**
- Best balance of speed/quality for legal docs
- 768 dimensions (better semantic capture)
- Widely used, well-supported
- ~120M parameters

**Install:**
```bash
pip install sentence-transformers
```

---

### 4b. Implement Embedding Generation (15 min)

**Create:** `olmocr_pipeline/utils_embeddings.py`

```python
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import numpy as np

class EmbeddingGenerator:
    """Generate embeddings for text chunks"""

    def __init__(self, model_name: str = "all-mpnet-base-v2"):
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()

    def generate(self, text: str) -> np.ndarray:
        """Generate embedding for single text"""
        return self.model.encode(text, normalize_embeddings=True)

    def generate_batch(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for batch of texts"""
        return self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=True,
            batch_size=32
        )

    def add_embeddings_to_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Add embeddings to JSONL chunks"""
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.generate_batch(texts)

        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding.tolist()

        return chunks
```

**Integration Point:** After entity extraction, before JSONL write

---

### 4c. Set Up Qdrant (10 min)

**Option 1: Docker (Recommended for Dev)**
```bash
docker pull qdrant/qdrant
docker run -p 6333:6333 -p 6334:6334 \
    -v $(pwd)/qdrant_storage:/qdrant/storage:z \
    qdrant/qdrant
```

**Option 2: Python In-Memory (Quick Testing)**
```bash
pip install qdrant-client
```

```python
from qdrant_client import QdrantClient
from qdrant_client.http import models

# In-memory for testing
client = QdrantClient(":memory:")

# Or connect to Docker
# client = QdrantClient("localhost", port=6333)
```

**Recommendation:** Use Docker for persistence, in-memory for quick tests

---

### 4d. Create Qdrant Loader (20 min)

**Create:** `olmocr_pipeline/utils_qdrant.py`

```python
from qdrant_client import QdrantClient
from qdrant_client.http import models
from typing import List, Dict
from pathlib import Path
import json

class QdrantLoader:
    """Load chunks with embeddings into Qdrant"""

    def __init__(self, collection_name: str = "legal_docs",
                 host: str = "localhost", port: int = 6333):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name

    def create_collection(self, vector_size: int = 768):
        """Create Qdrant collection if doesn't exist"""
        try:
            self.client.get_collection(self.collection_name)
            print(f"Collection '{self.collection_name}' already exists")
        except:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )
            print(f"Created collection '{self.collection_name}'")

    def upload_chunks(self, chunks: List[Dict]):
        """Upload chunks to Qdrant"""
        points = []

        for chunk in chunks:
            # Extract embedding
            embedding = chunk.get('embedding')
            if not embedding:
                continue

            # Prepare payload (everything except embedding)
            payload = {
                "doc_id": chunk.get("doc_id"),
                "chunk_index": chunk.get("chunk_index"),
                "text": chunk.get("text"),
                "source": chunk.get("source", {}).get("filename"),
                "page": chunk.get("attrs", {}).get("bbox", {}).get("page"),
                "entities": chunk.get("entities", {}),
                "processed_at": chunk.get("processed_at")
            }

            # Create point
            point = models.PointStruct(
                id=chunk.get("id"),  # Use chunk ID as point ID
                vector=embedding,
                payload=payload
            )
            points.append(point)

        # Upload batch
        self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )

        return len(points)

    def search(self, query_text: str, embedding_model, limit: int = 5):
        """Semantic search"""
        query_embedding = embedding_model.generate(query_text)

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding.tolist(),
            limit=limit,
            with_payload=True
        )

        return results
```

---

### 4e. Integration into Pipeline (10 min)

**Update handlers:**

```python
# In pdf_digital.py and pdf_scanned.py, after entity extraction:

# Generate embeddings
from utils_embeddings import EmbeddingGenerator

if config.get("embeddings", {}).get("enabled", False):
    print(f"   🔢 Generating embeddings...")
    embedding_gen = EmbeddingGenerator(
        model_name=config.get("embeddings", {}).get("model", "all-mpnet-base-v2")
    )
    chunks = embedding_gen.add_embeddings_to_chunks(chunks)
    print(f"   ✅ Generated {len(chunks)} embeddings (dim: {embedding_gen.dimension})")
```

**Update config/default.yaml:**

```yaml
# Embedding generation
embeddings:
  enabled: false                    # Toggle embedding generation
  model: "all-mpnet-base-v2"        # sentence-transformers model
  batch_size: 32                    # Batch size for generation
  normalize: true                   # Normalize embeddings to unit vectors

# Qdrant vector database
qdrant:
  enabled: false                    # Toggle Qdrant upload
  host: "localhost"
  port: 6333
  collection_name: "legal_docs"
  vector_size: 768                  # Must match embedding model dimension
```

---

## Testing Strategy

### Quick Test (5 min)

```python
# test_embeddings.py
from utils_embeddings import EmbeddingGenerator

gen = EmbeddingGenerator()
text = "This is a test deed transfer"
embedding = gen.generate(text)

print(f"Embedding dimension: {len(embedding)}")
print(f"First 5 values: {embedding[:5]}")
# Expected: [0.1234, -0.5678, ...]
```

### Full Integration Test (10 min)

```python
# test_embeddings_qdrant.py
import json
from pathlib import Path
from utils_embeddings import EmbeddingGenerator
from utils_qdrant import QdrantLoader

# Load existing JSONL
jsonl_path = Path("test_output/entity_retest/SDTO_170.0 ac 12-5-2022.jsonl")
chunks = []
with open(jsonl_path) as f:
    for line in f:
        chunks.append(json.loads(line))

# Generate embeddings
gen = EmbeddingGenerator()
chunks = gen.add_embeddings_to_chunks(chunks)

# Upload to Qdrant
loader = QdrantLoader(collection_name="test_legal_docs")
loader.create_collection(vector_size=768)
uploaded = loader.upload_chunks(chunks)

print(f"Uploaded {uploaded} chunks to Qdrant")

# Test search
results = loader.search("grantor and grantee", gen, limit=3)
for i, result in enumerate(results, 1):
    print(f"{i}. Score: {result.score:.3f}")
    print(f"   Text: {result.payload['text'][:100]}...")
```

---

## Performance Expectations

**Embedding Generation:**
- Speed: ~100-200 chunks/second (CPU)
- Speed: ~500-1000 chunks/second (GPU)
- Memory: ~500MB (model) + ~1KB per chunk

**Qdrant Upload:**
- Speed: ~10,000 chunks/second
- Memory: Minimal (streaming)

**For 28-page doc (5 chunks):**
- Embedding time: <1 second
- Upload time: <1 second
- Total overhead: ~2 seconds

---

## Deliverables

1. ✅ `olmocr_pipeline/utils_embeddings.py` - Embedding generation
2. ✅ `olmocr_pipeline/utils_qdrant.py` - Qdrant loader
3. ✅ Updated `config/default.yaml` - Embedding/Qdrant config
4. ✅ `test_embeddings_qdrant.py` - Integration test
5. ✅ Updated handlers - Embedding generation integrated

---

## MVP Scope (1 hour)

**In Scope:**
- ✅ Embedding generation (sentence-transformers)
- ✅ Qdrant collection creation
- ✅ Chunk upload to Qdrant
- ✅ Basic semantic search test

**Out of Scope (Post-MVP):**
- ❌ Hybrid search (vector + keyword)
- ❌ Metadata filtering
- ❌ Multi-tenancy
- ❌ Embedding model fine-tuning
- ❌ Production deployment (scaling, monitoring)

---

**Status:** Ready to implement
**Next:** Create utils_embeddings.py
