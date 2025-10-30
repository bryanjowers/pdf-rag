# Phase 3 Infrastructure Setup Guide

> **For:** Demo 1+2 (Smart Entity Search) | **Duration:** 1-2 hours

---

## 🎯 Overview

Set up the following infrastructure for Phase 3:

1. ✅ **Qdrant** - Vector database (persistent storage)
2. ✅ **LangSmith** - Monitoring & tracing
3. ⚠️ **Docling bbox** - Test bounding box extraction (1-day spike)

---

## 1️⃣ Qdrant Setup

### **Option A: Docker (Recommended for Development)**

```bash
# Pull latest Qdrant image
docker pull qdrant/qdrant

# Run Qdrant container
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant

# Verify Qdrant is running
curl http://localhost:6333/

# Expected response:
# {
#   "title": "qdrant - vector search engine",
#   "version": "x.x.x"
# }
```

### **Option B: Conda/Pip Install (Alternative)**

```bash
# Activate environment
conda activate olmocr-optimized

# Install Qdrant client
pip install qdrant-client

# Create Python service wrapper (for running Qdrant as Python process)
# Note: Docker is preferred for production-like setup
```

### **Test Qdrant Connection**

```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

# Connect to Qdrant
client = QdrantClient("localhost", port=6333)

# Create test collection
client.create_collection(
    collection_name="test_collection",
    vectors_config=VectorParams(
        size=128,
        distance=Distance.COSINE
    )
)

# Insert test point
client.upsert(
    collection_name="test_collection",
    points=[
        PointStruct(
            id="test_001",
            vector=[0.1] * 128,
            payload={"text": "Hello world"}
        )
    ]
)

# Search test
results = client.search(
    collection_name="test_collection",
    query_vector=[0.1] * 128,
    limit=1
)

print("✅ Qdrant working:", results[0].id)

# Clean up
client.delete_collection("test_collection")
```

**Expected Output:**
```
✅ Qdrant working: test_001
```

---

## 2️⃣ LangSmith Setup

### **Create Account**

1. Visit https://smith.langchain.com/
2. Sign up with email (free tier: 5K traces/month)
3. Create a new project: "legal-rag-demo1-2"

### **Get API Key**

1. Navigate to Settings → API Keys
2. Create new API key: "pdf-rag-phase3"
3. Copy API key (starts with `ls__...`)

### **Configure Environment**

```bash
# Add to ~/.bashrc or ~/.zshrc
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
export LANGCHAIN_API_KEY="ls__your_api_key_here"
export LANGCHAIN_PROJECT="legal-rag-demo1-2"

# Reload shell
source ~/.bashrc  # or source ~/.zshrc
```

### **Test LangSmith**

```python
from langsmith import Client

# Connect to LangSmith
client = Client()

# Test connection
projects = list(client.list_projects())
print(f"✅ LangSmith connected: {len(projects)} projects")

# Create test trace
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
response = llm.invoke([HumanMessage(content="Hello, test trace!")])

print("✅ Test trace logged to LangSmith")
print(f"   Response: {response.content}")
```

**Verify in LangSmith UI:**
- Go to https://smith.langchain.com/
- Navigate to "legal-rag-demo1-2" project
- You should see the test trace with input/output

---

## 3️⃣ Docling Bbox Extraction Spike

### **Objective**

Determine if Docling exposes bounding box coordinates in its JSON output.

**Timeline:** 1 day maximum

**Success Criteria:**
- ✅ Bbox available → Extract coordinates, update schema
- ❌ Bbox not available → Fall back to page-level citations, document in schema

### **Test Script**

```python
import json
from docling.document_converter import DocumentConverter

# Test with sample PDF
converter = DocumentConverter()
result = converter.convert("/path/to/sample_deed.pdf")

# Check for bbox data in result
print("=== Docling Output Structure ===")
print(json.dumps(result.model_dump(), indent=2)[:1000])  # First 1000 chars

# Look for bbox-related fields
doc_dict = result.model_dump()

def find_bbox_fields(obj, path=""):
    """Recursively search for bbox-related fields"""
    if isinstance(obj, dict):
        for key, value in obj.items():
            new_path = f"{path}.{key}" if path else key
            if "bbox" in key.lower() or "bound" in key.lower() or "coord" in key.lower():
                print(f"✅ Found bbox field: {new_path}")
                print(f"   Sample value: {value}")
            find_bbox_fields(value, new_path)
    elif isinstance(obj, list) and obj:
        find_bbox_fields(obj[0], f"{path}[0]")

find_bbox_fields(doc_dict)

# Check specific locations where bbox might be
print("\n=== Checking Common Bbox Locations ===")

# Check document chunks/blocks
if hasattr(result, 'chunks'):
    for i, chunk in enumerate(result.chunks[:3]):  # First 3 chunks
        print(f"\nChunk {i}:")
        if hasattr(chunk, 'bbox'):
            print(f"  ✅ bbox: {chunk.bbox}")
        elif hasattr(chunk, 'position'):
            print(f"  ✅ position: {chunk.position}")
        else:
            print(f"  ❌ No bbox found")

# Check document elements
if hasattr(result, 'document'):
    doc = result.document
    if hasattr(doc, 'elements'):
        for i, elem in enumerate(doc.elements[:3]):
            print(f"\nElement {i}:")
            print(f"  Type: {type(elem)}")
            print(f"  Attributes: {dir(elem)}")
            if hasattr(elem, 'bbox'):
                print(f"  ✅ bbox: {elem.bbox}")
```

### **Decision Tree**

**Case 1: Bbox Available**
```python
# Extract bbox from Docling output
def extract_bbox(docling_chunk):
    """Extract bbox coordinates from Docling chunk"""
    if hasattr(docling_chunk, 'bbox'):
        bbox = docling_chunk.bbox
        return {
            "page": bbox.page,
            "x0": bbox.x0,
            "y0": bbox.y0,
            "x1": bbox.x1,
            "y1": bbox.y1,
            "width": bbox.page_width,
            "height": bbox.page_height,
            "unit": "points"
        }
    return None

# Update schema v2.3.0 with bbox extraction enabled
# Status: ✅ Bbox available
```

**Case 2: Bbox NOT Available**
```python
# Fall back to page-level citations
def extract_bbox_fallback(docling_chunk):
    """Return null for bbox if not available"""
    return None  # Use page_span from attrs.page_span instead

# Update SCHEMA_V2.3.0.md to reflect:
# - bbox field is OPTIONAL (null when unavailable)
# - Citations format: "Source: deed.pdf, Page 5" (no bbox coordinates)
# - Future enhancement: Consider PyMuPDF post-processing if bbox becomes critical

# Status: ⚠️ Bbox not available (page-level fallback)
```

### **Deliverables**

After 1-day spike, create:

1. **bbox_spike_results.md** - Document findings
2. Update **SCHEMA_V2.3.0.md** - Mark bbox as available/unavailable
3. Update **PHASE3_PLAN.md** - Adjust Demo 1+2 scope if needed

---

## 4️⃣ Install Additional Dependencies

```bash
# Activate environment
conda activate olmocr-optimized

# Install Phase 3 dependencies
pip install qdrant-client langsmith langchain langchain-openai rank-bm25

# Verify installations
python -c "
import qdrant_client
import langsmith
import langchain
from rank_bm25 import BM25Okapi
print('✅ All Phase 3 dependencies installed')
"
```

---

## 5️⃣ Create Qdrant Collection for Demo 1+2

```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient("localhost", port=6333)

# Create production collection
client.create_collection(
    collection_name="legal_docs_v2_3",
    vectors_config=VectorParams(
        size=1536,  # OpenAI text-embedding-3-small
        distance=Distance.COSINE
    )
)

print("✅ Qdrant collection 'legal_docs_v2_3' created")

# Verify collection info
info = client.get_collection("legal_docs_v2_3")
print(f"   Vectors: {info.vectors_count}")
print(f"   Points: {info.points_count}")
```

---

## 6️⃣ Verify All Infrastructure

```bash
# Run comprehensive check
python -c "
import os
from qdrant_client import QdrantClient
from langsmith import Client

print('=== Infrastructure Check ===\n')

# 1. Qdrant
try:
    qdrant = QdrantClient('localhost', port=6333)
    collections = qdrant.get_collections()
    print(f'✅ Qdrant: {len(collections.collections)} collections')
except Exception as e:
    print(f'❌ Qdrant: {e}')

# 2. LangSmith
try:
    ls_client = Client()
    projects = list(ls_client.list_projects())
    print(f'✅ LangSmith: {len(projects)} projects')
except Exception as e:
    print(f'❌ LangSmith: {e}')

# 3. OpenAI API
if 'OPENAI_API_KEY' in os.environ:
    print(f'✅ OpenAI API Key: Set')
else:
    print(f'❌ OpenAI API Key: Not set')

# 4. Environment variables
required_env = ['LANGCHAIN_TRACING_V2', 'LANGCHAIN_API_KEY', 'LANGCHAIN_PROJECT']
for var in required_env:
    if var in os.environ:
        print(f'✅ {var}: Set')
    else:
        print(f'❌ {var}: Not set')

print('\n=== Infrastructure Ready ===')
"
```

**Expected Output:**
```
=== Infrastructure Check ===

✅ Qdrant: 1 collections
✅ LangSmith: 1 projects
✅ OpenAI API Key: Set
✅ LANGCHAIN_TRACING_V2: Set
✅ LANGCHAIN_API_KEY: Set
✅ LANGCHAIN_PROJECT: Set

=== Infrastructure Ready ===
```

---

## 7️⃣ Create Infrastructure Config File

```bash
# Create config for Phase 3
cat > config/phase3.yaml <<EOF
# Phase 3 Infrastructure Configuration

qdrant:
  host: localhost
  port: 6333
  collection_name: legal_docs_v2_3
  vector_size: 1536
  distance_metric: cosine

embeddings:
  provider: openai
  model: text-embedding-3-small
  dimensions: 1536
  batch_size: 100

llm:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.0
  max_tokens: 2000

entity_extraction:
  provider: openai
  model: gpt-4o-mini
  temperature: 0.0
  confidence_threshold: 0.7

bm25:
  tokenizer: simple  # Options: simple, spacy, nltk
  k1: 1.5
  b: 0.75

reranker:
  model: BAAI/bge-reranker-large
  top_k: 10

hybrid_search:
  bm25_weight: 0.3
  vector_weight: 0.7
  rerank_top_k: 10

monitoring:
  langsmith:
    project: legal-rag-demo1-2
    tracing: true
    log_prompts: true
    log_responses: true

schema:
  version: "2.3.0"
  bbox_enabled: null  # Set after bbox spike: true/false
EOF

echo "✅ Phase 3 config created: config/phase3.yaml"
```

---

## ✅ Checklist

**Before moving to Demo 1+2 implementation:**

- [ ] Qdrant running and accessible (http://localhost:6333/)
- [ ] Qdrant collection `legal_docs_v2_3` created
- [ ] LangSmith account created and API key configured
- [ ] LangSmith test trace visible in UI
- [ ] OpenAI API key set in environment
- [ ] All Python dependencies installed
- [ ] Bbox spike completed (results documented)
- [ ] `config/phase3.yaml` created
- [ ] Infrastructure verification script passes

**Estimated Time:** 1-2 hours (excluding bbox spike)

---

## 🚀 Next Steps

Once infrastructure is ready:

1. ✅ Run bbox spike (1 day)
2. ✅ Update SCHEMA_V2.3.0.md with bbox findings
3. Begin Demo 1+2 implementation:
   - Week 1: Extend ingestion pipeline (entities + embeddings)
   - Week 2: Implement hybrid search
   - Week 3: Entity filtering + UI

See [PHASE3_PLAN.md](PHASE3_PLAN.md) for detailed roadmap.

---

**Created:** $(date +%Y-%m-%d)
**Status:** Ready for execution
