# Task 3: Entity Extraction Integration Plan

**Status:** In Progress
**Started:** 2025-10-29

---

## 🎯 Objective

Integrate entity extraction (GPT-4o-mini) into both digital and scanned PDF pipelines to enrich JSONL chunks with structured legal entities.

---

## 📋 Current Status

### ✅ Completed:
- [x] Entity extraction utility created ([utils_entity.py](olmocr_pipeline/utils_entity.py))
- [x] GPT-4o-mini integration implemented
- [x] Entity types defined (PERSON, PARCEL, DATE, AMOUNT, ORG)
- [x] Legal roles defined (grantor, grantee, subject, witness, notary)
- [x] Normalization and deduplication logic
- [x] Cost tracking implemented

### 🔧 To Do:
- [ ] Integrate into pdf_digital.py
- [ ] Integrate into pdf_scanned.py
- [ ] Add entity field to JSONL schema
- [ ] Test with validation document
- [ ] Document cost estimates

---

## 🏗️ Integration Architecture

### **Schema Extension**

**Current JSONL Structure:**
```json
{
  "id": "...",
  "doc_id": "...",
  "chunk_index": 0,
  "text": "...",
  "attrs": {
    "bbox": {...},
    "page_span": null,
    "sections": [],
    "table": false,
    "token_count": 1430
  },
  "source": {...},
  "metadata": {...}
}
```

**Extended with Entities:**
```json
{
  "id": "...",
  "doc_id": "...",
  "chunk_index": 0,
  "text": "...",
  "attrs": {
    "bbox": {...},
    "page_span": null,
    "sections": [],
    "table": false,
    "token_count": 1430
  },
  "entities": {
    "extracted_entities": [
      {
        "text": "Silver Hill Haynesville E&P, LLC",
        "type": "ORG",
        "role": "grantee",
        "confidence": 0.95,
        "text_normalized": "silver hill haynesville e&p, llc"
      },
      {
        "text": "December 5, 2022",
        "type": "DATE",
        "role": null,
        "confidence": 0.98,
        "text_normalized": "december 5, 2022"
      }
    ],
    "extraction_metadata": {
      "model": "gpt-4o-mini",
      "tokens_in": 1234,
      "tokens_out": 123,
      "cost": 0.0015,
      "extracted_at": "2025-10-29T17:30:00Z"
    }
  },
  "source": {...},
  "metadata": {...}
}
```

---

## 📝 Implementation Plan

### **Step 1: Create Entity Integration Helper** (15 min)

Create `olmocr_pipeline/utils_entity_integration.py`:

```python
"""Helper functions for integrating entity extraction into pipelines"""

def add_entities_to_chunks(
    chunks: List[Dict],
    enable_entities: bool = True,
    api_key: Optional[str] = None
) -> tuple[List[Dict], Dict]:
    """
    Add entity extraction to JSONL chunks.

    Returns:
        (enriched_chunks, aggregate_stats)
    """
    if not enable_entities:
        return chunks, {"entities_extracted": False}

    from utils_entity import extract_entities

    total_cost = 0.0
    total_entities = 0

    for chunk in chunks:
        try:
            result = extract_entities(
                text=chunk["text"],
                extractor="gpt-4o-mini",
                normalize=True,
                api_key=api_key,
                track_costs=True
            )

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

            total_cost += result.get("cost", 0.0)
            total_entities += len(result.get("entities", []))

        except Exception as e:
            # Don't fail pipeline if entity extraction fails
            chunk["entities"] = {
                "error": str(e),
                "extraction_metadata": None
            }

    stats = {
        "entities_extracted": True,
        "total_entities": total_entities,
        "total_chunks_processed": len(chunks),
        "total_cost_usd": total_cost
    }

    return chunks, stats
```

---

### **Step 2: Integrate into pdf_digital.py** (15 min)

**Location:** After chunk creation, before JSONL write

**Changes needed:**

```python
# In process_digital_pdf() function, after chunks are created:

# Get entity extraction config
enable_entities = config.get("entity_extraction", {}).get("enabled", False)
api_key = config.get("entity_extraction", {}).get("openai_api_key") or os.getenv("OPENAI_API_KEY")

# Add entities if enabled
if enable_entities:
    from utils_entity_integration import add_entities_to_chunks
    print(f"   🔍 Extracting entities...")
    chunks, entity_stats = add_entities_to_chunks(chunks, enable_entities=True, api_key=api_key)
    print(f"      Found {entity_stats['total_entities']} entities")
    print(f"      Cost: ${entity_stats['total_cost_usd']:.4f}")
```

---

### **Step 3: Integrate into pdf_scanned.py** (15 min)

**Location:** After chunk creation, before JSONL write

**Changes:** Same as pdf_digital.py

---

### **Step 4: Update config/default.yaml** (5 min)

Add entity extraction configuration:

```yaml
entity_extraction:
  enabled: false  # Default: off (requires API key)
  openai_api_key: null  # Set via environment variable OPENAI_API_KEY
  extractor: "gpt-4o-mini"  # Future: support "gliner", "spacy"
  normalize: true
  track_costs: true
```

---

### **Step 5: Test with Validation Document** (20 min)

```python
# test_entity_extraction.py

# 1. Enable entity extraction in config
# 2. Set OPENAI_API_KEY environment variable
# 3. Process validation document
# 4. Check JSONL for entities field
# 5. Verify cost tracking
# 6. Spot-check entity quality
```

**Expected Results:**
- 6 chunks (digital) or 5 chunks (scanned)
- Each chunk has `entities` field
- Entities include: organizations (Silver Hill, Freeman Mills), dates, parcels
- Total cost: ~$0.05-0.15 for 28-page document

---

## 💰 Cost Estimation

### **GPT-4o-mini Pricing (Oct 2024):**
- Input: $0.150 per 1M tokens
- Output: $0.600 per 1M tokens

### **Expected Costs:**

| Document Size | Chunks | Tokens/Chunk | Total Tokens | Cost per Doc | Cost per 1K docs |
|---------------|--------|--------------|--------------|--------------|------------------|
| 5 pages | 2-3 | 1,500 | 4,500 | $0.003 | $3 |
| 10 pages | 3-5 | 1,500 | 7,500 | $0.005 | $5 |
| 20 pages | 5-8 | 1,500 | 12,000 | $0.008 | $8 |
| 30 pages | 7-10 | 1,500 | 15,000 | $0.010 | $10 |

**For validation document (28 pages, 6 chunks):**
- Estimated: ~9,000 tokens total
- Cost: **~$0.006** (less than 1 cent)

**For production (1,000 docs/month @ 20 pages avg):**
- Estimated: ~12M tokens/month
- Cost: **~$8-10/month**

---

## ⚠️ Important Considerations

### **API Key Management:**
- **Never commit API keys** to git
- Use environment variables only
- Document setup instructions

### **Error Handling:**
- Entity extraction failures should **not break pipeline**
- Log errors but continue processing
- Set `entities.error` field if extraction fails

### **Performance:**
- Entity extraction adds ~1-2 sec per chunk
- For 6 chunks: +6-12 seconds total
- Consider batching for large-scale processing

### **Quality:**
- GPT-4o-mini is highly accurate for structured extraction
- Legal entities are well-supported
- Monitor confidence scores

---

## 📊 Success Criteria

- [ ] Entity extraction integrated into both pipelines
- [ ] Config flag to enable/disable (default: disabled)
- [ ] Cost tracking working
- [ ] Entities present in JSONL output
- [ ] Test document processed successfully
- [ ] Cost < $0.01 per document
- [ ] Entity accuracy > 90% (spot-check)

---

## 🚀 Next Steps (After Integration)

1. **Week 2:** Test with diverse documents (different legal types)
2. **Week 2:** Benchmark entity extraction quality
3. **Week 2:** Optimize prompt for legal domain
4. **Week 3:** Consider local NER models (GLiNER, spaCy) for cost savings

---

**Estimated Time:** 1-1.5 hours total
**Dependencies:** OpenAI API key
**Risk:** Low (feature is optional, won't break existing functionality)
