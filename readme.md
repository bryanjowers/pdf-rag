
# Legal LLM OCR → RAG Pipeline (OlmOCR + Docling + Haystack)

> End-to-end system for transforming scanned legal documents (deeds, assignments, exhibits)
> into a searchable, layout-preserving Retrieval-Augmented Generation (RAG) knowledge base.

**Production Environment:** Headless VM with GCS bucket mounts and NVIDIA L4 GPUs

---

## 📚 Overview

This project converts complex **recorded instruments** (e.g., assignments, deeds, and liens)
into a **structured, queryable corpus** using:

| Stage                     | Component                                              | Purpose                                          |
| ------------------------- | ------------------------------------------------------ | ------------------------------------------------ |
| **OCR**                   | [**OlmOCR-2**](https://github.com/allenai/olmocr)      | Layout-aware visual text extraction              |
| **Normalization**         | `combine_olmocr_outputs.py`                            | Merge per-page JSONL → layout-preserving HTML/MD |
| **QA Dashboard**          | `generate_ocr_dashboard.py`                            | Visual completeness + density metrics            |
| **Structural Parsing**    | [**Docling**](https://github.com/IBM/docling)          | Convert HTML/MD → structured document blocks     |
| **Embedding & Retrieval** | [**Haystack**](https://github.com/deepset-ai/haystack) | Dense retrieval & RAG orchestration              |
| **Generation**            | **OpenAI GPT-4o-mini**                                 | Natural-language answers with citations          |

---

## 🚀 Quick Start

```bash
# 1. Activate environment
conda activate olmocr-optimized

# 2. Place PDFs in GCS input bucket
cp your-pdfs/*.pdf /mnt/gcs/legal-ocr-pdf-input/

# 3. Process all PDFs in batches
python olmocr_pipeline/process_pdf.py --auto --summary --batch-size 5

# 4. Generate QA dashboard
python olmocr_pipeline/utils/generate_ocr_dashboard.py

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

Place raw PDFs in the GCS input bucket:

```bash
cp your-pdfs/*.pdf /mnt/gcs/legal-ocr-pdf-input/
```

**Option B: Manual Mode**

Specify PDF paths directly on command line.

### 2️⃣ OCR Extraction

**Auto Mode** - Process all PDFs from GCS bucket in batches:

```bash
python olmocr_pipeline/process_pdf.py --auto --summary --batch-size 5
```

**Manual Mode** - Process specific files:

```bash
python olmocr_pipeline/process_pdf.py path/to/file.pdf --summary
```

**Watch Mode** - Continuously monitor for new PDFs:

```bash
python olmocr_pipeline/process_pdf.py --auto --watch --watch-interval 300 --summary
```

**Dry Run** - Preview what would be processed:

```bash
python olmocr_pipeline/process_pdf.py --auto --dry-run
```

**Additional Options:**
- `--batch-size N` - PDFs per batch (default: 5)
- `--workers N` - Parallel workers for OlmOCR (default: 6)
- `--preprocess` - Apply image cleanup before OCR
- `--merge` - Merge JSONL outputs at end
- `--limit N` - Process only first N PDFs
- `--sort-by {name,mtime,mtime_desc}` - Sort order for auto mode

Output:

```
/mnt/gcs/legal-ocr-results/rag_staging/
 ├── jsonl/           # per-page OCR results
 ├── markdown/        # raw plain Markdown
 └── logs/            # processing logs
```

### 3️⃣ Merge & Normalize

Combine per-page JSONL into layout-preserving outputs (optional - can use `--merge` flag with `process_pdf.py` instead):

```bash
python olmocr_pipeline/utils/combine_olmocr_outputs.py rag_staging/jsonl/*.jsonl --html --md
```

Produces:

```
rag_staging/
 ├── html/*.merged.html
 ├── markdown_merged/*.merged.md
 └── reports/ocr_merge_summary.json
```

### 4️⃣ QA Dashboard

Generate dashboard:

```bash
python olmocr_pipeline/utils/generate_ocr_dashboard.py
```

View the dashboard by opening `/mnt/gcs/legal-ocr-results/rag_staging/reports/index.html` in a browser (download to local machine if running on headless VM).

See page counts, empty-page ratios, and document completion metrics.

### 5️⃣ Manual QA

Review outputs manually:

```bash
# View markdown outputs
ls /mnt/gcs/legal-ocr-results/rag_staging/markdown/

# View merged HTML (download to local machine for browser viewing)
ls /mnt/gcs/legal-ocr-results/rag_staging/html/

# Check processing logs
ls /mnt/gcs/legal-ocr-results/logs/
```

Confirm tables, exhibits, and signatures look correct in the output files.

### 6️⃣ Structural Parsing (Docling)

```python
from docling.document_converter import DocumentConverter
doc = DocumentConverter().convert("rag_staging/html/<doc>.merged.html")
```

Outputs structured blocks (paragraphs, tables, figures).

### 7️⃣ Embedding & Retrieval (Haystack)

```python
from haystack import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.retrievers import InMemoryEmbeddingRetriever
```

Embed each Docling block and store in an `InMemoryDocumentStore`.

### 8️⃣ Interactive RAG

```bash
python main.py
```

Ask natural-language questions — the system retrieves top-k relevant
sections and generates context-grounded answers with source citations.

### 9️⃣ QA & Reporting Loop

Review:

* `rag_staging/reports/index.html` → visual metrics
* `rag_staging/reports/ocr_merge_summary.json` → quantitative stats
* Optionally run semantic QA on flagged docs (see `qa_assistant.py`, future module).

### 🔟 (Optional) Corpus Export

Persist embeddings for downstream retrieval or web app integration.

---

## 🧩 Directory Layout

```
.
├── pdf_input/                          # local PDFs (manual mode)
├── /mnt/gcs/legal-ocr-pdf-input/       # GCS input bucket (auto mode)
├── /mnt/gcs/legal-ocr-results/         # GCS output bucket
│   ├── rag_staging/
│   │   ├── jsonl/                      # raw OCR JSONL
│   │   ├── markdown/                   # raw MD
│   │   ├── html/                       # merged HTML
│   │   ├── markdown_merged/            # merged MD
│   │   └── results/                    # temporary OlmOCR outputs
│   ├── logs/                           # processing logs
│   └── reports/                        # QA summaries + dashboard
├── olmocr_pipeline/
│   ├── process_pdf.py                  # main OCR processing script
│   ├── utils_batch.py                  # batch processing utilities
│   ├── utils_preprocess.py             # image preprocessing
│   ├── qa_summary.py                   # QA summary generation
│   └── utils/
│       ├── combine_olmocr_outputs.py   # JSONL merger
│       └── generate_ocr_dashboard.py   # dashboard generator
└── main.py                             # RAG entrypoint
```

---

## 🔄 Batch Processing Features

### Auto-Discovery Mode
Automatically discovers and processes all PDFs from the GCS input bucket:
- Configurable batch sizes (default: 5 PDFs per batch)
- Sorting options: alphabetical, oldest first, newest first
- Built-in re-run safety via OlmOCR's hash-based caching

### Watch Mode
Continuously monitors the input bucket for new files:
- Polls at configurable intervals (default: 60 seconds)
- Processes new PDFs automatically
- Graceful handling of Ctrl-C interrupts

### Single-Instance Locking
Prevents multiple concurrent process runs:
- File lock at `/mnt/gcs/legal-ocr-results/.process_pdf.lock`
- Automatically released on exit or crash
- Ensures no output file conflicts

### GCS Mount Health Checks
Verifies bucket accessibility before each batch:
- PID-based test files prevent conflicts
- Automatic cleanup on success or failure
- Early detection of mount issues

### Progress Tracking
Detailed visibility into processing status:
- Per-batch progress reporting
- File relocation tracking
- Final statistics with success/failure counts
- Individual log files per batch

---

## 🧪 Quality Assurance Strategy

| Tier  | Type                       | Description                                          |
| ----- | -------------------------- | ---------------------------------------------------- |
| **1** | Visual QA                  | Human inspection via dashboard / preview             |
| **2** | Quantitative QA            | Empty-page %, chars/page metrics                     |
| **3** | Semantic QA (LLM-assisted) | GPT-4o-mini detects truncations, malformed tables    |
| **4** | Diff QA (optional)         | Compare OCR text vs. original PDF text for debugging |

---

## 🏗️ Architecture Overview



┌─────────────────────┐
│  Recorded PDFs      │
│  (Deeds, Leases)    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  🧠 OlmOCR-2        │
│  Layout-Aware OCR   │
│  → JSONL + Markdown │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────────────┐
│  🧩 combine_olmocr_outputs  │
│  Merge per-page JSONL →     │
│  layout-preserving HTML/MD  │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│  📊 QA Dashboard             │
│  (generate_ocr_dashboard)   │
│  Visual + quantitative QA   │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│  🧱 Docling Parser          │
│  Convert HTML/MD → Blocks   │
│  (paragraphs, tables, etc.) │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│  🔍 Haystack + Embeddings   │
│  Store structured chunks    │
│  for semantic retrieval     │
└─────────┬───────────────────┘
          │
          ▼
┌─────────────────────────────┐
│  💬 OpenAI GPT-4o-mini      │
│  RAG answers + citations    │
└─────────────────────────────┘

---

## 🔧 Troubleshooting

### Lock File Issues
**Problem:** `Another instance is already running`

**Solution:**
```bash
# Check if process is actually running
ps aux | grep process_pdf.py

# If no process is running, remove stale lock file
rm /mnt/gcs/legal-ocr-results/.process_pdf.lock
```

### GCS Mount Issues
**Problem:** `GCS mount check FAILED`

**Solution:**
```bash
# Check if bucket is mounted
df -h | grep gcs

# Remount if needed
gcsfuse legal-ocr-results /mnt/gcs/legal-ocr-results
gcsfuse legal-ocr-pdf-input /mnt/gcs/legal-ocr-pdf-input

# Verify write access
touch /mnt/gcs/legal-ocr-results/test.txt && rm /mnt/gcs/legal-ocr-results/test.txt
```

### OlmOCR Errors
**Problem:** `OlmOCR pipeline FAILED`

**Solution:**
```bash
# Check log file mentioned in error
cat /mnt/gcs/legal-ocr-results/logs/<logfile>.log

# Common issues:
# - GPU memory: Reduce --workers or adjust --gpu-memory-utilization
# - Invalid PDF: Check PDF is not corrupted
# - Missing dependencies: Verify conda environment is activated
```

### Import Errors
**Problem:** `ModuleNotFoundError: No module named 'bs4'`

**Solution:**
```bash
# Ensure correct environment is activated
conda activate olmocr-optimized

# Reinstall dependencies
pip install -r requirements.txt
```

### No PDFs Found
**Problem:** `No valid PDF files to process`

**Solution:**
```bash
# Verify PDFs exist in input bucket
ls -la /mnt/gcs/legal-ocr-pdf-input/

# Check file permissions
ls -l /mnt/gcs/legal-ocr-pdf-input/*.pdf

# Ensure files have .pdf extension (case-sensitive)
```

---

## 📝 Notes

- **Headless VM:** All browser-based QA features have been removed. Download output files to local machine for visual inspection.
- **Re-run Safety:** OlmOCR's hash-based caching prevents re-processing already completed PDFs. Safe to re-run `--auto` mode.
- **Batch Size:** Default of 5 PDFs per batch balances throughput and memory usage on L4 GPUs. Adjust based on document complexity.
- **Watch Mode:** Intended for periodic processing, not real-time monitoring. Use appropriate `--watch-interval` for your use case.
- **Lock File:** Automatically cleaned up on normal exit. If process crashes, may need manual removal.
