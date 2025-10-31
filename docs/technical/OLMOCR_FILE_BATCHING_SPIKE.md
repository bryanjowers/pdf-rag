# OlmOCR File-Level Batching - Technical Spike

**Date:** 2025-10-30
**Author:** Claude (with Bryan)
**Status:** Design Complete - Ready for Implementation
**Estimated Implementation:** 4-8 hours
**Expected Performance Gain:** 2-3x faster for scanned PDFs

---

## Executive Summary

**Problem:** Scanned PDFs are processed sequentially one-at-a-time, causing ~30% time waste on OlmOCR model loading/unloading between files. GPU utilization drops to 0% between files despite having 12 workers configured.

**Root Cause:** Architecture processes each scanned PDF individually through separate `run_olmocr_batch()` calls, causing model initialization overhead for every file.

**Solution:** Implement file-level batching to group 10 scanned PDFs and process them in a single OlmOCR batch call. This amortizes model startup/teardown across multiple files.

**Impact:** Potential 2-3x speedup for scanned PDF processing with current 105-file corpus.

---

## Current Architecture Analysis

### File Processing Flow

**1. Entry Point: [olmocr_pipeline/utils_processor.py:276-288](../../olmocr_pipeline/utils_processor.py#L276-L288)**

```python
# Process remaining files sequentially (scanned PDFs, DOCX, XLSX, etc.)
start_idx = len(digital_pdfs) + 1 if (digital_pdfs and digital_workers > 1) else 1
for idx, file_path in enumerate(other_files if (digital_pdfs and digital_workers > 1) else file_paths, start_idx):
    print(f"\n[{idx}/{len(file_paths)}]")

    result = process_file_with_retry(
        file_path,  # ← SINGLE FILE AT A TIME
        output_dir,
        config,
        batch_id,
        apply_preprocessing,
        skip_enrichment
    )
```

**Problem:** Sequential loop processes one file at a time. No batching logic for scanned PDFs.

---

**2. Handler: [olmocr_pipeline/handlers/pdf_scanned.py:97-102](../../olmocr_pipeline/handlers/pdf_scanned.py#L97-L102)**

```python
# Run OlmOCR batch
run_olmocr_batch(
    file_paths=[processed_pdf_path],  # ← ONLY PASSING 1 FILE!
    output_dir=olmocr_staging,
    config=config,
    log_file=log_file
)
```

**Problem:** Handler always passes single file to OlmOCR, even though API supports multiple files.

---

**3. OlmOCR Wrapper: [olmocr_pipeline/utils_olmocr.py:39-91](../../olmocr_pipeline/utils_olmocr.py#L39-L91)**

```python
def run_olmocr_batch(
    file_paths: List[Path],  # ← API ALREADY SUPPORTS MULTIPLE FILES!
    output_dir: Path,
    config: Dict,
    log_file: Path,
    workers: Optional[int] = None
) -> None:
    """
    Run OlmOCR CLI pipeline on batch of files (PDFs or images).
    """
    # Convert paths to strings
    file_path_strings = [str(p.resolve()) for p in file_paths]

    # Build command
    command = [
        sys.executable,
        "-m", module_path,
        str(output_dir),
        "--markdown",
        "--model", model_id,
        "--workers", str(workers),
        "--target_longest_image_dim", target_dim,
        "--gpu-memory-utilization", str(gpu_util),
        "--pdfs", *file_path_strings  # ← ALREADY SUPPORTS MULTIPLE FILES!
    ]
```

**Good News:** The wrapper already supports multiple files! Just need to pass them in.

---

### Configuration Settings

**Current config ([config/default.yaml:138-145](../../config/default.yaml#L138-L145)):**

```yaml
olmocr:
  model_id: "allenai/olmOCR-2-7B-1025-FP8"
  target_image_dim: "1288"
  gpu_memory_utilization: 0.8
  default_workers: 12           # ← Page-level parallelism WITHIN a document
  default_batch_size: 10        # ← NOT CURRENTLY USED! Should control file batching
  pages_per_group: 10           # ← Controls page grouping within OlmOCR
```

**Issue:** `default_batch_size: 10` is defined but never used in the code. It should control how many files we batch together.

---

## OlmOCR Multi-File Support

From the [OlmOCR README](https://github.com/allenai/olmocr/blob/main/README.md):

### API Confirmation

**Multi-file processing is fully supported:**

```bash
# Example from OlmOCR README
python -m olmocr.pipeline ./workspace --markdown --pdfs tests/gnarly_pdfs/*.pdf
```

### Key Parameters

- `--pdfs`: Accepts multiple file paths or glob patterns
- `--workers`: Concurrent workers for page-level parallelism
- `--pages_per_group`: Controls page grouping per work item (default strategy)

### Performance Notes

From README:
> "For large-scale processing (millions of PDFs), use S3-coordinated workspace with multiple nodes"

This confirms OlmOCR is designed for batch processing multiple files efficiently.

---

## Proposed Solution

### Design: File-Level Batching for Scanned PDFs

**Key Idea:** Group scanned PDFs into batches of 10 (configurable via `default_batch_size`) and process each batch with a single `run_olmocr_batch()` call.

### Architecture Changes

**1. Update `utils_processor.py` to batch scanned PDFs**

Add new function to group scanned PDFs:

```python
def batch_scanned_pdfs(
    scanned_pdfs: List[Path],
    batch_size: int
) -> List[List[Path]]:
    """
    Group scanned PDFs into batches for efficient OlmOCR processing.

    Args:
        scanned_pdfs: List of scanned PDF paths
        batch_size: Number of PDFs per batch

    Returns:
        List of batches (each batch is a list of PDF paths)
    """
    batches = []
    for i in range(0, len(scanned_pdfs), batch_size):
        batches.append(scanned_pdfs[i:i + batch_size])
    return batches
```

**2. Modify processing loop to handle batches**

Replace sequential loop with batch processing:

```python
# Separate scanned PDFs from other file types
scanned_pdfs = [f for f in other_files if f.suffix.lower() == '.pdf']
non_pdf_files = [f for f in other_files if f.suffix.lower() != '.pdf']

# Get batch size from config
batch_size = config.get("processors", {}).get("olmocr", {}).get("default_batch_size", 10)

# Process scanned PDFs in batches
if scanned_pdfs:
    batches = batch_scanned_pdfs(scanned_pdfs, batch_size)

    for batch_idx, pdf_batch in enumerate(batches, 1):
        print(f"\n📦 Processing Scanned PDF Batch {batch_idx}/{len(batches)} ({len(pdf_batch)} files)")

        batch_results = process_scanned_pdf_batch(
            pdf_batch,
            output_dir,
            config,
            batch_id,
            apply_preprocessing,
            skip_enrichment
        )

        results.extend(batch_results)
        # Handle quarantine for batch results...

# Process non-PDF files sequentially (DOCX, XLSX, etc.)
for idx, file_path in enumerate(non_pdf_files, start_idx):
    # ... existing sequential processing ...
```

**3. Create new batch processing function**

New function in `utils_processor.py`:

```python
def process_scanned_pdf_batch(
    pdf_paths: List[Path],
    output_dir: Path,
    config: Dict,
    batch_id: str,
    apply_preprocessing: bool,
    skip_enrichment: bool
) -> List[Dict]:
    """
    Process a batch of scanned PDFs with OlmOCR in a single call.

    This amortizes model loading/unloading across multiple files for
    significant performance improvement (2-3x faster).

    Args:
        pdf_paths: List of scanned PDF paths to process together
        output_dir: Output directory for results
        config: Configuration dictionary
        batch_id: Batch identifier for tracking
        apply_preprocessing: Whether to apply preprocessing
        skip_enrichment: Whether to skip entity/embedding enrichment

    Returns:
        List of result dictionaries (one per PDF)
    """
    from olmocr_pipeline.handlers.pdf_scanned import process_scanned_pdf_batch

    return process_scanned_pdf_batch(
        pdf_paths=pdf_paths,
        output_dir=output_dir,
        config=config,
        batch_id=batch_id,
        apply_preprocessing=apply_preprocessing,
        skip_enrichment=skip_enrichment
    )
```

**4. Update `pdf_scanned.py` handler**

Add new batch processing function while keeping existing single-file handler:

```python
def process_scanned_pdf_batch(
    pdf_paths: List[Path],
    output_dir: Path,
    config: Dict,
    batch_id: str,
    apply_preprocessing: bool = False,
    skip_enrichment: bool = False
) -> List[Dict]:
    """
    Process multiple scanned PDFs in a single OlmOCR batch.

    This function groups multiple PDFs and processes them together,
    amortizing OlmOCR model startup/teardown costs across all files.

    Args:
        pdf_paths: List of scanned PDF paths to process
        output_dir: Output directory
        config: Configuration dictionary
        batch_id: Batch identifier
        apply_preprocessing: Whether to apply preprocessing
        skip_enrichment: Whether to skip enrichment

    Returns:
        List of result dictionaries (one per PDF)
    """
    # Prepare output directories (same as before)
    olmocr_staging = output_dir / "olmocr_staging"
    markdown_dir = output_dir / "markdown"
    jsonl_dir = output_dir / "jsonl"
    log_dir = output_dir / "logs"

    for d in [olmocr_staging, markdown_dir, jsonl_dir, log_dir]:
        d.mkdir(parents=True, exist_ok=True)

    # Create batch log file
    log_file = log_dir / f"olmocr_batch_{batch_id}_{len(pdf_paths)}files.log"

    print(f"   🔄 Processing {len(pdf_paths)} scanned PDFs with OlmOCR-2 batch")

    # Apply preprocessing if needed (for all files)
    processed_paths = []
    for pdf_path in pdf_paths:
        if apply_preprocessing:
            processed_path = apply_pdf_preprocessing(pdf_path, output_dir, config)
        else:
            processed_path = pdf_path
        processed_paths.append(processed_path)

    try:
        # ✨ KEY CHANGE: Pass ALL files to OlmOCR at once!
        run_olmocr_batch(
            file_paths=processed_paths,  # ← MULTIPLE FILES!
            output_dir=olmocr_staging,
            config=config,
            log_file=log_file
        )

        # Process results for each file
        results = []
        for pdf_path in pdf_paths:
            result = process_single_olmocr_output(
                pdf_path=pdf_path,
                olmocr_staging=olmocr_staging,
                markdown_dir=markdown_dir,
                jsonl_dir=jsonl_dir,
                config=config,
                skip_enrichment=skip_enrichment
            )
            results.append(result)

        return results

    except Exception as e:
        # Handle batch failure - return failure results for all files
        print(f"   ❌ Batch processing failed: {e}")
        return [
            {
                "file_path": str(pdf_path),
                "file_name": pdf_path.name,
                "file_type": "pdf",
                "processor": "olmocr",
                "success": False,
                "error": f"Batch processing failed: {e}",
                "quarantined": True,
                "retry_count": 0
            }
            for pdf_path in pdf_paths
        ]


def process_single_olmocr_output(
    pdf_path: Path,
    olmocr_staging: Path,
    markdown_dir: Path,
    jsonl_dir: Path,
    config: Dict,
    skip_enrichment: bool
) -> Dict:
    """
    Extract and process OlmOCR output for a single PDF from batch results.

    This function handles the post-processing after OlmOCR has completed
    a batch run containing this PDF.

    Args:
        pdf_path: Original PDF path
        olmocr_staging: OlmOCR staging directory
        markdown_dir: Output markdown directory
        jsonl_dir: Output JSONL directory
        config: Configuration dictionary
        skip_enrichment: Whether to skip enrichment

    Returns:
        Result dictionary for this PDF
    """
    stem = pdf_path.stem

    try:
        # Get OlmOCR JSONL output
        jsonl_path_olmocr = get_olmocr_jsonl_path(pdf_path, olmocr_staging)

        if jsonl_path_olmocr is None or not jsonl_path_olmocr.exists():
            raise FileNotFoundError(f"OlmOCR did not produce JSONL output for: {pdf_path.name}")

        # Get OlmOCR markdown output
        olmocr_md_path = pdf_path.with_suffix('.md')
        if not olmocr_md_path.exists():
            olmocr_md_path = olmocr_staging / "markdown" / f"{stem}.md"

        if not olmocr_md_path.exists():
            raise FileNotFoundError(f"OlmOCR did not produce markdown for: {pdf_path.name}")

        # Copy markdown to output directory
        output_md_path = markdown_dir / f"{stem}.md"
        shutil.copy2(olmocr_md_path, output_md_path)

        # Convert to final JSONL format
        output_jsonl_path = jsonl_dir / f"{stem}.jsonl"

        # Extract metadata
        page_count = count_pdf_pages(pdf_path)
        file_size = pdf_path.stat().st_size

        # Process without enrichment (or with, based on flag)
        if skip_enrichment:
            convert_olmocr_to_jsonl_no_enrichment(
                input_jsonl=jsonl_path_olmocr,
                output_jsonl=output_jsonl_path,
                source_file=pdf_path.name,
                file_type="pdf_scanned",
                page_count=page_count,
                file_size_bytes=file_size,
                config=config
            )
        else:
            # Add entities and embeddings
            # ... existing enrichment code ...
            pass

        return {
            "file_path": str(pdf_path),
            "file_name": pdf_path.name,
            "file_type": "pdf",
            "processor": "olmocr",
            "success": True,
            "output_markdown": str(output_md_path),
            "output_jsonl": str(output_jsonl_path),
            "page_count": page_count,
            "file_size_bytes": file_size
        }

    except Exception as e:
        print(f"   ❌ Error processing OlmOCR output for {pdf_path.name}: {e}")
        return {
            "file_path": str(pdf_path),
            "file_name": pdf_path.name,
            "file_type": "pdf",
            "processor": "olmocr",
            "success": False,
            "error": str(e),
            "quarantined": True,
            "retry_count": 0
        }
```

---

## Implementation Strategy

### Phase 1: Core Batching (High Priority)

**Files to modify:**
1. [olmocr_pipeline/utils_processor.py](../../olmocr_pipeline/utils_processor.py)
   - Add `batch_scanned_pdfs()` function
   - Modify sequential processing loop to batch scanned PDFs
   - Keep sequential processing for DOCX, XLSX, images

2. [olmocr_pipeline/handlers/pdf_scanned.py](../../olmocr_pipeline/handlers/pdf_scanned.py)
   - Add `process_scanned_pdf_batch()` function
   - Add `process_single_olmocr_output()` helper
   - Keep existing `process_scanned_pdf()` for backward compatibility

**Testing Strategy:**
1. Run baseline with current architecture (Batch 1 - in progress)
2. Implement batching changes
3. Run Batch 2 with batching enabled
4. Compare metrics (time/page, GPU utilization, success rate)

### Phase 2: Error Handling (Medium Priority)

**Graceful degradation:**
- If batch fails, fall back to processing files individually
- Track which files succeeded/failed in batch
- Quarantine only failed files, keep successful outputs

**Retry logic:**
```python
try:
    # Try batch processing first
    return process_scanned_pdf_batch(...)
except Exception as batch_error:
    print(f"⚠️  Batch processing failed, falling back to sequential: {batch_error}")

    # Fall back to sequential processing
    results = []
    for pdf_path in pdf_paths:
        result = process_scanned_pdf(pdf_path, ...)  # Existing single-file handler
        results.append(result)
    return results
```

### Phase 3: Optimization (Low Priority)

**Adaptive batch sizing:**
- Monitor GPU memory usage
- Adjust batch size based on file sizes
- Smaller batches for large PDFs (50+ pages)
- Larger batches for small PDFs (1-10 pages)

**Progress tracking:**
- Show per-file progress within batch
- Better logging for batch vs sequential processing
- Estimate time remaining based on batch throughput

---

## Risks and Mitigations

### Risk 1: Batch Failure Loses All Progress

**Scenario:** OlmOCR crashes or fails on file 8 of 10, losing work on files 1-7.

**Mitigation:**
- OlmOCR writes outputs incrementally (confirmed from logs)
- Files 1-7 will have JSONL/markdown outputs even if batch fails
- Implement robust output detection to recover partial results
- Fall back to sequential processing if batch fails repeatedly

**Code:**
```python
# After batch run, check which files succeeded
successful_outputs = []
failed_files = []

for pdf_path in pdf_paths:
    jsonl_path = get_olmocr_jsonl_path(pdf_path, olmocr_staging)
    if jsonl_path and jsonl_path.exists():
        successful_outputs.append(pdf_path)
    else:
        failed_files.append(pdf_path)

# Retry only failed files
if failed_files:
    print(f"⚠️  Retrying {len(failed_files)} failed files individually...")
    for pdf_path in failed_files:
        # Process individually with existing handler
        result = process_scanned_pdf(pdf_path, ...)
```

---

### Risk 2: Memory Issues with Large Batches

**Scenario:** Processing 10 large PDFs (100+ pages each) exhausts GPU memory.

**Mitigation:**
- Start with conservative batch size (10 files)
- Monitor GPU memory usage in baseline testing
- Add adaptive batching based on file sizes
- Config option to disable batching if needed

**Code:**
```python
# Adaptive batch sizing
def calculate_batch_size(pdf_paths: List[Path], base_batch_size: int) -> int:
    """Adjust batch size based on estimated PDF sizes."""
    avg_size_mb = sum(p.stat().st_size for p in pdf_paths) / len(pdf_paths) / 1024 / 1024

    # Reduce batch size for large files
    if avg_size_mb > 50:  # Large scans
        return max(5, base_batch_size // 2)
    elif avg_size_mb > 20:  # Medium scans
        return max(8, base_batch_size - 2)
    else:  # Small scans
        return base_batch_size
```

---

### Risk 3: Breaking Existing Workflows

**Scenario:** Changing processing flow breaks manifest tracking, quarantine, or retry logic.

**Mitigation:**
- Keep existing single-file handler for backward compatibility
- Return same result format from batch handler
- Thorough testing with current baseline metrics
- Feature flag to disable batching if issues arise

**Config:**
```yaml
olmocr:
  enable_file_batching: true   # Set to false to disable batching
  default_batch_size: 10
```

---

### Risk 4: OlmOCR Multi-File Bugs

**Scenario:** OlmOCR has undiscovered bugs when processing multiple files.

**Mitigation:**
- OlmOCR README explicitly shows multi-file usage (tested by maintainers)
- Start with small batch sizes (10 files)
- Monitor for output quality degradation
- Fall back to sequential if batch quality issues detected

---

## Configuration Changes

**Update [config/default.yaml](../../config/default.yaml):**

```yaml
olmocr:
  model_id: "allenai/olmOCR-2-7B-1025-FP8"
  target_image_dim: "1288"
  gpu_memory_utilization: 0.8
  default_workers: 12

  # File-level batching settings
  enable_file_batching: true      # NEW: Enable batching multiple PDFs
  default_batch_size: 10          # USED: Number of PDFs per batch (was unused before)
  fallback_to_sequential: true    # NEW: Fall back if batch fails

  # Page-level settings (unchanged)
  pages_per_group: 10             # Page grouping within OlmOCR
```

---

## Expected Performance Improvement

### Current Performance (Sequential)

**Observed from baseline test:**
- File 1 processing: ~60-90 seconds total
  - Model loading: ~35 seconds (58%)
  - OCR processing: ~25 seconds (42%)
- GPU utilization: Drops to 0% between files
- 10 files: ~600-900 seconds (10-15 minutes)

### Expected Performance (Batched)

**With 10-file batching:**
- Batch setup: ~35 seconds (model loading, once)
- OCR processing: ~250 seconds (10 files × 25 sec/file)
- Total: ~285 seconds (4.75 minutes)
- **Speedup: 2.1-3.1x faster**

**GPU utilization:**
- Continuous GPU usage during entire batch
- No idle time between files
- Better hardware utilization

### ROI Analysis

**Current corpus:**
- 105 scanned PDFs total
- Sequential time: ~105 × 60s = 6,300 seconds (105 minutes)
- Batched time (10-file batches): ~11 batches × 285s = 3,135 seconds (52 minutes)
- **Time saved: 53 minutes (50% reduction)**

**For larger deployments:**
- 1,000 PDFs: Sequential ~16.7 hours → Batched ~7.9 hours (8.8 hours saved)
- 10,000 PDFs: Sequential ~7 days → Batched ~3.3 days (3.7 days saved)

---

## Success Metrics

### Quantitative Metrics

1. **Processing Time**
   - Target: ≥2x faster than baseline
   - Measure: Total batch time / number of files

2. **GPU Utilization**
   - Target: >80% average during batch (vs <30% sequential)
   - Measure: nvidia-smi monitoring during batch

3. **Throughput**
   - Current: ~0.67 files/minute (sequential)
   - Target: ≥1.3 files/minute (batched)

4. **Success Rate**
   - Target: ≥95% (same as sequential)
   - Measure: Files successfully processed / total files

### Qualitative Metrics

1. **Output Quality**
   - Compare character counts (should be identical)
   - Spot-check markdown formatting
   - Validate JSONL schema compliance

2. **Reliability**
   - Batch processing completes without crashes
   - Partial results recoverable on failure
   - Graceful fallback to sequential works

---

## Testing Plan

### Test 1: Baseline Comparison

**Current:** Baseline Batch 1 (in progress)
- 10 scanned PDFs, sequential processing
- Capture: time/file, GPU utilization, success rate

**New:** Batch 2 with batching enabled
- Same 10 files OR next 10 files
- Capture: same metrics
- Compare: speedup, GPU utilization improvement

### Test 2: Error Handling

**Scenario 1:** Corrupt PDF in batch
- Include 1 known-bad PDF in batch of 10
- Verify: Other 9 PDFs process successfully
- Verify: Bad PDF quarantined, doesn't crash batch

**Scenario 2:** OOM (out of memory)
- Process batch of 10 very large PDFs (100+ pages each)
- Verify: Graceful failure or adaptive batch reduction
- Verify: Fallback to sequential works

### Test 3: Scale Testing

**Scenario:** Full corpus processing
- Process all 105 scanned PDFs with batching
- Verify: Total time matches expected improvement
- Verify: All files processed successfully
- Verify: Outputs match quality standards

---

## Migration Path

### Stage 1: Feature Flag (Safe)

1. Implement batching behind feature flag (disabled by default)
2. Run baseline tests with batching disabled
3. Run comparison tests with batching enabled
4. Validate results match quality standards

### Stage 2: Opt-In (Conservative)

1. Enable batching by default
2. Keep fallback to sequential enabled
3. Monitor for any batch failures
4. Gather performance metrics from production use

### Stage 3: Hardened (Optimized)

1. Remove sequential fallback (if batching 100% reliable)
2. Add adaptive batch sizing
3. Optimize batch size based on observed performance
4. Consider parallel batches (if GPU can handle it)

---

## Alternative Approaches Considered

### Alternative 1: Parallel Sequential Processing

**Idea:** Process multiple scanned PDFs in parallel, each with own OlmOCR instance.

**Pros:**
- Simpler to implement (similar to digital PDF workers)
- Natural isolation between files

**Cons:**
- Each worker loads model separately (N × 35 seconds overhead)
- GPU memory contention (can't fit 4+ models on L4 23GB)
- No better than current sequential (possibly worse)

**Decision:** Rejected - File batching is superior.

---

### Alternative 2: Pre-processing Queue

**Idea:** Pre-process all PDFs to images, then batch process images.

**Pros:**
- More control over batching
- Could mix pages from different PDFs

**Cons:**
- Adds preprocessing step (more disk I/O)
- OlmOCR already handles PDF-to-image conversion
- Complicates output mapping back to source PDFs

**Decision:** Rejected - Unnecessary complexity.

---

### Alternative 3: Keep Current Architecture

**Idea:** Accept sequential processing as limitation.

**Pros:**
- No code changes needed
- Zero implementation risk

**Cons:**
- Wastes 50%+ of processing time
- Poor GPU utilization
- Doesn't scale for larger deployments

**Decision:** Rejected - Performance gain too significant to ignore.

---

## Implementation Checklist

### Pre-Implementation

- [x] Complete baseline testing (Batch 1)
- [x] Document current performance metrics
- [x] Review OlmOCR multi-file support
- [x] Design batching architecture
- [ ] Get approval from Bryan

### Implementation

- [ ] Add `batch_scanned_pdfs()` helper function
- [ ] Add `process_scanned_pdf_batch()` handler
- [ ] Add `process_single_olmocr_output()` helper
- [ ] Modify `utils_processor.py` processing loop
- [ ] Update config with batching settings
- [ ] Add feature flag for batching

### Testing

- [ ] Run Batch 2 with batching enabled
- [ ] Compare metrics to Batch 1 baseline
- [ ] Test error handling (corrupt PDF in batch)
- [ ] Test fallback to sequential
- [ ] Validate output quality matches baseline

### Documentation

- [ ] Update README with batching info
- [ ] Document config options
- [ ] Add performance benchmarks
- [ ] Create runbook for troubleshooting

---

## Next Steps

1. **Complete Batch 1 baseline** (~30 more minutes)
2. **Review this spike with Bryan** - get approval
3. **Implement Phase 1** (core batching) - ~4 hours
4. **Run Batch 2 comparison** - ~1 hour
5. **Validate and iterate** - ~2 hours
6. **Update roadmap** with implementation status

---

## References

- **OlmOCR README:** https://github.com/allenai/olmocr/blob/main/README.md
- **Baseline Test Doc:** [SCANNED_PDF_BASELINE_BATCH1.md](../testing/SCANNED_PDF_BASELINE_BATCH1.md)
- **Roadmap Item:** [ROADMAP.md#2](../planning/ROADMAP.md#L47)
- **Config File:** [config/default.yaml](../../config/default.yaml)

---

**Status:** Ready for implementation pending Bryan's approval
