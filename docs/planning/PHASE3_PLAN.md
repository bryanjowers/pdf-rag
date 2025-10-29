# Phase 3: RAG Pipeline Implementation Plan

> **Status:** Planning Complete | **Start Date:** TBD | **Duration:** ~16-18 weeks
>
> **Philosophy:** Achieve 95% results with pragmatic solutions. Optimize later.

---

## 📋 Executive Summary

**Phase 3 delivers a production-ready Legal RAG system** through 3 sequential demos:

1. **Demo 1+2: Smart Entity Search** (5 weeks) - Hybrid search + entity extraction + citations
2. **Demo 3: Chain-of-Title Assistant** (6-8 weeks) - Graph RAG with multi-hop reasoning
3. **Demo 4: Title Opinion Generator** (8-10 weeks) - Agentic RAG with QA verification

**Total Timeline:** 19-23 weeks (~5-6 months)

**Key Decisions:**
- ✅ **Pragmatic Stack:** OpenAI (GPT-4o-mini + embeddings) for speed → migrate to OSS later if needed
- ✅ **Bbox Strategy:** Try Docling native → fallback to page-level citations if needed
- ✅ **Merged Demos:** 1+2 combined for faster time-to-value
- ✅ **Graph DB:** Neo4j Community Edition (self-hosted)
- ✅ **Monitoring:** LangSmith (free tier) for visibility
- ❌ **Cut Scope:** Demo 5 (Governance Dashboard) removed - integrate governance throughout

---

## 🎯 North Star Alignment

**Goal:** Defensible title verification with precise legal citations

**Success Criteria:**
- ✅ Retrieve exact clauses with page + bbox coordinates
- ✅ Extract and link legal entities (parties, parcels, dates)
- ✅ Trace chain-of-title across multiple documents
- ✅ Generate draft title opinions with source citations
- ✅ Identify defects with supporting evidence

---

## 🏗️ Technology Stack (Locked In)

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Vector DB** | Qdrant | Best OSS vector store, easy local dev |
| **Graph DB** | Neo4j Community | Mature, Cypher queries, great for CoT |
| **Embeddings** | OpenAI text-embedding-3-small | Fast, cheap ($0.02/1M tokens), 1536d |
| **LLM** | GPT-4o-mini | Fast, cheap ($0.15/1M in), good quality |
| **Reranker** | bge-reranker-large | OSS, high-quality reranking |
| **BM25** | rank-bm25 | In-memory, fast lexical search |
| **Agent Framework** | LangGraph | OSS, best for agentic workflows |
| **Monitoring** | LangSmith | Free tier, great visibility |
| **Entity Extraction** | GPT-4o-mini | Fast, accurate, defer custom NER |
| **Graph Ontology** | Existing legal ontology (e.g., LKIF) | 95% solution, customize later |

**OSS Migration Path (Future):**
- Embeddings: OpenAI → `BAAI/bge-base-en-v1.5`
- LLM: GPT-4o-mini → `Llama-3.1-8B-Instruct`
- Monitoring: LangSmith → MLflow

---

## 📅 Phase Breakdown

### **Phase 2B: Closeout & Planning** (Current, 1 week)

**Objectives:**
1. ✅ Kill background processes from Phase 2 testing
2. ✅ Final validation of Phase 2 outputs (manifests, JSONL quality)
3. ✅ Document Phase 2 learnings and handoff notes
4. Design Phase 3 architecture (schema v2.3.0, system design)
5. Set up infrastructure (Qdrant, Neo4j, LangSmith)
6. Create detailed Demo 1+2 implementation plan

**Deliverables:**
- ✅ Phase 2 closure report
- Schema v2.3.0 specification (bbox, entities, metadata)
- Tech stack setup guide
- Demo 1+2 detailed task breakdown
- Week-by-week implementation plan

**Status:** ✅ Background processes cleaned up, ready for planning

---

### **Demo 1+2: Smart Entity Search** (5 weeks)

**Goal:** Enable entity-aware legal document search with precise citations

**User Story:**
> "As a title examiner, I want to find all documents where John Smith (grantor) conveyed property to Mary Johnson (grantee) between 2010-2020, with exact clause locations and page references."

**Core Features:**
1. **Hybrid Search** - BM25 + vector embeddings + reranking
2. **Entity Extraction** - Detect parties, parcels, dates, amounts
3. **Entity Filtering** - Filter results by entity attributes
4. **Precise Citations** - Page + bbox coordinates (or page-only fallback)
5. **Simple UI** - Streamlit demo for queries

**Technical Components:**

#### Week 1: Foundation
- Set up Qdrant (Docker or local)
- Design schema v2.3.0 with bbox + entity fields
- Spike: Test Docling bbox extraction (1 day max)
- Decision: Native bbox OR page-level fallback
- Set up LangSmith project

#### Week 2: Ingestion Pipeline
- Extend Phase 2 output to include:
  - Bounding boxes (if Docling supports)
  - Entity extraction per chunk (GPT-4o-mini)
  - Entity normalization (lowercase, strip, dedupe)
- Embed chunks with OpenAI embeddings
- Load into Qdrant with metadata filters

#### Week 3: Hybrid Search
- Implement BM25 index (rank-bm25)
- Implement vector search (Qdrant)
- Implement reranking (bge-reranker-large)
- Fusion: RRF (Reciprocal Rank Fusion) for BM25 + vector

#### Week 4: Entity Features
- Entity-based filtering (e.g., "grantor:John Smith")
- Entity highlighting in results
- Entity aggregation (show all parties/parcels in corpus)

#### Week 5: Demo Polish
- Build Streamlit UI with:
  - Query input
  - Entity filter dropdowns
  - Result cards with citations
  - Source document preview
- Test on real legal docs
- Document learnings

**Success Metrics:**
- ✅ MRR@10 > 0.8 (Mean Reciprocal Rank for test queries)
- ✅ Entity extraction accuracy > 90% (manual validation)
- ✅ Citation precision: Page + bbox (or page-only with note)
- ✅ Query latency < 2s (p95)
- ✅ Demo works end-to-end with 20+ documents

**Validation Gate (before Demo 3):**
- [ ] 10 test queries with ground truth relevance labels
- [ ] Entity extraction validated on 50 documents
- [ ] Bbox extraction working OR page-level fallback documented
- [ ] LangSmith shows <2s latency for 95% of queries
- [ ] Stakeholder demo completed with positive feedback

---

### **Demo 3: Chain-of-Title Assistant** (6-8 weeks)

**Goal:** Trace ownership history across documents using graph relationships

**User Story:**
> "As a title examiner, I want to generate a complete chain-of-title for Parcel 123 from 2000-2024, showing all transfers with supporting citations."

**Core Features:**
1. **Graph Ingestion** - Extract relationships from documents
2. **Entity Linking** - Normalize and link entities across docs
3. **Multi-Hop Queries** - Cypher queries for CoT traversal
4. **Chain Reports** - Text-based reports with citations (not visual UI)
5. **Gap Detection** - Identify missing links in chain

**Technical Components:**

#### Week 1-2: Graph Schema Design
- Adapt existing legal ontology (e.g., LKIF)
- Define core relationships:
  - `(Party)-[:CONVEYS_TO]->(Party)`
  - `(Party)-[:OWNS]->(Parcel)`
  - `(Document)-[:MENTIONS]->(Entity)`
  - `(Transfer)-[:RECORDED_ON]->(Date)`
- Set up Neo4j Community Edition (Docker)
- Create sample graph with test data

#### Week 3-4: Graph Ingestion
- Extract relationships from documents (GPT-4o-mini)
- Entity normalization and linking
- Load entities + relationships into Neo4j
- Validate graph structure with Cypher queries

#### Week 4-5: Multi-Hop Reasoning
- Implement CoT query patterns:
  - "Find all transfers for Parcel X"
  - "Trace ownership from Person A to Person B"
  - "Identify gaps in chain between Date1 and Date2"
- Combine graph traversal + vector retrieval for evidence
- Return graph paths + supporting document chunks

#### Week 6-7: Chain Reports
- Generate markdown chain-of-title reports:
  - Timeline of transfers (text-based)
  - Entity summary (parties, parcels)
  - Citations for each transfer
  - Gaps and warnings
- Static Mermaid diagrams (optional, if time permits)
- Test on real legal datasets

#### Week 8: Demo Polish (if needed)
- Build simple UI (Streamlit or CLI)
- Test on complex multi-document chains
- Document learnings

**Success Metrics:**
- ✅ Graph completeness: >95% of entities extracted and linked
- ✅ CoT accuracy: Manually validate 10 chains against ground truth
- ✅ Gap detection: Identify 100% of known chain breaks
- ✅ Citation coverage: Every transfer has ≥1 supporting citation
- ✅ Query latency: <5s for typical CoT query

**Validation Gate (before Demo 4):**
- [ ] Graph schema validated with legal expert
- [ ] Entity linking accuracy >90% (fuzzy matching working)
- [ ] 5 complex CoT queries successfully traced
- [ ] Reports include citations for all claims
- [ ] Neo4j queries optimized (indexed properties)

---

### **Demo 4: Title Opinion Generator** (8-10 weeks)

**Goal:** Autonomous agent that drafts title opinions with QA verification

**User Story:**
> "As a title attorney, I want an AI to draft a preliminary title opinion for Parcel 123, identifying defects and citing supporting evidence, so I can review and finalize it faster."

**Core Features:**
1. **Agentic Workflow** - LangGraph multi-step reasoning
2. **Title Analysis** - Identify defects, exceptions, requirements
3. **QA Verification** - Self-check claims against sources
4. **Report Generation** - Structured markdown with sections
5. **Citation Anchoring** - Every claim backed by document evidence

**Technical Components:**

#### Week 1-2: Agent Architecture
- Design LangGraph workflow:
  - Step 1: Gather evidence (hybrid search + graph)
  - Step 2: Analyze chain-of-title (graph reasoning)
  - Step 3: Identify defects (LLM reasoning)
  - Step 4: Draft opinion sections (LLM generation)
  - Step 5: QA verification (self-critique)
  - Step 6: Finalize report (markdown output)
- Set up LangGraph agent skeleton
- Define agent state schema

#### Week 3-4: Evidence Gathering
- Agent Step 1: Retrieve all relevant docs for parcel
- Use hybrid search + graph queries
- Rank evidence by relevance
- Store in agent memory

#### Week 5-6: Title Analysis
- Agent Step 2: Trace chain-of-title via Neo4j
- Agent Step 3: Identify defects using LLM:
  - Missing signatures
  - Incomplete legal descriptions
  - Recording defects
  - Lien or encumbrance issues
- Store findings in structured format

#### Week 7-8: Opinion Generation
- Agent Step 4: Generate opinion sections:
  - Executive Summary
  - Chain-of-Title (from Demo 3)
  - Title Defects & Exceptions
  - Requirements for Clear Title
  - Recommendations
- Each section includes citations

#### Week 9: QA Verification
- Agent Step 5: Self-critique loop
  - Check: Is every claim cited?
  - Check: Are citations accurate (bbox match)?
  - Check: Are defects logically sound?
  - Retry if QA fails (max 2 iterations)

#### Week 10: Demo Polish
- Build UI for opinion generation
- Test on real parcels (10+ examples)
- Manual review: Compare AI opinions to human-drafted
- Document accuracy, gaps, edge cases

**Success Metrics:**
- ✅ Opinion completeness: All required sections present
- ✅ Citation coverage: 100% of claims have supporting citations
- ✅ Defect detection recall: >80% of known defects identified
- ✅ QA verification: <5% of claims fail citation check
- ✅ Human review: Attorneys rate opinions as "useful draft" (≥7/10)

**Validation Gate (Phase 3 Complete):**
- [ ] 10 title opinions generated and reviewed by attorney
- [ ] All opinions pass QA verification (100% citation coverage)
- [ ] Defect detection validated against manual review
- [ ] Report format meets professional standards
- [ ] Stakeholder approval to move to production pilot

---

## 🔄 Cross-Cutting Concerns

### **Governance (Integrated Throughout)**

Instead of Demo 5, governance is embedded in each demo:

**Demo 1+2:**
- Track retrieval metrics in LangSmith (precision, recall, latency)
- Log entity extraction accuracy (manual spot checks)
- Document bbox extraction limitations

**Demo 3:**
- Track graph completeness (node/edge counts)
- Log entity linking errors (manual review queue)
- Validate CoT queries against ground truth

**Demo 4:**
- Track agent success rate (% of opinions passing QA)
- Log citation failures (QA verification misses)
- Human review loop for opinion quality

### **Schema Evolution**

**v2.2.0 (Current - Phase 2):**
```json
{
  "doc_id": "deed_123",
  "chunk_id": "deed_123_chunk_001",
  "page_num": 5,
  "content": "...",
  "char_count": 1234,
  "estimated_tokens": 300
}
```

**v2.3.0 (Demo 1+2):**
```json
{
  "doc_id": "deed_123",
  "chunk_id": "deed_123_chunk_001",
  "page_num": 5,
  "bbox": {"x0": 100, "y0": 200, "x1": 500, "y1": 300},  // NEW
  "content": "...",
  "entities": [  // NEW
    {"text": "John Smith", "type": "PERSON", "role": "grantor"},
    {"text": "Parcel 123", "type": "PARCEL", "role": "subject"}
  ],
  "char_count": 1234,
  "estimated_tokens": 300,
  "embedding": [0.1, 0.2, ...],  // NEW (stored in Qdrant)
  "schema_version": "2.3.0"
}
```

**v3.0.0 (Demo 3):**
```json
{
  // ... v2.3.0 fields ...
  "graph_entities": [  // NEW - for Neo4j linking
    {"id": "person_001", "text": "John Smith", "type": "PERSON"},
    {"id": "parcel_123", "text": "Parcel 123", "type": "PARCEL"}
  ],
  "graph_relationships": [  // NEW
    {"source": "person_001", "relation": "CONVEYS_TO", "target": "person_002"}
  ]
}
```

### **Testing Strategy**

**Demo 1+2:**
- Unit tests: Entity extraction, search ranking
- Integration tests: End-to-end query → results
- Manual QA: 10 test queries validated

**Demo 3:**
- Unit tests: Graph loading, Cypher queries
- Integration tests: CoT traversal accuracy
- Manual QA: 5 complex chains validated

**Demo 4:**
- Unit tests: Agent steps, QA verification
- Integration tests: Full opinion generation
- Manual QA: 10 opinions reviewed by attorney

---

## 📊 Risk Management

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| **Docling bbox not available** | Medium | Medium | Fallback to page-level citations (documented) |
| **Entity extraction accuracy <90%** | Low | Medium | Manual review queue + incremental training data |
| **Graph schema too complex** | Medium | High | Start simple, iterate based on queries |
| **Neo4j performance issues** | Low | Medium | Index optimization + query profiling |
| **LLM hallucinations in opinions** | Medium | High | QA verification loop + citation checks |
| **Timeline slippage** | Medium | Medium | Weekly checkpoints + scope cut options |

---

## 🎯 Phase 2B: Immediate Next Steps

### **This Week: Planning & Design**

**Day 1-2: Phase 2 Closeout**
- [x] Kill background processes
- [ ] Validate Phase 2 outputs (manifests, JSONL)
- [ ] Run final QA on multi-format batch
- [ ] Document Phase 2 learnings
- [ ] Archive test data

**Day 3-4: Schema Design**
- [ ] Design schema v2.3.0 (bbox + entities)
- [ ] Document entity types (PERSON, PARCEL, DATE, AMOUNT, ORG)
- [ ] Define entity roles (grantor, grantee, subject)
- [ ] Create schema validation tests

**Day 5: Infrastructure Setup**
- [ ] Install Qdrant (Docker: `docker run -p 6333:6333 qdrant/qdrant`)
- [ ] Test Qdrant: Create collection, insert vectors, query
- [ ] Set up LangSmith account (free tier)
- [ ] Test LangSmith: Log sample trace

**Day 6-7: Bbox Spike**
- [ ] Test Docling JSON output for bbox data
- [ ] If present: Extract bbox coordinates
- [ ] If absent: Document page-level fallback plan
- [ ] Update schema v2.3.0 based on findings

### **Next Week: Demo 1+2 Kickoff**

**Week 1 Goals:**
- [ ] Extend Phase 2 pipeline to extract entities (GPT-4o-mini)
- [ ] Generate embeddings for chunks (OpenAI API)
- [ ] Load chunks into Qdrant with metadata
- [ ] Test basic vector search

**Success Criteria:**
- [ ] 100 documents processed with entities extracted
- [ ] All chunks embedded and loaded into Qdrant
- [ ] Basic query: "Find clauses about John Smith" works
- [ ] LangSmith shows query traces

---

## 📝 Open Questions & Decisions

### **Resolved ✅**
- [x] Open source stack: Pragmatic (OpenAI for now)
- [x] Bbox extraction: Try Docling (A), fallback to page-level
- [x] Demo 1+2: Merged into single demo
- [x] Graph DB: Neo4j Community Edition
- [x] Monitoring: LangSmith (free tier)
- [x] Demo 5: Cut entirely (governance integrated)

### **To Be Resolved (During Planning Week)**
- [ ] Exact entity types to extract (beyond PERSON, PARCEL)
- [ ] Entity normalization rules (fuzzy match threshold?)
- [ ] Qdrant collection schema (vector size, distance metric)
- [ ] LangSmith project structure (separate per demo?)
- [ ] Test dataset: Which 20+ documents for initial testing?

---

## 🎓 Key Principles

1. **95% Rule:** Choose easier path if it delivers 95% of value
2. **Defer Optimization:** Use OpenAI now, migrate to OSS later
3. **Demo Gating:** Each demo must pass validation before next
4. **Citation First:** Every claim must have source evidence
5. **Fail Closed:** Log errors, never fail silently
6. **Iterative:** Ship working demo, then polish
7. **Pragmatic Over Pure:** Results > ideology

---

## 📚 References

- **Phase 2 Summary:** [readme.md](readme.md)
- **RAG Analysis:** RAG_Architecture_Analysis.md (if available)
- **Schema Spec:** To be created in planning week
- **Tech Stack Docs:**
  - [Qdrant](https://qdrant.tech/documentation/)
  - [Neo4j](https://neo4j.com/docs/)
  - [LangGraph](https://langchain-ai.github.io/langgraph/)
  - [LangSmith](https://docs.smith.langchain.com/)

---

**Next Action:** Complete Phase 2 closeout, then begin planning week.
