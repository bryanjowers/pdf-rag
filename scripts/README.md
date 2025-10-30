# Scripts Directory

This directory contains all utility scripts for the PDF-RAG pipeline.

## Directory Structure

```
scripts/
├── README.md                    # This file
├── maintenance/                 # System maintenance and setup
├── testing/                     # Performance and feature testing
├── analysis/                    # Data analysis and inspection
│
├── process_documents.py         # 🔥 MAIN: Process PDFs through pipeline
├── rebuild_inventory.py         # Build inventory of input files
├── load_to_qdrant.py           # Load embeddings to vector DB
├── query_cli.py                # Query RAG system via CLI
└── enrich_from_markdown.py     # Add entities/embeddings to existing markdown
```

---

## Production Scripts (scripts/)

These are the main scripts you'll use for production operations.

### 🔥 `process_documents.py`
**Main processing pipeline** - Converts PDFs to searchable JSONL with entities & embeddings.

```bash
# Process all PDFs automatically
python scripts/process_documents.py --auto

# Process specific file types
python scripts/process_documents.py --auto --file-types pdf

# Process only digital PDFs
python scripts/process_documents.py --auto --pdf-type digital

# Limit number of files
python scripts/process_documents.py --auto --limit 10

# Skip entity extraction and embeddings (faster)
python scripts/process_documents.py --auto --ingest-only
```

**Features:**
- Auto-classifies PDFs as digital or scanned
- Parallel processing for digital PDFs (4 workers, ~3x speedup)
- Automatic retry and quarantine on failures
- Generates: markdown, JSONL with entities & embeddings
- Creates processing manifests and success markers

### `rebuild_inventory.py`
Build/rebuild inventory of all input files with classification.

```bash
# Build fresh inventory
python scripts/rebuild_inventory.py

# Force rebuild (ignore cache)
python scripts/rebuild_inventory.py --force
```

**Output:** `inventory/inventory.csv` with all files classified

### `load_to_qdrant.py`
Load JSONL embeddings into Qdrant vector database.

```bash
# Load all JSONL files
python scripts/load_to_qdrant.py

# Specify collection name
python scripts/load_to_qdrant.py --collection legal_docs
```

**Requirements:** Qdrant must be running on `localhost:6333`

### `query_cli.py`
Interactive CLI for querying the RAG system.

```bash
# Start interactive query session
python scripts/query_cli.py

# Single query
python scripts/query_cli.py --query "Find all drilling permits"
```

### `enrich_from_markdown.py`
Add entities and embeddings to existing markdown files (useful for re-enrichment).

```bash
# Enrich all markdown files
python scripts/enrich_from_markdown.py

# Enrich specific directory
python scripts/enrich_from_markdown.py --input-dir /path/to/markdown
```

---

## Maintenance Scripts (scripts/maintenance/)

### `clean_slate.sh`
**Complete system reset** - Clears all processed data while preserving input PDFs.

```bash
# Run clean slate operation
./scripts/maintenance/clean_slate.sh
# Type "DELETE" when prompted
```

**Deletes:**
- All processed outputs (markdown, JSONL, HTML)
- All inventory, manifests, logs
- All Qdrant collections

**Preserves:**
- Input PDFs (100% safe)
- Configuration files
- Pipeline code

**Use when:** Starting fresh or testing from scratch

### `setup_env.sh`
Environment setup and dependency installation.

```bash
# Setup conda environment
./scripts/maintenance/setup_env.sh
```

---

## Testing Scripts (scripts/testing/)

### Performance Testing

#### `test_4workers.py`
Quick test comparing 2 vs 4 worker performance.

```bash
python scripts/testing/test_4workers.py
```

#### `test_parallel_speedup.py`
Comprehensive test of 1/2/4 worker configurations.

```bash
python scripts/testing/test_parallel_speedup.py
```

#### `debug_parallel_performance.py`
Detailed profiling of parallel processing bottlenecks.

```bash
python scripts/testing/debug_parallel_performance.py [workers] [files]
# Example: python scripts/testing/debug_parallel_performance.py 4 10
```

#### `test_classifier_performance.py`
Benchmark PDF classification speed.

```bash
python scripts/testing/test_classifier_performance.py
```

### Feature Testing

#### `test_new_classifier.py`
Test updated PDF classifier logic.

```bash
python scripts/testing/test_new_classifier.py
```

#### `test_digital_vs_scanned.py`
Verify digital vs scanned PDF classification.

```bash
python scripts/testing/test_digital_vs_scanned.py [pdf_path]
```

#### `test_entity_extraction.py`
Test entity extraction on sample PDFs.

```bash
python scripts/testing/test_entity_extraction.py
```

#### `test_entity_extraction_fast.py`
Quick entity extraction test (single file).

```bash
python scripts/testing/test_entity_extraction_fast.py [pdf_path]
```

#### `test_embeddings_qdrant.py`
Test embedding generation and Qdrant upload.

```bash
python scripts/testing/test_embeddings_qdrant.py
```

### Bbox Testing

#### `test_bbox_extraction.py`
Test bounding box extraction from PDFs.

```bash
python scripts/testing/test_bbox_extraction.py [pdf_path]
```

#### `test_scanned_bbox.py` / `test_scanned_bbox_fix.py`
Test bbox extraction for scanned PDFs (with fix).

```bash
python scripts/testing/test_scanned_bbox.py [pdf_path]
```

### Page Extraction Testing

#### `test_page_extraction.py`
Test individual page extraction.

```bash
python scripts/testing/test_page_extraction.py [pdf_path]
```

#### `test_page_extraction_fast.py`
Quick page extraction test.

```bash
python scripts/testing/test_page_extraction_fast.py [pdf_path] [page_num]
```

### Debug Scripts

#### `debug_inventory_performance.py`
Profile inventory building performance.

```bash
python scripts/testing/debug_inventory_performance.py
```

---

## Analysis Scripts (scripts/analysis/)

### `analyze_page_coverage.py`
Analyze digital vs scanned page coverage in PDFs.

```bash
python scripts/analysis/analyze_page_coverage.py
```

### `compare_content.py`
Compare output content between different processing runs.

```bash
python scripts/analysis/compare_content.py [file1] [file2]
```

### `inspect_bbox.py`
Inspect bounding box data in JSONL files.

```bash
python scripts/analysis/inspect_bbox.py [jsonl_path]
```

### `spot_check_entities.py`
Quick check of entity extraction quality.

```bash
python scripts/analysis/spot_check_entities.py
```

### `olmocr_generation_analysis.py`
Analyze OlmOCR generation quality and performance.

```bash
python scripts/analysis/olmocr_generation_analysis.py
```

### `verify_qdrant_persistence.py`
Verify Qdrant data persists after restart.

```bash
python scripts/analysis/verify_qdrant_persistence.py
```

---

## Quick Start Workflow

### First Time Setup
```bash
# 1. Setup environment
./scripts/maintenance/setup_env.sh

# 2. Build inventory
python scripts/rebuild_inventory.py

# 3. Process documents
python scripts/process_documents.py --auto

# 4. Load to Qdrant
python scripts/load_to_qdrant.py

# 5. Query system
python scripts/query_cli.py
```

### Clean Slate & Restart
```bash
# 1. Clean all processed data
./scripts/maintenance/clean_slate.sh

# 2. Rebuild inventory
python scripts/rebuild_inventory.py

# 3. Process documents
python scripts/process_documents.py --auto
```

### Testing Performance
```bash
# Quick 2 vs 4 worker comparison
python scripts/testing/test_4workers.py

# Full benchmark
python scripts/testing/test_parallel_speedup.py
```

---

## Configuration

All scripts use [`config/default.yaml`](../config/default.yaml) for configuration.

Key settings:
- `processors.digital_pdf_workers: 4` - Parallel workers (optimized)
- `entity_extraction.enabled: true` - Enable entity extraction
- `embeddings.enabled: true` - Enable embedding generation
- `qdrant.enabled: false` - Auto-upload to Qdrant (set to true if desired)

---

## Common Issues

### "No PDFs found"
- Check GCS mount: `df -h | grep gcs`
- Rebuild inventory: `python scripts/rebuild_inventory.py`

### "Qdrant not running"
- Start Qdrant: `docker-compose up -d qdrant`
- Check status: `curl http://localhost:6333/collections`

### "Module not found"
- Activate environment: `conda activate olmocr-optimized`
- Install dependencies: `pip install -r requirements.txt`

---

## See Also

- [Main README](../readme.md) - Project overview
- [Configuration Guide](../docs/guides/SETUP_INFRASTRUCTURE.md) - Setup instructions
- [Performance Docs](../docs/technical/PARALLELIZATION_OPTIMIZATION_COMPLETE.md) - Optimization details
- [Query Guide](../docs/guides/QUERY_GUIDE.md) - How to query the RAG system
