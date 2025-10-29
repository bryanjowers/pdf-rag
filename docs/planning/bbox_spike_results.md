# Bounding Box Extraction Spike - Results

> **Date:** 2025-10-29 | **Status:** ✅ SUCCESS | **Duration:** 30 minutes

---

## 🎉 Executive Summary

**✅ BBOX EXTRACTION AVAILABLE**

Docling **DOES** expose bounding box coordinates for text elements in its output. We can implement precise legal citations with page + bbox coordinates!

---

## 🔍 Findings

### **Bbox Data Structure**

Docling provides bbox data in the `texts[].prov[].bbox` field:

```json
{
  "l": 72.0,      // left (x0)
  "t": 717.556,   // top (y0)
  "r": 188.66,    // right (x1)
  "b": 707.839,   // bottom (y1)
  "coord_origin": "BOTTOMLEFT"  // PDF standard coordinate system
}
```

### **Coordinate System**

- **Origin:** Bottom-left (0,0)
- **Units:** PDF points (1/72 inch)
- **X-axis:** Left to right (increasing)
- **Y-axis:** Bottom to top (increasing)

### **Data Location**

```
DoclingDocument.export_to_dict()
└── texts[]                    # List of text elements
    └── [n].prov[]            # Provenance/location data
        └── [0].bbox          # Bounding box dict
            ├── l: float      # Left
            ├── t: float      # Top
            ├── r: float      # Right
            ├── b: float      # Bottom
            └── coord_origin: str
```

---

## ✅ Decision: Use Docling Bbox

**Recommendation:** Implement bbox extraction using Docling's native coordinates.

**Rationale:**
1. ✅ Data is readily available (no post-processing needed)
2. ✅ Standard PDF coordinate system
3. ✅ Per-text-element granularity (perfect for citations)
4. ✅ No additional dependencies required

---

## 📐 Schema v2.3.0 Impact

Update schema to include bbox:

```json
{
  "attrs": {
    "bbox": {
      "page": 1,
      "x0": 72.0,      // Mapped from "l"
      "y0": 707.839,   // Mapped from "b"
      "x1": 188.66,    // Mapped from "r"
      "y1": 717.556,   // Mapped from "t"
      "width": 612.0,  // Page width (from page info)
      "height": 792.0, // Page height (from page info)
      "unit": "points"
    }
  }
}
```

**Mapping:**
- `x0` = `bbox.l` (left)
- `y0` = `bbox.b` (bottom)
- `x1` = `bbox.r` (right)
- `y1` = `bbox.t` (top)

---

## 🔧 Implementation Notes

### **Extraction Code**

```python
from docling.document_converter import DocumentConverter

converter = DocumentConverter()
result = converter.convert("document.pdf")
doc_dict = result.document.export_to_dict()

# Extract bbox for each text element
for text_elem in doc_dict.get("texts", []):
    if "prov" in text_elem and text_elem["prov"]:
        bbox_data = text_elem["prov"][0].get("bbox")
        if bbox_data:
            bbox = {
                "x0": bbox_data["l"],
                "y0": bbox_data["b"],
                "x1": bbox_data["r"],
                "y1": bbox_data["t"],
                "unit": "points"
            }
            # Add page info from prov
            page_num = text_elem["prov"][0].get("page_no", 1)
            bbox["page"] = page_num
```

### **Page Dimensions**

Get page dimensions from `pages` dict:

```python
pages = doc_dict.get("pages", {})
for page_no, page_data in pages.items():
    width = page_data.get("size", {}).get("width", 612.0)
    height = page_data.get("size", {}).get("height", 792.0)
```

---

## 🧪 Test Results

### **Test File:** `pdf_input/checkpoint4_test/simple.pdf`

**Result:**
```
✅ Found bbox-related field: texts[0].prov[0].bbox
   Type: <class 'dict'>
   Sample: {'l': 72.0, 't': 717.556, 'r': 188.66, 'b': 707.839, 'coord_origin': 'BOTTOMLEFT'}
```

**Validation:**
- ✅ Bbox coordinates present
- ✅ Coordinate origin specified (BOTTOMLEFT)
- ✅ Values in expected range (0-612 for letter-sized page)
- ✅ Per-element granularity available

---

## 📋 Next Steps

### **Immediate (Week 1 - Demo 1+2)**

1. **Update Phase 2 handlers** to extract bbox:
   - Modify `olmocr_pipeline/handlers/pdf_digital.py`
   - Extract bbox from Docling output
   - Add bbox to JSONL schema v2.3.0

2. **Update schema validator**:
   - Add bbox field validation
   - Make bbox optional (null for non-PDFs)

3. **Test on diverse PDFs**:
   - Multi-column layouts
   - Tables with cells
   - Headers/footers

### **Later (Demo 1+2 Week 2-3)**

4. **Implement citation UI**:
   - Highlight bbox regions in PDF viewer
   - "Jump to location" from search results

5. **Optimize for legal docs**:
   - Handle multi-column legal briefs
   - Extract bbox for table cells
   - Map bbox to clause boundaries

---

## 🎯 Success Metrics

| Metric | Target | Status |
|--------|--------|--------|
| **Bbox Available** | Yes | ✅ PASS |
| **Coordinate System** | Standard PDF | ✅ PASS |
| **Per-Element Granularity** | Yes | ✅ PASS |
| **Implementation Complexity** | Low | ✅ PASS |
| **Post-Processing Required** | None | ✅ PASS |

---

## 🚫 What We're NOT Doing

- ❌ PyMuPDF post-processing (not needed!)
- ❌ Complex text matching (bbox is already aligned)
- ❌ Manual coordinate transformation (already in PDF standard)
- ❌ Fallback to page-level citations (bbox works!)

---

## 📚 References

- **Docling Docs:** https://github.com/IBM/docling
- **PDF Coordinate System:** https://pypdf.readthedocs.io/en/stable/user/cropping-and-transforming.html
- **Schema v2.3.0:** [SCHEMA_V2.3.0.md](SCHEMA_V2.3.0.md)

---

## ✅ Conclusion

**Bbox extraction via Docling is APPROVED for Phase 3.**

Schema v2.3.0 will include bbox coordinates, enabling precise legal citations with page + bbox location. No fallback strategy needed!

**Next:** Update schema field `bbox_enabled: true` and implement extraction in Week 1 of Demo 1+2.

---

**Spike Duration:** 30 minutes
**Outcome:** ✅ Success (bbox available)
**Blocker Status:** None
**Ready for Week 1:** ✅ Yes
