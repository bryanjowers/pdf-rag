# PDF RAG Pipeline - Roadmap

## Cost Optimization: GPU/CPU Machine Split

### Objective
Separate GPU-intensive OCR workload from CPU-only enrichment tasks to reduce infrastructure costs while maintaining performance.

### Current Architecture
- **Single GPU machine**: Runs both OCR (GPU) and enrichment (CPU)
- **Cost issue**: GPU instances (g2-standard-4) are 3-5x more expensive than CPU instances
- **Idle waste**: GPU sits idle during entity extraction and embedding generation

### Target Architecture

**Two-machine setup with shared GCS storage:**

1. **GPU Box** (g2-standard-4 or similar)
   - **Purpose**: OCR-only workload (scanned PDF → markdown)
   - **Runtime**: On-demand, shut down when idle
   - **Command**: `python scripts/process_documents.py --auto --ingest-only --file-types pdf`
   - **Dependencies**: torch+CUDA, vLLM, OlmOCR, FlashInfer

2. **CPU Box** (n2-standard-8 or c3-standard-8)
   - **Purpose**: Enrichment pipeline (markdown → entities + embeddings)
   - **Runtime**: Continuous or scheduled
   - **Command**: `python scripts/process_documents.py --auto --enrich-only`
   - **Dependencies**: torch (CPU), spaCy, sentence-transformers, qdrant-client

3. **Shared Storage**: GCS buckets mounted on both machines
   - Acts as message queue (GPU writes markdown, CPU reads)
   - No orchestration layer needed

### Benefits

1. **Cost savings**: 60-80% reduction by only running GPU box during OCR
2. **Scalability**: Enrichment can run continuously while GPU is off
3. **Simplicity**: No complex orchestration - GCS is the queue
4. **Docker-ready**: Architecture maps cleanly to containerized deployment
5. **Flexibility**: Scale GPU and CPU boxes independently

### Implementation Plan

#### Phase 1: Environment Setup Script ✅
Created `scripts/setup_machine.sh` with machine role detection:

```bash
./scripts/setup_machine.sh --role gpu   # Installs GPU dependencies
./scripts/setup_machine.sh --role cpu   # Installs CPU-only dependencies
```

**Tasks:**
- [x] Create setup script with gpu/cpu modes
- [x] Install appropriate conda environment per role
- [x] Validate GCS mount access
- [x] Create activation helper script
- [ ] Configure systemd services or cron jobs (optional - future)

#### Phase 2: Documentation 🚧
- [x] Update README.md with machine setup quick start
- [x] Document `--ingest-only` and `--enrich-only` flags
- [ ] Document GPU box provisioning and teardown workflow
- [ ] Add cost comparison table (single GPU vs split architecture)
- [ ] Create troubleshooting guide for cross-machine coordination

#### Phase 3: Testing & Validation
- [ ] Test full workflow: GPU ingest → CPU enrich
- [ ] Verify GCS locking works across machines
- [ ] Benchmark cost savings over 1-week test period
- [ ] Document any edge cases or coordination issues

### Pipeline Flags (Already Implemented)

The codebase already supports this split via existing flags:

| Flag | Purpose | Machine |
|------|---------|---------|
| `--ingest-only` | OCR → markdown only | GPU box |
| `--enrich-only` | Entities + embeddings only | CPU box |
| (no flags) | Full pipeline | Single machine (current) |

### Future Enhancements

- **Auto-shutdown**: Script to shut down GPU box after ingest completes
- **Cloud Run/Batch**: Migrate GPU workload to serverless (even more cost savings)
- **Monitoring**: Dashboard showing GPU vs CPU utilization and cost
- **Queue-based**: Replace GCS polling with Pub/Sub for instant triggering

### Status
🟢 **Phase 1 Complete** - Setup script created and tested. CPU machine deployed (rag-cpu, us-central1-f).
🟡 **Phase 2-3 In Progress** - Documentation updates ongoing, full workflow testing pending.

---

*Last updated: 2025-10-31*
