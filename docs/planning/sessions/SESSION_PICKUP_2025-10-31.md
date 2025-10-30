# Session Pickup - October 31, 2025

**Status:** Ready to investigate parallelization performance issues
**Priority:** HIGH - Need to understand why speedup is only 1.28x instead of expected 1.8-2x

---

## 🚨 CRITICAL ISSUES TO INVESTIGATE

### **Issue 1: Disappointing Parallelization Speedup**

**Expected:** 2 workers should give ~1.8-2x speedup
**Actual:** Only 1.28x speedup

**Test Results:**
| Configuration | Time | Files | Per-File | Speedup |
|---------------|------|-------|----------|---------|
| Sequential | 87.3s | 10 PDFs | 8.73s/file | Baseline |
| Parallel (2 workers) | 68.2s | 10 PDFs | 6.82s/file | **1.28x** ❌ |

**Time Breakdown (Parallel Test):**
- Docling (PDF extraction): 56.8s (83%)
- Entities + Embeddings: 11.5s (17%)

**Possible Causes:**
1. ❓ Docling may have GPU contention with 2 workers
2. ❓ ThreadPoolExecutor overhead
3. ❓ OpenAI API rate limiting (unlikely)
4. ❓ Embedding model loading/initialization bottleneck
5. ❓ Files not actually running in parallel (implementation bug?)

---

### **Issue 2: Actual Files Processed**

**User Expected:** 20 files (10 + 10)
**Actual Result:** 15 unique files

**Why?**
- Sequential test: 10 files from Tract 4, 8, etc.
- Parallel test: 10 DIFFERENT files (Lewis No. 11-18)
- **No overlap** between the two tests
- Some duplicate filenames within sequential test (same file in multiple folders)

**Markdown Output:** 16 files (includes 1 from earlier test)
**JSONL Output:** 16 files

---

## 📊 WHAT WE ACCOMPLISHED TODAY

### ✅ **Completed Work**

1. **Fixed Critical Classifier Bug**
   - Pre-OCR'd scanned PDFs now correctly detected
   - Added image detection (bbox area coverage + DPI heuristics)
   - Problem PDF (357s) now routes to OlmOCR-2

2. **Classifier Optimizations**
   - Metadata pre-scan (1000x faster for raw scans)
   - Lightweight image detection (`get_images(full=False)`)
   - Early exit sampling (stop after 3 scans)
   - Final classifier: 31.3s for 331 files (7% faster than baseline)

3. **Implemented Parallelization** (⚠️ BUT NEEDS INVESTIGATION)
   - Added `digital_pdf_workers: 2` to config
   - Modified `utils_processor.py` to parallelize digital PDFs
   - Keeps scanned PDFs sequential (OlmOCR needs full GPU)

4. **Sanity Check - All Systems Working**
   - ✅ Manifests: 15 PDFs processed successfully
   - ✅ Markdown: 16 files generated
   - ✅ JSONL: 16 files with entities + embeddings
   - ❌ HTML: Not generated (need to clarify if required)
   - ✅ Entity extraction: GPT-4o-mini working (5 entities per file avg)
   - ✅ Embeddings: all-mpnet-base-v2 (768-dim)

---

## 🔍 TOMORROW'S INVESTIGATION PLAN

### **Priority 1: Debug Parallelization Performance**

**Goal:** Understand why 2 workers only gives 1.28x speedup

**Investigation Steps:**

1. **Check if files are actually running in parallel**
   ```bash
   # Look for overlapping timestamps in parallel test log
   grep "Processing document" /tmp/digital_pdf_test_parallel.log
   ```

2. **Profile where time is spent**
   - Docling initialization time
   - Entity extraction (OpenAI API calls)
   - Embedding generation
   - File I/O / writing

3. **Test different configurations**
   - Try 4 workers (see if it scales better)
   - Try 1 worker as new baseline
   - Compare multiprocessing vs ThreadPoolExecutor

4. **Check for bottlenecks**
   - GPU utilization during parallel run
   - CPU utilization
   - API rate limits
   - Shared resource locks

**Diagnostic Commands:**
```bash
# Check GPU usage during processing
nvidia-smi dmon -s pucvmet -d 1

# Check if parallel execution is actually happening
grep -E "Processing document.*pdf" /tmp/digital_pdf_test_parallel.log | \
  awk '{print $1, $2, $NF}'

# Compare Docling times between sequential and parallel
grep "Finished converting" /tmp/digital_pdf_test_v2.log
grep "Finished converting" /tmp/digital_pdf_test_parallel.log
```

---

### **Priority 2: Clarify HTML Output Requirement**

**Question:** Is HTML output needed for RAG, or is markdown sufficient?

**Current State:**
- Markdown: ✅ Generated for all files
- JSONL: ✅ Generated with entities + embeddings
- HTML: ❌ Only 1 old file (Oct 28)

**If HTML is needed:**
- Investigate Docling config
- Check if HTML generation is disabled
- Add HTML output verification to tests

**If HTML is NOT needed:**
- Remove HTML checks from sanity tests
- Update documentation

---

### **Priority 3: Production Run Decision**

**Question:** Should we run the full 94 remaining digital PDFs?

**Current Projections (with 2 workers, 1.28x speedup):**
- 94 PDFs × 6.82s = 641 seconds (~10.7 minutes)
- Savings vs sequential: 3.5 minutes

**Options:**
1. **Run with current 2-worker config** (simple, modest benefit)
2. **Investigate & fix parallelization first** (might unlock 1.8-2x)
3. **Run sequentially** (simpler, only 3.5 min slower)

---

## 📁 KEY FILES

### **Modified Today**
- [`config/default.yaml`](../config/default.yaml) - Added `digital_pdf_workers: 2`
- [`olmocr_pipeline/utils_classify.py`](../olmocr_pipeline/utils_classify.py) - Image detection + optimizations
- [`olmocr_pipeline/utils_processor.py`](../olmocr_pipeline/utils_processor.py) - Parallel processing
- [`olmocr_pipeline/utils_inventory.py`](../olmocr_pipeline/utils_inventory.py) - Parallelized inventory building

### **Test Logs**
- `/tmp/digital_pdf_test_v2.log` - Sequential test (10 PDFs, 87.3s)
- `/tmp/digital_pdf_test_parallel.log` - Parallel test (10 PDFs, 68.2s)

### **Documentation**
- [`docs/CLASSIFIER_UPGRADE.md`](CLASSIFIER_UPGRADE.md) - Classifier improvements
- [`docs/CLASSIFIER_OPTIMIZATIONS.md`](CLASSIFIER_OPTIMIZATIONS.md) - Performance optimizations
- [`docs/PERFORMANCE_FINAL.md`](PERFORMANCE_FINAL.md) - Final performance report

---

## 🎯 CURRENT STATE

### **Inventory Status**
- Total PDFs: 321
- Digital PDFs: 110
- Scanned PDFs: 211

### **Processed So Far**
- Digital PDFs processed: **15** (testing)
- Remaining digital PDFs: **~95**
- Scanned PDFs: **0** (not started)

### **Pipeline Status**
✅ Classifier: Fixed and optimized
✅ Entity Extraction: Working (GPT-4o-mini)
✅ Embeddings: Working (all-mpnet-base-v2)
⚠️ Parallelization: Implemented but underperforming
❓ HTML Output: Not generated (clarification needed)

---

## 🤔 KEY QUESTIONS TO ANSWER TOMORROW

1. **Why is parallelization only 1.28x faster?**
   - Are files actually running in parallel?
   - Is there a bottleneck we're missing?
   - Should we try 4 workers?

2. **Is HTML output required?**
   - For RAG queries?
   - For debugging/validation?
   - Or is markdown sufficient?

3. **Should we proceed with production run?**
   - Fix parallelization first?
   - Run with current config?
   - Run sequentially instead?

4. **What's the plan for 211 scanned PDFs?**
   - These will take ~17.5 hours (sequential, GPU-bound)
   - Start after digital PDFs complete?
   - Run overnight?

---

## 🚀 QUICK START FOR TOMORROW

```bash
# 1. Activate environment
source ~/miniconda/etc/profile.d/conda.sh
conda activate olmocr-optimized

# 2. Re-run parallelization test with profiling
python scripts/process_documents.py --auto --file-types pdf --pdf-type digital --limit 10

# 3. Check logs for parallel execution
grep "Processing document" /tmp/digital_pdf_test_parallel.log | head -20

# 4. Compare timing breakdowns
python scripts/analyze_parallel_performance.py  # (create this script)
```

---

## 📈 SUCCESS METRICS

**For parallelization to be "worth it":**
- 2 workers: Should get ≥1.6x speedup (currently: 1.28x ❌)
- 4 workers: Should get ≥2.5x speedup (untested)
- 6 workers: Should get ≥3.5x speedup (untested)

**If we can't achieve these numbers:**
- Consider running sequentially (simpler is better)
- Or focus on optimizing the bottleneck (Docling?)

---

**Status:** Ready for deep investigation tomorrow
**Next Session:** Focus on understanding & fixing parallelization performance
**Expected Duration:** 1-2 hours to debug, then decide on production run

---

Good night! 🌙
