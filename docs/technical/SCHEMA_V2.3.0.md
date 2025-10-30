# Schema v2.3.0 Specification

> **Version:** 2.3.0 | **Effective:** Phase 3 (Demo 1+2) | **Migration from:** v2.2.0

---

## 📋 Overview

**Schema v2.3.0 extends v2.2.0** with bounding box coordinates and entity extraction for RAG-ready document chunks. This schema enables:

1. **Precise legal citations** - Page + bbox coordinates for exact clause location
2. **Entity-aware search** - Filter by parties, parcels, dates, amounts
3. **Graph preparation** - Entities ready for Neo4j linking in Demo 3

---

## 🔄 Migration Path: v2.2.0 → v2.3.0

### **Current Schema (v2.2.0)**

```json
{
  "id": "abc123_0000",
  "doc_id": "abc123",
  "chunk_index": 0,
  "text": "This deed conveys Parcel 123 from John Smith to Mary Johnson...",
  "attrs": {
    "page_span": [5],
    "sections": [],
    "table": false,
    "token_count": 145
  },
  "source": {
    "file_path": "/path/to/deed.pdf",
    "file_name": "deed.pdf",
    "mime_type": "application/pdf"
  },
  "metadata": {
    "schema_version": "2.2.0",
    "file_type": "pdf_digital",
    "processing_timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### **New Schema (v2.3.0)**

```json
{
  "id": "abc123_0000",
  "doc_id": "abc123",
  "chunk_index": 0,
  "text": "This deed conveys Parcel 123 from John Smith to Mary Johnson...",

  // EXISTING v2.2.0 fields
  "attrs": {
    "page_span": [5],
    "sections": [],
    "table": false,
    "token_count": 145,
    "bbox": {                          // NEW in v2.3.0
      "page": 5,
      "x0": 100.5,
      "y0": 200.2,
      "x1": 500.8,
      "y1": 350.6,
      "width": 612.0,
      "height": 792.0,
      "unit": "points"
    }
  },

  // NEW in v2.3.0
  "entities": [
    {
      "text": "John Smith",
      "type": "PERSON",
      "role": "grantor",
      "start_char": 30,
      "end_char": 40,
      "confidence": 0.95,
      "normalized": "john smith"
    },
    {
      "text": "Mary Johnson",
      "type": "PERSON",
      "role": "grantee",
      "start_char": 44,
      "end_char": 56,
      "confidence": 0.96,
      "normalized": "mary johnson"
    },
    {
      "text": "Parcel 123",
      "type": "PARCEL",
      "role": "subject",
      "start_char": 19,
      "end_char": 29,
      "confidence": 0.99,
      "normalized": "parcel 123"
    },
    {
      "text": "January 15, 2020",
      "type": "DATE",
      "role": "effective_date",
      "start_char": 100,
      "end_char": 116,
      "confidence": 0.98,
      "normalized": "2020-01-15",
      "iso_format": "2020-01-15"
    }
  ],

  // NEW in v2.3.0 - For Qdrant
  "embedding": null,  // Filled during ingestion, not in JSONL

  "source": {
    "file_path": "/path/to/deed.pdf",
    "file_name": "deed.pdf",
    "mime_type": "application/pdf"
  },

  "metadata": {
    "schema_version": "2.3.0",              // UPDATED
    "file_type": "pdf_digital",
    "processing_timestamp": "2024-01-15T10:30:00Z",
    "entity_extraction_model": "gpt-4o-mini",   // NEW
    "embedding_model": "text-embedding-3-small" // NEW
  }
}
```

---

## 📐 Schema Fields Reference

### **Existing Fields (v2.2.0)**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | ✅ | Unique chunk identifier: `{doc_id}_{chunk_index}` |
| `doc_id` | string | ✅ | Document identifier (SHA256 prefix or filename hash) |
| `chunk_index` | int | ✅ | Zero-based chunk index within document |
| `text` | string | ✅ | Chunk content (markdown for tables) |
| `attrs.page_span` | list[int] | ✅ | Pages covered by chunk (null for non-paginated docs) |
| `attrs.sections` | list[str] | ✅ | Document section hierarchy (e.g., ["Chapter 1", "Section 1.1"]) |
| `attrs.table` | bool | ✅ | Whether chunk contains table content |
| `attrs.token_count` | int | ✅ | Estimated token count (for LLM context windows) |
| `source.file_path` | string | ✅ | Full path to source document |
| `source.file_name` | string | ✅ | Source filename |
| `source.mime_type` | string | ✅ | MIME type (e.g., `application/pdf`) |
| `metadata.schema_version` | string | ✅ | Schema version identifier |
| `metadata.file_type` | string | ✅ | Handler type: `pdf_digital`, `pdf_scanned`, `docx`, `xlsx`, `image` |
| `metadata.processing_timestamp` | string | ✅ | ISO 8601 timestamp |

### **New Fields (v2.3.0)**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| **Bounding Box** | | | |
| `attrs.bbox` | object | ⚠️ | Bounding box for chunk location (null if unavailable) |
| `attrs.bbox.page` | int | ✅ | Page number (1-indexed) |
| `attrs.bbox.x0` | float | ✅ | Left coordinate (PDF points, 0,0 = bottom-left) |
| `attrs.bbox.y0` | float | ✅ | Bottom coordinate |
| `attrs.bbox.x1` | float | ✅ | Right coordinate |
| `attrs.bbox.y1` | float | ✅ | Top coordinate |
| `attrs.bbox.width` | float | ✅ | Page width (for normalization) |
| `attrs.bbox.height` | float | ✅ | Page height (for normalization) |
| `attrs.bbox.unit` | string | ✅ | Coordinate unit (always `"points"` for PDF) |
| **Entities** | | | |
| `entities` | list[object] | ✅ | Extracted entities (empty list if none) |
| `entities[].text` | string | ✅ | Original entity text |
| `entities[].type` | string | ✅ | Entity type (see Entity Types below) |
| `entities[].role` | string | ⚠️ | Entity role in context (optional) |
| `entities[].start_char` | int | ✅ | Start character offset in `text` field |
| `entities[].end_char` | int | ✅ | End character offset (exclusive) |
| `entities[].confidence` | float | ✅ | Extraction confidence (0.0-1.0) |
| `entities[].normalized` | string | ✅ | Normalized form (lowercase, stripped) |
| `entities[].iso_format` | string | ⚠️ | ISO format (for dates only) |
| **Embeddings** | | | |
| `embedding` | list[float] | ⚠️ | Vector embedding (1536d for OpenAI, stored in Qdrant, null in JSONL) |
| **Metadata Updates** | | | |
| `metadata.entity_extraction_model` | string | ✅ | Model used for entity extraction |
| `metadata.embedding_model` | string | ✅ | Model used for embeddings |

---

## 🏷️ Entity Types & Roles

### **Core Entity Types**

| Type | Description | Example | Role Options |
|------|-------------|---------|--------------|
| `PERSON` | Individual or entity name | "John Smith", "ABC Corp" | `grantor`, `grantee`, `witness`, `notary`, `attorney` |
| `PARCEL` | Property/parcel identifier | "Parcel 123", "Lot 5 Block 2" | `subject`, `adjacent`, `referenced` |
| `DATE` | Date or date range | "January 15, 2020", "2010-2024" | `effective_date`, `recording_date`, `execution_date`, `expiration_date` |
| `AMOUNT` | Monetary amount | "$50,000", "Fifty thousand dollars" | `consideration`, `mortgage_amount`, `lien_amount`, `tax_amount` |
| `LOCATION` | Geographic location | "Mountrail County, ND", "Section 10-158N-92W" | `property_location`, `jurisdiction`, `recording_office` |
| `DOCUMENT_REF` | Reference to another document | "Book 123, Page 456", "Document #2020-0001" | `prior_deed`, `mortgage`, `lien`, `covenant`, `easement` |
| `ORG` | Organization or entity | "County Recorder's Office", "First National Bank" | `lender`, `title_company`, `recorder`, `government_entity` |

### **Entity Role Guidelines**

**For PERSON entities:**
- `grantor`: Transferring party (seller, mortgagor)
- `grantee`: Receiving party (buyer, mortgagee)
- `witness`: Signature witness
- `notary`: Notary public
- `attorney`: Legal representative

**For PARCEL entities:**
- `subject`: Main parcel being conveyed/discussed
- `adjacent`: Neighboring parcel mentioned for context
- `referenced`: Parcel mentioned in legal description

**For DATE entities:**
- `effective_date`: When transfer takes effect
- `recording_date`: When document was recorded
- `execution_date`: When document was signed
- `expiration_date`: When rights expire (leases, options)

---

## 🔧 Bounding Box Specification

### **Coordinate System**

PDF uses **bottom-left origin** (0,0 = bottom-left corner):
```
(0, height) ┌─────────────┐ (width, height)
            │             │
            │   PAGE      │
            │             │
 (0, 0)     └─────────────┘ (width, 0)
```

**Typical PDF page sizes:**
- Letter: 612 x 792 points
- Legal: 612 x 1008 points
- A4: 595 x 842 points

### **Bbox Examples**

**Single-line text chunk:**
```json
{
  "bbox": {
    "page": 5,
    "x0": 100.0,
    "y0": 600.0,
    "x1": 500.0,
    "y1": 620.0,
    "width": 612.0,
    "height": 792.0,
    "unit": "points"
  }
}
```

**Multi-line paragraph (spanning multiple bbox regions):**
```json
{
  "bbox": {
    "page": 5,
    "x0": 100.0,   // Left margin
    "y0": 400.0,   // Bottom of paragraph
    "x1": 500.0,   // Right margin
    "y1": 650.0,   // Top of paragraph
    "width": 612.0,
    "height": 792.0,
    "unit": "points"
  }
}
```

**Fallback (page-level only, no bbox available):**
```json
{
  "bbox": null  // Bbox extraction not supported, use page_span instead
}
```

---

## 🧪 Entity Extraction Guidelines

### **Extraction Pipeline (GPT-4o-mini)**

**Prompt Template:**
```
Extract legal entities from the following text. Return JSON with this structure:

{
  "entities": [
    {
      "text": "original text",
      "type": "PERSON|PARCEL|DATE|AMOUNT|LOCATION|DOCUMENT_REF|ORG",
      "role": "grantor|grantee|subject|etc (if applicable)",
      "start_char": 0,
      "end_char": 10,
      "confidence": 0.95
    }
  ]
}

Text:
{chunk_text}

Guidelines:
- Extract all parties (PERSON) with roles (grantor/grantee)
- Extract parcels (PARCEL) with legal descriptions
- Extract dates (DATE) with roles (effective_date/recording_date)
- Extract amounts (AMOUNT) with roles (consideration/mortgage_amount)
- Include start_char and end_char offsets
- Assign confidence 0.9-1.0 for clear entities, 0.7-0.9 for ambiguous

Return only valid JSON, no markdown or explanations.
```

### **Normalization Rules**

Apply these rules to `normalized` field:

1. **Lowercase:** `"John Smith"` → `"john smith"`
2. **Strip whitespace:** `"  Mary Johnson  "` → `"mary johnson"`
3. **Remove punctuation (names):** `"Smith, John"` → `"smith john"`
4. **Standardize parcels:** `"Parcel #123"` → `"parcel 123"`
5. **ISO dates:** `"January 15, 2020"` → `"2020-01-15"` (in `iso_format` field)
6. **Normalize amounts:** `"$50,000.00"` → `"50000"` (numeric only in `normalized`)

**Fuzzy matching threshold:** Use 85% similarity (Levenshtein distance) for entity linking across documents.

---

## 🗄️ Qdrant Integration

### **Collection Schema**

```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient("localhost", port=6333)

client.create_collection(
    collection_name="legal_docs_v2_3",
    vectors_config=VectorParams(
        size=1536,  # OpenAI text-embedding-3-small
        distance=Distance.COSINE
    )
)
```

### **Point Structure**

```python
{
    "id": "abc123_0000",  # Chunk ID
    "vector": [0.1, 0.2, ...],  # 1536d embedding
    "payload": {
        # Full JSONL record (excluding 'embedding' field)
        "doc_id": "abc123",
        "chunk_index": 0,
        "text": "...",
        "attrs": {...},
        "entities": [...],
        "source": {...},
        "metadata": {...}
    }
}
```

### **Metadata Filters (Qdrant)**

**Filter by entity:**
```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

# Find chunks mentioning "John Smith" as grantor
Filter(
    must=[
        FieldCondition(
            key="entities[].normalized",
            match=MatchValue(value="john smith")
        ),
        FieldCondition(
            key="entities[].role",
            match=MatchValue(value="grantor")
        )
    ]
)
```

**Filter by parcel:**
```python
# Find chunks about Parcel 123
Filter(
    must=[
        FieldCondition(
            key="entities[].type",
            match=MatchValue(value="PARCEL")
        ),
        FieldCondition(
            key="entities[].normalized",
            match=MatchValue(value="parcel 123")
        )
    ]
)
```

**Filter by date range:**
```python
# Find chunks with dates between 2010-2020
Filter(
    must=[
        FieldCondition(
            key="entities[].type",
            match=MatchValue(value="DATE")
        ),
        FieldCondition(
            key="entities[].iso_format",
            range={"gte": "2010-01-01", "lte": "2020-12-31"}
        )
    ]
)
```

---

## 📝 Schema Evolution Plan

### **v2.2.0 → v2.3.0 Migration**

**Step 1: Extend Pipeline (Week 1)**
- Add bbox extraction (Docling spike or page-level fallback)
- Add entity extraction (GPT-4o-mini API calls)
- Update schema validator to accept v2.3.0

**Step 2: Reprocess Documents (Week 2)**
- Reprocess existing JSONL files to add bbox + entities
- Store updated files in `/mnt/gcs/legal-ocr-results/rag_staging/jsonl_v2.3/`
- Keep v2.2.0 files for rollback

**Step 3: Load into Qdrant (Week 2-3)**
- Generate embeddings (OpenAI API)
- Create Qdrant collection
- Upload all chunks with embeddings

**Step 4: Validate (Week 3)**
- Test entity filtering
- Test hybrid search (BM25 + vector)
- Validate bbox coordinates (spot check)

### **v2.3.0 → v3.0.0 (Demo 3, Future)**

Future enhancements for Graph RAG:

```json
{
  // ... v2.3.0 fields ...

  "graph_entities": [  // NEW in v3.0.0
    {
      "id": "person_001",  // Global entity ID (linked across docs)
      "text": "John Smith",
      "type": "PERSON",
      "canonical_name": "john smith"
    }
  ],

  "graph_relationships": [  // NEW in v3.0.0
    {
      "source": "person_001",
      "relation": "CONVEYS_TO",
      "target": "person_002",
      "confidence": 0.95
    }
  ],

  "metadata": {
    "schema_version": "3.0.0",
    "graph_ingestion_timestamp": "2024-02-01T10:00:00Z"
  }
}
```

---

## ✅ Validation & Testing

### **Schema Validation Script**

```python
import json
from pathlib import Path

def validate_schema_v2_3(jsonl_path):
    """Validate JSONL file against schema v2.3.0"""

    required_fields = [
        "id", "doc_id", "chunk_index", "text", "entities",
        "attrs", "source", "metadata"
    ]

    with open(jsonl_path) as f:
        for line_num, line in enumerate(f, 1):
            data = json.loads(line)

            # Check required fields
            missing = [f for f in required_fields if f not in data]
            if missing:
                print(f"Line {line_num}: Missing fields: {missing}")
                continue

            # Check schema version
            if data["metadata"]["schema_version"] != "2.3.0":
                print(f"Line {line_num}: Wrong schema version: {data['metadata']['schema_version']}")

            # Check entities structure
            for entity in data.get("entities", []):
                required_entity_fields = ["text", "type", "start_char", "end_char", "confidence", "normalized"]
                missing_entity = [f for f in required_entity_fields if f not in entity]
                if missing_entity:
                    print(f"Line {line_num}: Entity missing fields: {missing_entity}")

            # Check bbox if present
            if "bbox" in data.get("attrs", {}):
                bbox = data["attrs"]["bbox"]
                if bbox is not None:  # null is valid (fallback)
                    required_bbox = ["page", "x0", "y0", "x1", "y1", "width", "height", "unit"]
                    missing_bbox = [f for f in required_bbox if f not in bbox]
                    if missing_bbox:
                        print(f"Line {line_num}: Bbox missing fields: {missing_bbox}")

    print(f"✅ Validation complete: {jsonl_path}")

# Usage
validate_schema_v2_3("/mnt/gcs/legal-ocr-results/rag_staging/jsonl_v2.3/deed_123.jsonl")
```

### **Test Data Examples**

See [test_data/](test_data/) for sample JSONL files:
- `deed_digital.jsonl` - Digital PDF with bbox
- `deed_scanned.jsonl` - Scanned PDF (page-level only, bbox=null)
- `assignment.jsonl` - Assignment with entity roles
- `doi_spreadsheet.jsonl` - Division of Interest (XLSX chunks)

---

## 📚 References

- **Phase 2 Schema (v2.2.0):** [readme.md](readme.md)
- **Phase 3 Plan:** [PHASE3_PLAN.md](PHASE3_PLAN.md)
- **OpenAI Embeddings:** https://platform.openai.com/docs/guides/embeddings
- **Qdrant Docs:** https://qdrant.tech/documentation/
- **PDF Coordinate System:** https://pypdf.readthedocs.io/en/stable/user/cropping-and-transforming.html

---

**Version:** 2.3.0
**Effective Date:** Phase 3 Demo 1+2
**Authors:** Claude Code
**Status:** Draft (awaiting bbox spike results)
