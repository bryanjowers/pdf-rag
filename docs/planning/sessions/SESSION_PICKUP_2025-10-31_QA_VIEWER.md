# Session Pickup - QA Viewer Implementation

**Date:** 2025-10-31
**Status:** Plan approved, ready to implement
**Estimated Time:** ~3 hours 20 minutes

---

## 🎯 Objective

Build a standalone Flask-based web viewer for QA'ing ~100 processed PDF documents by comparing original PDFs with extracted Markdown side-by-side.

---

## ✅ Decisions Made

### 1. **Tech Stack - APPROVED**
- **Backend:** Flask (Python)
- **Frontend:** Tailwind CSS + Alpine.js (CDN, no build step)
- **Access:** SSH tunnel from laptop to GCP machine
- **Data Source:** Manifest CSV (most recent)

### 2. **Project Structure - STANDALONE MODULE**
```
qa_viewer/                    # NEW standalone module
├── app.py                   # Flask application (~250 lines)
├── templates/
│   └── viewer.html          # Single-page UI (~200 lines)
└── README.md               # Usage documentation
```

**Rationale:** QA Viewer is a standalone tool, not part of the processing pipeline. It has its own lifecycle, dependencies, and could grow independently.

### 3. **Manifest Handling - MOST RECENT ONLY**

**Current manifest files:**
```
manifest_20251030_193924_u9x2.csv  (6 records)
manifest_20251030_202726_2p1z.csv  (6 records)
manifest_20251030_203033_pxxl.csv  (6 records)
manifest_20251030_203450_dmfd.csv  (6 records)
manifest_20251030_204532_4vzl.csv  (7 records)
manifest_20251031_010004_t00i.csv  (104 records) ← LOAD THIS ONE
```

**Decision:** Load most recent manifest by default (`manifest_20251031_010004_t00i.csv`)
- Contains 104 records (most comprehensive)
- Earlier manifests were test batches (5-7 records each)
- Avoids duplicate entries

---

## 📋 Implementation Plan

### MVP Features
1. ✅ **File picker** (left sidebar) - clickable list from manifest CSV
2. ✅ **PDF viewer** (center) - browser's native PDF viewer
3. ✅ **Markdown viewer** (right) - rendered HTML
4. ✅ **Search files** - filter by filename
5. ✅ **Filter by status** - All / Success / Quarantined / Pending
6. ✅ **Sort options** - By name, pages, duration, tokens
7. ✅ **Metadata card** - Show manifest data (collapsible)
8. ✅ **Error messages** - Display quarantine errors
9. ✅ **Stats summary** - "81 processed, 23 pending, 1 error"

### Implementation Steps

#### 1. Create Project Structure (5 min)
```bash
mkdir -p qa_viewer/templates
touch qa_viewer/app.py
touch qa_viewer/templates/viewer.html
touch qa_viewer/README.md
```

#### 2. Implement Flask Backend - app.py (1 hour)

**Dependencies to install:**
```bash
conda activate pdf-rag
pip install flask markdown
```

**Flask Routes:**
```python
GET  /                           # Serve main UI (viewer.html)
GET  /api/files                  # JSON: manifest data (all files)
GET  /pdf/<file_hash>            # Serve original PDF from GCS
GET  /md/<file_hash>             # Serve rendered Markdown as HTML
GET  /api/file/<file_hash>/meta  # File metadata (detailed)
```

**Key Backend Features:**
- Load most recent manifest CSV on startup (sorted by timestamp)
- Create file hash → path mapping for quick lookup
- Serve PDFs from `/mnt/gcs/legal-ocr-pdf-input/`
- Serve Markdown from `/mnt/gcs/legal-ocr-results/rag_staging/markdown/`
- Handle missing files gracefully (404 with helpful errors)

**Manifest Loading Logic:**
```python
manifest_dir = Path("/mnt/gcs/legal-ocr-results/manifests/")
manifest_files = sorted(manifest_dir.glob("manifest_*.csv"), reverse=True)
latest_manifest = manifest_files[0]  # Most recent first
df = pd.read_csv(latest_manifest)
```

#### 3. Implement Frontend - viewer.html (1 hour)

**Layout:** Three-column responsive design using Tailwind CSS
- **Left sidebar (30%)**: File picker with search/filter/sort
- **Center panel (35%)**: PDF viewer (native browser iframe)
- **Right panel (35%)**: Markdown viewer (rendered HTML)

**CDN Dependencies:**
```html
<script src="https://cdn.tailwindcss.com"></script>
<script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
```

**Alpine.js State:**
```javascript
{
  files: [],              // All files from manifest
  filteredFiles: [],      // After search/filter/sort
  selectedFile: null,     // Currently selected file
  searchQuery: '',        // Text search input
  statusFilter: 'all',    // Current status filter
  sortBy: 'name'         // Current sort option
}
```

#### 4. Wire Up Interactivity (30 min)

**Features to implement:**
- File click → Load PDF + Markdown
- Search input → Filter file list reactively
- Filter/sort dropdowns → Update filtered list
- Metadata toggle → Expand/collapse details
- Stats calculation → Count success/quarantined/pending

#### 5. Test & Polish (30 min)

**Testing checklist:**
- [ ] Load viewer in browser via SSH tunnel
- [ ] Select files from list - verify PDF + Markdown load
- [ ] Test search functionality (partial matches)
- [ ] Test all status filters (All, Success, Quarantined)
- [ ] Test all sort options (Name, Pages, Duration, Tokens)
- [ ] Verify metadata card displays correctly
- [ ] Test error handling (missing files)
- [ ] Check responsive layout (different window sizes)
- [ ] Verify quarantine error messages display

#### 6. Documentation (15 min)

**Create qa_viewer/README.md:**
- Purpose and features
- Installation steps
- Usage instructions (server + SSH tunnel)
- Architecture diagram
- Extension points

**Update main README.md:**
- Add QA Viewer section
- Link to qa_viewer/README.md

---

## 📊 Manifest Schema (17 columns)

| Column | Type | Purpose | Example |
|--------|------|---------|---------|
| `doc_id` | string | Document identifier | `unknown` |
| `file_path` | string | Full input path | `/mnt/gcs/legal-ocr-pdf-input/...` |
| `file_name` | string | Original filename | `110-532_WD_Annie...pdf` |
| `file_type` | string | File extension | `pdf`, `docx`, `xlsx` |
| `processor` | string | Handler used | `olmocr-2`, `olmocr`, `docling` |
| `status` | enum | Success/failed/quarantined | `success`, `quarantined`, `failed` |
| `page_count` | int | Pages (PDFs only) | `1`, `4`, `14` |
| `chunks_created` | int | Text chunks generated | `1`, `2`, `3` |
| `processing_duration_ms` | int | Processing time | `847`, `1285` |
| `char_count` | int | Output characters | `3073`, `21935` |
| `estimated_tokens` | int | Token estimate | `562`, `3711` |
| `hash_sha256` | string | Input file hash | `` (currently empty) |
| `batch_id` | string | Batch identifier | `` (currently empty) |
| `processed_at` | timestamp | ISO 8601 timestamp | `2025-10-31T03:16:44Z` |
| `warnings` | string | Semicolon-separated warnings | `` |
| `error` | string | Error message if failed | `OlmOCR did not produce...` |
| `confidence_score` | float | Quality score 0.0-1.0 | `1.0` |

---

## 🎯 Success Criteria

**MVP is complete when:**
1. ✅ Can view any PDF + Markdown side-by-side
2. ✅ Can search files by name (reactive filtering)
3. ✅ Can filter by status (Success / Quarantined / Pending)
4. ✅ Can sort by Name, Pages, Duration, Tokens
5. ✅ Can see detailed metadata for selected file
6. ✅ Can see error messages for quarantined files
7. ✅ Stats summary displays correctly
8. ✅ Runs on GCP machine, accessible via SSH tunnel from laptop

---

## ⏱️ Timeline Estimate

- **Project setup:** 5 minutes
- **Flask backend:** 1 hour
- **HTML template:** 1 hour
- **Interactivity wiring:** 30 minutes
- **Testing:** 30 minutes
- **Documentation:** 15 minutes

**Total: ~3 hours 20 minutes**

---

## 🚀 Quick Start (Next Session)

```bash
# 1. Activate environment
conda activate pdf-rag

# 2. Install dependencies (if not already installed)
pip install flask markdown

# 3. Create project structure
mkdir -p qa_viewer/templates

# 4. Start implementation
# - Create qa_viewer/app.py (Flask backend)
# - Create qa_viewer/templates/viewer.html (Frontend)
# - Create qa_viewer/README.md (Documentation)

# 5. Test locally
cd /home/bryanjowers/pdf-rag
python qa_viewer/app.py

# 6. On laptop - create SSH tunnel
gcloud compute ssh <machine-name> -- -L 5000:localhost:5000

# 7. Open browser
open http://localhost:5000
```

---

## 📁 Key File Paths

**GCS Mounts:**
- Input PDFs: `/mnt/gcs/legal-ocr-pdf-input/`
- Manifests: `/mnt/gcs/legal-ocr-results/manifests/`
- Markdown: `/mnt/gcs/legal-ocr-results/rag_staging/markdown/`

**Code References:**
- Manifest generation: `olmocr_pipeline/utils_manifest.py`
- Batch ID generation: `olmocr_pipeline/utils_batch.py`
- Manifest writing: `olmocr_pipeline/utils_processor.py:180`

---

## 🔮 Future Extensions (Not in MVP)

- Page navigation (jump to specific PDF page)
- Sync scrolling between PDF and Markdown
- Enrichment view (entities, embeddings from JSONL)
- Download buttons (export Markdown/JSONL)
- Batch operations (approve/reject multiple files)
- Manifest selector dropdown (switch between batches)
- Text search/highlight within panels

---

## 📌 Notes

- **Tech stack approved:** Flask + Tailwind + Alpine.js
- **Standalone module:** Keeps QA viewer isolated from pipeline
- **Manifest strategy:** Load most recent by default (104 records)
- **Zero build step:** All frontend dependencies via CDN
- **Minimal dependencies:** Only need to install flask + markdown

---

**Status:** Ready to implement
**Next Step:** Create project structure and start building
**Estimated Completion:** ~3 hours from start

---

**Related Documents:**
- [QA_VIEWER_PROPOSAL.md](../QA_VIEWER_PROPOSAL.md) - Original proposal
- [ROADMAP.md](../ROADMAP.md) - Project roadmap (add QA Viewer item)
