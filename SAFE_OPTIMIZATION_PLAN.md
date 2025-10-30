# Safe OCR Optimization Plan - Zero Quality Impact

**Date:** October 30, 2025
**Philosophy:** Speed improvements WITHOUT compromising output quality

---

## ✅ Safe Optimizations (No Quality Trade-offs)

### 1. Increase Worker Count (RECOMMENDED)

**Change:** `olmocr.default_workers: 6` → `8` or `10`

**Why it's safe:**
- Workers control parallel page processing, NOT quality
- Each page gets the same full OCR treatment
- More workers = more pages processed simultaneously
- Only limitation is GPU memory

**Expected speedup:** 20-30%
**Quality impact:** ZERO - same OCR quality per page
**Risk:** Low - just watch GPU memory with `nvidia-smi`

**How to test safely:**
```bash
# Step 1: Try 8 workers first
# Edit config/default.yaml:
olmocr:
  default_workers: 8

# Step 2: Process same PDF again
python scripts/process_documents.py --auto --file-types pdf --pdf-type scanned --limit 1

# Step 3: Compare timing - quality should be identical
# Step 4: If stable, try 10 workers
```

---

### 2. Batch Multiple PDFs (RECOMMENDED)

**Change:** Process multiple PDFs in one OlmOCR session instead of one at a time

**Why it's safe:**
- Each PDF still gets full OCR processing
- Reduces model loading overhead (50s → amortized)
- Same quality per document

**Expected speedup:** 30-40% for small PDFs (amortized)
**Quality impact:** ZERO
**Risk:** None

**Example:**
```bash
# Instead of processing 10 PDFs one at a time (10x 50s loading = 500s overhead)
# Process them in one batch (1x 50s loading = 50s overhead)
python scripts/process_documents.py --auto --pdf-type scanned --limit 10 --batch-size 10
```

---

### 3. FlashInfer (ALREADY DONE ✅)

**Status:** Active as of today
**Expected speedup:** 10-30%
**Quality impact:** ZERO - same inference, just faster
**Action needed:** None - already deployed!

---

### 4. GPU Memory Utilization (OPTIONAL)

**Change:** `gpu_memory_utilization: 0.8` → `0.85`

**Why it's safe:**
- More GPU memory = larger batch sizes internally
- Same model, same quality
- Just more efficient GPU usage

**Expected speedup:** 5-10%
**Quality impact:** ZERO
**Risk:** Slightly higher OOM risk (monitor with nvidia-smi)

**Recommendation:** Only try if worker count increase is stable

---

## ❌ NOT RECOMMENDED (Quality Risk)

### Resolution Reduction
- `target_longest_image_dim: 1920 → 1536`
- **Quality impact:** May reduce OCR accuracy on small text
- **Your concern is valid** - stick with 1920 for quality

### Preprocessing Disabled
- Keep current default (disabled)
- **Quality impact:** May help poor scans, but adds time
- Only enable if you have specific quality issues

---

## Recommended Implementation Plan

### Phase 1: Worker Count Test (Safe, Quick)

```bash
# 1. Backup current config
cp config/default.yaml config/default.yaml.backup

# 2. Edit config/default.yaml
# Change: default_workers: 6 → 8

# 3. Test with same PDF we just processed
python scripts/process_documents.py --auto --file-types pdf --pdf-type scanned --limit 1

# 4. Compare results:
#    - Timing: Should be ~20-30% faster
#    - Quality: Output should be identical
#    - GPU memory: Check with `nvidia-smi` during processing

# 5. If successful, try workers: 10
```

### Phase 2: Batch Processing (Safe, Workflow Change)

```bash
# Process 5-10 PDFs at once instead of sequentially
python scripts/process_documents.py --auto --pdf-type scanned --limit 10 --batch-size 10

# Monitor:
# - First PDF: Same ~50s model loading
# - Subsequent PDFs: No loading overhead
# - Total time should be significantly better amortized
```

### Phase 3: GPU Memory (Optional, Low Risk)

```bash
# Only if Phase 1 is stable
# Edit config: gpu_memory_utilization: 0.85
# Test with same process
```

---

## Expected Safe Speedup

### Current Baseline
- 15-page PDF: 320.9s (21.4s/page)

### After Worker Count Increase (8-10 workers)
- 15-page PDF: **~225-260s (15-17s/page)**
- Improvement: **1.2-1.4x faster**
- Quality: **IDENTICAL**

### After Batch Processing (10 PDFs)
- Per-PDF overhead: 50s → 5s (amortized)
- Total time for 10 PDFs: **Much better**
- Quality: **IDENTICAL**

### Combined (Workers + Batching + FlashInfer)
- 15-page PDF: **~200-240s (13-16s/page)**
- Improvement: **1.3-1.6x faster**
- Quality: **IDENTICAL**
- Risk: **LOW**

---

## Quality Verification Checklist

After each optimization test:

```bash
# 1. Compare character count
wc -m /mnt/gcs/legal-ocr-results/rag_staging/markdown/OLD.md
wc -m /mnt/gcs/legal-ocr-results/rag_staging/markdown/NEW.md
# Should be very similar (±5%)

# 2. Spot check output
head -50 /mnt/gcs/legal-ocr-results/rag_staging/markdown/NEW.md
# Text should be clean and accurate

# 3. Check for errors in log
grep -i error /mnt/gcs/legal-ocr-results/rag_staging/logs/olmocr_*.log

# 4. Verify SUCCESS marker exists
ls /mnt/gcs/legal-ocr-results/rag_staging/jsonl/*_SUCCESS
```

---

## Monitoring During Tests

### Terminal 1: Run processing
```bash
python scripts/process_documents.py --auto --pdf-type scanned --limit 1
```

### Terminal 2: Monitor GPU
```bash
watch -n 1 nvidia-smi
```

**What to watch:**
- GPU Memory: Should stay under 21GB (L4 has 22GB total)
- GPU Utilization: Should be 90-100% during inference
- Temperature: Should stay under 80°C

**Warning signs:**
- GPU Memory approaching 22GB → Reduce workers
- OOM errors in logs → Reduce workers or gpu_memory_utilization
- Quality degradation → Revert changes

---

## Rollback Procedure

If anything goes wrong:

```bash
# Restore config
cp config/default.yaml.backup config/default.yaml

# Verify settings
grep -A 5 "olmocr:" config/default.yaml

# Test again
python scripts/process_documents.py --auto --pdf-type scanned --limit 1
```

---

## Why These Are Safe

### Worker Count
- **Technical reason:** Workers control parallelism, not inference quality
- **Analogy:** Like having 10 cashiers vs 5 cashiers - service quality is the same, just faster checkout
- **Evidence:** vLLM documentation confirms this is safe

### Batch Processing
- **Technical reason:** Model processes each document independently
- **Analogy:** Baking 10 cookies in one batch vs 10 separate batches - cookies are identical
- **Evidence:** Common pattern in ML inference

### FlashInfer
- **Technical reason:** Optimizes attention computation, doesn't change outputs
- **Analogy:** Using a faster CPU - same calculations, different implementation
- **Evidence:** Already tested yesterday in isolated environment

---

## Conservative Approach

If you want to be extra cautious:

### Step 1: Test workers=8 with known document
```bash
# Process a document you've already processed
# Compare output character-by-character if needed
diff /path/to/old/output.md /path/to/new/output.md
```

### Step 2: Validate on 5-10 documents
```bash
# Process a small batch with new settings
# Spot check quality before committing
```

### Step 3: Full deployment
```bash
# Once confident, use new settings for production
```

---

## Bottom Line Recommendation

**START HERE (Lowest Risk, Good Reward):**
1. ✅ Keep FlashInfer (already done)
2. 🎯 Increase workers to 8 (test with same PDF)
3. 🎯 If quality looks good, try workers to 10
4. 🎯 Use batch processing for multiple PDFs

**AVOID (Quality Risk):**
- ❌ Don't reduce resolution from 1920
- ❌ Don't change model or quantization
- ❌ Don't skip preprocessing if you need it

**Expected Result:**
- **Speed:** 1.3-1.6x faster
- **Quality:** Identical
- **Risk:** Low
- **Effort:** 5 minutes of config changes

---

## Your Concern is Valid

You're absolutely right to be cautious about quality. The optimizations above are specifically chosen because they:

1. **Don't change the model** - Same OlmOCR-2-7B-FP8
2. **Don't change inference** - Same attention, same decoding
3. **Don't change resolution** - Keep 1920px
4. **Only change parallelism** - More pages at once, not different per-page processing

These are **infrastructure optimizations**, not **algorithm changes**.

---

## Next Step

Would you like to test the worker count increase? It's the safest, easiest optimization with good returns.

```bash
# This is all you need to do:
# 1. Edit config/default.yaml - change workers: 6 → 8
# 2. Run same command we just ran
# 3. Compare timing (should be ~25% faster)
# 4. Compare output quality (should be identical)
```

No quality risk, easy to test, easy to rollback.
