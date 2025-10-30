# RAG Query Guide

## 📊 Current Database Status

**Collection:** `legal_docs_v2_3`
**Documents:** 1 document (SDTO_170.0 ac 12-5-2022.pdf)
**Chunks:** 5 searchable text chunks
**Document Type:** Supplemental Drilling Title Opinion (Oil & Gas)

---

## 🔍 What You Can Query

This document is a legal title opinion for:
- **Property:** Cavin Unit, Tracts 7, 8, and 9
- **Location:** Panola County, Texas
- **Acreage:** 170.00 acres
- **Client:** Silver Hill Energy Operating, LLC

### **Document Contains:**

1. **Title Information**
   - Ownership chains
   - Deeds and transfers
   - Recording information (volumes, pages)

2. **Oil & Gas Leases**
   - Lease agreements
   - Assignments
   - Modifications and amendments

3. **Legal Requirements**
   - Title requirements
   - Advisories
   - Legal opinions

4. **Property Details**
   - Legal descriptions
   - Surveys (Benjamin C. Jordan Survey, A-348)
   - Pooled units

5. **Parties**
   - Silver Hill Energy Operating, LLC (client)
   - Forcap Investments, LP (mentioned party)
   - Madison Timber, LLC (mentioned party)
   - Meriwether Louisiana Land & Timber, LLC (mentioned party)

---

## 💡 Example Queries

### **Good Queries (Semantic Search Works Well):**

```bash
# About parties/ownership
python query_cli.py "Who are the grantors?"
python query_cli.py "Who owns this property?"
python query_cli.py "Tell me about the parties involved"

# About property
python query_cli.py "What properties are mentioned?"
python query_cli.py "Tell me about the Cavin Unit"
python query_cli.py "What is the acreage?"

# About legal documents
python query_cli.py "What deeds are referenced?"
python query_cli.py "Are there any lease assignments?"
python query_cli.py "What recording volumes are mentioned?"

# About requirements
python query_cli.py "What are the title requirements?"
python query_cli.py "Are there any advisories?"
python query_cli.py "What needs to be addressed?"

# General questions
python query_cli.py "When was this document created?"
python query_cli.py "Where is the property located?"
python query_cli.py "What is this document about?"
```

### **Query Types Not Yet Supported:**

❌ **Entity filtering** - No entities extracted yet (shows 0 in stats)
- To enable: Re-process documents with entity extraction
- Then you could filter by PERSON, ORG, DATE, PARCEL, etc.

❌ **Multi-document queries** - Only 1 document loaded
- To enable: Load more documents into Qdrant
- Then you could search across entire corpus

❌ **Exact phrase matching** - Pure vector search
- Future: Add BM25 hybrid search for keyword matching

---

## 🎯 Query Modes

### **1. Simple Query (Command Line)**
```bash
python query_cli.py "your question here"
```

### **2. Interactive Mode**
```bash
python query_cli.py

Query> Who are the grantors?
Query> Tell me about the Cavin Unit
Query> /stats
Query> /quit
```

### **3. With Options**
```bash
# Limit results
python query_cli.py "query" --limit 3

# Show stats
python query_cli.py --stats

# Different collection
python query_cli.py "query" --collection other_collection
```

### **4. Advanced (When Entity Data Available)**
```bash
# Filter by entity types (not working yet - no entities loaded)
python query_cli.py --entity-filter PERSON,ORG "query"

# Require entities
python query_cli.py --require-entities "query"
```

---

## 📈 How to Expand Your Database

### **Option 1: Add More Documents**

```bash
# Process more PDFs from your corpus
python olmocr_pipeline/handlers/pdf_digital.py --input pdf_input/your_doc.pdf

# Or batch process
# (you'll need to create a batch processing script)
```

### **Option 2: Add Entity Extraction**

Currently, chunks don't have entities extracted. To enable:

1. Re-process documents with entity extraction enabled
2. Update chunks with entity metadata
3. Reload into Qdrant

Then entity filtering will work:
```bash
python query_cli.py --entity-filter PERSON "who are the parties?"
```

### **Option 3: Use Existing Test Data**

You have other test documents processed:
- `test_output/bbox_fix_test/jsonl/*.jsonl`
- `test_output/validation_test/digital_output/jsonl/*.jsonl`

Load them:
```python
# Modify setup_persistent_qdrant.py to include more files
test_files = [
    Path("test_output/entity_test/jsonl/SDTO_170.0 ac 12-5-2022.jsonl"),
    Path("test_output/bbox_fix_test/jsonl/SDTO_170.0 ac 12-5-2022.jsonl"),
    Path("test_output/validation_test/digital_output/jsonl/SDTO_170.0 ac 12-5-2022.jsonl"),
]
```

---

## 🔧 Troubleshooting

### **"No results found"**
- Query might be too specific
- Try broader terms
- Check what's in the database with `--stats`

### **Low scores (< 0.3)**
- Results may not be very relevant
- Try rephrasing your query
- Semantic search works best with natural questions

### **"Source: None"**
- Fixed! Should now show `Source: SDTO_170.0 ac 12-5-2022.pdf`
- If still seeing this, data might need reloading

### **"Chunks with entities: 0"**
- Entity extraction hasn't been run on these chunks
- They were processed before entity extraction was added
- Re-process with entity extraction to enable filtering

---

## 🚀 Next Steps

To make this more useful:

1. **Load more documents** (10-50 legal documents)
   - More diverse queries will work
   - Better representation of your corpus

2. **Enable entity extraction** on chunks
   - Re-process with `--extract-entities` flag
   - Or run entity extraction separately

3. **Test with real user queries**
   - Ask legal professionals what they'd search for
   - Iterate based on feedback

4. **Add hybrid search** (optional)
   - Combine vector search with keyword (BM25)
   - Better for exact phrase matching

---

## 📞 Quick Reference

**Show stats:**
```bash
python query_cli.py --stats
```

**Simple query:**
```bash
python query_cli.py "your question"
```

**Interactive mode:**
```bash
python query_cli.py
```

**Check Qdrant health:**
```bash
curl http://localhost:6333/
```

**Qdrant UI:**
http://localhost:6333/dashboard

---

**Last Updated:** 2025-10-29
**Current Database:** 1 document, 5 chunks, 0 entities
