# Scanned PDF OCR Processing - Optimization Guide

**Date:** October 30, 2025
**Current Baseline:** ~320s for 15-page PDF
**Target:** Identify all optimization opportunities

---

## Current Configuration

### OlmOCR Settings (from config/default.yaml)
```yaml
olmocr:
  model_id: "allenai/olmOCR-2-7B-1025-FP8"
  gpu_memory_utilization: 0.8   # 80% GPU memory
  default_workers: 6            # Parallel workers for page processing
```

### Current Performance (15-page test)
- **Total time:** 320.9 seconds (~5.3 minutes)
- **Time per page:** ~21.4 seconds/page
- **Model loading:** ~50 seconds (one-time cost)
- **Actual inference:** ~270 seconds

---

## Optimization Strategies

### 1. ✅ FlashInfer (Already Implemented)

**Status:** ACTIVE as of today
**Expected benefit:** 10-30% speedup for inference
**Evidence:** Log shows "Using FlashInfer for top-p & top-k sampling"

**Estimated improvement:**
- Before FlashInfer: ~270s inference
- After FlashInfer: ~210-240s inference (20-30% faster)
- **New estimated time:** 260-290s for 15-page PDF

**To verify actual gains:** Need to test same PDF without FlashInfer for comparison

---

### 2. Increase Worker Count (Easy Win)

**Current:** 6 workers
**Recommendation:** Test with 8-12 workers

OlmOCR processes pages in parallel using vLLM's internal batching. More workers = more pages processed simultaneously.

**How to test:**
```bash
# Edit config/default.yaml
olmocr:
  default_workers: 8  # Try 8, 10, 12
```

Or override at runtime:
```bash
python scripts/process_documents.py ... --workers 8
```

**Expected benefit:** 20-30% speedup
**GPU constraint:** L4 has 22GB VRAM, monitor with `nvidia-smi` to avoid OOM

**Recommended testing:**
1. Test with 8 workers (safe)
2. If stable, try 10 workers
3. Monitor GPU memory usage
4. Find sweet spot before OOM

---

### 3. Reduce Image Resolution (Trade Quality for Speed)

**Current:** `target_longest_image_dim: "1920"`
**Options:** 1920 (high), 1536 (medium), 1280 (faster), 1024 (fast)

Lower resolution = faster processing but potentially lower OCR accuracy.

**Where to configure:**
```yaml
# config/default.yaml
olmocr:
  target_longest_image_dim: "1536"  # Down from 1920
```

**Expected benefit:** 15-25% speedup
**Trade-off:** May reduce accuracy on small text or complex layouts

**Recommendation:**
- Keep 1920 for critical documents
- Use 1536 for bulk processing
- Test 1280 for simple documents

---

### 4. Adjust GPU Memory Utilization (Experimental)

**Current:** `gpu_memory_utilization: 0.8` (80%)
**Options:** 0.85-0.95 (higher risk of OOM)

More GPU memory allows larger batch sizes and longer context windows.

**Caution:** Higher values increase OOM risk
**Recommendation:** Only try if you have consistent headroom
**How to test:**
```yaml
olmocr:
  gpu_memory_utilization: 0.85  # Carefully increase from 0.8
```

**Expected benefit:** 5-10% speedup
**Risk:** Medium (can cause OOM crashes)

---

### 5. Batch Processing Multiple PDFs

**Current approach:** Process PDFs sequentially (one at a time)
**Optimization:** Process multiple small PDFs in one OlmOCR session

OlmOCR loads the model once and can process multiple documents. If you're processing many small PDFs, batching them reduces the per-document overhead.

**Example:**
```bash
# Instead of processing 1 PDF at a time
python scripts/process_documents.py --limit 1 --pdf-type scanned

# Process 10 PDFs in one batch (model loads once)
python scripts/process_documents.py --limit 10 --pdf-type scanned --batch-size 10
```

**Expected benefit:**
- Small PDFs (1-5 pages): 30-40% speedup amortized
- Large PDFs (50+ pages): Minimal benefit

---

### 6. Pre-processing Optimization

**Current:** Optional preprocessing disabled by default

If PDFs have poor quality scans, you can enable preprocessing:
```bash
python scripts/process_documents.py ... --preprocess
```

**Preprocessing includes:**
- Image cleanup
- Contrast enhancement
- Deskewing
- Noise reduction

**Trade-off:**
- Adds 5-10s per page
- But may improve OCR accuracy significantly
- Net effect depends on document quality

**Recommendation:** Use only for poor-quality scans

---

### 7. Use FP8 Quantization (Already Using)

**Current:** Model is `olmOCR-2-7B-1025-FP8` ✅

FP8 (8-bit floating point) is already enabled, providing:
- 2x faster inference vs FP16
- 2x less GPU memory
- Minimal accuracy loss

**No action needed** - already optimized!

---

### 8. Model Compilation Cache (Already Active)

**Current:** vLLM uses torch.compile with caching ✅

From test log:
```
Using cache directory: /home/bryanjowers/.cache/vllm/torch_compile_cache/...
Directly load the compiled graph(s) for dynamic shape from the cache, took 3.574 s
```

The first run compiles the model (~12s), subsequent runs load from cache (~3.5s).

**No action needed** - already optimized!

---

### 9. CUDA Graphs (Already Active)

**Current:** vLLM uses CUDA graphs for faster execution ✅

From test log:
```
Capturing CUDA graphs (mixed prefill-decode, PIECEWISE): 100%
```

CUDA graphs optimize GPU kernel launches and reduce overhead.

**No action needed** - already optimized!

---

### 10. Parallel Document Classification

**Current:** `parallel_workers: 8` for classification ✅

Classification (determining if PDF is digital vs scanned) uses 8 parallel workers.

**Already optimized** - classification is fast (~1-2s per PDF)

---

## Recommended Optimization Priority

### Quick Wins (Low Risk, High Impact)

1. **✅ FlashInfer** - Already done! (10-30% speedup)
2. **🎯 Increase workers to 8-10** - Easy config change (20-30% speedup)
3. **🎯 Batch multiple small PDFs** - Workflow change (30-40% speedup for small docs)

### Medium Risk (Requires Testing)

4. **Reduce image resolution to 1536** - Test accuracy impact (15-25% speedup)
5. **Increase GPU memory to 0.85** - Monitor for OOM (5-10% speedup)

### Situational (Use Case Specific)

6. **Enable preprocessing** - Only for poor-quality scans (varies)
7. **Further reduce resolution to 1280** - Only for simple documents (25-35% speedup)

---

## Expected Performance After Optimizations

### Current Baseline (15-page PDF)
- Total: 320.9s
- Per page: 21.4s/page

### After Quick Wins (FlashInfer + 8-10 workers)
- Total: ~180-220s (44-31% reduction)
- Per page: ~12-15s/page
- **Improvement: 1.5-1.8x faster**

### After Medium Risk (+ Resolution + GPU Memory)
- Total: ~140-180s (56-44% reduction)
- Per page: ~9-12s/page
- **Improvement: 1.8-2.3x faster**

### Optimal Configuration (All optimizations)
- Total: ~120-150s (63-53% reduction)
- Per page: ~8-10s/page
- **Improvement: 2.1-2.7x faster**

---

## Testing Plan

### Phase 1: Worker Count Testing

```bash
# Test with current config (6 workers) - baseline
python scripts/process_documents.py --auto --file-types pdf --pdf-type scanned --limit 1

# Test with 8 workers
# Edit config: olmocr.default_workers: 8
python scripts/process_documents.py --auto --file-types pdf --pdf-type scanned --limit 1

# Test with 10 workers (if 8 workers stable)
# Edit config: olmocr.default_workers: 10
python scripts/process_documents.py --auto --file-types pdf --pdf-type scanned --limit 1

# Compare processing times
```

### Phase 2: Resolution Testing

```bash
# Test with 1536 resolution
# Edit config: olmocr.target_longest_image_dim: "1536"
python scripts/process_documents.py --auto --file-types pdf --pdf-type scanned --limit 1

# Compare output quality and processing time
```

### Phase 3: Batch Processing Testing

```bash
# Test batch of 5 small PDFs
python scripts/process_documents.py --auto --file-types pdf --pdf-type scanned --limit 5 --batch-size 5

# Compare per-PDF time vs sequential
```

---

## Monitoring Commands

### Watch GPU Usage During Processing
```bash
watch -n 1 nvidia-smi
```

Key metrics:
- **GPU Memory:** Should stay under 21GB (avoid OOM)
- **GPU Utilization:** Should be 90-100% during inference
- **Temperature:** Should stay under 80°C

### Check Processing Logs
```bash
tail -f /mnt/gcs/legal-ocr-results/rag_staging/logs/olmocr_*.log
```

### Profile Individual PDF
```bash
# Look for timing in logs
grep -E "(Duration|took|seconds)" /tmp/flashinfer_test_run.log
```

---

## Configuration Examples

### Optimized for Speed (Balanced)
```yaml
olmocr:
  model_id: "allenai/olmOCR-2-7B-1025-FP8"
  gpu_memory_utilization: 0.85
  default_workers: 8
  target_longest_image_dim: "1536"
```

### Optimized for Quality (Slower)
```yaml
olmocr:
  model_id: "allenai/olmOCR-2-7B-1025-FP8"
  gpu_memory_utilization: 0.8
  default_workers: 6
  target_longest_image_dim: "1920"
```

### Optimized for Maximum Speed (Lower Quality)
```yaml
olmocr:
  model_id: "allenai/olmOCR-2-7B-1025-FP8"
  gpu_memory_utilization: 0.9
  default_workers: 10
  target_longest_image_dim: "1280"
```

---

## Hardware Considerations

### Current Hardware: NVIDIA L4 (22GB VRAM)

**Strengths:**
- ✅ 22GB VRAM (plenty for 7B model)
- ✅ Good for inference workloads
- ✅ Supports FP8 quantization

**Limitations:**
- Not the fastest GPU for LLMs (but cost-effective)
- Single GPU (no multi-GPU scaling)

### Upgrade Options (If Needed)

If you need 2-3x more speed:
- **L40 (48GB):** 2x faster than L4, 2x VRAM
- **A100 (40GB):** 3x faster than L4, premium price
- **A100 (80GB):** 3x faster, 4x VRAM (overkill for 7B model)

**Recommendation:** L4 is sufficient; focus on software optimizations first

---

## Current Status Summary

**Already Optimized:**
- ✅ FP8 quantization (2x faster than FP16)
- ✅ FlashInfer (10-30% faster inference)
- ✅ torch.compile with caching
- ✅ CUDA graphs
- ✅ Parallel classification (8 workers)

**Not Yet Optimized:**
- ⏸️ OlmOCR worker count (6 → 8-10)
- ⏸️ Image resolution (could reduce if acceptable)
- ⏸️ GPU memory utilization (could increase cautiously)
- ⏸️ Batch processing (workflow optimization)

**Estimated Remaining Speedup Potential:** 1.5-2x faster with minimal risk

---

## Next Steps

1. **Quick Test:** Increase workers to 8 and re-run the same PDF
2. **Benchmark:** Compare processing times with worker count
3. **Monitor:** Check GPU memory usage with `nvidia-smi`
4. **Iterate:** Find optimal worker count for your hardware
5. **Document:** Update this guide with actual benchmarks

---

## Related Documentation

- [FLASHINFER_DEPLOYMENT_SUCCESS.md](../../FLASHINFER_DEPLOYMENT_SUCCESS.md) - FlashInfer installation
- [PARALLELIZATION_OPTIMIZATION_COMPLETE.md](PARALLELIZATION_OPTIMIZATION_COMPLETE.md) - Digital PDF optimization
- [config/default.yaml](../../config/default.yaml) - Current configuration

---

**Last Updated:** October 30, 2025
**Test Platform:** NVIDIA L4 (22GB), OlmOCR v0.4.2, vLLM v0.11.0
**Current Baseline:** 320.9s for 15-page PDF (21.4s/page)
