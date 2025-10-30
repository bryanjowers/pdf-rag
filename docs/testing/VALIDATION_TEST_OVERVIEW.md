# Validation Test: Digital vs Scanned Pipeline Comparison

> **Date:** 2025-10-29 | **Status:** 🔄 Running | **Type:** Research/Validation

---

## 🎯 Purpose

This is a **research test** to validate assumptions about our processing pipelines. It is **NOT** a pipeline change or new feature implementation.

### **What We're Testing:**
- How much quality/precision do we lose when processing scanned PDFs vs digital PDFs?
- Does OlmOCR's OCR quality justify the page-level bbox limitation?
- Can we quantify the trade-offs in our current strategy?

### **What We're NOT Doing:**
- ❌ Changing the current pipeline strategy
- ❌ Implementing a hybrid processor
- ❌ Modifying production code

---

## 🧪 Test Design

### **Test Document:**
- **File:** SDTO_170.0 ac 12-5-2022.pdf
- **Type:** Complex legal document (362KB, 28 pages)
- **Content:** Tables, multi-column text, legal formatting
- **Why This Doc:** Real-world complexity, known to have tables

### **Test Process:**

```
Step 1: Baseline (Ground Truth)
   Input: Digital PDF (original)
   Pipeline: Docling
   Output: High-quality text + precise bbox

Step 2: Simulated Scan
   Input: Convert PDF pages → PNG images @ 300 DPI
   Purpose: Simulate real-world scanning

Step 3: Scanned Processing
   Input: PNG images → PDF
   Pipeline: OlmOCR
   Output: OCR text + page-level bbox

Step 4: Comparison
   Compare: Text quality, bbox coverage, tables, performance
```

---

## 📊 Metrics We're Measuring

### **1. Text Quality**
- **Character count:** Digital vs Scanned
- **Text similarity:** SequenceMatcher ratio (0.0 - 1.0)
- **Expected:** >95% similarity if OlmOCR is good

### **2. Bbox Coverage**
- **Digital:** % chunks with bbox (should be ~100%)
- **Scanned:** % chunks with bbox (should be ~100%)
- **Precision difference:** Element-level vs page-level

### **3. Bbox Precision**
- **Digital:** How many chunks have precise coordinates (x0, y0, x1, y1)?
- **Scanned:** How many chunks have precise coordinates? (MVP: 0)
- **Expected:** Digital 100%, Scanned 0% (page-level only)

### **4. Table Detection**
- **Digital:** Number of chunks marked as tables
- **Scanned:** Number of chunks marked as tables
- **Quality:** Do both pipelines preserve table structure?

### **5. Performance**
- **Digital pipeline:** Processing time (seconds)
- **Scanned pipeline:** Processing time (seconds)
- **Speed ratio:** How much slower is scanned processing?

---

## 🔍 What This Will Tell Us

### **Question 1: Is OlmOCR worth the trade-off?**
If text similarity is >95%, then OlmOCR's superior OCR justifies the page-level bbox limitation for scanned documents.

### **Question 2: How much precision do we lose?**
Quantify the difference between:
- Digital: Element-level bbox (precise)
- Scanned: Page-level bbox only (MVP)

### **Question 3: Should we consider a hybrid approach?**
**IF** we discover:
- Docling can extract bbox from scanned PDFs (✅ Already proven!)
- Docling bbox quality is good
- Performance penalty is acceptable

**THEN** we could consider future enhancement:
```
Hybrid Pipeline (Future):
  Pass 1: OlmOCR → Superior text quality
  Pass 2: Docling → Precise bbox extraction
  Merge: OlmOCR text + Docling bbox = Best of both worlds
```

### **Question 4: Table handling comparison**
Which pipeline preserves legal document tables better?
- Digital: Native table structure
- Scanned: OlmOCR HTML tables vs Docling tables

---

## 💡 Current Strategy (Unchanged)

### **Our Phase 3 Approach:**

| Document Type | Processor | Text Quality | Bbox Precision | Status |
|---------------|-----------|--------------|----------------|--------|
| **Digital PDF** | Docling | Native (best) | Element-level | ✅ Implemented |
| **Scanned PDF** | OlmOCR | OCR (high quality) | Page-level only | ✅ Implemented |

### **Schema v2.3.0 Bbox Format:**

**Digital PDF:**
```json
{
  "attrs": {
    "bbox": {
      "page": 1,
      "x0": 72.0,      // ✅ Precise
      "y0": 600.0,     // ✅ Precise
      "x1": 500.0,     // ✅ Precise
      "y1": 650.0      // ✅ Precise
    }
  }
}
```

**Scanned PDF (MVP):**
```json
{
  "attrs": {
    "bbox": {
      "page": 1,       // ✅ From OlmOCR
      "x0": null,      // ⏳ Future enhancement
      "y0": null,
      "x1": null,
      "y1": null
    }
  }
}
```

---

## 📈 Expected Outcomes

### **Best Case Scenario:**
- Text similarity: 98%+
- OlmOCR OCR quality excellent
- Page-level bbox sufficient for legal citations
- Current strategy validated ✅

### **Interesting Discovery:**
- Text similarity: 90-95%
- Scanned processing much slower
- Some table structure loss
- MVP approach still valid, but room for future enhancement

### **Worst Case:**
- Text similarity: <90%
- Significant quality degradation
- Tables poorly preserved
- Need to reconsider strategy

---

## 🚀 Next Steps After Test

### **If Current Strategy Validated:**
1. ✅ Continue with Week 1 tasks (entity extraction, embeddings)
2. ✅ Document trade-offs for future reference
3. ✅ Focus on completing Demo 1+2

### **If Hybrid Approach Looks Promising:**
1. Document findings in decision log
2. Add hybrid processor to Phase 3 backlog
3. **Still complete Week 1 with current approach**
4. Evaluate hybrid as Week 2+ enhancement

### **Regardless of Outcome:**
- Week 1 plan unchanged
- Task 3: Entity extraction (next)
- Task 4: Embeddings + Qdrant
- Task 5: End-to-end testing

---

## 📁 Test Outputs

**Location:** `/home/bryanjowers/pdf-rag/test_output/validation_test/`

**Files Generated:**
```
validation_test/
├── scanned_images/           # PDF → PNG conversion
│   ├── page_000.png
│   ├── page_001.png
│   └── ...
├── digital_output/           # Docling processing
│   ├── jsonl/
│   └── markdown/
├── scanned_output/           # OlmOCR processing
│   ├── jsonl/
│   └── markdown/
└── scanned_temp.pdf          # Combined images → PDF
```

---

## ⏱️ Timeline

- **Test Started:** 2025-10-29 17:13 UTC
- **Expected Duration:** 5-10 minutes
- **Current Status:** 🔄 Processing digital PDF through Docling
- **ETA:** ~17:20-17:25 UTC

---

**Status:** 🔄 Validation test running in background
**Purpose:** Research and validate assumptions
**Impact:** No changes to current pipeline
**Next:** Resume Week 1 tasks after test completes
