# TODO: Project Restructure

**Date Created:** 2025-10-30
**Priority:** Medium
**Status:** Planning

---

## 🎯 Objective

Reorganize project structure to be more intuitive and production-ready.

---

## 🔍 Current Issues

### **1. Confusing Entry Points**
- `process_documents.py` lives in `olmocr_pipeline/` folder
  - **Problem:** Main entry point buried in subdirectory
  - **Expected:** Top-level scripts for main workflows

### **2. Mixed Concerns**
- `olmocr_pipeline/` contains:
  - Core processing logic ✅
  - Main entry point (`process_documents.py`) ❌
  - Utilities (scattered) ⚠️

### **3. Lack of Clear "Scripts" vs "Library" Separation**
- Hard to tell what's meant to be run vs imported

### **4. Growing Root Directory**
- Many test scripts and utilities at root level
- Needs organization

---

## 💡 Proposed Structure

### **Option A: Scripts Directory**
```
pdf-rag/
├── scripts/                      # User-facing entry points
│   ├── process_documents.py      # Main: process documents
│   ├── load_to_qdrant.py         # Main: load to vector DB
│   ├── query_cli.py              # Main: query interface
│   ├── setup_persistent_qdrant.py
│   └── verify_qdrant_persistence.py
│
├── olmocr_pipeline/              # Core library
│   ├── handlers/                 # Document processors
│   ├── utils_*.py                # Utilities
│   └── __init__.py
│
├── tests/                        # All test scripts
│   ├── test_*.py
│   └── integration/
│
├── docs/
│   └── planning/
│
└── config/
```

### **Option B: Flat Top-Level Scripts**
```
pdf-rag/
├── process.py                    # Main: process documents
├── load.py                       # Main: load to Qdrant
├── query.py                      # Main: query interface
│
├── olmocr_pipeline/              # Core library
│   ├── handlers/
│   ├── utils/                    # Organized utilities
│   │   ├── config.py
│   │   ├── qdrant.py
│   │   ├── embeddings.py
│   │   └── entity.py
│   └── __init__.py
│
├── tests/
└── docs/
```

### **Option C: Full CLI Package**
```
pdf-rag/
├── cli.py                        # Single entry point with subcommands
│                                 # python cli.py process
│                                 # python cli.py load
│                                 # python cli.py query
│
├── olmocr_pipeline/              # Core library
│   ├── commands/                 # CLI command implementations
│   ├── core/                     # Core logic
│   ├── handlers/
│   └── utils/
│
└── tests/
```

---

## 🎯 Recommended Approach

**Start with Option A** (Scripts Directory):
- Minimal disruption
- Clear separation of concerns
- Easy to evolve to Option C later

### **Migration Steps:**

1. **Phase 1: Create `scripts/` directory**
   - Move main entry points: `process_documents.py`, `load_to_qdrant.py`, `query_cli.py`
   - Update import paths
   - Update README

2. **Phase 2: Consolidate test scripts**
   - Move all `test_*.py` to `tests/`
   - Move analysis scripts to `tests/analysis/`

3. **Phase 3: Organize utilities**
   - Consolidate `utils_*.py` into `olmocr_pipeline/utils/` package
   - Better module organization

4. **Phase 4: Update documentation**
   - README with new structure
   - Update all doc references

---

## 📋 Files to Move

### **To `scripts/`:**
- `olmocr_pipeline/process_documents.py` → `scripts/process_documents.py`
- `load_to_qdrant.py` → `scripts/load_to_qdrant.py`
- `query_cli.py` → `scripts/query_cli.py`
- `setup_persistent_qdrant.py` → `scripts/setup_qdrant.py`
- `verify_qdrant_persistence.py` → `scripts/verify_qdrant.py`

### **To `tests/`:**
- All `test_*.py` files
- `analyze_*.py` files → `tests/analysis/`
- `compare_*.py` files → `tests/analysis/`
- `spot_check_*.py` files → `tests/analysis/`

### **To `olmocr_pipeline/utils/`:**
- `utils_config.py` → `olmocr_pipeline/utils/config.py`
- `utils_qdrant.py` → `olmocr_pipeline/utils/qdrant.py`
- `utils_embeddings.py` → `olmocr_pipeline/utils/embeddings.py`
- `utils_entity*.py` → `olmocr_pipeline/utils/entity/`

---

## ⚠️ Breaking Changes

### **Import Path Changes:**
```python
# Old
from olmocr_pipeline.process_documents import main

# New
from scripts.process_documents import main
```

### **CLI Changes:**
```bash
# Old
python olmocr_pipeline/process_documents.py --auto

# New
python scripts/process_documents.py --auto
# OR (with symlinks)
python process_documents.py --auto
```

---

## 🎯 Benefits

1. **Clarity:** Clear what's meant to be run vs imported
2. **Discoverability:** Entry points at top level or in `scripts/`
3. **Maintainability:** Organized utilities, cleaner imports
4. **Scalability:** Easy to add new scripts/commands
5. **Production-ready:** Professional project structure

---

## 📅 Timeline

- **Week 3:** Review and finalize structure
- **Week 4:** Implement Phase 1 (scripts directory)
- **Week 5:** Implement Phase 2-3 (tests, utils)
- **Week 6:** Update docs, test everything

---

## 🤝 Decision Needed

Before implementing, confirm:
1. Which option (A, B, or C)?
2. Breaking changes acceptable?
3. Backward compatibility needed?

---

**Status:** Draft - needs review and approval before implementation
