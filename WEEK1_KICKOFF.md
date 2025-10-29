# Week 1 Kickoff: Demo 1+2 Implementation

> **Status:** Ready to Start | **Duration:** 5 days | **Goal:** Extend ingestion pipeline with bbox + entities + embeddings

---

## 🎯 Week 1 Goal

**Extend Phase 2 ingestion pipeline to v2.3.0:**
- Add bbox extraction (digital PDFs: precise, scanned PDFs: page-level)
- Add entity extraction (GPT-4o-mini)
- Generate embeddings (OpenAI text-embedding-3-small)
- Load all chunks into Qdrant with metadata

---

## ✅ Prerequisites (Complete!)

- [x] Phase 2 ingestion pipeline working (100%)
- [x] Qdrant running (localhost:6333)
- [x] LangSmith connected
- [x] Schema v2.3.0 designed
- [x] Bbox strategy finalized
- [x] Configuration files ready

---

## 📋 Week 1 Tasks

### **Day 1-2: Extend PDF Handlers**

**1. Update `handlers/pdf_digital.py`:**
```python
# Extract bbox from Docling
def extract_docling_bbox(result):
    doc_dict = result.document.export_to_dict()
    for text_elem in doc_dict.get("texts", []):
        bbox_data = text_elem["prov"][0].get("bbox")
        # Map: l→x0, b→y0, r→x1, t→y1
```

**2. Update `handlers/pdf_scanned.py`:**
```python
# Add page-level bbox for OlmOCR output
for chunk in olmocr_chunks:
    chunk["attrs"]["bbox"] = {
        "page": chunk["page_num"],
        "x0": None,  # Page-level only
        "y0": None,
        "x1": None,
        "y1": None
    }
```

### **Day 2-3: Entity Extraction Pipeline**

**3. Create `olmocr_pipeline/entity_extractor.py`:**
```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json

def extract_entities(text_chunk):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

    prompt = f"""Extract legal entities from this text. Return JSON:
    {{
      "entities": [
        {{"text": "John Smith", "type": "PERSON", "role": "grantor",
          "start_char": 0, "end_char": 10, "confidence": 0.95}}
      ]
    }}

    Entity types: PERSON, PARCEL, DATE, AMOUNT, LOCATION, DOCUMENT_REF, ORG

    Text: {text_chunk}
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    return json.loads(response.content)
```

### **Day 3-4: Embedding Pipeline**

**4. Create `olmocr_pipeline/embedding_generator.py`:**
```python
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

def generate_and_store_embeddings(chunks):
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    client = QdrantClient("localhost", port=6333)

    points = []
    for i, chunk in enumerate(chunks):
        vector = embeddings.embed_query(chunk["text"])

        point = PointStruct(
            id=i,
            vector=vector,
            payload={
                "doc_id": chunk["doc_id"],
                "text": chunk["text"],
                "entities": chunk["entities"],
                "bbox": chunk["attrs"]["bbox"],
                "page_num": chunk["page_num"]
            }
        )
        points.append(point)

    client.upsert(collection_name="legal_docs_v2_3", points=points)
```

### **Day 4-5: Integration & Testing**

**5. Update `process_documents.py` to orchestrate:**
```python
# For each document:
# 1. Run Phase 2 handler (with bbox)
# 2. Extract entities per chunk
# 3. Generate embeddings
# 4. Store in Qdrant
# 5. Update manifest
```

**6. Test on sample batch:**
- Process 10 digital PDFs
- Process 10 scanned PDFs
- Verify bbox extraction
- Verify entity extraction >90% accuracy
- Verify all chunks in Qdrant

---

## 📊 Success Criteria

By end of Week 1:

- [ ] 100+ documents processed with v2.3.0 schema
- [ ] Digital PDFs have precise bbox coordinates
- [ ] Scanned PDFs have page-level bbox
- [ ] All chunks have extracted entities
- [ ] Entity extraction accuracy >90% (manual spot check)
- [ ] All chunks embedded and in Qdrant
- [ ] Basic vector search working (test query returns results)
- [ ] LangSmith traces visible for all operations

---

## 🔧 Files to Modify

1. `olmocr_pipeline/handlers/pdf_digital.py` - Add bbox extraction
2. `olmocr_pipeline/handlers/pdf_scanned.py` - Add page-level bbox
3. `olmocr_pipeline/entity_extractor.py` - NEW (entity extraction)
4. `olmocr_pipeline/embedding_generator.py` - NEW (embedding + Qdrant)
5. `olmocr_pipeline/process_documents.py` - Orchestrate new pipeline
6. `olmocr_pipeline/utils_schema.py` - Update for v2.3.0 validation

---

## 📚 Reference Documents

- [PHASE3_PLAN.md](docs/planning/PHASE3_PLAN.md) - Overall roadmap
- [SCHEMA_V2.3.0.md](docs/planning/SCHEMA_V2.3.0.md) - Schema specification
- [OLMOCR_BBOX_STRATEGY.md](docs/planning/OLMOCR_BBOX_STRATEGY.md) - Bbox extraction strategy
- [config/phase3.yaml](config/phase3.yaml) - Configuration settings

---

## 🚀 Getting Started

**Day 1 Morning:**

1. Review schema v2.3.0 specification
2. Set up environment:
   ```bash
   conda activate olmocr-optimized
   source setup_env.sh
   docker ps | grep qdrant  # Verify Qdrant running
   ```
3. Create new branch (optional):
   ```bash
   git checkout -b demo1-2-week1
   ```
4. Start with `handlers/pdf_digital.py` bbox extraction

---

## 💡 Tips

- **Start simple:** Get bbox working first, then entities, then embeddings
- **Test incrementally:** Test each handler with 1-2 files before batch
- **Use LangSmith:** Log all LLM calls for debugging
- **Manual QA:** Spot check entity extraction on 10 documents
- **Qdrant UI:** Check http://localhost:6333/dashboard for stored vectors

---

## 📞 When You're Ready

Just say "Let's start Week 1" and we'll begin with bbox extraction for digital PDFs!

---

**Status:** ✅ Ready to code
**Context:** Compacted and ready for new session
**Next:** Extend pdf_digital.py handler
