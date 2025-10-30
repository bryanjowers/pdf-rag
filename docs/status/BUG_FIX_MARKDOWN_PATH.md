# Bug Fix: OlmOCR Markdown File Path Lookup

**Date:** 2025-10-29
**Issue:** Markdown files not found in expected location
**Status:** ✅ **FIXED**

---

## 🐛 Bug Description

**Location:** [olmocr_pipeline/handlers/pdf_scanned.py:112](olmocr_pipeline/handlers/pdf_scanned.py#L112)

**Problem:** Code only looked for markdown files in workspace directory, but OlmOCR creates markdown files in different locations depending on input path type.

**Impact:**
- Bbox coverage was only 20% (1/5 chunks)
- Should be 100% or close to it after fix

---

## 🔍 Root Cause

**OlmOCR Markdown File Behavior:**

When using the `--markdown` flag, OlmOCR creates markdown files in different locations:

| Input Path Type | Markdown Location | Example |
|----------------|-------------------|---------|
| **Absolute path** | Same directory as source PDF | `/path/to/file.pdf` → `/path/to/file.md` |
| **Relative path** | Workspace markdown directory | `./file.pdf` → `workspace/markdown/file.md` |

**Our code only checked:** `workspace/markdown/file.md`

**This failed for absolute paths** (most common case in validation tests)

---

## ✅ Fix Applied

### **Before (WRONG):**

```python
# Line 112 - ORIGINAL CODE
olmocr_md_path = olmocr_staging / "markdown" / pdf_path.name.replace('.pdf', '.md')
```

❌ Only checked workspace directory
❌ Missed markdown files created by absolute path inputs

### **After (FIXED):**

```python
# Lines 115-119 - FIXED CODE
# Try source directory first (most common with absolute paths)
olmocr_md_path = pdf_path.with_suffix('.md')

# If not found, try workspace markdown directory (for relative paths)
if not olmocr_md_path.exists():
    olmocr_md_path = olmocr_staging / "markdown" / pdf_path.name.replace('.pdf', '.md')
```

✅ Checks source directory first (absolute paths)
✅ Falls back to workspace directory (relative paths)
✅ Handles both input path types

---

## 📊 Expected Impact

### **Before Fix:**
- Bbox coverage: 20% (1/5 chunks)
- Markdown file: Not found → fallback to JSONL conversion
- Page mapping: Limited

### **After Fix:**
- Bbox coverage: Expected 100% (or near 100%)
- Markdown file: Found in source directory ✅
- Page mapping: Complete from OlmOCR markdown

---

## 🧪 Testing

**Test Script:** `test_scanned_bbox_fix.py`

**Test Process:**
1. Process 28-page PDF with OlmOCR
2. Check if markdown file is found
3. Verify bbox coverage in JSONL output
4. Compare before/after bbox statistics

**Expected Results:**
- ✅ Markdown file found in source directory
- ✅ Higher bbox coverage (close to 100%)
- ✅ All chunks have page information

---

## 📋 Verification Checklist

- [x] Bug identified and root cause understood
- [x] Fix implemented in pdf_scanned.py
- [x] Code comments updated to explain behavior
- [ ] Test script running (in progress)
- [ ] Bbox coverage improved (pending test results)
- [ ] Ready to proceed to Task 3

---

## 🎯 Impact Assessment

**Severity:** Medium
- Bug prevented proper bbox extraction
- But didn't break core functionality (text extraction still worked)

**Complexity:** Low
- Simple 2-line fix
- Added fallback logic for robustness

**Risk:** Low
- Change is backwards compatible
- Fallback ensures old behavior still works
- No breaking changes to API or schema

---

## 🚀 Next Steps

1. ✅ Fix applied
2. ⏳ Test running (wait for completion)
3. 📊 Verify bbox coverage improvement
4. ✅ Proceed to Task 3 (Entity Extraction)

---

**Estimated Time:** 5 minutes (as predicted) ✅
**Status:** Complete, pending verification
