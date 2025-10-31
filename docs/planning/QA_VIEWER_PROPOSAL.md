# QA Viewer Implementation Proposal

## Overview
Build a minimal browser-based PDF/Markdown comparison viewer for QA'ing ~100 processed documents.

---

## Architecture

```
Your Laptop                    GCP Machine (GPU/CPU)
┌──────────────┐              ┌─────────────────────┐
│              │              │                     │
│  Browser     │  SSH Tunnel  │  Flask App          │
│  localhost:  │◄─────────────┤  :5000              │
│  5000        │              │  ├─ Serves PDFs     │
│              │              │  ├─ Renders MD      │
│              │              │  └─ Manifest CSV    │
└──────────────┘              └─────────────────────┘
                                       │
                                       ▼
                              ┌─────────────────────┐
                              │  /mnt/gcs/          │
                              │  ├─ pdf-input/      │
                              │  ├─ manifests/      │
                              │  └─ markdown/       │
                              └─────────────────────┘
```

**Key Decision**: Run Flask on GCP machine (where GCS is mounted), access via SSH tunnel from your laptop.

---

## Tech Stack

### Backend (Python)
```bash
flask          # Web framework (~500 KB)
pandas         # CSV parsing (already installed)
markdown       # MD → HTML (~100 KB)
```

**Total new dependencies**: 2 packages, ~1 MB

### Frontend (CDN - Zero Install)
```html
<!-- Tailwind CSS - Styling -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- Alpine.js - Reactive UI (15 KB) -->
<script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js"></script>
```

**Why Alpine.js?**
- Ultra-lightweight (15 KB)
- No build step, no npm, no webpack
- Perfect for simple interactivity (search, filter, sort)
- HTML-first (keeps code readable)

**Total CDN assets**: ~18 KB

---

## Features

### MVP (Now)
1. ✅ **File picker** (left sidebar) - clickable list from manifest CSV
2. ✅ **PDF viewer** (center) - browser's native PDF viewer
3. ✅ **Markdown viewer** (right) - rendered HTML
4. ✅ **Search files** - filter by filename
5. ✅ **Filter by status** - All / Processed / Pending / Quarantined
6. ✅ **Sort options** - By name, pages, duration, tokens
7. ✅ **Metadata card** - Show manifest data (collapsible)
8. ✅ **Error messages** - Display quarantine errors
9. ✅ **Stats summary** - "81 processed, 23 pending, 1 error"

### Deferred (Easy to Add Later)
- Page navigation (jump to PDF page)
- Text search/highlight within panels
- Sync scrolling between PDF/MD
- Enrichment view (entities, embeddings - Phase 3)
- Download markdown button
- Batch approve/reject workflow

---

## UI Layout

```
┌──────────────────────────────────────────────────────────────┐
│ 📄 PDF/Markdown QA Viewer        [81/104 processed]         │
├────────────────┬─────────────────────┬───────────────────────┤
│                │                     │                       │
│ 🔍 Search...   │  📄 PDF Preview     │  📝 Markdown Preview  │
│ Sort: Pages ▼  │                     │                       │
│ Filter: All ▼  │                     │                       │
│                │                     │                       │
│ ✅ doc1 (1pg)  │  [Browser PDF]      │  # Title              │
│ ❌ doc2 (err)  │                     │                       │
│ ✅ doc3 (5pg)  │  (Scroll, zoom,     │  Extracted text...    │
│ ⏳ doc4 (pend) │   search built-in)  │                       │
│ ✅ doc5 (18pg) │                     │  | Table | Data |     │
│                │                     │                       │
│ [Metadata ▼]   │                     │                       │
│ Pages: 18      │                     │                       │
│ Duration: 178s │                     │                       │
│ Tokens: 8.2k   │                     │                       │
└────────────────┴─────────────────────┴───────────────────────┘
```

---

## Data Source: Manifest CSV

**Why manifest over filesystem scanning?**

| Approach | Metadata | Speed | Errors | Extensible |
|----------|----------|-------|--------|------------|
| **Filesystem scan** | ❌ None | Slower | ❌ No | Limited |
| **Manifest CSV** | ✅ Rich | Fast | ✅ Yes | Easy |

**Manifest provides:**
- File status (success, quarantined, pending)
- Page count, duration, tokens
- Processor type (olmocr-2, docling)
- Error messages for failures
- Confidence scores
- Processing timestamps

---

## File Structure

```
scripts/
  qa_viewer.py              # Flask backend (~250 lines)
  templates/
    viewer.html             # Single HTML template (~200 lines)
```

**Total**: 2 files, ~450 lines of code

---

## Flask Routes

```python
GET  /                            # Main UI (loads viewer.html)
GET  /api/files                   # JSON: manifest data
GET  /pdf/<file_hash>             # Serve PDF from GCS
GET  /md/<file_hash>              # Serve rendered Markdown
GET  /api/file/<file_hash>/meta   # File metadata (for detail card)
```

---

## Implementation Steps

1. **Create Flask backend** (~1 hour)
   - Load manifest CSV on startup (pandas)
   - Create 5 routes (home, API, PDF, MD, meta)
   - Serve files from `/mnt/gcs/` paths
   - Handle file hashing for URLs

2. **Create HTML template** (~1 hour)
   - Three-column layout (Tailwind grid)
   - Alpine.js for search/filter/sort state
   - PDF iframe + markdown div
   - Collapsible metadata card

3. **Wire up interactivity** (~30 min)
   - File selection updates URL hash
   - Search filters file list reactively
   - Sort/filter dropdowns work
   - Metadata card toggles open/closed

4. **Test & polish** (~30 min)
   - Load a few PDFs, verify rendering
   - Test search, filter, sort combinations
   - Responsive sizing
   - Error handling for missing files

**Total estimated time: ~3 hours**

---

## Usage

```bash
# On GCP machine (GPU or CPU)
conda activate pdf-rag
pip install flask markdown  # If not already installed
python scripts/qa_viewer.py

# Server starts on http://0.0.0.0:5000
```

```bash
# On your laptop - create SSH tunnel
gcloud compute ssh <machine-name> --zone=<zone> -- -L 5000:localhost:5000

# Open browser
open http://localhost:5000
```

---

## Extension Points (Future)

### Phase 3 - Enrichment View

Add new route:
```python
GET  /api/file/<hash>/enrichment  # Return entities, embeddings, JSONL
```

Add UI toggle:
- **[View: Source]** - PDF + MD (current)
- **[View: Enrichment]** - Entities + metadata + JSONL chunks

### Other Easy Additions
- **Download buttons** - Export markdown or JSONL
- **Batch operations** - Select multiple files, approve/reject
- **Document comparison** - Side-by-side diff of two documents
- **Export filtered list** - Export current view to CSV/JSON
- **Pagination** - Handle 1000+ documents efficiently

---

## Why This Stack?

| Choice | Rationale |
|--------|-----------|
| **Flask** | Minimal, standard, easy to extend |
| **Tailwind (CDN)** | Beautiful UI, no build step, 3 KB |
| **Alpine.js (CDN)** | Reactive UI without React complexity |
| **Pandas** | Already installed, perfect for CSV |
| **Manifest-driven** | Rich metadata vs filesystem scanning |
| **Single file backend** | Easy to maintain, iterate, extend |
| **Native PDF viewer** | Zero dependencies, full zoom/search |

---

## Tradeoffs

### ✅ Pros
- Minimal dependencies (~1 MB new packages)
- No build step (CDN for frontend)
- Fast development (~3 hours)
- Easy to extend (enrichment view, filters)
- Rich metadata from manifest
- Works with GCS-mounted files (no copying)

### ⚠️ Cons
- Requires Flask server (can't be pure static HTML)
- Requires SSH tunnel to access from laptop
- Alpine.js is less common than React (but simpler)

---

## Success Criteria

**MVP is complete when:**
1. ✅ Can view any PDF + Markdown side-by-side
2. ✅ Can search files by name
3. ✅ Can filter by status (processed/pending/error)
4. ✅ Can sort by pages, duration, name
5. ✅ Can see metadata for selected file
6. ✅ Can see error messages for quarantined files
7. ✅ Runs on GCP machine, accessible via SSH tunnel

---

## Timeline

- **Setup** (5 min): Install flask, markdown
- **Backend** (1 hour): Flask routes + manifest loading
- **Frontend** (1 hour): HTML template + Tailwind layout
- **Interactivity** (30 min): Alpine.js wiring
- **Testing** (30 min): Load real files, verify features

**Total: ~3 hours to working MVP**

---

## Questions Before We Start?

1. Does the tech stack (Flask + Tailwind + Alpine.js) make sense?
2. Are the MVP features sufficient for your QA needs?
3. Any concerns about the manifest-driven approach?
4. Want to adjust scope before we code?

---

**Status**: Awaiting approval to proceed with implementation
**Created**: 2025-10-31
**Estimated Completion**: ~3 hours from start
