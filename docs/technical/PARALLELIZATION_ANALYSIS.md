# Parallelization Performance Analysis

**Date:** October 30, 2025
**Issue:** Digital PDF parallel processing only achieves 1.28x speedup with 2 workers (expected 1.8-2x)

## Problem Summary

From the session notes:
- **Sequential:** 87.3s for 10 PDFs (8.73s/file)
- **Parallel (2 workers):** 68.2s for 10 PDFs (6.82s/file)
- **Actual Speedup:** 1.28x
- **Expected Speedup:** 1.8-2x

Time breakdown shows **83% of time** spent in Docling conversion, so that's the primary focus.

## Root Cause Analysis

After analyzing the code in [`handlers/pdf_digital.py`](../../olmocr_pipeline/handlers/pdf_digital.py), I identified **three major bottlenecks**:

### 1. Docling Converter Initialization Per-Worker (HIGH IMPACT)

**Location:** [`pdf_digital.py:121`](../../olmocr_pipeline/handlers/pdf_digital.py#L121)

```python
def process_digital_pdf(...):
    # ...
    converter = DocumentConverter()  # ❌ Created fresh for EVERY PDF
    result = converter.convert(str(pdf_path))
```

**Problem:**
- Each worker thread creates a new `DocumentConverter` instance for every PDF
- Converter initialization likely loads models, initializes GPU context, etc.
- This overhead is **repeated for every single file**

**Impact:** If initialization takes 2-3 seconds, and we process 10 files with 2 workers (5 files each), we waste 10-15 seconds on just initialization!

### 2. Embedding Model Loading Per-Worker (MEDIUM IMPACT)

**Location:** [`pdf_digital.py:176-182`](../../olmocr_pipeline/handlers/pdf_digital.py#L176-L182)

```python
if enable_embeddings:
    from utils_embeddings import EmbeddingGenerator
    embedding_gen = EmbeddingGenerator(
        model_name=config.get("embeddings", {}).get("model", "all-mpnet-base-v2")
    )  # ❌ Loads model for every PDF
    chunks = embedding_gen.add_embeddings_to_chunks(chunks, show_progress=False)
```

**Problem:**
- `EmbeddingGenerator.__init__()` loads the sentence-transformer model from disk/downloads it
- Each worker loads its own copy of the model (768MB for all-mpnet-base-v2)
- Model loading can take 1-2 seconds, repeated for every file

### 3. Sequential API Calls Within Parallel Workers (LOW-MEDIUM IMPACT)

**Location:** [`pdf_digital.py:166-172`](../../olmocr_pipeline/handlers/pdf_digital.py#L166-L172)

```python
if enable_entities:
    chunks, entity_stats = add_entities_to_chunks(
        chunks,
        enable_entities=True,
        api_key=api_key
    )  # Makes sequential OpenAI API calls
```

**Problem:**
- Entity extraction makes OpenAI API calls sequentially within each worker
- While workers run in parallel, each worker is blocked waiting for API responses
- OpenAI API calls can take 500ms-2s each

## Why ThreadPoolExecutor Doesn't Help

`ThreadPoolExecutor` in [`utils_processor.py:229`](../../olmocr_pipeline/utils_processor.py#L229) parallelizes **file processing**, but WITHIN each file's processing:
1. Docling init + conversion is sequential
2. Entity extraction API calls are sequential
3. Embedding model loading + generation is sequential

So with 2 workers processing 10 files:
- Worker 1 handles files 1, 3, 5, 7, 9
- Worker 2 handles files 2, 4, 6, 8, 10

But each worker wastes time on:
- 5x Docling initializations
- 5x Embedding model loads
- Sequential API calls for each file

## Recommended Fixes

### Fix 1: Reuse Docling Converter (CRITICAL - Implement First)

Create a **module-level singleton** or **pass converter as parameter**:

#### Option A: Singleton Pattern
```python
# At module level in pdf_digital.py
_converter_instance = None

def get_converter():
    global _converter_instance
    if _converter_instance is None:
        _converter_instance = DocumentConverter()
    return _converter_instance

def process_digital_pdf(...):
    converter = get_converter()  # ✅ Reuses same instance
    result = converter.convert(str(pdf_path))
```

#### Option B: Thread-Local Storage (if Docling isn't thread-safe)
```python
import threading

_thread_local = threading.local()

def get_converter():
    if not hasattr(_thread_local, 'converter'):
        _thread_local.converter = DocumentConverter()
    return _thread_local.converter
```

**Expected Impact:** Eliminate 2-3s × 10 files = **20-30 seconds saved**

### Fix 2: Pre-load Embedding Model

Initialize `EmbeddingGenerator` once and reuse:

```python
# Thread-local for embedding generator
_thread_local = threading.local()

def get_embedding_generator(model_name):
    if not hasattr(_thread_local, 'embedding_gen'):
        _thread_local.embedding_gen = EmbeddingGenerator(model_name=model_name)
    return _thread_local.embedding_gen

def process_digital_pdf(...):
    if enable_embeddings:
        embedding_gen = get_embedding_generator(
            config.get("embeddings", {}).get("model", "all-mpnet-base-v2")
        )
        chunks = embedding_gen.add_embeddings_to_chunks(chunks, show_progress=False)
```

**Expected Impact:** Eliminate 1-2s × 10 files = **10-20 seconds saved**

### Fix 3: Batch Entity Extraction (Optional)

If `add_entities_to_chunks` supports batching, batch chunks across multiple files:

```python
# Instead of per-file entity extraction, collect all chunks from all files
# and extract entities in one batch API call
all_chunks = []
for pdf in pdfs:
    chunks = process_pdf(pdf)
    all_chunks.extend(chunks)

# Single batch call
all_chunks_with_entities, stats = add_entities_to_chunks(all_chunks, ...)
```

**Expected Impact:** Reduce API overhead, **5-10 seconds saved**

## Expected Performance After Fixes

**Conservative Estimate:**
- Fix 1 (Docling reuse): Save 20 seconds
- Fix 2 (Embedding reuse): Save 10 seconds
- **Total:** 30 seconds saved

**New parallel time:** 68.2s - 30s = **38.2s**
**New speedup:** 87.3s / 38.2s = **2.28x** ✅

This exceeds the target of 1.8-2x!

## Implementation Priority

1. **CRITICAL:** Implement Fix 1 (Docling converter reuse) - Biggest impact
2. **HIGH:** Implement Fix 2 (Embedding model reuse) - Significant impact
3. **MEDIUM:** Test with 4 workers to see if we can scale further
4. **LOW:** Implement Fix 3 (batch entity extraction) - Nice-to-have optimization

## Testing Plan

After implementing fixes:

1. **Re-run parallel test** with same 10 PDFs
2. **Measure speedup** - target ≥ 2.0x
3. **Test with 4 workers** - should get 3-3.5x speedup
4. **Monitor GPU/CPU** usage to identify any remaining bottlenecks
5. **Run production batch** on remaining 95 digital PDFs

## Files to Modify

- [`olmocr_pipeline/handlers/pdf_digital.py`](../../olmocr_pipeline/handlers/pdf_digital.py) - Add singleton/thread-local for Docling and embeddings
- [`olmocr_pipeline/utils_embeddings.py`](../../olmocr_pipeline/utils_embeddings.py) - Verify thread-safety
- [`olmocr_pipeline/utils_processor.py`](../../olmocr_pipeline/utils_processor.py) - No changes needed (parallelization logic is sound)

## References

- Session Notes: [`docs/planning/sessions/SESSION_PICKUP_2025-10-31.md`](../planning/sessions/SESSION_PICKUP_2025-10-31.md)
- Original test logs: `/tmp/digital_pdf_test_v2.log`, `/tmp/digital_pdf_test_parallel.log` (no longer available)
- Configuration: [`config/default.yaml`](../../config/default.yaml) (digital_pdf_workers: 2)
