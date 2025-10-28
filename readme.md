Absolutely — here’s a complete, production-grade **`README.md`** you can drop straight into your repo.
It’s written in a clear, developer-facing tone and covers setup, architecture, workflow, and QA guidance — perfect for onboarding others or documenting your own stack.

---

# 🧠 Legal LLM OCR → RAG Pipeline (OlmOCR + Docling + Haystack)

> End-to-end system for transforming scanned legal documents (deeds, assignments, exhibits)
> into a searchable, layout-preserving Retrieval-Augmented Generation (RAG) knowledge base.

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

## ⚙️ Prerequisites

* Python ≥ 3.10

* `conda activate olmocr-optimized` or similar environment

* Installed dependencies:

  ```bash
  pip install pandoc markdown openai haystack-ai docling sentence-transformers
  ```

* `OPENAI_API_KEY` exported in your environment.

---

## 🧭 End-to-End Workflow

### 1️⃣ Input

Place raw PDFs in:

```
app/samples/
```

### 2️⃣ OCR Extraction

Run OlmOCR to generate Markdown + JSONL:

```bash
python olmocr_pipeline/process_pdf.py app/samples/*.pdf --summary --qa
```

Output:

```
rag_staging/
 ├── jsonl/           # per-page OCR results
 ├── markdown/        # raw plain Markdown
```

### 3️⃣ Merge & Normalize

Combine per-page JSONL into layout-preserving outputs:

```bash
python utils/combine_olmocr_outputs.py rag_staging/jsonl/*.jsonl --html --md
```

Produces:

```
rag_staging/
 ├── html/*.merged.html
 ├── markdown_merged/*.merged.md
 └── reports/ocr_merge_summary.json
```

### 4️⃣ QA Dashboard

Generate and open dashboard:

```bash
python utils/generate_ocr_dashboard.py
open rag_staging/reports/index.html
```

See page counts, empty-page ratios, and links to previews.

### 5️⃣ Manual QA / Preview

Visual check of layout fidelity:

```bash
python preview.py rag_staging/html/<doc>.merged.html
```

Confirm tables, exhibits, and signatures look correct.

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
├── app/
│   └── samples/                # raw PDFs
├── olmocr_pipeline/            # OCR scripts & model runner
├── rag_staging/
│   ├── jsonl/                  # raw OCR JSONL
│   ├── markdown/               # raw MD
│   ├── html/                   # merged HTML
│   ├── markdown_merged/        # merged MD
│   └── reports/                # QA summaries + dashboard
├── utils/
│   ├── combine_olmocr_outputs.py
│   ├── generate_ocr_dashboard.py
│   └── preview.py
└── main.py                     # RAG entrypoint
```

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
