# OlmOCR Bbox Extraction Strategy

> **Critical Requirement:** Scanned PDFs must use OlmOCR-2 (better OCR quality than Docling for legal docs)

---

## 🎯 The Challenge

**Requirement:** Use OlmOCR-2 for scanned PDFs (better OCR quality)
**Need:** Extract bbox coordinates for precise legal citations
**Question:** Does OlmOCR-2 provide bbox data?

---

## 🔍 Research Findings

### **OlmOCR-2 Model Output**

OlmOCR-2 is a VLM (Vision-Language Model) that:
1. Takes document images as input
2. Generates markdown/HTML as output
3. Does NOT natively output structured bbox coordinates

**Why:**
- OlmOCR-2 is generative (like GPT-4V for documents)
- It "reads" the image and generates text
- Unlike traditional OCR (Tesseract, EasyOCR), it doesn't detect text regions first

### **Current Phase 2 Implementation**

Your `handlers/pdf_scanned.py` calls OlmOCR CLI which outputs:
- Markdown text (clean, well-formatted)
- HTML with basic structure
- **No bbox coordinates**

---

## ✅ Solution: Hybrid Approach

**Use BOTH OlmOCR and Docling strategically:**

### **For Scanned PDFs:**

1. **Pass 1: OlmOCR-2** (Text extraction)
   - Run OlmOCR-2 for superior OCR quality
   - Extract clean text content
   - Store as primary text source

2. **Pass 2: Docling with RapidOCR** (Bbox extraction)
   - Run Docling on same PDF (it will use RapidOCR for scanned pages)
   - Extract bbox coordinates from Docling output
   - **Text matching:** Align OlmOCR text with Docling bbox regions

3. **Merge:** Combine OlmOCR text + Docling bbox
   - Primary content: OlmOCR text (higher quality)
   - Citations: Docling bbox (spatial coordinates)
   - Fuzzy text matching to align chunks

---

## 📐 Implementation Plan

### **Week 1: Extend `handlers/pdf_scanned.py`**

```python
def process_scanned_pdf_with_bbox(pdf_path, config):
    """
    Hybrid processing: OlmOCR text + Docling bbox
    """

    # Step 1: OlmOCR for text (existing code)
    olmocr_output = run_olmocr(pdf_path)
    olmocr_text_chunks = parse_olmocr_markdown(olmocr_output)

    # Step 2: Docling for bbox (NEW)
    from docling.document_converter import DocumentConverter
    converter = DocumentConverter()
    result = converter.convert(pdf_path)
    doc_dict = result.document.export_to_dict()

    # Step 3: Extract Docling bbox
    docling_bbox_map = {}
    for text_elem in doc_dict.get("texts", []):
        if "prov" in text_elem and text_elem["prov"]:
            bbox_data = text_elem["prov"][0].get("bbox")
            page_no = text_elem["prov"][0].get("page_no", 1)
            text_content = text_elem.get("text", "")

            if bbox_data:
                docling_bbox_map[text_content] = {
                    "page": page_no,
                    "bbox": {
                        "x0": bbox_data["l"],
                        "y0": bbox_data["b"],
                        "x1": bbox_data["r"],
                        "y1": bbox_data["t"]
                    }
                }

    # Step 4: Match OlmOCR chunks to Docling bbox (fuzzy matching)
    from difflib import SequenceMatcher

    for chunk in olmocr_text_chunks:
        chunk_text = chunk["text"]
        best_match = None
        best_score = 0.0

        # Find best matching Docling text
        for docling_text, bbox_info in docling_bbox_map.items():
            score = SequenceMatcher(None, chunk_text, docling_text).ratio()
            if score > best_score and score > 0.7:  # 70% similarity threshold
                best_score = score
                best_match = bbox_info

        # Add bbox to chunk
        if best_match:
            chunk["attrs"]["bbox"] = best_match["bbox"]
            chunk["attrs"]["bbox"]["page"] = best_match["page"]
        else:
            # Fallback: page-level bbox (no precise coordinates)
            chunk["attrs"]["bbox"] = None

    return olmocr_text_chunks
```

### **Alternative: Page-Level Fallback**

If fuzzy matching proves unreliable:

```python
# Simpler approach: Use page numbers only for scanned PDFs
for chunk in olmocr_text_chunks:
    page_num = chunk.get("page_num", 1)
    chunk["attrs"]["bbox"] = {
        "page": page_num,
        "x0": None,  # No precise coordinates
        "y0": None,
        "x1": None,
        "y1": None,
        "note": "Scanned PDF - page-level citation only"
    }
```

**Citation format:**
- Digital PDFs: "Source: deed.pdf, Page 5, Lines 10-15"
- Scanned PDFs: "Source: deed.pdf, Page 5" (no bbox)

---

## 📊 Comparison Matrix

| Approach | Text Quality | Bbox Precision | Complexity | Recommended? |
|----------|--------------|----------------|------------|--------------|
| **Docling Only** | Good (RapidOCR) | ✅ High | Low | ❌ No (text quality lower) |
| **OlmOCR Only** | ✅ Excellent | ❌ None | Low | ❌ No (no bbox) |
| **Hybrid (OlmOCR + Docling)** | ✅ Excellent | ⚠️ Medium (via matching) | Medium | ✅ Yes (best of both) |
| **OlmOCR + Page-Level** | ✅ Excellent | ⚠️ Low (page only) | Low | ✅ Yes (simple fallback) |

---

## 🎯 Recommended Strategy

**Start with Option 4 (OlmOCR + Page-Level), upgrade to Option 3 (Hybrid) if needed:**

### **Phase 3 Demo 1+2:**
- **Digital PDFs:** Docling with precise bbox ✅
- **Scanned PDFs:** OlmOCR text + page-level citations
- **Citation format:**
  - Digital: "deed.pdf, Page 5, bbox(72, 600, 500, 650)"
  - Scanned: "deed.pdf, Page 5"

### **Phase 3 Demo 3-4 (if bbox precision becomes critical):**
- Implement hybrid approach with fuzzy text matching
- Test alignment accuracy on real scanned legal documents
- Measure: % of chunks with successful bbox matching

---

## ⚙️ Configuration Update

Update `config/phase3.yaml`:

```yaml
schema:
  version: "2.3.0"
  bbox_enabled: true
  bbox_strategy:
    digital_pdf: "docling_native"  # Full bbox precision
    scanned_pdf: "page_level"      # Page-level only (for now)
    # Future: "hybrid_match"       # OlmOCR text + Docling bbox matching
```

---

## ✅ Decision

**Approved Strategy:**

1. **Digital PDFs:** Use Docling bbox (native, precise) ✅
2. **Scanned PDFs:** Use OlmOCR text + page-level citations ✅
3. **Future upgrade:** Implement hybrid matching if bbox precision is needed

**Rationale:**
- Preserves OlmOCR's superior text quality
- Provides citations (page-level is acceptable for MVP)
- Low complexity, fast implementation
- Can upgrade to hybrid approach later if needed

---

## 📝 Next Steps

**Week 1 (Demo 1+2):**
1. Update `handlers/pdf_digital.py` - Extract Docling bbox ✅
2. Update `handlers/pdf_scanned.py` - Keep OlmOCR text, add page-level bbox
3. Update schema v2.3.0 - Make bbox optional (null for page-level)
4. Test on mixed document set (digital + scanned)

**Future (Demo 3-4, if needed):**
5. Implement hybrid text matching
6. Measure bbox alignment accuracy
7. Upgrade scanned PDF handler if >90% alignment achieved

---

**Status:** ✅ Strategy approved
**Blocker:** None
**Ready for Week 1:** ✅ Yes
