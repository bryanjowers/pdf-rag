# FlashInfer Installation Workarounds for PyTorch 2.8

**Status:** Experimental - Not yet tested
**Goal:** Install FlashInfer optimization without breaking PyTorch 2.8.0+cu128
**Problem:** Old FlashInfer wheel downgrades PyTorch from 2.8 to 2.4.x
**Impact:** Significant speedup for OlmOCR inference if successful

---

## Background

The OlmOCR README originally referenced this installation:
```bash
pip install https://download.pytorch.org/whl/cu128/flashinfer/flashinfer_python-0.2.5%2Bcu128torch2.7-cp38-abi3-linux_x86_64.whl
```

**Problem:** This wheel is built for PyTorch 2.7 and when installed, dependency resolution downgrades PyTorch to 2.4.x, breaking the pipeline.

**Research Finding:** FlashInfer now has modern PyPI packages that may avoid this version conflict, plus building from source is an option.

---

## Current Working Setup (Baseline)

- **PyTorch:** 2.8.0+cu128
- **OlmOCR:** 0.4.2
- **CUDA:** 12.8
- **FlashInfer:** Not installed (avoiding version conflicts)
- **Performance:** Working, but could be faster with FlashInfer

---

## Workaround Options

### **Workaround 1: Modern PyPI Installation (RECOMMENDED FIRST TRY)**

**Theory:** The newer `flashinfer-python` package from PyPI may not have strict PyTorch version pinning.

```bash
# Prerequisites: OlmOCR already installed with PyTorch 2.8.0
conda activate olmocr-optimized

# Install modern FlashInfer packages
pip install flashinfer-python flashinfer-cubin
pip install flashinfer-jit-cache --index-url https://flashinfer.ai/whl/cu128

# Verify PyTorch version didn't downgrade
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
# Should still show: 2.8.0+cu128

# Verify FlashInfer installation
flashinfer show-config

# Test OlmOCR still works
python -c "import olmocr; print('✅ OlmOCR still works')"
```

**Pros:**
- Simple pip install
- Uses official PyPI packages
- Includes pre-compiled kernels (flashinfer-cubin)
- Most likely to work without issues

**Cons:**
- May still have version conflicts (untested)
- Requires testing before committing

**References:**
- [FlashInfer Installation Docs](https://docs.flashinfer.ai/installation.html)
- [flashinfer-python on PyPI](https://pypi.org/project/flashinfer-python/)

---

### **Workaround 2: Build from Source**

**Theory:** Compiling FlashInfer directly against PyTorch 2.8 avoids pre-built wheel version conflicts.

```bash
conda activate olmocr-optimized

# Clone FlashInfer repository
git clone https://github.com/flashinfer-ai/flashinfer.git --recursive
cd flashinfer

# Build and install against current PyTorch
pip install -v .

# Verify PyTorch version didn't change
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
# Should still show: 2.8.0+cu128

# Verify FlashInfer
flashinfer show-config

# Test OlmOCR still works
python -c "import olmocr; print('✅ OlmOCR still works')"
```

**Pros:**
- Guaranteed compatibility with exact PyTorch version
- Most flexible approach
- Used successfully by other projects (vLLM, SGLang)

**Cons:**
- Requires compilation (5-15 minutes)
- Needs build tools and CUDA toolkit
- More complex than pip install

**Build Requirements:**
- CUDA 12.8 toolkit
- C++ compiler (gcc/g++)
- PyTorch already installed

**References:**
- [FlashInfer GitHub](https://github.com/flashinfer-ai/flashinfer)
- [Issue #922: PyTorch 2.7 + CUDA 12.8](https://github.com/flashinfer-ai/flashinfer/issues/922)
- [SGLang Issue #6197](https://github.com/sgl-project/sglang/issues/6197)

---

### **Workaround 3: Constrained Installation (Advanced)**

**Theory:** Install FlashInfer without dependency resolution, then manually satisfy dependencies.

```bash
conda activate olmocr-optimized

# Install without dependencies to prevent downgrades
pip install flashinfer-python --no-deps
pip install flashinfer-cubin --no-deps

# Check what dependencies are actually needed
pip show flashinfer-python

# Install missing dependencies manually (if any)
# (Determine this from the pip show output)

# Verify PyTorch version
python -c "import torch; print(f'PyTorch: {torch.__version__}')"

# Test if FlashInfer works
python -c "import flashinfer; print('✅ FlashInfer imported')"

# Verify FlashInfer
flashinfer show-config
```

**Pros:**
- Precise control over dependencies
- Can avoid unwanted downgrades

**Cons:**
- May break if FlashInfer actually needs specific PyTorch version
- Requires manual dependency management
- Higher risk of runtime errors

**Use Case:** If Workaround 1 and 2 fail, this can help diagnose what's actually causing conflicts.

---

## Testing Procedure

Before trying any workaround in production:

### 1. Save Current Environment
```bash
# Export current working environment
conda activate olmocr-optimized
pip freeze > ~/olmocr-baseline-$(date +%Y%m%d).txt
conda env export > ~/olmocr-env-baseline-$(date +%Y%m%d).yml
```

### 2. Test Installation
Choose one workaround and follow its steps.

### 3. Verification Checklist
After installation, verify:

- [ ] PyTorch version still 2.8.0+cu128: `python -c "import torch; print(torch.__version__)"`
- [ ] CUDA still available: `python -c "import torch; print(torch.cuda.is_available())"`
- [ ] OlmOCR imports: `python -c "import olmocr; print('OK')"`
- [ ] FlashInfer imports: `python -c "import flashinfer; print('OK')"`
- [ ] FlashInfer config: `flashinfer show-config`
- [ ] Process test PDF: `python scripts/process_documents.py <test-pdf-path>`

### 4. Performance Benchmark
If verification passes, test actual speedup:

```bash
# Run benchmark on scanned PDFs (OlmOCR uses FlashInfer)
python scripts/testing/test_parallel_speedup.py

# Compare against baseline performance (documented in PARALLELIZATION_OPTIMIZATION_COMPLETE.md)
# Baseline: ~2.3x speedup with 2 workers, ~3.1x with 4 workers
# Expected with FlashInfer: 10-30% additional speedup on inference
```

### 5. Rollback if Needed
If anything breaks:

```bash
# Remove FlashInfer
pip uninstall flashinfer-python flashinfer-cubin flashinfer-jit-cache -y

# Restore from baseline (if needed)
pip install -r ~/olmocr-baseline-<date>.txt --force-reinstall
```

---

## Expected Performance Gains

Based on FlashInfer documentation and OlmOCR architecture:

- **Scanned PDFs (OlmOCR):** 10-30% faster inference
- **Digital PDFs (Docling):** No impact (Docling doesn't use FlashInfer)
- **Overall Pipeline:** 5-15% improvement (depends on scanned/digital ratio)

**Current Performance (Baseline):**
- 2 workers: ~2.3x speedup
- 4 workers: ~3.1x speedup

**Potential with FlashInfer:**
- 2 workers: ~2.5-2.8x speedup
- 4 workers: ~3.4-3.7x speedup

*Note: These are estimates. Actual gains depend on GPU utilization, document complexity, and other factors.*

---

## Known Issues

### Issue 1: PyTorch 2.7+ Compatibility
- **Status:** Unconfirmed if FlashInfer 0.4.x supports PyTorch 2.8
- **Evidence:** GitHub issues suggest building from source may be needed for PyTorch 2.7+
- **Mitigation:** Try Workaround 2 (build from source) if Workaround 1 fails

### Issue 2: CUDA 12.8 Wheel Availability
- **Status:** FlashInfer supports cu128, cu129, cu130
- **Evidence:** JIT cache index includes CUDA 12.8
- **Resolution:** Should work, use `--index-url https://flashinfer.ai/whl/cu128`

### Issue 3: Old Wheel References
- **Status:** OlmOCR README references old 0.2.5 wheel
- **Evidence:** PyPI has newer 0.4.1 version
- **Resolution:** Use modern PyPI packages, not direct wheel URLs

---

## Documentation Updates After Success

If any workaround succeeds, update these files:

1. **docs/guides/VM_SETUP_COMPLETE.md**
   - Remove "DO NOT install FlashInfer" warning
   - Add working FlashInfer installation section
   - Update performance expectations

2. **requirements.txt**
   - Add FlashInfer packages with notes
   - Document working installation method

3. **docs/technical/PARALLELIZATION_OPTIMIZATION_COMPLETE.md**
   - Add FlashInfer performance results
   - Update speedup metrics

4. **CONTRIBUTING.md**
   - Add FlashInfer to development environment setup
   - Document testing procedures

---

## References

- [FlashInfer GitHub Repository](https://github.com/flashinfer-ai/flashinfer)
- [FlashInfer Installation Documentation](https://docs.flashinfer.ai/installation.html)
- [OlmOCR GitHub Repository](https://github.com/allenai/olmocr)
- [PyTorch 2.7 Release Notes](https://pytorch.org/blog/pytorch-2-7/)
- [GitHub Issue: PyTorch 2.7 + CUDA 12.8 Build](https://github.com/flashinfer-ai/flashinfer/issues/922)

---

**Last Updated:** October 31, 2025
**Status:** Untested - Awaiting experimentation
**Next Step:** Try Workaround 1 (Modern PyPI Installation)
