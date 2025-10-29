
# Legal LLM RAG Pipeline - Phase 2 (Multi-Format Ingestion)

> **Production-ready** document processing pipeline for legal documents
> Supports PDFs (scanned + digital), Word, Excel, and images with deterministic output

**Status:** ✅ Phase 2 Complete (100%) | **Environment:** Headless VM with GCS + NVIDIA L4 GPUs

---

## 📚 Overview

**Phase 2 delivers a deterministic, multi-format document ingestion pipeline** that processes
legal documents (deeds, assignments, title opinions, Division of Interest spreadsheets) into
unified Markdown + JSONL outputs ready for RAG.

### Architecture (Phase 2)

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Digital PDFs** | [Docling](https://github.com/IBM/docling) | Extract text + tables from PDFs with text layers |
| **Scanned PDFs** | [OlmOCR-2](https://github.com/allenai/olmocr) | OCR for image-based PDFs (GPU-accelerated) |
| **Word Documents** | Docling + python-docx fallback | Process DOCX with sections and tables |
| **Excel Files** | openpyxl with smart chunking | Extract and chunk tables semantically |
| **Images** | OlmOCR-2 | OCR for JPG/PNG/TIF files |
| **Unified Output** | JSONL + Markdown | Consistent schema v2.2.0 for all file types |
| **QA & Validation** | Token range checks, schema validation | Ensure chunk quality (800-2000 tokens) |

### Key Features (Phase 2)

✅ **5 file types supported:** PDF (digital/scanned), DOCX, XLSX, CSV, Images (JPG/PNG/TIF)
✅ **200-page hard limit** for PDFs (safety guardrail)
✅ **Smart XLSX chunking** with 4 heuristic rules (blank rows, schema changes, headers, hard cap)
✅ **Table preservation** in Markdown format
✅ **Automatic retry + quarantine** for failed files
✅ **Manifest CSVs** with full processing metadata
✅ **Deterministic output:** Same input → same output
✅ **70% code reuse** (OlmOCR logic extracted once, used 3x)

---

## 🚀 Quick Start

```bash
# 1. Activate environment
conda activate olmocr-optimized

# 2. Place documents in input directory or GCS bucket
cp your-files/* /mnt/gcs/legal-ocr-pdf-input/
# Supported: PDF, DOCX, XLSX, CSV, JPG, PNG, TIF

# 3. Process all documents in batch
python olmocr_pipeline/process_documents.py --auto --batch-size 10

# 4. Review manifest and quarantine logs
cat /mnt/gcs/legal-ocr-results/manifests/manifest_*.csv
cat /mnt/gcs/legal-ocr-results/quarantine/quarantine.csv  # if any failures

# 5. Run RAG queries
python main.py
```

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
python olmocr_pipeline/process_documents.py --auto --batch-size 10
```

**Manual Mode** - Process specific files:

```bash
python olmocr_pipeline/process_documents.py file1.pdf file2.docx file3.xlsx
```

**Dry Run** - Preview what would be processed:

```bash
python olmocr_pipeline/process_documents.py --auto --dry-run
```

**Additional Options:**
- `--batch-size N` - Files per batch (default: 10)
- `--preprocess` - Apply image cleanup before OCR (scanned PDFs only)
- `--limit N` - Process only first N files
- `--sort-by {name,mtime,mtime_desc}` - Sort order for auto mode

**Processing Routes by File Type:**
- **Digital PDFs** → Docling (text extraction + table detection)
- **Scanned PDFs** → OlmOCR-2 (GPU-accelerated OCR)
- **DOCX** → Docling + python-docx fallback
- **XLSX/CSV** → openpyxl (smart table chunking)
- **Images** → OlmOCR-2 (OCR)

Output:

```
/mnt/gcs/legal-ocr-results/rag_staging/
 ├── jsonl/           # Unified JSONL schema v2.2.0
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

### 5️⃣ Embedding & Retrieval (Haystack)

```python
from haystack import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.retrievers import InMemoryEmbeddingRetriever
```

Embed each Docling block and store in an `InMemoryDocumentStore`.

### 6️⃣ Interactive RAG

```bash
python main.py
```

Ask natural-language questions — the system retrieves top-k relevant
sections and generates context-grounded answers with source citations.

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
│   └── default.yaml                    # Phase 2 configuration
├── /mnt/gcs/legal-ocr-pdf-input/       # GCS input bucket (auto mode)
├── /mnt/gcs/legal-ocr-results/         # GCS output bucket
│   ├── rag_staging/
│   │   ├── jsonl/                      # Unified JSONL schema v2.2.0
│   │   ├── markdown/                   # Markdown with tables
│   │   ├── logs/                       # Processing logs
│   │   └── olmocr_staging/             # OlmOCR temp outputs
│   ├── manifests/                      # Processing metadata CSVs
│   │   └── manifest_*.csv              # Batch manifests
│   └── quarantine/                     # Failed files
│       ├── quarantine.csv              # Quarantine log
│       └── */                          # Timestamped failures
├── olmocr_pipeline/
│   ├── process_documents.py            # Main multi-format processor
│   ├── process_pdf.py                  # Legacy scanned PDF processor
│   ├── handlers/
│   │   ├── pdf_digital.py              # Digital PDF (Docling)
│   │   ├── pdf_scanned.py              # Scanned PDF (OlmOCR-2)
│   │   ├── docx.py                     # Word documents
│   │   ├── xlsx.py                     # Excel/CSV
│   │   └── image.py                    # JPG/PNG/TIF
│   ├── utils_config.py                 # Config loader
│   ├── utils_classify.py               # PDF classification
│   ├── utils_processor.py              # Unified batch processor
│   ├── utils_quarantine.py             # Retry + quarantine logic
│   ├── utils_manifest.py               # Manifest generation
│   ├── utils_schema.py                 # JSONL validation
│   ├── utils_olmocr.py                 # OlmOCR wrapper (reusable)
│   ├── utils_estimator.py              # Time estimation
│   └── utils/
│       ├── combine_olmocr_outputs.py   # JSONL merger (legacy)
│       └── generate_ocr_dashboard.py   # Dashboard generator (legacy)
└── main.py                             # RAG entrypoint
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
Configurable batch sizes for optimal throughput:
- Default: 10 files per batch (adjustable via `--batch-size`)
- Sorting options: alphabetical, oldest first, newest first
- Progress tracking with per-file status updates
- Manifest CSVs with full processing metadata

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
| **1** | Schema Validation          | All JSONL records validated against schema v2.2.0    |
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
│  Unified JSONL Schema v2.2.0           │
│  + Markdown with Preserved Tables      │
│  + Manifest CSV + Quarantine Tracking  │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│  🔍 Haystack Embedding + Retrieval     │
│  Store chunks in InMemoryDocumentStore │
└────────────────┬───────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────┐
│  💬 OpenAI GPT-4o-mini RAG             │
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
