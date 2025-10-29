# Project Planning & Documentation Index

> **Last Updated:** 2025-10-29 | **Current Phase:** 3 (Planning Complete)

---

## 🗂️ Quick Navigation

### **🚀 START HERE**
- **[PHASE3_READY.md](PHASE3_READY.md)** - **Read this first!** Executive summary, next actions, quick reference

### **📋 Current Phase Documents**
- **[PHASE3_PLAN.md](PHASE3_PLAN.md)** - Complete Phase 3 roadmap (3 demos, 5-6 months)
- **[SCHEMA_V2.3.0.md](SCHEMA_V2.3.0.md)** - Technical schema specification (bbox + entities)
- **[SETUP_INFRASTRUCTURE.md](SETUP_INFRASTRUCTURE.md)** - Qdrant + LangSmith setup guide

### **📚 Reference & Historical Documents**
- **[RAG_Architecture_Analysis.md](RAG_Architecture_Analysis.md)** - Comprehensive RAG architecture analysis (60+ pages)
- **[PHASE2_CLOSEOUT.md](PHASE2_CLOSEOUT.md)** - Phase 2 completion report and handoff
- **[WEEK2_SUMMARY.md](WEEK2_SUMMARY.md)** - Week 2 progress summary
- **[WEEK3_SUMMARY.md](WEEK3_SUMMARY.md)** - Week 3 progress summary
- **[PROGRESS_PHASE2.md](PROGRESS_PHASE2.md)** - Phase 2 progress tracking
- **[PHASE2_COMPLETE.md](PHASE2_COMPLETE.md)** - Phase 2 completion announcement

---

## 📖 Document Guide

### **Planning & Roadmap**

#### **PHASE3_READY.md** ⭐ START HERE
**Purpose:** Executive summary of Phase 3 planning
**Key Content:**
- All decisions locked in (OSS stack, demo scope, timeline)
- Approved 3-demo roadmap
- Immediate next actions (Qdrant setup, bbox spike)
- Quick reference to all other docs

**When to Read:** Right now! This is your entry point.

---

#### **PHASE3_PLAN.md** 📋 COMPREHENSIVE PLAN
**Purpose:** Detailed Phase 3 implementation roadmap
**Key Content:**
- 3 demos with week-by-week breakdown
  - Demo 1+2: Smart Entity Search (5 weeks)
  - Demo 3: Chain-of-Title Assistant (6-8 weeks)
  - Demo 4: Title Opinion Generator (8-10 weeks)
- Success metrics per demo
- Tech stack specification
- Risk management
- Cross-cutting concerns (governance, testing)

**When to Read:**
- Before starting each demo (refresh on goals)
- During weekly planning (track progress)
- When making scope decisions (refer to North Star)

**Sections:**
1. Executive Summary
2. Phase Breakdown (detailed)
3. Technology Stack (locked in)
4. Schema Evolution (v2.2.0 → v2.3.0 → v3.0.0)
5. Risk Management
6. Phase 2B: Immediate Next Steps

---

### **Technical Specifications**

#### **SCHEMA_V2.3.0.md** 🔧 TECHNICAL SPEC
**Purpose:** Detailed schema specification for Phase 3
**Key Content:**
- Migration from v2.2.0 → v2.3.0
- Bounding box specification (PDF coordinate system)
- Entity types & roles (7 core types)
- Qdrant integration schema
- Validation scripts
- Evolution path to v3.0.0 (Graph RAG)

**When to Read:**
- During Week 1 implementation (extending pipeline)
- When debugging schema issues
- Before integrating with Qdrant
- When adding new entity types

**Key Sections:**
- Field reference table (comprehensive)
- Entity extraction guidelines
- Normalization rules
- Qdrant payload structure
- Validation scripts (copy-paste ready)

---

#### **SETUP_INFRASTRUCTURE.md** 🛠️ SETUP GUIDE
**Purpose:** Step-by-step infrastructure setup
**Key Content:**
- Qdrant setup (Docker + testing)
- LangSmith account creation
- Bbox extraction spike (test script)
- Dependency installation
- Infrastructure verification
- Config file template

**When to Read:**
- Today/tomorrow (before starting Demo 1+2)
- When setting up new dev environment
- When debugging infrastructure issues

**Sections:**
1. Qdrant Setup (Docker recommended)
2. LangSmith Setup (account + API key)
3. Docling Bbox Spike (1-day test)
4. Dependency Installation
5. Infrastructure Verification
6. Config File Creation

---

### **Phase 2 Historical**

#### **PHASE2_CLOSEOUT.md** ✅ HANDOFF DOCUMENT
**Purpose:** Clean closure of Phase 2, handoff to Phase 3
**Key Content:**
- Phase 2 accomplishments (100% complete)
- Final validation results (13 JSONL files, 0 quarantined)
- Learnings & challenges
- Known limitations (no bbox, no entities, no graph)
- Archive instructions

**When to Read:**
- When understanding what Phase 2 delivered
- When debugging Phase 2 output
- When referencing Phase 2 architecture decisions

---

#### **WEEK2_SUMMARY.md** 📅 HISTORICAL
**Purpose:** Week 2 progress summary
**Key Content:**
- Week 2 accomplishments (Docling integration, DOCX handler)
- Checkpoints passed
- Learnings

**When to Read:** Reference only, historical context.

---

#### **WEEK3_SUMMARY.md** 📅 HISTORICAL
**Purpose:** Week 3 progress summary
**Key Content:**
- Week 3 accomplishments (XLSX handler, multi-format batch)
- CHECKPOINT 4 passed (100% success)
- Phase 2 completion

**When to Read:** Reference only, historical context.

---

#### **PROGRESS_PHASE2.md** 📊 HISTORICAL
**Purpose:** Phase 2 progress tracking
**Key Content:**
- Checkpoint tracking
- Task completion status
- Deliverables list

**When to Read:** Reference only, historical context.

---

#### **PHASE2_COMPLETE.md** 🎉 HISTORICAL
**Purpose:** Phase 2 completion announcement
**Key Content:**
- Summary of Phase 2 deliverables
- Metrics achieved
- Next steps to Phase 3

**When to Read:** Reference only, historical context.

---

## 🗺️ How to Use This Documentation

### **Scenario 1: Starting Phase 3 Implementation**
1. Read [PHASE3_READY.md](PHASE3_READY.md) - Get oriented
2. Follow [SETUP_INFRASTRUCTURE.md](SETUP_INFRASTRUCTURE.md) - Set up Qdrant + LangSmith
3. Refer to [SCHEMA_V2.3.0.md](SCHEMA_V2.3.0.md) - Understand schema
4. Use [PHASE3_PLAN.md](PHASE3_PLAN.md) - Week-by-week implementation guide

### **Scenario 2: Mid-Demo Progress Check**
1. Open [PHASE3_PLAN.md](PHASE3_PLAN.md) - Check success metrics for current demo
2. Review validation gate criteria - Ensure you're on track
3. Update todo list based on remaining tasks

### **Scenario 3: Debugging Phase 2 Output**
1. Read [PHASE2_CLOSEOUT.md](PHASE2_CLOSEOUT.md) - Understand Phase 2 architecture
2. Check schema v2.2.0 specification (in PHASE2_CLOSEOUT.md)
3. Review known limitations

### **Scenario 4: Making Scope Decisions**
1. Open [PHASE3_PLAN.md](PHASE3_PLAN.md) - Review North Star alignment
2. Check Key Principles section - "95% Rule"
3. Refer to Risk Management section - Mitigation strategies

### **Scenario 5: Schema Questions**
1. Open [SCHEMA_V2.3.0.md](SCHEMA_V2.3.0.md) - Comprehensive field reference
2. Check Entity Types & Roles section
3. Use validation scripts to verify output

---

## 📊 Project Status

| Phase | Status | Completion | Documents |
|-------|--------|------------|-----------|
| **Phase 1** | ✅ Complete | 100% | (Not documented in this folder) |
| **Phase 2** | ✅ Complete | 100% | PHASE2_CLOSEOUT.md, WEEK2_SUMMARY.md, WEEK3_SUMMARY.md |
| **Phase 3** | 📋 Planning Complete | 0% (ready to start) | PHASE3_PLAN.md, PHASE3_READY.md, SCHEMA_V2.3.0.md, SETUP_INFRASTRUCTURE.md |

### **Current Milestone:** Infrastructure Setup (Week 0)
- [ ] Qdrant setup
- [ ] LangSmith setup
- [ ] Bbox spike (1 day)
- [ ] Ready for Demo 1+2 Week 1

---

## 🎯 Key Decisions Summary

Quick reference to major decisions (see [PHASE3_READY.md](PHASE3_READY.md) for full context):

| Decision | Choice | Document |
|----------|--------|----------|
| **OSS Stack** | Pragmatic (OpenAI now, OSS later) | PHASE3_PLAN.md |
| **Bbox Strategy** | Try Docling, fallback to page-level | SETUP_INFRASTRUCTURE.md |
| **Demo Scope** | Merge Demos 1+2, keep 3-4, cut Demo 5 | PHASE3_PLAN.md |
| **Graph DB** | Neo4j Community Edition | PHASE3_PLAN.md |
| **Monitoring** | LangSmith (free tier) | PHASE3_PLAN.md |
| **Vector DB** | Qdrant | PHASE3_PLAN.md |
| **Embeddings** | OpenAI text-embedding-3-small | SCHEMA_V2.3.0.md |
| **LLM** | GPT-4o-mini | PHASE3_PLAN.md |
| **Entity Extraction** | GPT-4o-mini (defer custom NER) | SCHEMA_V2.3.0.md |

---

## 📁 Folder Structure

```
docs/planning/
├── INDEX.md                       # This file (you are here!)
├── PHASE3_READY.md                # ⭐ START HERE - Executive summary
├── PHASE3_PLAN.md                 # 📋 Comprehensive Phase 3 roadmap
├── SCHEMA_V2.3.0.md               # 🔧 Technical schema specification
├── SETUP_INFRASTRUCTURE.md        # 🛠️ Infrastructure setup guide
├── RAG_Architecture_Analysis.md   # 📚 Comprehensive RAG analysis (60+ pages)
├── PHASE2_CLOSEOUT.md             # ✅ Phase 2 handoff document
├── WEEK2_SUMMARY.md               # 📅 Historical (Week 2)
├── WEEK3_SUMMARY.md               # 📅 Historical (Week 3)
├── PROGRESS_PHASE2.md             # 📊 Historical (Phase 2 tracking)
└── PHASE2_COMPLETE.md             # 🎉 Historical (Phase 2 completion)
```

---

## 🔄 Document Lifecycle

### **Active Documents** (refer to these regularly)
- ✅ PHASE3_READY.md
- ✅ PHASE3_PLAN.md
- ✅ SCHEMA_V2.3.0.md
- ✅ SETUP_INFRASTRUCTURE.md

### **Reference Documents** (background & context)
- 📚 RAG_Architecture_Analysis.md (comprehensive RAG strategy)
- 📚 PHASE2_CLOSEOUT.md
- 📚 WEEK2_SUMMARY.md
- 📚 WEEK3_SUMMARY.md
- 📚 PROGRESS_PHASE2.md
- 📚 PHASE2_COMPLETE.md

### **Future Documents** (will be created)
- 🔮 bbox_spike_results.md (after 1-day spike)
- 🔮 DEMO1_2_WEEK1_PLAN.md (detailed Week 1 tasks)
- 🔮 DEMO1_2_COMPLETE.md (after Demo 1+2 validation gate)
- 🔮 DEMO3_PLAN.md (before Demo 3 kickoff)
- 🔮 DEMO4_PLAN.md (before Demo 4 kickoff)
- 🔮 PHASE3_COMPLETE.md (after Demo 4 validation gate)

---

## 📞 Need Help?

**Finding a specific topic?**
- Use Ctrl+F (or Cmd+F) to search this index
- Each document has a table of contents (TOC)

**Questions about Phase 3 implementation?**
- Start with [PHASE3_READY.md](PHASE3_READY.md)
- Deep dive in [PHASE3_PLAN.md](PHASE3_PLAN.md)

**Schema or technical questions?**
- [SCHEMA_V2.3.0.md](SCHEMA_V2.3.0.md) has comprehensive field reference
- Includes validation scripts (copy-paste ready)

**Infrastructure setup issues?**
- [SETUP_INFRASTRUCTURE.md](SETUP_INFRASTRUCTURE.md) has step-by-step instructions
- Includes verification scripts

---

## 🎓 Principles (Reminder)

1. **95% Rule:** Choose easier path if it delivers 95% of value
2. **Pragmatic Stack:** OpenAI now, migrate to OSS later
3. **Demo Gating:** Each demo must pass validation before next
4. **Citation First:** Every claim must have source evidence
5. **Fail Closed:** Log errors, never fail silently
6. **North Star:** Defensible title verification with precise legal citations

---

**Status:** ✅ **PHASE 3 PLANNING COMPLETE - READY TO IMPLEMENT**

**Last Updated:** 2025-10-29
**Maintained By:** Claude Code + You
