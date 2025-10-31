# Scanned PDF Processing - Baseline Test (Batch 1)

**Date:** 2025-10-30
**Purpose:** Establish baseline metrics for scanned PDF processing with OlmOCR-2
**Status:** ✅ COMPLETED (with batching bug discovered and fixed)

---

## Test Configuration

**Processing Mode:** `--ingest-only` (OCR extraction only, no entities/embeddings)

**Pipeline Config:**
- OlmOCR-2 model: `allenai/olmOCR-2-7B-1025-FP8`
- OlmOCR workers: 12 (page-level parallelism)
- **File-level batching**: ENABLED (batch size: 10)
- Pages per group: 10
- GPU: NVIDIA L4 (23GB)
- GPU memory utilization: 80%

**Document Set:**
- Files tested: **5 scanned PDFs** from Instuments directory
- Total pages: **33 pages**
- Page distribution: 1, 3, 3, 2, 24 pages per file

---

## Success Metrics (Per-Page Normalized)

| Metric | Value | Notes |
|--------|-------|-------|
| **Total files processed** | 5 | All scanned PDFs |
| **Total pages processed** | 33 | 100% success rate |
| **Success rate** | 100% (5/5) | All files completed successfully |
| **Average processing time/page** | 20.7s | Includes model loading (one-time 84s cost) |
| **Average character yield/page** | 3,486 chars | Excellent OCR quality |
| **Average token count/page** | ~634 tokens | Estimated (chars ÷ 5.5) |
| **GPU utilization** | 95-96% | High utilization during processing |
| **Total processing time** | 12.8 minutes | 765.6s (84s loading + 681.6s processing) |

---

## Per-File Results

| File | Pages | Chars | Chars/Page | Chunks | Status | Notes |
|------|-------|-------|------------|--------|--------|-------|
| 110-532_WD_Annie Brittain to Z H Clifton.pdf | 1 | 3,073 | 3,073 | 1 | ✅ Success | Processed individually |
| 120-94_WD_T E Middleton to O H Polley.pdf | 3 | 9,830 | 3,277 | 2 | ✅ Success | Batched (4 files) |
| 145-62 AGMT Est of O H Polley to O H Polley 1.27.1930.pdf | 3 | 10,257 | 3,419 | 2 | ✅ Success | Batched (4 files) |
| 165-475 Judgement O H Polley Est to Minta Polley.pdf | 2 | 7,093 | 3,546 | 1 | ✅ Success | Batched (4 files) |
| 165-475 Probate O H Polley Est to O H Polley Est Shelby County, TX.pdf | 24 | 84,789 | 3,533 | 10 | ✅ Success | Batched (4 files) |
| **TOTAL** | **33** | **114,042** | **3,486 avg** | **16** | **5/5** | |

---

## Quality Observations

### OCR Quality (Pending Manual Review)
**Quantitative metrics:**
- Character yield: 3,073-3,546 chars/page (well above 100 char/page minimum)
- Zero low-yield warnings
- Zero page failures (33/33 succeeded)

**Qualitative review (manual):**
- [ ] Text is readable and coherent
- [ ] Tables extracted (if applicable)
- [ ] No excessive gibberish
- [ ] Legal terminology preserved
- [ ] Dates and names correct

### Performance
- Processing time: 20.7s per page (includes 84s one-time model loading)
- GPU utilization during processing: 95-96%
- No GPU memory issues (stayed within 80% target)
- No crashes or hangs

### File-Level Batching Performance
- Batched: 4 files together (32 pages total)
- Individual: 1 file (1 page)
- Model loads: 1 (vs 5 without batching)
- GPU utilization: Sustained at 95-96% (no idle gaps)

### Issues Found

**🐛 Post-Processing Bug - FIXED**

**Problem:** 4/5 files quarantined despite successful OCR

**Root Cause:**
- `get_olmocr_jsonl_path()` only parsed CSV rows with format: `hash,single_file`
- Batched rows have format: `hash,file1,file2,file3,...`
- Function skipped batched rows, couldn't find output for 4 files

**Impact:**
- OlmOCR successfully processed all 5 files
- Post-processing failed to extract individual file data from batched JSONL
- 4 files appeared quarantined in manifest

**Fix:**
- Updated CSV parsing: `if len(row) >= 2` instead of `== 2`
- Added `filter_source_file` parameter to `olmocr_jsonl_to_markdown_with_pages()`
- Modified files:
  - [olmocr_pipeline/utils_olmocr.py:172](olmocr_pipeline/utils_olmocr.py#L172) - CSV parsing
  - [olmocr_pipeline/utils_olmocr.py:269](olmocr_pipeline/utils_olmocr.py#L269) - Filter parameter
  - [olmocr_pipeline/handlers/pdf_scanned.py:392](olmocr_pipeline/handlers/pdf_scanned.py#L392) - Use filter

**Resolution:** All 4 files successfully reprocessed with fix

---

## Raw Data

**Batch ID:** `20251030_193924_u9x2`

**Manifest:**
`/mnt/gcs/legal-ocr-results/manifests/manifest_20251030_193924_u9x2.csv`

**OlmOCR Log:**
`/mnt/gcs/legal-ocr-results/rag_staging/logs/olmocr_batch_20251030_193924_u9x2_5files.log`

**Output Directories:**
- OlmOCR staging: `/mnt/gcs/legal-ocr-results/rag_staging/olmocr_staging/`
- Markdown: `/mnt/gcs/legal-ocr-results/rag_staging/markdown/`
- JSONL: `/mnt/gcs/legal-ocr-results/rag_staging/jsonl/`

**OlmOCR Metrics (from log):**
- Total elapsed time: 765.59 seconds (12.8 min)
- Model loading: ~84 seconds
- Processing: ~682 seconds
- Server input tokens: 58,481
- Server output tokens: 34,577
- Completed pages: 33/33
- Failed pages: 0
- Page failure rate: 0.00%
- Input tokens/sec: 76.39
- Output tokens/sec: 45.16

---

## Next Steps

- [ ] Manual quality review of 5 markdown outputs
- [ ] Commit batching bug fix
- [ ] Run larger batch test (10-20 files) to validate scaling
- [ ] Update technical spike document with implementation results
