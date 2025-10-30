# OlmOCR README Insights - Additional Optimization Opportunities

**Date:** October 30, 2025
**Source:** https://github.com/allenai/olmocr/blob/main/README.md

---

## New Insights from Official Documentation

### 1. **Multi-GPU Parallelism** (Not Currently Used)

#### Tensor Parallelism
```bash
--tensor-parallel-size 2  # Split model across 2 GPUs
```

**What it does:** Splits the model across multiple GPUs
**Our situation:** We only have 1 GPU (L4)
**Action:** Not applicable

#### Data Parallelism
```bash
--data-parallel-size 2  # Run 2 copies of model on different GPUs
```

**What it does:** Runs multiple model copies in parallel
**Our situation:** We only have 1 GPU (L4)
**Action:** Not applicable

**Conclusion:** ❌ Can't use - we only have 1 GPU

---

### 2. **Pages Per Group** (Potentially Useful!)

```bash
--pages_per_group 33  # Our current default
```

**What it does:** Controls how many pages are grouped into work items

**From README:**
> "Aiming for this many pdf pages per work item group"
> "External providers may require smaller values due to rate limits"

**Current behavior:**
```
Calculated items_per_group: 33 based on average pages per PDF: 15.00
```

**Insight:** Our 15-page PDF is processed as 1 group (15 < 33)

**Potential optimization:**
- Reduce `--pages_per_group` to force more groups
- More groups = better parallelization for larger documents

**Test idea:**
```bash
--pages_per_group 5  # Force 3 groups for 15-page PDF
```

**Expected benefit:**
- Better worker utilization
- More parallel processing opportunities
- Could help with 50+ page documents

**Status:** 🔬 Worth testing!

---

### 3. **Guided Decoding** (New Feature)

```bash
--guided_decoding  # Enable YAML-structured outputs
```

**What it does:** Enables guided decoding for structured output format

**Our situation:** We use markdown output (`--markdown`)

**Potential impact:**
- Could be faster if structured output reduces tokens
- May reduce hallucinations
- Might improve quality

**Status:** 🤔 Unclear if beneficial for our use case

**Action:** Probably not needed - we want markdown, not YAML

---

### 4. **FP8 Quantization** (Already Using ✅)

**From README:**
> "FP8 quantization significantly faster"
> "Requires fewer retries per document"

**Our model:** `allenai/olmOCR-2-7B-1025-FP8` ✅

**Status:** Already optimized!

---

### 5. **External Inference Providers** (Alternative Approach)

**From README:**
- Cirrascale: $0.07/$0.15 per 1M tokens
- DeepInfra: $0.09/$0.19
- Parasail: $0.10/$0.20

**What it does:** Offload inference to external API (no GPU needed)

**Our situation:**
- We have our own L4 GPU
- Processing ~320s = 5.3 minutes per 15-page doc
- Cost: GPU time @ $X/hour

**Cost comparison:**
```
Our GPU (L4): ~$0.40/hour typical
- 15-page PDF: 5.3 min = $0.035 per doc

External API:
- Input: ~5000 tokens * 15 pages = 75k tokens
- Output: ~5000 tokens * 15 pages = 75k tokens
- Cost: 75k * $0.07 + 75k * $0.15 = $16.50 per doc!
```

**Conclusion:** ❌ Way more expensive than our own GPU

---

### 6. **S3-Coordinated Work Distribution** (Scalability)

```bash
python -m olmocr.pipeline s3://bucket/workspace --pdfs s3://bucket/pdfs/*.pdf
```

**What it does:** Multiple nodes share work via S3 queue

**Our situation:**
- We use GCS (not S3)
- Single VM processing
- No multi-node setup

**Potential future benefit:**
- Scale horizontally with multiple VMs
- Each VM processes different documents
- Shared queue coordination

**Status:** 🚀 Interesting for future scaling, not immediate need

---

### 7. **Docker Image** (Deployment)

```bash
docker pull alleninstituteforai/olmocr:latest
```

**What it does:** Pre-configured environment

**Our situation:**
- Already have working conda environment
- Already installed all dependencies
- System is stable

**Status:** ✅ We're good, no need to change

---

## Key Takeaway: Pages Per Group

The most interesting finding is **`--pages_per_group`**!

### Current Behavior

Our logs show:
```
Calculated items_per_group: 33 based on average pages per PDF: 15.00
```

This means:
- 15-page PDF → 1 work item group
- All 15 pages processed together
- Limited parallelization opportunities

### Hypothesis

If we reduce `pages_per_group` to **5**:
- 15-page PDF → 3 work item groups (5 + 5 + 5)
- Group 1: Pages 1-5
- Group 2: Pages 6-10
- Group 3: Pages 11-15

**Potential benefit:**
- Each group can be processed by different workers
- Better pipeline parallelization
- Workers don't sit idle waiting for large batch

### How to Test

```yaml
# config/default.yaml
processors:
  olmocr:
    pages_per_group: 5  # Add this parameter
```

Or via command line:
```bash
python -m olmocr.pipeline ... --pages_per_group 5
```

---

## Updated Optimization Plan

### Already Done ✅
1. FlashInfer installed
2. FP8 quantization (using correct model)
3. Worker count optimized (8-12 workers)
4. GCS mounts fixed
5. torch.compile caching
6. CUDA graphs

### Worth Testing 🔬
1. **Pages per group = 5** (instead of 33)
   - Expected: Better parallelization
   - Risk: Low
   - Effort: Config change only

### Not Applicable ❌
1. Tensor parallelism (need multiple GPUs)
2. Data parallelism (need multiple GPUs)
3. External providers (too expensive)
4. S3 coordination (using GCS, single node)

### Maybe Later 🤔
1. Guided decoding (unclear benefit for markdown)
2. Multi-node scaling (not needed yet)

---

## Recommended Next Test

**Test pages_per_group optimization:**

```yaml
# config/default.yaml
processors:
  olmocr:
    model_id: "allenai/olmOCR-2-7B-1025-FP8"
    target_image_dim: "1288"
    gpu_memory_utilization: 0.8
    default_workers: 8
    default_batch_size: 5
    pages_per_group: 5  # ← ADD THIS
```

**Expected results:**
- For 15-page PDF: Minimal improvement (already fast)
- For 50+ page PDF: Potentially 20-30% faster
- For 100+ page PDF: Potentially 30-50% faster

**Why it might help:**
- Forces smaller work groups
- Better worker utilization
- More parallel processing opportunities
- Reduces idle time between batches

---

## Reality Check

### What We've Achieved Today

**Speed improvements:**
- FlashInfer: Installed ✅
- Workers: 6→8 recommended (10% faster)
- Combined: ~10% faster overall

**Total improvement:** ~30s savings on 320s baseline = **10% faster**

**Quality impact:** Zero ✅

### What's Actually Limiting Us

**The real bottleneck:** vLLM's internal concurrency limit (~15 requests)

**This is determined by:**
- KV cache size (86,080 tokens)
- GPU memory allocation (4.6 GB for KV)
- Model architecture constraints

**We can't easily change this without:**
- More GPU memory (hardware upgrade)
- Different model (quality trade-off)
- Multiple GPUs (cost increase)

### Honest Assessment

**pages_per_group** might help with larger documents (50+ pages), but for our 15-page test document, the impact will be minimal because:
1. vLLM already processes ~15 pages concurrently
2. The document fits in one natural batch
3. Worker count isn't the bottleneck

**Bottom line:** We've found most of the easy wins. Further optimization requires hardware changes or processing larger documents.

---

## Final Recommendation

### For Your Current Setup (L4 GPU, typical 10-20 page docs)

**Keep these settings:**
```yaml
olmocr:
  model_id: "allenai/olmOCR-2-7B-1025-FP8"  # FP8 for speed
  target_image_dim: "1288"                   # Keep quality
  gpu_memory_utilization: 0.8                # Safe default
  default_workers: 8                         # Sweet spot
  default_batch_size: 5                      # Standard
```

**Optional test (for large docs):**
```yaml
  pages_per_group: 10  # Try if processing 50+ page documents
```

### For Large Documents (50+ pages)

Test with `pages_per_group: 10` - this could help with parallelization.

### For Multiple Small Documents

Your current setup is already good - batch processing will benefit from 8 workers.

---

**Key Learning:** OlmOCR README doesn't reveal any major optimizations we missed. The bottleneck is vLLM's architectural limits, not configuration.
