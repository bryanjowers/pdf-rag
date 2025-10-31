# Project Roadmap

**Last Updated:** 2025-10-30 19:20 UTC
**Current Phase:** Phase 3 (RAG + Entities) - Demo 1+2, Week 2
**Last Review:** 2025-10-30 (Active session with Bryan)

This document tracks high-level roadmap items and priorities for the PDF-RAG pipeline project. For detailed session notes, see [sessions/](sessions/).

---

## Current Sprint

### 🔴 High Priority

#### 1. Establish Baseline for Scanned PDF Processing
**Status:** In Progress (Batch 1 running)
**Priority:** HIGH
**Estimated Time:** 1-2 hours

**Goal:** Create baseline metrics for scanned PDF processing with OlmOCR-2

**Current Work:**
- Running Batch 1: 10 scanned PDFs (ingest-only mode)
- Config: 12 workers, batch size 10, pages_per_group 10
- Document set: 105 scanned PDFs total (0 digital)
- Capturing per-page normalized metrics for comparison

**Baseline Metrics to Capture:**
- Processing time per page (seconds)
- Character yield per page (OCR quality)
- Success/failure rate
- GPU utilization
- Per-file breakdown

**Next Steps:**
- [ ] Complete Batch 1 baseline (~45-60 min)
- [ ] Extract and document metrics
- [ ] Run Batch 2 (next 10 files) for comparison
- [ ] Validate config performs consistently
- [ ] Decide on production processing approach

**Documentation:**
- [SCANNED_PDF_BASELINE_BATCH1.md](../testing/SCANNED_PDF_BASELINE_BATCH1.md)

---

#### 2. OlmOCR Sequential Processing Inefficiency (Scanned PDFs)
**Status:** Documented
**Priority:** HIGH
**Estimated Time:** 4-8 hours (architectural change)

**Problem:** Scanned PDFs processed sequentially one-at-a-time, causing ~30% time waste on model loading/unloading between files.

**Root Cause Analysis:**
- **File:** [olmocr_pipeline/utils_processor.py:276-288](../../olmocr_pipeline/utils_processor.py#L276-L288)
  - Scanned PDFs processed in sequential loop, one file at a time
  - Each iteration calls `process_file_with_retry()` with single file

- **File:** [olmocr_pipeline/handlers/pdf_scanned.py:97-102](../../olmocr_pipeline/handlers/pdf_scanned.py#L97-L102)
  - Each file independently calls `run_olmocr_batch()` with single file
  - Causes OlmOCR model to load → process → unload → repeat

**Current Config Behavior:**
- `batch_size: 10` controls page batching WITHIN a document
- `default_workers: 12` controls page parallelism WITHIN a document
- No file-level batching across multiple documents

**Impact:**
- GPU utilization drops to 0% between files (confirmed with nvidia-smi)
- ~30% of processing time wasted on model startup/teardown
- Potential 2-3x speedup with true file-level batching

**Potential Solution:**
- Group 10 scanned PDFs and pass all to single `run_olmocr_batch()` call
- OlmOCR loads once, processes all files, unloads once
- Requires architectural change to batch files before processing

**Next Steps:**
- [ ] Complete baseline testing with current architecture
- [ ] Measure actual time waste (model loading vs OCR time)
- [ ] Review OlmOCR README for multi-file batch support
- [ ] Prototype file-level batching implementation
- [ ] Compare baseline vs batched performance

**Related Docs:**
- [SCANNED_PDF_BASELINE_BATCH1.md](../testing/SCANNED_PDF_BASELINE_BATCH1.md)
- OlmOCR README: https://github.com/allenai/olmocr/blob/main/README.md

---

#### 3. Investigate Digital PDF Parallelization Underperformance
**Status:** Pending
**Priority:** MEDIUM (lower after discovering scanned PDF issue)
**Estimated Time:** 1-2 hours

**Problem:** Digital PDF parallel processing only achieving 1.28x speedup instead of expected 1.8-2x with 2 workers.

**Current Config:**
- 8 workers configured in `config/default.yaml` (updated from 4)
- Expected: ~1.6-1.8x speedup with 8 workers
- Need to measure actual performance

**Investigation Plan:**
- [ ] Check if files are actually running in parallel (log analysis)
- [ ] Profile where time is spent (Docling, entities, embeddings, I/O)
- [ ] Test different worker counts (1, 2, 4, 8)
- [ ] Check for GPU contention or bottlenecks
- [ ] Verify thread-local resource reuse is working

**Success Criteria:**
- 2 workers: ≥1.6x speedup
- 4 workers: ≥2.5x speedup
- 8 workers: ≥3.5x speedup

**Related Docs:**
- [SESSION_PICKUP_2025-10-31.md](sessions/SESSION_PICKUP_2025-10-31.md)
- [PARALLELIZATION_OPTIMIZATION_COMPLETE.md](../technical/PARALLELIZATION_OPTIMIZATION_COMPLETE.md)

---

#### 4. Clarify HTML Output Requirement
**Status:** ✅ Resolved
**Priority:** HIGH (completed)
**Time Spent:** 15 minutes

**Decision:** HTML output NOT needed for Phase 3

**Rationale:**
- Phase 3 plan (PHASE3_PLAN.md) requires only JSONL + Markdown
- JSONL feeds Qdrant vector database (primary RAG source)
- Markdown provides human-readable format for QA and reports
- HTML not mentioned in any demo requirements or validation gates

**Current State:**
- Markdown: ✅ Generated for all files
- JSONL: ✅ Generated with entities + embeddings (schema v2.3.0)
- HTML: ❌ Not required

**Follow-up Actions:**
- [ ] Remove HTML directory creation from pipeline (optional cleanup)
- [ ] Update tests to not check for HTML output
- [ ] Document decision in schema docs

---

### 🟡 Medium Priority

#### 5. Process All Scanned PDFs (Ingest-Only)
**Status:** Pending
**Priority:** MEDIUM
**Estimated Time:** ~11 minutes (with 4 workers)

**Details:**
- Remaining: 94 digital PDFs
- Current config: 4 workers
- Expected time: ~11 minutes
- Savings vs sequential: ~3.5 minutes

**Depends On:** Baseline testing completion (#1)

**Command:**
```bash
python scripts/process_documents.py --auto --file-types pdf --pdf-type scanned --ingest-only
```

---

#### 6. Enrich Markdown with Entities & Embeddings
**Status:** Pending
**Priority:** MEDIUM
**Estimated Time:** ~10-15 minutes for 50 files

**After ingest-only completes**, run enrichment pipeline:

**Details:**
- Process existing markdown files
- Add entity extraction (GPT-4o-mini)
- Add embeddings (all-mpnet-base-v2, 768d)
- Create final JSONL with schema v2.3.0
- 23x faster than full pipeline

**Depends On:** Completing ingest-only (#5)

**Command:**
```bash
python scripts/enrich_from_markdown.py --auto --limit 50
```

**Benefits:**
- Fast iteration on entity/embedding logic
- Can change models without re-running OCR
- Can adjust chunking strategy
- Can switch embedding models later

---

### 🟢 Phase 3 Completion

#### 7. Test RAG Query System End-to-End
**Status:** Pending
**Priority:** MEDIUM
**Estimated Time:** 1-2 hours

**Test Plan:**
- [ ] Load all processed documents to Qdrant
- [ ] Run sample queries across different document types
- [ ] Verify entity extraction quality
- [ ] Validate embedding search relevance
- [ ] Test context-grounded answers
- [ ] Measure query response times

**Command:**
```bash
# Load to Qdrant
python scripts/load_to_qdrant.py

# Run interactive queries
python scripts/query_cli.py
```

**Success Criteria:**
- Relevant chunks retrieved for test queries
- Entity extraction accuracy >80%
- Query response time <2 seconds
- Context-grounded answers with citations

---

#### 8. Verify Qdrant Persistence
**Status:** Pending
**Priority:** LOW
**Estimated Time:** 30 minutes

**Test Plan:**
- [ ] Restart Qdrant container
- [ ] Verify collections persist
- [ ] Run sample queries after restart
- [ ] Validate vector count matches loaded documents

**Command:**
```bash
python scripts/analysis/verify_qdrant_persistence.py
```

---

#### 9. Document Phase 3 Completion
**Status:** Pending
**Priority:** LOW
**Estimated Time:** 1-2 hours

**Deliverables:**
- [ ] Final performance metrics (throughput, accuracy)
- [ ] End-to-end processing results
- [ ] RAG query quality assessment
- [ ] Known limitations and future improvements
- [ ] Handoff documentation

**Output:** `docs/planning/phases/PHASE3_COMPLETE.md`

---

## Backlog

### Future Enhancements
- **Switch to OpenAI embeddings** - text-embedding-3-small (1536d) per Phase 3 plan
  - Current: all-mpnet-base-v2 (768d, free, local GPU)
  - Future: OpenAI text-embedding-3-small (1536d, $0.02/1M tokens)
  - Rationale: Following "95% rule" - current embeddings working, switch if needed
- Query API with REST endpoints
- Batch query processing
- Advanced entity linking and normalization
- Custom entity extraction templates per document type
- Performance monitoring dashboard
- Automated quality metrics
- Multi-tenant Qdrant collections
- Document versioning and updates

### Technical Debt
- Refactor handlers to share more common code
- Add comprehensive unit tests
- Set up CI/CD pipeline
- Improve error messages and logging
- Add schema migration utilities

---

## Completed Items

### Phase 2 (Multi-Format Ingestion)
- ✅ Digital PDF processing (Docling)
- ✅ Scanned PDF processing (OlmOCR-2)
- ✅ DOCX processing
- ✅ XLSX/CSV processing with smart chunking
- ✅ Image processing (JPG/PNG/TIF)
- ✅ Unified JSONL schema v2.3.0
- ✅ Manifest tracking and quarantine system
- ✅ 200-page hard limit safety guardrail
- ✅ Token range QA (800-2000 tokens)

### Phase 3 (RAG + Entities) - In Progress
- ✅ Entity extraction (GPT-4o-mini)
- ✅ Semantic embeddings (all-mpnet-base-v2)
- ✅ Qdrant vector database setup
- ✅ RAG query engine with citations
- ✅ Persistent Qdrant storage
- ✅ Classifier upgrade (image detection)
- ✅ Parallelization implementation (4 workers)
- ✅ FlashInfer GPU acceleration
- ✅ OlmOCR-2 optimization (12 workers, batch 10)
- ✅ Documentation restructure
- ✅ HTML output clarified (not needed - JSONL + Markdown only)
- ⚠️ Parallelization performance (needs investigation)

---

## Priority Legend

- 🔴 **HIGH** - Blockers or critical issues
- 🟡 **MEDIUM** - Important for completion
- 🟢 **LOW** - Nice to have, not blocking

---

## How to Use This Roadmap

1. **Review weekly** - Update priorities and status
2. **Add new items** - Capture tasks as they emerge
3. **Move completed items** - Archive to "Completed Items" section
4. **Link to details** - Reference session notes and technical docs
5. **Estimate time** - Help with planning and scheduling

---

**Next Review:** After completing HIGH priority items
**Updated By:** Claude (automated)
