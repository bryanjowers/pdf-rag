# START HERE - New Session Onboarding

**Last Updated:** 2025-10-30
**Project:** PDF-RAG Legal Document Pipeline

This document is the **single entry point** for starting new sessions with Claude. It acts as a roadmap to the right documentation—not a replacement for it.

---

## 🚀 Quick Start for Claude

When starting a new session, read these documents **in this order**:

### 1. Core Project Documentation (Required)
Read these three documents to understand the project:

1. **[readme.md](readme.md)** - Project overview, architecture, quick start guide
2. **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development standards, workflows, coding practices
3. **[docs/README.md](docs/README.md)** - Documentation structure and organization

### 2. Current Status (Required)
After reading core docs, check current state:

4. **Git Status** - Run `git status` to see what's changed
5. **Recent Commits** - Run `git log --oneline -10` to see recent work
6. **[docs/planning/sessions/](docs/planning/sessions/)** - Check for recent session notes or pickup docs

### 3. Phase-Specific Context (As Needed)
Depending on the work focus, read relevant deep-dive docs:

- **[docs/planning/phases/PHASE3_READY.md](docs/planning/phases/PHASE3_READY.md)** - Current phase status
- **[docs/technical/SCHEMA_V2.3.0.md](docs/technical/SCHEMA_V2.3.0.md)** - Technical specification
- **[scripts/README.md](scripts/README.md)** - All available scripts and utilities

---

## 📋 Session Checklist

When starting a new session with Claude, complete these steps:

### For Claude:
- [ ] Read START_HERE.md (this file)
- [ ] Read readme.md, CONTRIBUTING.md, docs/README.md in order
- [ ] Check git status and recent commits
- [ ] Look for SESSION_PICKUP_*.md in docs/planning/sessions/
- [ ] Use the session initialization template below
- [ ] Ask user: "What's our focus for this session?"

### For User (Bryan):
- [ ] Provide focus/goal for the session
- [ ] Share any specific context or blockers
- [ ] Indicate urgency or constraints

---

## 🔍 Context Navigation Guide

**Working on specific areas?** Use this guide to find the right documentation:

| Working On | Read This |
|------------|-----------|
| **Performance optimization** | [docs/technical/PARALLELIZATION_OPTIMIZATION_COMPLETE.md](docs/technical/PARALLELIZATION_OPTIMIZATION_COMPLETE.md) |
| **Entity extraction** | [docs/guides/ENTITY_EXTRACTION_QA_PLAN.md](docs/guides/ENTITY_EXTRACTION_QA_PLAN.md) |
| **Qdrant/Embeddings** | [docs/guides/SETUP_INFRASTRUCTURE.md](docs/guides/SETUP_INFRASTRUCTURE.md) |
| **Schema details** | [docs/technical/SCHEMA_V2.3.0.md](docs/technical/SCHEMA_V2.3.0.md) |
| **Debugging failures** | Check quarantine.csv, logs/, and recent session notes |
| **Script usage** | [scripts/README.md](scripts/README.md) |
| **Phase planning** | [docs/planning/phases/](docs/planning/phases/) |

---

## 🎯 Session Initialization Template

**Claude should use this after reading the required docs:**

```markdown
## Session Initialized ✓

**Documents Read:**
- ✅ START_HERE.md
- ✅ readme.md
- ✅ CONTRIBUTING.md
- ✅ docs/README.md

**Current State:**
- Branch: [from git status]
- Recent work: [from git log]
- Uncommitted changes: [from git status]
- Latest session: [from docs/planning/sessions/]

**Environment:** Headless VM | GCS + NVIDIA L4 GPUs | Phase 3 (RAG + Entities)

---

What's our focus for this session?
```

---

## 🚨 Critical Rules (Quick Reference)

**See [CONTRIBUTING.md](CONTRIBUTING.md) for full details. Key rules:**

- ❌ Never touch `/mnt/gcs/legal-ocr-pdf-input/` (input is sacred)
- ❌ Never run clean slate without explicit confirmation
- ❌ Never make performance claims without measurements
- ✅ Always document performance changes with before/after metrics
- ✅ Always update docs when changing functionality
- ✅ Always test with real data before claiming success

---

## 📞 Quick Reference Links

| Category | Link |
|----------|------|
| **Main docs** | [readme.md](readme.md) · [CONTRIBUTING.md](CONTRIBUTING.md) · [docs/README.md](docs/README.md) |
| **Current work** | [Phase 3 status](docs/planning/phases/PHASE3_READY.md) · [Recent sessions](docs/planning/sessions/) |
| **Technical** | [Schema v2.3.0](docs/technical/SCHEMA_V2.3.0.md) · [Infrastructure](docs/guides/SETUP_INFRASTRUCTURE.md) |
| **Scripts** | [All scripts](scripts/README.md) |

---

## 🔄 Maintenance

**Update START_HERE.md when:**
- Phase changes (e.g., Phase 3 → Phase 4)
- New critical documents added
- Navigation structure changes

**This document is a roadmap, not a replacement.** Keep it lean. Let the other docs do the heavy lifting.

---

**Next Step for Claude:** Complete the session checklist above, then ask: "What's our focus for this session?"
