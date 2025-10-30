# Contributing Guide & Development Standards

**Project:** PDF-RAG Legal Document Pipeline
**Updated:** October 31, 2025

This document captures our established development practices, workflows, and standards to maintain consistency and quality over time.

---

## 🎯 Core Principles

1. **Documentation First** - Document as you build, not after
2. **Clean Slate Capability** - Always able to start fresh without losing work
3. **Organized Structure** - Everything has a place, nothing in root unless necessary
4. **Test Before Production** - Validate optimizations with real data
5. **Preserve Input Data** - Never touch source files during processing
6. **Session Continuity** - Make it easy to pick up where we left off

---

## 📁 Project Organization Standards

### Directory Structure

```
pdf-rag/
├── config/                      # Configuration files
│   └── default.yaml            # Main config (never commit secrets!)
│
├── docs/                        # 📚 ALL documentation goes here
│   ├── README.md               # Docs overview
│   ├── planning/               # Project planning & roadmaps
│   │   ├── INDEX.md           # Master planning index
│   │   ├── phases/            # Phase-specific plans
│   │   ├── weekly/            # Weekly summaries
│   │   └── sessions/          # Daily session notes
│   ├── technical/             # Technical documentation
│   ├── testing/               # Test results & validation
│   ├── guides/                # User guides & how-tos
│   └── status/                # Status updates & reports
│
├── olmocr_pipeline/            # Core pipeline code
│   ├── handlers/              # Document type handlers
│   ├── utils_*.py             # Utility modules
│   └── __init__.py
│
├── scripts/                    # 🛠️ All scripts organized here
│   ├── README.md              # Comprehensive script docs
│   ├── maintenance/           # System maintenance
│   ├── testing/               # Test & debug scripts
│   ├── analysis/              # Analysis utilities
│   └── *.py                   # Production scripts (root level)
│
├── readme.md                   # Project overview
├── CONTRIBUTING.md             # This file
├── common_commands.md          # Quick reference
└── main.py                     # Entry point (if applicable)
```

### What Goes Where?

| Content Type | Location | Example |
|--------------|----------|---------|
| Session notes | `docs/planning/sessions/` | `SESSION_2025-10-31.md` |
| Technical analysis | `docs/technical/` | `PARALLELIZATION_ANALYSIS.md` |
| Status updates | `docs/status/` | `CLEAN_SLATE_2025-10-31.md` |
| Test results | `docs/testing/` | `VALIDATION_TEST_FINAL_RESULTS.md` |
| How-to guides | `docs/guides/` | `QUERY_GUIDE.md` |
| Production scripts | `scripts/` (root) | `process_documents.py` |
| Test scripts | `scripts/testing/` | `test_4workers.py` |
| Maintenance scripts | `scripts/maintenance/` | `clean_slate.sh` |
| Analysis scripts | `scripts/analysis/` | `spot_check_entities.py` |

---

## 📝 Documentation Standards

### 1. Session Documentation

**When to create:** At the start or end of each major work session

**Location:** `docs/planning/sessions/SESSION_YYYY-MM-DD_[TOPIC].md`

**Required sections:**
```markdown
# Session: [Topic]

**Date:** YYYY-MM-DD
**Focus:** Brief description

## Problem / Goal
Clear statement of what we're trying to solve or achieve

## Analysis / Investigation
What we learned, what we tried

## Solution / Changes
What we implemented

## Files Modified
- [file.py](path/to/file.py) - What changed
- [config.yaml](path/to/config.yaml) - What changed

## Results / Impact
Measurable outcomes, performance improvements

## Next Steps
- [ ] Outstanding tasks
- [ ] Follow-up items
```

**Example:** `docs/planning/sessions/SESSION_2025-10-31_PARALLELIZATION_FIX.md`

### 2. Technical Documentation

**When to create:** When implementing significant features or optimizations

**Location:** `docs/technical/[TOPIC].md`

**Required sections:**
- **Problem statement** - What issue are we solving?
- **Root cause analysis** - Why is this happening?
- **Solution approach** - How will we fix it?
- **Implementation details** - Code changes, patterns used
- **Expected impact** - Performance gains, improvements
- **Testing / validation** - How to verify it works

**Example:** `docs/technical/PARALLELIZATION_OPTIMIZATION_COMPLETE.md`

### 3. Script Documentation

**Rule:** Every script must be documented in `scripts/README.md`

**Required:**
- Purpose (one line)
- Usage example
- Key parameters
- When to use it

**Update:** Whenever you add/modify scripts, update `scripts/README.md`

### 4. Code Comments

**Guidelines:**
- Use docstrings for all functions
- Comment WHY, not WHAT (code shows what)
- Explain non-obvious decisions
- Document performance considerations
- Link to relevant docs when applicable

**Example:**
```python
def get_docling_converter() -> DocumentConverter:
    """
    Get or create a thread-local Docling converter instance.

    Reusing the converter across multiple PDFs in the same thread eliminates
    expensive initialization overhead (model loading, GPU context setup, etc.).

    This is critical for parallel processing performance - without reuse,
    each PDF would create a new converter, wasting 2-3 seconds per file.

    See: docs/technical/PARALLELIZATION_OPTIMIZATION_COMPLETE.md

    Returns:
        DocumentConverter instance (one per thread)
    """
```

---

## 🔄 Development Workflow

### Starting a Session

1. **Review pickup document** (if exists): `docs/planning/sessions/SESSION_PICKUP_*.md`
2. **Check git status**: Understand current state
3. **Review recent commits**: `git log --oneline -10`
4. **Create session note**: Document your focus for the session

### During Development

1. **Make incremental commits** with clear messages
2. **Document as you go** - Don't wait until end
3. **Test before committing** - Validate changes work
4. **Update relevant docs** - Keep documentation current

### Ending a Session

1. **Create/update session document** with:
   - What was accomplished
   - What was learned
   - What's next
2. **Commit all changes** with clear message
3. **Create pickup document** (if needed) for next session
4. **Update status docs** if major changes made

### Session Document Naming

- **During session:** `SESSION_YYYY-MM-DD_[TOPIC].md`
- **Pickup for next:** `SESSION_PICKUP_YYYY-MM-DD.md`
- **Keep historical:** Don't delete old pickup docs, rename them

---

## 🗺️ Roadmap Management

### Active Roadmap: docs/planning/ROADMAP.md

**Claude's Responsibilities:**
1. **Review at session start** - Check current priorities and status
2. **Update during work** - Mark items as in-progress/completed
3. **Add new items** - Capture tasks as they emerge during sessions
4. **Propose priorities** - Suggest next items based on dependencies and impact
5. **Reference in planning** - Use roadmap to guide session focus

### When to Update Roadmap

**Always update when:**
- Starting work on a roadmap item (mark "In Progress")
- Completing a roadmap item (move to "Completed Items")
- Discovering new tasks or blockers (add to appropriate priority)
- Changing priorities (user request or dependency changes)
- Session ends (update status of all active items)

**Roadmap Structure:**
- **Current Sprint** - Active HIGH/MEDIUM priority items
- **Backlog** - Future enhancements and technical debt
- **Completed Items** - Archive of finished work

### Workflow Example

```markdown
## Session Start
1. Read docs/planning/ROADMAP.md
2. Identify HIGH priority items
3. Propose focus: "Based on roadmap, should we tackle item #1 (parallelization)?"

## During Work
4. Update roadmap: Change item #1 status to "In Progress"
5. Document findings in session note
6. If blocked, add new item: "Debug GPU contention issue"

## Session End
7. Update roadmap: Mark completed items, update blockers
8. Create SESSION_PICKUP if needed
9. Commit roadmap changes with session notes
```

---

## 🧪 Testing Standards

### Before Committing Code

1. **Run basic validation** - Does it work?
2. **Test edge cases** - What could break?
3. **Check performance** - Did we make it slower?
4. **Verify no regressions** - Did we break existing functionality?

### Performance Testing

When making performance optimizations:

1. **Establish baseline** - Measure before changes
2. **Implement optimization** - Make changes
3. **Measure improvement** - Compare with baseline
4. **Document results** in `docs/technical/`
5. **Update config** if needed

**Example workflow:**
```bash
# 1. Baseline test
python scripts/testing/test_4workers.py

# 2. Make optimization changes

# 3. Re-test
python scripts/testing/test_4workers.py

# 4. Document in docs/technical/
```

### Creating Test Scripts

**Location:** `scripts/testing/`

**Naming:** `test_[feature].py` or `debug_[feature].py`

**Requirements:**
- Clear output showing pass/fail
- Measurable results (timing, counts, etc.)
- Document in `scripts/README.md`
- Make reusable for future testing

---

## 🛠️ Code Standards

### Configuration Management

**Rule:** All configuration in `config/default.yaml`, never hardcode

**Good:**
```python
workers = config.get("processors", {}).get("digital_pdf_workers", 2)
```

**Bad:**
```python
workers = 4  # Hardcoded!
```

### Thread Safety

When implementing parallel processing:

1. **Use thread-local storage** for expensive resources
2. **Document thread safety** in docstrings
3. **Avoid shared state** without proper locking
4. **Test with multiple workers** to validate

**Example:**
```python
import threading
_thread_local = threading.local()

def get_resource():
    """Thread-safe resource getter using thread-local storage."""
    if not hasattr(_thread_local, 'resource'):
        _thread_local.resource = ExpensiveResource()
    return _thread_local.resource
```

### Error Handling

**Guidelines:**
- Catch specific exceptions, not bare `except:`
- Log errors with context
- Provide helpful error messages
- Allow graceful degradation when possible

### Performance Considerations

**Document these in code:**
- Initialization overhead
- Memory usage (especially for large models)
- Thread safety implications
- GPU vs CPU operations

---

## 🗂️ File Management Standards

### Scripts

**Rule:** No scripts in project root (except `main.py`)

**Process:**
1. Create script in appropriate `scripts/` subdirectory
2. Document in `scripts/README.md`
3. Update main `readme.md` if it's a key script
4. Make executable if shell script: `chmod +x`

### Temporary Files

**Rule:** Clean up temporary files before committing

**Common temp files to remove:**
- `*.log` (except production logs)
- `*_test.py` (unless it's a keeper)
- `debug_*.py` (unless documented)
- `*.tmp`
- `profiling_*.json`

**Keep:**
- Production logs (if < 10MB)
- Documented test scripts
- Configuration backups

### Data Files

**Rule:** Never commit large data files to git

**Instead:**
- Keep in GCS buckets
- Document location in README
- Use `.gitignore` for data directories

---

## 🔒 Clean Slate Standards

### Before Clean Slate

**Required:**
1. ✅ Verify input bucket is untouched
2. ✅ Optional: Create backup if unsure
3. ✅ Document what will be deleted
4. ✅ Explicit user confirmation required

### Clean Slate Script Template

```bash
#!/bin/bash
set -e  # Exit on error

# 1. Verify mounts
# 2. Show what will be deleted
# 3. Require "DELETE" confirmation
# 4. Clear results bucket (selective deletion)
# 5. Reset Qdrant (delete collections)
# 6. Verify clean slate
# 7. Verify input preserved
```

**See:** `scripts/maintenance/clean_slate.sh`

### After Clean Slate

**Manual steps when ready:**

The clean slate script does NOT automatically rebuild - you control when to run these:

1. **Rebuild inventory** (when ready to start processing)
   ```bash
   python scripts/rebuild_inventory.py
   ```

2. **Process documents** (when ready to process PDFs)
   ```bash
   python scripts/process_documents.py --auto
   ```

3. **Load to Qdrant** (when ready to enable search)
   ```bash
   python scripts/load_to_qdrant.py
   ```

4. **Verify system** (optional validation)
   ```bash
   python scripts/query_cli.py "test query"
   ```

**Document operation in:** `docs/status/CLEAN_SLATE_YYYY-MM-DD.md`

---

## 📊 Performance Optimization Workflow

### 1. Identify Bottleneck

- Profile current performance
- Identify slowest component
- Measure baseline metrics
- Document findings in `docs/technical/`

### 2. Research Solution

- Analyze root cause
- Research best practices
- Design solution approach
- Consider trade-offs

### 3. Implement & Test

- Make changes incrementally
- Test after each change
- Compare with baseline
- Validate no regressions

### 4. Document Results

**Required documentation:**
- Problem statement
- Root cause analysis
- Solution implemented
- Performance improvement (with numbers!)
- Files modified
- How to verify

**Location:** `docs/technical/[OPTIMIZATION]_COMPLETE.md`

### 5. Update Configuration

If optimization requires config changes:
1. Update `config/default.yaml`
2. Add comments explaining settings
3. Document in config file itself

---

## 🎨 Git Standards

### Commit Messages

**Format:**
```
[Category] Brief description (50 chars or less)

More detailed explanation if needed (wrap at 72 chars).

- Bullet points are fine
- List key changes

Related: docs/technical/SOME_DOC.md
```

**Categories:**
- `feat:` New feature
- `fix:` Bug fix
- `perf:` Performance improvement
- `docs:` Documentation changes
- `refactor:` Code restructuring
- `test:` Testing additions/changes
- `chore:` Maintenance tasks

**Examples:**
```
perf: Add thread-local resource reuse for 3x speedup

Implemented thread-local storage for Docling converter and
embedding generator to eliminate per-file initialization overhead.

- Added get_docling_converter() with threading.local
- Added get_embedding_generator() with threading.local
- Updated config to use 4 workers (up from 2)
- Expected improvement: 2.3x speedup

See: docs/technical/PARALLELIZATION_OPTIMIZATION_COMPLETE.md
```

### Branch Strategy

**Main branch:** `main` (production-ready code)

**Feature branches:** `feature/[description]` (if using branches)

**Rule:** Keep `main` stable and working

---

## 📦 Dependency Management

### Adding Dependencies

1. **Evaluate necessity** - Do we really need it?
2. **Check license** - Is it compatible?
3. **Test installation** - Does it work in our env?
4. **Update requirements.txt** - Pin versions
5. **Document in README** - Note any special setup

### Version Pinning

**Rule:** Pin versions for reproducibility

**Good:**
```
docling==1.2.3
sentence-transformers==2.2.2
```

**Bad:**
```
docling
sentence-transformers>=2.0
```

---

## 🔍 Code Review Checklist

Before considering work "done":

- [ ] **Functionality** - Does it work as intended?
- [ ] **Tests** - Have you tested it?
- [ ] **Documentation** - Is it documented?
- [ ] **Performance** - Is it fast enough?
- [ ] **Code quality** - Is it readable and maintainable?
- [ ] **Error handling** - What happens when it fails?
- [ ] **Configuration** - Any config changes needed?
- [ ] **Scripts updated** - scripts/README.md current?
- [ ] **Commit message** - Clear and descriptive?
- [ ] **No temp files** - Cleaned up after yourself?

---

## 📚 Documentation Maintenance

### When to Update

**Immediately update when:**
- Adding/modifying scripts
- Changing configuration
- Implementing major features
- Fixing significant bugs
- Optimizing performance

**Weekly review:**
- Session notes complete?
- Status docs current?
- README accurate?
- Script docs up-to-date?

### Documentation Locations Quick Reference

| What Changed | Update This |
|--------------|-------------|
| Added script | `scripts/README.md` |
| Major feature | `docs/technical/[FEATURE].md` |
| Performance fix | `docs/technical/[FIX].md` |
| Daily session | `docs/planning/sessions/SESSION_*.md` |
| Clean slate | `docs/status/CLEAN_SLATE_*.md` |
| Config change | `config/default.yaml` (comments) |
| Project overview | `readme.md` |

---

## 🚀 Quick Reference

### Starting Work
```bash
# 1. Check status
git status
git log --oneline -5

# 2. Review pickup doc (if exists)
cat docs/planning/sessions/SESSION_PICKUP_*.md

# 3. Activate environment
conda activate olmocr-optimized

# 4. Create session note
touch docs/planning/sessions/SESSION_$(date +%Y-%m-%d)_[TOPIC].md
```

### Testing Changes
```bash
# Run relevant test
python scripts/testing/test_[feature].py

# Measure performance
time python scripts/process_documents.py --auto --limit 10
```

### Ending Session
```bash
# 1. Update session doc with results
# 2. Commit changes
git add .
git commit -m "feat: [description]"

# 3. Create pickup doc if needed
# 4. Push changes (if applicable)
```

### Clean Slate
```bash
# Complete reset (only clears processed data)
./scripts/maintenance/clean_slate.sh

# Then manually rebuild when ready:
# 1. Rebuild inventory (when ready)
python scripts/rebuild_inventory.py

# 2. Process documents (when ready)
python scripts/process_documents.py --auto

# 3. Load to Qdrant (when ready)
python scripts/load_to_qdrant.py
```

---

## 🎯 Success Criteria

You're following these standards if:

- ✅ No scripts in root directory (except `main.py`)
- ✅ Every session has documentation
- ✅ Performance changes have before/after metrics
- ✅ All scripts documented in `scripts/README.md`
- ✅ Configuration in YAML, not hardcoded
- ✅ Can execute clean slate and rebuild anytime
- ✅ README accurately describes current state
- ✅ Commit messages explain WHY, not just WHAT
- ✅ No temporary files committed
- ✅ Input data is always preserved

---

**Remember:** These standards exist to make future work easier, not harder. When in doubt, ask: "Will future me thank me for this?"

Last updated: October 31, 2025
