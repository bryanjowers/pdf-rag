# QA Viewer

**Flask-based web interface for quality assurance of PDF-RAG pipeline outputs**

View original PDFs side-by-side with extracted Markdown to validate document processing quality.

---

## Features

- **Side-by-side comparison** - Original PDF and extracted Markdown in split view
- **File browser** - Browse all processed files from manifest CSV
- **Search & filter** - Find files by name, filter by status (success/quarantined/pending)
- **Sort options** - Sort by name, page count, processing duration, or tokens
- **Metadata display** - View detailed processing metadata for each file
- **Error reporting** - Display quarantine errors and warnings inline
- **Stats summary** - Overview of processing success rate

---

## Quick Start

### Prerequisites

1. **GCS buckets mounted** (required for file access):
   ```bash
   # Check if buckets are mounted
   ls /mnt/gcs/legal-ocr-pdf-input/
   ls /mnt/gcs/legal-ocr-results/manifests/
   ```

2. **Flask and markdown installed**:
   ```bash
   pip install flask markdown
   ```
   (Already in `requirements.txt` for new installs)

### Running the Viewer

1. **Start the Flask server**:
   ```bash
   cd /home/bryanjowers/pdf-rag
   python qa_viewer/app.py
   ```

   Server will start on `http://0.0.0.0:5000`

2. **Create SSH tunnel from your laptop**:
   ```bash
   gcloud compute ssh <machine-name> -- -L 5000:localhost:5000
   ```

3. **Open in browser**:
   ```
   http://localhost:5000
   ```

---

## Architecture

```
┌──────────────────────────────────────────────────┐
│                   Browser (Laptop)               │
│           http://localhost:5000                  │
└─────────────────┬────────────────────────────────┘
                  │ SSH Tunnel
                  ▼
┌──────────────────────────────────────────────────┐
│              GCP VM (Flask Server)               │
│           Running on 0.0.0.0:5000                │
└─────────────────┬────────────────────────────────┘
                  │
        ┌─────────┴──────────┐
        ▼                    ▼
┌──────────────┐    ┌────────────────────┐
│ Manifest CSV │    │   GCS Buckets      │
│ (metadata)   │    │ - Input PDFs       │
│              │    │ - Markdown outputs │
└──────────────┘    └────────────────────┘
```

### File Paths

The QA Viewer expects these GCS mount paths:

| Resource | Path |
|----------|------|
| **Manifests** | `/mnt/gcs/legal-ocr-results/manifests/manifest_*.csv` |
| **Input PDFs** | `/mnt/gcs/legal-ocr-pdf-input/` |
| **Markdown** | `/mnt/gcs/legal-ocr-results/rag_staging/markdown/` |

---

## API Endpoints

### `GET /`
Serve the main viewer UI (HTML page)

### `GET /api/files`
Get list of all files from the most recent manifest CSV

**Response:**
```json
{
  "files": [
    {
      "file_name": "110-532_WD_Annie.pdf",
      "file_type": "pdf",
      "status": "success",
      "page_count": 4,
      "chunks_created": 2,
      "processing_duration_ms": 1285,
      "estimated_tokens": 3711,
      "processor": "olmocr-2",
      "error": "",
      "warnings": ""
    }
  ],
  "total": 104
}
```

### `GET /api/file/<file_name>/meta`
Get detailed metadata for a specific file

### `GET /pdf/<file_name>`
Serve original PDF file for browser's native PDF viewer

### `GET /md/<file_name>`
Serve rendered Markdown as HTML with styling

---

## Usage

### Browsing Files

1. **File list** (left sidebar) shows all files from the latest manifest
2. **Click a file** to view PDF and Markdown side-by-side
3. **Search** to filter by filename (live filtering)
4. **Filter by status**:
   - All Files
   - Success Only (processed successfully)
   - Quarantined Only (failed with errors)
   - Pending Only (not yet processed)
5. **Sort files** by:
   - Name (alphabetical)
   - Pages (highest first)
   - Duration (longest processing time first)
   - Tokens (most tokens first)

### Viewing Metadata

1. **Click "Show Metadata"** in the markdown panel header
2. View detailed processing information:
   - Status, processor type
   - Page count, chunk count
   - Processing duration, token estimate
   - Error messages (for quarantined files)
   - Warnings (if any)

### QA Workflow

1. **Select a file** from the list
2. **Compare PDF (center) with Markdown (right)**
3. **Check for issues**:
   - Missing text or sections
   - Table formatting problems
   - OCR errors
   - Chunking issues
4. **Review metadata** for processing details
5. **For errors**: Check error message in metadata panel
6. **Move to next file** in the list

---

## Troubleshooting

### "No manifest files found"

**Problem:** Flask server can't find manifest CSV files

**Solution:**
```bash
# Check if GCS bucket is mounted
ls /mnt/gcs/legal-ocr-results/manifests/

# If not mounted, mount the bucket (see infrastructure docs)
# Or update app.py MANIFEST_DIR path if files are elsewhere
```

### "Failed to load PDF"

**Problem:** PDF file not found or inaccessible

**Causes:**
- GCS bucket not mounted (`/mnt/gcs/legal-ocr-pdf-input/`)
- File path in manifest is incorrect
- File was deleted or moved

**Solution:**
```bash
# Verify GCS mount
ls /mnt/gcs/legal-ocr-pdf-input/

# Check file exists
cat /mnt/gcs/legal-ocr-results/manifests/manifest_*.csv | grep <filename>
```

### "Failed to load Markdown"

**Problem:** Markdown file not found

**Causes:**
- File not yet processed
- Processing failed (check status in file list)
- Markdown directory not accessible

**Solution:**
```bash
# Check if markdown exists
ls /mnt/gcs/legal-ocr-results/rag_staging/markdown/<filename>.md

# Check processing status in manifest
```

### Can't access from laptop

**Problem:** SSH tunnel not working

**Solution:**
```bash
# Verify Flask server is running on VM
curl http://localhost:5000

# Re-create SSH tunnel with correct machine name
gcloud compute ssh <machine-name> -- -L 5000:localhost:5000

# Verify tunnel in new terminal on laptop
curl http://localhost:5000
```

---

## Configuration

### Port

Default port: `5000`

To change, edit `qa_viewer/app.py`:
```python
app.run(host='0.0.0.0', port=5000)  # Change port here
```

### File Paths

GCS mount paths are configured at the top of `app.py`:
```python
MANIFEST_DIR = Path("/mnt/gcs/legal-ocr-results/manifests/")
INPUT_DIR = Path("/mnt/gcs/legal-ocr-pdf-input/")
MARKDOWN_DIR = Path("/mnt/gcs/legal-ocr-results/rag_staging/markdown/")
```

### Debug Mode

Debug mode is enabled by default for development:
```python
app.run(debug=True)
```

For production, set `debug=False`

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **Backend** | Flask 3.x | Web server and API |
| **Frontend** | Tailwind CSS | Styling (CDN) |
| **Interactivity** | Alpine.js | Reactive UI (CDN) |
| **PDF Viewer** | Browser native | Embedded iframe |
| **Markdown Rendering** | Python `markdown` library | Convert MD to HTML |

**Zero build step** - All frontend dependencies loaded via CDN

---

## File Structure

```
qa_viewer/
├── app.py                  # Flask backend (~250 lines)
├── templates/
│   └── viewer.html         # Single-page UI (~400 lines)
└── README.md              # This file
```

---

## Extension Points

### Future Enhancements (Not in MVP)

- **Page navigation** - Jump to specific PDF page
- **Sync scrolling** - Scroll PDF and Markdown together
- **Enrichment view** - Display entities and embeddings from JSONL
- **Download buttons** - Export Markdown/JSONL
- **Batch operations** - Approve/reject multiple files
- **Manifest selector** - Switch between different manifest files
- **Text search** - Highlight search terms within panels
- **Comparison mode** - View before/after for reprocessed files

### Adding New Features

1. **Backend changes**: Edit `qa_viewer/app.py`
   - Add new Flask routes for API endpoints
   - Modify manifest loading logic

2. **Frontend changes**: Edit `qa_viewer/templates/viewer.html`
   - Update Alpine.js `qaViewer()` function for new state
   - Add HTML elements with `x-` directives
   - Style with Tailwind utility classes

---

## Manifest Schema

The viewer loads data from manifest CSV files with these columns:

| Column | Type | Description |
|--------|------|-------------|
| `file_name` | string | Original filename |
| `file_path` | string | Full input path |
| `file_type` | string | Extension (pdf, docx, etc.) |
| `processor` | string | Handler used (olmocr-2, docling, etc.) |
| `status` | enum | success / quarantined / pending |
| `page_count` | int | Number of pages (PDFs only) |
| `chunks_created` | int | Text chunks generated |
| `processing_duration_ms` | int | Processing time in milliseconds |
| `char_count` | int | Output character count |
| `estimated_tokens` | int | Token estimate |
| `processed_at` | timestamp | ISO 8601 timestamp |
| `error` | string | Error message if failed |
| `warnings` | string | Semicolon-separated warnings |
| `confidence_score` | float | Quality score (0.0-1.0) |

---

## Development

### Local Testing (Without GCS)

For local development without GCS buckets:

1. Create mock directories:
   ```bash
   mkdir -p /tmp/qa_viewer_test/{manifests,pdfs,markdown}
   ```

2. Update paths in `app.py`:
   ```python
   MANIFEST_DIR = Path("/tmp/qa_viewer_test/manifests")
   INPUT_DIR = Path("/tmp/qa_viewer_test/pdfs")
   MARKDOWN_DIR = Path("/tmp/qa_viewer_test/markdown")
   ```

3. Add sample manifest CSV and test files

### Debugging

Flask debug mode provides:
- Auto-reload on code changes
- Interactive debugger in browser
- Detailed error pages

Access debugger PIN in terminal output:
```
* Debugger PIN: 870-299-039
```

---

## Production Deployment (Future)

For production use, consider:

1. **Use production WSGI server** (Gunicorn/uWSGI):
   ```bash
   gunicorn -w 4 -b 0.0.0.0:5000 qa_viewer.app:app
   ```

2. **Add authentication** (if exposing beyond SSH tunnel)

3. **Enable HTTPS** (if not using SSH tunnel)

4. **Add rate limiting** (if public-facing)

5. **Use reverse proxy** (Nginx/Apache)

---

## Notes

- **Standalone module** - QA Viewer is independent of the processing pipeline
- **Read-only** - Does not modify any pipeline files or data
- **Manifest-driven** - Always loads the most recent manifest CSV
- **Headless VM compatible** - Designed for SSH tunnel access
- **Minimal dependencies** - Only Flask and markdown required

---

**Created:** 2025-10-31
**Version:** MVP 1.0
**Author:** Claude (automated)
**Related:** [SESSION_PICKUP_2025-10-31_QA_VIEWER.md](../docs/planning/sessions/SESSION_PICKUP_2025-10-31_QA_VIEWER.md)
