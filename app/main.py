# === main.py — Minimal RAG (Docling + Haystack + OpenAI Direct) ===
from docling.document_converter import DocumentConverter
from haystack import Document
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.embedders import SentenceTransformersTextEmbedder
from haystack.components.retrievers import InMemoryEmbeddingRetriever
from openai import OpenAI
import os
from pathlib import Path

# -------------------------------------------------------------------
# CONFIGURATION
# -------------------------------------------------------------------
PDF_DIR = Path("samples")
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
OPENAI_MODEL = "gpt-4o-mini"
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_KEY)

# -------------------------------------------------------------------
# STEP 1: Parse PDFs via Docling
# -------------------------------------------------------------------
converter = DocumentConverter()
docs = []

if not PDF_DIR.exists():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📂 Created folder {PDF_DIR}. Place PDFs there and rerun.")

for pdf in PDF_DIR.glob("*.pdf"):
    try:
        result = converter.convert(str(pdf))
        text = result.text if hasattr(result, "text") else str(result)
        docs.append(Document(content=text, meta={"source": pdf.name}))
        print(f"✅ Parsed {pdf.name}")
    except Exception as e:
        print(f"⚠️  Skipped {pdf.name}: {e}")

if not docs:
    print("⚠️  No PDFs found in samples/. Add some and rerun.")
    exit(0)

# -------------------------------------------------------------------
# STEP 2: Embed + Store
# -------------------------------------------------------------------
store = InMemoryDocumentStore()

# Initialize embedder and warm up once (loads model into memory)
embedder = SentenceTransformersTextEmbedder(model=EMBED_MODEL)
embedder.warm_up()  # ✅ Required in Haystack ≥2.18

# Compute embeddings for each parsed document before writing to store
print("🔢 Embedding documents...")
for d in docs:
    emb = embedder.run(text=d.content)   # generate embedding for doc text
    d.embedding = emb["embedding"]       # attach vector to the Document object

# Now write embedded documents into the in-memory store
store.write_documents(docs)
retriever = InMemoryEmbeddingRetriever(document_store=store)

print(f"📚 Indexed {len(docs)} document(s) with embeddings.")
print("\n💬 Ready! Ask questions about your PDFs (type 'exit' to quit).")

# -------------------------------------------------------------------
# STEP 3: Interactive Q&A Loop
# -------------------------------------------------------------------
MAX_CONTEXT_CHARS = 12000   # prevent token overflow
TOP_K = 3                   # number of retrieved docs

while True:
    q = input("\n❓ Question: ").strip()
    if q.lower() in {"exit", "quit"}:
        print("👋 Goodbye!")
        break

    try:
        # 1️⃣ Embed query + retrieve context
        embed_output = embedder.run(text=q)
        retrieved = retriever.run(query_embedding=embed_output["embedding"], top_k=TOP_K)
        docs_found = retrieved["documents"]

        if not docs_found:
            print("⚠️  No relevant passages found.")
            continue

        # 2️⃣ Build context prompt
        context = "\n\n---\n\n".join(d.content for d in docs_found)
        context = context[:MAX_CONTEXT_CHARS]  # truncate to fit token window

        print("\n📄 Top retrieved sources:")
        for d in docs_found:
            print(f"  - {d.meta.get('source', 'unknown')}")

        prompt = (
            "You are a helpful legal assistant.\n"
            "Use only the context below to answer.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {q}\n\n"
            "Answer:"
        )

        # 3️⃣ Call OpenAI directly
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )

        print("\n🧠 Answer:\n", completion.choices[0].message.content)

    except Exception as e:
        print(f"⚠️  Error: {e}")
