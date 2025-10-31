
# Legal LLM RAG Pipeline - Phase 3 (RAG + Entities)

> **Production-ready** document processing pipeline for legal documents
> Multi-format ingestion + Entity extraction + Embeddings + Vector search

**Status:** ✅ Phase 2 Complete | 🚧 Phase 3 In Progress | **Environment:** Headless VM with GCS + NVIDIA L4 GPUs

---

## 📋 Project Planning & Documentation

All planning documents, roadmaps, and technical specifications are organized in **[docs/](docs/)**

**Quick Links:**
- 🤝 **[Contributing Guide](CONTRIBUTING.md)** - ⭐ Development standards & workflows
- 📚 **[All Documentation](docs/README.md)** - Complete documentation index
- 🔧 **[Schema v2.3.0](docs/technical/SCHEMA_V2.3.0.md)** - Technical specification (bbox + entities)
- 🛠️ **[Infrastructure Setup](docs/guides/SETUP_INFRASTRUCTURE.md)** - Qdrant + LangSmith setup guide
- 🚀 **[Performance Optimization](docs/technical/PARALLELIZATION_OPTIMIZATION_COMPLETE.md)** - 3x speedup details

---

## 📚 Overview

**Phase 2 delivers a deterministic, multi-format document ingestion pipeline** that processes
legal documents (deeds, assignments, title opinions, Division of Interest spreadsheets) into
unified Markdown + JSONL outputs ready for RAG.

### Architecture (Phase 3)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Digital PDFs** | [Docling](https://github.com/IBM/docling) | Extract text + tables from PDFs with text layers |
| **Scanned PDFs** | [OlmOCR-2](https://github.com/allenai/olmocr) | OCR for image-based PDFs (GPU-accelerated) |
| **Word Documents** | Docling + python-docx fallback | Process DOCX with sections and tables |
| **Excel Files** | openpyxl with smart chunking | Extract and chunk tables semantically |
| **Images** | OlmOCR-2 | OCR for JPG/PNG/TIF files |
| **Entity Extraction** | GPT-4o-mini | Extract legal entities (parties, tracts, dates, etc.) |
| **Embeddings** | all-mpnet-base-v2 | 768-dim sentence embeddings (GPU-accelerated) |
| **Vector Database** | Qdrant | Persistent vector storage for semantic search |
| **Unified Output** | JSONL + Markdown | Consistent schema v2.3.0 with bbox + entities |
| **QA & Validation** | Token range checks, schema validation | Ensure chunk quality (800-2000 tokens) |

### Key Features (Phase 2 + Phase 3)

✅ **5 file types supported:** PDF (digital/scanned), DOCX, XLSX, CSV, Images (JPG/PNG/TIF)
✅ **Optimized parallel processing:** 4-worker parallelization with 3x speedup for digital PDFs
✅ **Pipeline separation:** Ingest-only and enrich-only modes for fast iteration
✅ **PDF classification filter:** Process only scanned or digital PDFs
✅ **Entity extraction:** GPT-4o-mini powered legal entity extraction
✅ **Semantic embeddings:** 768-dimensional vectors with all-mpnet-base-v2
✅ **Persistent vector DB:** Qdrant for similarity search
✅ **200-page hard limit** for PDFs (safety guardrail)
✅ **Smart XLSX chunking** with 4 heuristic rules (blank rows, schema changes, headers, hard cap)
✅ **Table preservation** in Markdown format
✅ **Automatic retry + quarantine** for failed files
✅ **Manifest CSVs** with full processing metadata
✅ **Deterministic output:** Same input → same output

---

## 🚀 Quick Start

### Machine Setup (First Time)

**For new GCP machines**, use the automated setup script:

```bash
# Clone repository
git clone https://github.com/bryanjowers/pdf-rag.git
cd pdf-rag

# Run setup script with appropriate role
./scripts/setup_machine.sh --role gpu   # For GPU machine (OCR workload)
# OR
./scripts/setup_machine.sh --role cpu   # For CPU machine (enrichment workload)

# Activate environment
conda activate pdf-rag
```

**What the setup script does:**
- Installs system dependencies (gcsfuse, build tools)
- Installs Miniconda + creates conda environment
- Installs role-specific packages:
  - **GPU role**: PyTorch (CUDA), vLLM, OlmOCR
  - **CPU role**: PyTorch (CPU-only), spaCy, sentence-transformers, Qdrant
- Validates GCS mount access
- Creates activation helper: `~/activate_rag.sh`

See **[roadmap.md](roadmap.md)** for two-machine architecture details.

### Processing Documents

```bash
# 1. Activate environment
conda activate pdf-rag  # or `olmocr-optimized` for existing setups

# 2. Place documents in input directory or GCS bucket
cp your-files/* /mnt/gcs/legal-ocr-pdf-input/
# Supported: PDF, DOCX, XLSX, CSV, JPG, PNG, TIF

# 3. Process documents
# For batch processing (100s of PDFs):
python scripts/process_documents.py --auto --batch-size 10

# For single/few documents:
python scripts/process_documents.py --auto

# GPU-only (OCR to markdown):
python scripts/process_documents.py --auto --ingest-only

# CPU-only (entities + embeddings):
python scripts/process_documents.py --auto --enrich-only

# 4. Load processed documents to Qdrant vector database
python scripts/load_to_qdrant.py

# 5. Run RAG queries
python scripts/query_cli.py

# Optional: Review processing results
cat /mnt/gcs/legal-ocr-results/manifests/manifest_*.csv
cat /mnt/gcs/legal-ocr-results/quarantine/quarantine.csv  # if any failures
```

---

## 🛠️ Scripts & Utilities

All utility scripts are organized in **[scripts/](scripts/)** with detailed documentation.

### Main Scripts
- 🔥 **[process_documents.py](scripts/process_documents.py)** - Main pipeline (PDFs → markdown → JSONL with entities & embeddings)
- 📋 **[rebuild_inventory.py](scripts/rebuild_inventory.py)** - Build/rebuild file inventory with classification
- 🔍 **[query_cli.py](scripts/query_cli.py)** - Interactive RAG query interface
- 📦 **[load_to_qdrant.py](scripts/load_to_qdrant.py)** - Load embeddings to vector database
- ✨ **[enrich_from_markdown.py](scripts/enrich_from_markdown.py)** - Add entities/embeddings to existing markdown

### Maintenance
- 🧹 **[clean_slate.sh](scripts/maintenance/clean_slate.sh)** - Complete system reset (preserves input PDFs)
- ⚙️ **[setup_env.sh](scripts/maintenance/setup_env.sh)** - Environment setup

### Testing & Analysis
- **[scripts/testing/](scripts/testing/)** - Performance tests, feature tests, debug tools
- **[scripts/analysis/](scripts/analysis/)** - Data analysis, inspection, verification tools

**Full documentation:** [scripts/README.md](scripts/README.md)

---

## ⚙️ Prerequisites

* Python ≥ 3.10

* `conda activate olmocr-optimized` or similar environment

* Installed dependencies:

  ```bash
  pip install -r requirements.txt
  ```

* `OPENAI_API_KEY` exported in your environment.

* GCS bucket mounted at `/mnt/gcs/legal-ocr-results` (for output)
* GCS bucket mounted at `/mnt/gcs/legal-ocr-pdf-input` (for input, when using `--auto` mode)

---

## 🧭 End-to-End Workflow

### 1️⃣ Input

**Option A: Auto-Discovery Mode** (Recommended for batch processing)

Place documents in the GCS input bucket:

```bash
cp your-files/* /mnt/gcs/legal-ocr-pdf-input/
# Supports: PDF, DOCX, XLSX, CSV, JPG, PNG, TIF
```

**Option B: Manual Mode**

Specify file paths directly on command line.

### 2️⃣ Multi-Format Processing

**Auto Mode** - Process all documents from GCS bucket in batches:

```bash
python scripts/process_documents.py --auto --batch-size 10
```

**Manual Mode** - Process specific files:

```bash
python scripts/process_documents.py file1.pdf file2.docx file3.xlsx
```

**Dry Run** - Preview what would be processed:

```bash
python scripts/process_documents.py --auto --dry-run
```

**Filter by File Type:**

```bash
# Process only PDFs
python scripts/process_documents.py --auto --file-types pdf

# Process only DOCX files
python scripts/process_documents.py --auto --file-types docx

# Multiple types
python scripts/process_documents.py --auto --file-types pdf,docx,xlsx
```

**Filter PDFs by Classification:**

```bash
# Only scanned PDFs (OCR required)
python scripts/process_documents.py --auto --file-types pdf --pdf-type scanned

# Only digital PDFs (text extraction)
python scripts/process_documents.py --auto --file-types pdf --pdf-type digital
```

**Pipeline Separation** (NEW - for iterative workflows):

```bash
# Step 1: Ingest only (OCR/extraction, skip entities & embeddings)
python scripts/process_documents.py --auto --ingest-only --file-types pdf --pdf-type scanned
# Output: Markdown files only (fast iteration later)

# Step 2: Enrich from existing markdown (entities + embeddings)
python scripts/process_documents.py --auto --enrich-only --limit 100
# Output: JSONL with entities and embeddings

# Full pipeline (default - both ingest + enrich)
python scripts/process_documents.py --auto --file-types pdf
# Output: Complete JSONL with everything
```

**Use Case:** For scanned PDFs, OCR takes ~300s per file but enrichment only ~13s.
With `--ingest-only`, you can run expensive OCR once, then iterate freely on entity
extraction and chunking logic using `--enrich-only` (23x faster!).

### Complete Flag Reference

| Category | Flag | Type | Default | Description |
|----------|------|------|---------|-------------|
| **Input Source** | `files` | positional | - | Path(s) to input file(s) - not required with --auto |
| | `--auto` | flag | False | Auto-discover files from GCS input bucket |
| **File Filtering** | `--file-types` | string | None | Comma-separated file types (e.g., 'pdf,docx,xlsx') |
| | `--pdf-type` | choice | None | Filter PDFs by type: `digital` or `scanned` |
| **Batch Processing** | `--batch-size` | int | 5 | Number of files to process per batch |
| | `--sort-by` | choice | `name` | Sort order: `name`, `mtime`, `mtime_desc`, `pages`, `pages_desc` |
| | `--limit` | int | None | Limit total number of files to process |
| **Watch Mode** | `--watch` | flag | False | Continuously poll for new files (requires --auto) |
| | `--watch-interval` | int | 60 | Seconds between scans in watch mode |
| **Processing Options** | `--summary` | flag | False | Generate summary JSON after processing each file |
| | `--preprocess` | flag | False | Apply image cleanup before OCR (scanned PDFs only) |
| | `--workers` | int | 6 | Parallel workers for processing |
| **Pipeline Separation** | `--ingest-only` | flag | False | Extract text/markdown but skip entities and embeddings |
| | `--enrich-only` | flag | False | Process existing markdown with entities and embeddings |
| **Utility Flags** | `--dry-run` | flag | False | Preview files without processing |
| | `--rebuild-inventory` | flag | False | Force rebuild inventory even if it exists |
| | `--no-skip-processed` | flag | True | Disable skipping of already-processed files |
| | `--reprocess-all` | flag | False | Clear all success markers and reprocess all files |
| | `--reprocess-hash` | string | None | Reprocess specific file by hash (prefix match) |

**Key Notes:**
- **NEW**: `--sort-by pages` sorts files by page count (smallest first, recommended for faster feedback)
- **NEW**: `--sort-by pages_desc` sorts files by page count (largest first)
- `--pdf-type` requires `--file-types` to include 'pdf'
- `--watch` requires `--auto`
- Cannot use `--ingest-only` and `--enrich-only` together
- Either provide file paths OR use `--auto`, not both

**Common Command Examples:**
```bash
# Process all PDFs, smallest first (recommended for faster feedback)
python scripts/process_documents.py --auto --ingest-only --file-types pdf --batch-size 10 --sort-by pages

# Process only scanned PDFs, largest first
python scripts/process_documents.py --auto --file-types pdf --pdf-type scanned --sort-by pages_desc

# Dry run to preview what would be processed
python scripts/process_documents.py --auto --file-types pdf --sort-by pages --dry-run
```

**Processing Routes by File Type:**
- **Digital PDFs** → Docling (text extraction + table detection)
- **Scanned PDFs** → OlmOCR-2 (GPU-accelerated OCR)
- **DOCX** → Docling + python-docx fallback
- **XLSX/CSV** → openpyxl (smart table chunking)
- **Images** → OlmOCR-2 (OCR)

Output:

```
/mnt/gcs/legal-ocr-results/rag_staging/
 ├── jsonl/           # Unified JSONL schema v2.3.0
 ├── markdown/        # Markdown with preserved tables
 └── logs/            # Processing logs
/mnt/gcs/legal-ocr-results/manifests/
 └── manifest_*.csv   # Processing metadata
/mnt/gcs/legal-ocr-results/quarantine/
 ├── quarantine.csv   # Failed file log
 └── */               # Quarantined files + error logs
```

### 3️⃣ Review Processing Results

**Check Manifest:**

```bash
# View processing summary
cat /mnt/gcs/legal-ocr-results/manifests/manifest_*.csv

# Columns: doc_id, file_path, file_type, processor, status, chunks_created,
#          processing_duration_ms, char_count, estimated_tokens, warnings, error
```

**Check Quarantine (if failures occurred):**

```bash
# View quarantined files
cat /mnt/gcs/legal-ocr-results/quarantine/quarantine.csv

# Inspect error details
ls /mnt/gcs/legal-ocr-results/quarantine/*/
```

### 4️⃣ Manual QA

Review outputs manually:

```bash
# View markdown outputs
ls /mnt/gcs/legal-ocr-results/rag_staging/markdown/

# View JSONL chunks
head -1 /mnt/gcs/legal-ocr-results/rag_staging/jsonl/filename.jsonl | jq .

# Check processing logs
ls /mnt/gcs/legal-ocr-results/rag_staging/logs/
```

Confirm tables, exhibits, and signatures look correct in the output files.

### 5️⃣ Load to Qdrant

```bash
# Load JSONL embeddings to Qdrant vector database
python scripts/load_to_qdrant.py
```

This creates a persistent Qdrant collection with all embeddings for semantic search.

### 6️⃣ Query the RAG System

```bash
# Interactive query CLI
python scripts/query_cli.py

# Or direct query
python scripts/query_cli.py --query "Find all drilling permits for Lewis tracts"
```

The system retrieves relevant chunks and provides context-grounded answers.

### 7️⃣ (Optional) Processing Time Estimation

After processing multiple batches, estimate time for new document folders:

```python
from olmocr_pipeline.utils_estimator import build_time_estimators, estimate_batch_time
import pandas as pd

# Load manifest data
df = pd.read_csv("/mnt/gcs/legal-ocr-results/manifests/manifest_*.csv")

# Build estimators
estimators = build_time_estimators(df)

# Estimate new batch
estimate = estimate_batch_time(
    file_counts={"pdf": 50, "docx": 20, "xlsx": 10},
    estimators=estimators
)
print(f"Estimated time: {estimate['estimated_time_min']:.1f} minutes")
```

Requires sufficient manifest data for accurate predictions (recommended: 20+ documents per file type).

---

## 🧩 Directory Layout

```
.
├── config/
│   └── default.yaml                    # Configuration (v2.3.0)
│
├── docs/                                # 📚 All documentation
│   ├── planning/                       # Project planning
│   │   ├── phases/                     # Phase plans
│   │   ├── weekly/                     # Weekly summaries
│   │   └── sessions/                   # Session notes
│   ├── technical/                      # Technical specs
│   ├── testing/                        # Test results
│   ├── guides/                         # How-to guides
│   └── reference/                      # Reference files
│
├── olmocr_pipeline/                     # Core pipeline code
│   ├── handlers/                       # Document handlers
│   │   ├── pdf_digital.py              # Digital PDF (Docling, optimized)
│   │   ├── pdf_scanned.py              # Scanned PDF (OlmOCR-2)
│   │   ├── docx.py                     # Word documents
│   │   ├── xlsx.py                     # Excel/CSV
│   │   └── image.py                    # Images
│   ├── utils_*.py                      # Utility modules
│   └── rag_query.py                    # RAG query engine
│
├── scripts/                             # 🛠️ All scripts
│   ├── process_documents.py            # Main processor
│   ├── load_to_qdrant.py               # Load to vector DB
│   ├── query_cli.py                    # RAG queries
│   ├── rebuild_inventory.py            # Rebuild inventory
│   ├── enrich_from_markdown.py         # Re-enrichment
│   ├── maintenance/                    # Maintenance scripts
│   ├── testing/                        # Test scripts
│   └── analysis/                       # Analysis tools
│
├── /mnt/gcs/legal-ocr-pdf-input/       # GCS input bucket
└── /mnt/gcs/legal-ocr-results/         # GCS output bucket
    ├── rag_staging/
    │   ├── jsonl/                      # Schema v2.3.0 with entities + embeddings
    │   ├── markdown/                   # Markdown with tables
    │   └── logs/                       # Processing logs
    ├── manifests/                      # Processing metadata
    ├── inventory/                      # File inventory cache
    └── quarantine/                     # Failed files
```

---

## 🔄 Multi-Format Processing Features

### Automatic Format Detection & Routing
Intelligently routes each file to the appropriate processor:
- **PDFs**: Classified as digital (75%+ text layer) or scanned
- **Digital PDFs** → Docling for fast text extraction
- **Scanned PDFs** → OlmOCR-2 for GPU-accelerated OCR
- **DOCX** → Docling with python-docx fallback
- **XLSX/CSV** → Smart table chunking (4 heuristic rules)
- **Images** → OlmOCR-2 OCR engine

### Smart XLSX Chunking
Semantic table boundary detection using 4 rules:
1. **Blank rows** (≥90% empty cells)
2. **Schema changes** (>30% column structure difference)
3. **Mid-sheet headers** (≥80% non-numeric cells)
4. **Hard cap** (2000 rows maximum per chunk)

### Retry + Quarantine System
Robust error handling with zero silent failures:
- **Transient errors** (timeout, connection) → Retry up to 2 times
- **Permanent errors** (corrupted, unsupported) → Immediate quarantine
- Quarantine CSV log with error classification
- Timestamped error logs alongside failed files

### Batch Processing
Optimized for high throughput with parallel processing:
- **12-worker parallelization** for scanned PDFs (28% faster for batches)
- **4-worker parallelization** for digital PDFs (3x speedup)
- **FlashInfer acceleration** for GPU inference (10-20% faster)
- **Batch size 10** amortizes model loading (saves 80+ minutes per 100 PDFs)
- **pages_per_group: 10** for better parallelization of large documents (100-200 pages)
- Thread-local resource reuse eliminates initialization overhead
- Configurable batch sizes via `--batch-size` flag
- Sorting options: alphabetical, oldest first, newest first
- Progress tracking with per-file status updates
- Manifest CSVs with full processing metadata

**Performance:** ~14.7 hours for 100 mixed PDFs (vs 20.5 hours sequential)

### Deterministic Output
Same input always produces same output:
- SHA256 hashing for file identification
- Config versioning in JSONL metadata
- `_SUCCESS` markers for idempotency checks
- Reproducible chunking across runs

---

## 🧪 Quality Assurance Strategy

| Tier  | Type                       | Description                                          |
| ----- | -------------------------- | ---------------------------------------------------- |
| **1** | Schema Validation          | All JSONL records validated against schema v2.3.0    |
| **2** | Token Range QA             | Warn if <700 or >2200 tokens, fail if >10% out of range |
| **3** | Manifest Auditing          | Processing metadata tracked in CSV for every file    |
| **4** | Quarantine Tracking        | All failures logged with error classification        |
| **5** | Visual QA (optional)       | Manual inspection of markdown outputs                |

---

## 🏗️ Architecture Overview (Phase 2)

```
┌──────────────────────────────────────────┐
│  Mixed Document Inputs                   │
│  (PDF, DOCX, XLSX, CSV, JPG, PNG, TIF)  │
└────────────────┬─────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────┐
│  📋 File Classification & Routing          │
│  - PDF → Digital (75%+) or Scanned        │
│  - DOCX/XLSX/CSV/Images → Direct routing  │
└────────────────┬───────────────────────────┘
                 │
       ┌─────────┴─────────┐
       ▼                   ▼
┌──────────────┐    ┌─────────────────┐
│  Docling     │    │  OlmOCR-2       │
│  (Digital)   │    │  (Scanned/OCR)  │
│  - PDF       │    │  - Scanned PDF  │
│  - DOCX      │    │  - Images       │
└──────┬───────┘    └────────┬────────┘
       │                     │
       └─────────┬───────────┘
                 │
                 ▼
       ┌─────────────────┐
       │  openpyxl       │
       │  (Tables)       │
       │  - XLSX         │
       │  - CSV          │
       └────────┬────────┘
                │
                ▼
┌────────────────────────────────────────┐
│  Unified JSONL Schema v2.3.0           │
│  + Markdown with Preserved Tables      │
│  + Manifest CSV + Quarantine Tracking  │
│  + Entities + Embeddings               │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│  🔍 Qdrant Vector Database             │
│  Persistent semantic search            │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│  💬 RAG Query Engine                   │
│  Context-grounded answers + citations  │
└────────────────────────────────────────┘
```

---

## 🔧 Troubleshooting

### Unsupported File Type
**Problem:** `Unsupported file type: .doc`

**Solution:**
```bash
# Phase 2 supports: PDF, DOCX, XLSX, CSV, JPG, PNG, TIF
# Convert .doc to .docx using LibreOffice:
libreoffice --headless --convert-to docx file.doc
```

### PDF Exceeds 200-Page Limit
**Problem:** `Rejected: Exceeds 200-page limit`

**Solution:**
- This is a safety guardrail to prevent excessive processing times
- Split large PDFs into smaller chunks using `pdftk` or similar tools
- Or adjust `max_pages_absolute` in [config/default.yaml](config/default.yaml) (not recommended)

### Quarantined Files
**Problem:** Files appear in quarantine directory

**Solution:**
```bash
# Check quarantine log for error details
cat /mnt/gcs/legal-ocr-results/quarantine/quarantine.csv

# Inspect specific error logs
cat /mnt/gcs/legal-ocr-results/quarantine/*/filename_error.txt

# Common causes:
# - Corrupted files → Re-download original
# - Password-protected PDFs → Remove password with qpdf
# - Scanned PDFs with poor quality → Apply preprocessing with --preprocess flag
```

### Token Range QA Failures
**Problem:** `FAIL: 15.2% out of range`

**Solution:**
```bash
# This means >10% of chunks are outside 800-2000 token range
# Check manifest for specific files:
cat /mnt/gcs/legal-ocr-results/manifests/manifest_*.csv | grep -v "pass"

# Common fixes:
# - Adjust token_min/token_max in config/default.yaml
# - Review XLSX chunking rules for table-heavy documents
```

### OlmOCR Errors
**Problem:** `OlmOCR-2 failed: CUDA out of memory`

**Solution:**
```bash
# Reduce GPU memory utilization in config/default.yaml:
# processors.olmocr.gpu_memory_utilization: 0.75 → 0.60

# Or reduce parallel workers:
# processors.olmocr.workers: 6 → 4

# Check log file for details:
cat /mnt/gcs/legal-ocr-results/rag_staging/logs/olmocr_*.log
```

### Import Errors
**Problem:** `ModuleNotFoundError: No module named 'docling'`

**Solution:**
```bash
# Ensure correct environment is activated
conda activate olmocr-optimized

# Reinstall Phase 2 dependencies
pip install -r requirements.txt
```

---

## 📝 Notes

- **Phase 2 Complete:** All multi-format ingestion features are implemented and tested (100% deliverables)
  - ✅ **CHECKPOINT 4 PASSED:** All 5 file types validated in multi-format batch (100% success rate)
- **Deterministic Output:** Same input always produces same output thanks to SHA256 hashing and config versioning
- **Code Reuse:** 70% code reuse achieved by extracting OlmOCR logic into `utils_olmocr.py`
- **Manifest Data:** Collect sufficient data (20+ docs per file type) before using time estimation features
- **200-Page Limit:** Hard limit for PDFs enforced as safety guardrail (configurable in `config/default.yaml`)
- **Token Range:** Target 1400 tokens per chunk, acceptable range 800-2000, warn/fail thresholds enforced
- **Table Preservation:** XLSX tables converted to markdown pipe tables, merged cells expanded, footnotes appended
- **Quarantine System:** All failures logged and quarantined, no silent failures (PRD North Star: "fail closed, never silent")
- **Headless VM:** Download output files to local machine for visual inspection (no browser-based QA)
- **Batch Size:** Default of 10 files per batch balances throughput and memory usage on L4 GPUs
