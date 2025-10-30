# Project Roadmap

**Last Updated:** 2025-10-30
**Current Phase:** Phase 3 (RAG + Entities)

This document tracks high-level roadmap items and priorities for the PDF-RAG pipeline project. For detailed session notes, see [sessions/](sessions/).

---

## Current Sprint

### 🔴 High Priority

#### 1. Investigate Parallelization Underperformance
**Status:** Pending
**Priority:** HIGH
**Estimated Time:** 1-2 hours

**Problem:** Digital PDF parallel processing only achieving 1.28x speedup instead of expected 1.8-2x with 2 workers.

**Current Config:**
- 4 workers configured in `config/default.yaml`
- Expected: ~3-3.5x speedup
- Need to measure actual performance

**Investigation Plan:**
- [ ] Check if files are actually running in parallel (log analysis)
- [ ] Profile where time is spent (Docling, entities, embeddings, I/O)
- [ ] Test different worker counts (1, 2, 4, 6)
- [ ] Check for GPU contention or bottlenecks
- [ ] Verify thread-local resource reuse is working

**Success Criteria:**
- 2 workers: ≥1.6x speedup
- 4 workers: ≥2.5x speedup
- 6 workers: ≥3.5x speedup

**Related Docs:**
- [SESSION_PICKUP_2025-10-31.md](sessions/SESSION_PICKUP_2025-10-31.md)
- [PARALLELIZATION_OPTIMIZATION_COMPLETE.md](../technical/PARALLELIZATION_OPTIMIZATION_COMPLETE.md)

---

#### 2. Clarify HTML Output Requirement
**Status:** Pending
**Priority:** HIGH
**Estimated Time:** 15 minutes

**Question:** Is HTML output needed for RAG queries, or is markdown sufficient?

**Current State:**
- Markdown: ✅ Generated for all files
- JSONL: ✅ Generated with entities + embeddings
- HTML: ❌ Only 1 old file (Oct 28)

**Options:**
1. **HTML needed:** Investigate Docling config, add HTML output verification
2. **HTML NOT needed:** Remove HTML checks from tests, update documentation

**Decision Needed:** User confirmation

---

### 🟡 Medium Priority

#### 3. Process Remaining Digital PDFs
**Status:** Pending
**Priority:** MEDIUM
**Estimated Time:** ~11 minutes (with 4 workers)

**Details:**
- Remaining: 94 digital PDFs
- Current config: 4 workers
- Expected time: ~11 minutes
- Savings vs sequential: ~3.5 minutes

**Depends On:** Decision on whether to fix parallelization first (#1)

**Command:**
```bash
python scripts/process_documents.py --auto --file-types pdf --pdf-type digital
```

---

#### 4. Process Scanned PDFs
**Status:** Pending
**Priority:** MEDIUM
**Estimated Time:** ~17.5 hours

**Details:**
- Total: 211 scanned PDFs
- Processing: Sequential (GPU-bound, OlmOCR-2)
- Current config: 12 workers, batch size 10, pages_per_group 10
- Best run as overnight batch

**Depends On:** Completing digital PDFs (#3)

**Command:**
```bash
python scripts/process_documents.py --auto --file-types pdf --pdf-type scanned --batch-size 10
```

**Optimization Notes:**
- 28% faster than baseline with current config
- FlashInfer acceleration enabled (10-20% speedup)
- See: [SCANNED_PDF_OPTIMIZATION_GUIDE.md](../technical/SCANNED_PDF_OPTIMIZATION_GUIDE.md)

---

### 🟢 Phase 3 Completion

#### 5. Test RAG Query System End-to-End
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

#### 6. Verify Qdrant Persistence
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

#### 7. Document Phase 3 Completion
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
