# Entity Extraction QA & Validation Plan

## 🎯 Purpose

Validate that GPT-4o-mini entity extraction is:
1. **Accurate** - Extracts real entities, not hallucinations
2. **Complete** - Doesn't miss critical entities
3. **Precise** - Correct entity types and roles
4. **Consistent** - Same input → same output (temperature=0.0)

---

## 🚨 Risk Assessment

### High-Risk Failure Modes:

1. **Hallucinations** - GPT invents entities not in the text
   - Example: Extracts "John Smith" when document says "Smith County"
   - Impact: Users cite non-existent parties/dates

2. **Missed Entities** - Critical information not extracted
   - Example: Missing grantor name in a deed
   - Impact: Incomplete legal analysis

3. **Type Misclassification** - Wrong entity type
   - Example: "Tract 7" labeled as ORG instead of PARCEL
   - Impact: Search/filtering doesn't work

4. **Role Misidentification** - Wrong legal role
   - Example: Grantee labeled as grantor
   - Impact: Legal analysis reversed

5. **Date Parsing Errors** - Incorrect date extraction
   - Example: "March 10, 1944" extracted as "March 10, 2044"
   - Impact: Timeline analysis broken

---

## ✅ QA Test Plan

### Phase 1: Manual Spot Check (30 min)

**Goal:** Quick validation that extraction is directionally correct

**Method:**
1. Take 3 representative chunks from test output
2. Manually read the source text
3. Compare GPT's entities vs what you see
4. Check for hallucinations, missed entities, wrong types

**Success Criteria:**
- ✅ Zero hallucinations (no fake entities)
- ✅ >90% of obvious entities found
- ✅ >95% correct entity types
- ✅ >90% correct roles (for PERSON/PARCEL)

**If fails:** Revise prompt, retest

---

### Phase 2: Ground Truth Validation (2-3 hours)

**Goal:** Create a small gold standard dataset for rigorous testing

**Method:**

1. **Select 5 diverse chunks:**
   - Title page (metadata-heavy)
   - Ownership table (structured data)
   - Legal description (parcels/acreage)
   - Assignment chain (dates/orgs)
   - Requirements section (mixed content)

2. **Manually annotate each chunk:**
   - List ALL entities (exhaustive)
   - Label each with type + role
   - Save as `test_output/ground_truth/chunk_N.json`

3. **Run entity extraction on same chunks**

4. **Compare results:**
   - Precision: What % of GPT's entities are correct?
   - Recall: What % of true entities did GPT find?
   - F1 Score: Harmonic mean of precision/recall

**Success Criteria:**
- ✅ Precision: >95% (low hallucination rate)
- ✅ Recall: >85% (acceptable miss rate for MVP)
- ✅ F1 Score: >90%

**Tools:** Create `validate_entities.py` script to automate comparison

---

### Phase 3: Edge Case Testing (1-2 hours)

**Goal:** Test failure modes and boundary conditions

**Test Cases:**

1. **Ambiguous Names**
   - Text: "Smith transferred to Jones"
   - Expected: PERSON (Smith), PERSON (Jones)
   - Risk: Might extract "Smith County" or miss context

2. **Compound Organizations**
   - Text: "Silver Hill Haynesville E&P, LLC, a Delaware limited liability company"
   - Expected: ORG (full legal name)
   - Risk: Might truncate or split

3. **Date Variations**
   - "December 5, 2022"
   - "12/5/2022"
   - "Dec. 5, 2022"
   - "the fifth day of December, 2022"
   - Expected: All extracted as DATE
   - Risk: Misses non-standard formats

4. **Legal Descriptions**
   - Text: "170.00 acres in the Benjamin C. Jordan Survey, A-348, Panola County, Texas"
   - Expected: PARCEL (entire description)
   - Risk: Might split into multiple parcels

5. **Tables/Structured Data**
   - HTML `<table>` content
   - Expected: Extract entities from cells
   - Risk: Might skip or misparse

6. **Role Ambiguity**
   - Text: "Assignment from A to B to C"
   - Expected: A=grantor, B=grantee (in first transfer), then B=grantor, C=grantee (in second)
   - Risk: Role confusion

**Success Criteria:**
- ✅ >80% correct on edge cases
- ✅ Document known failure modes

---

### Phase 4: Hallucination Detection (1 hour)

**Goal:** Ensure GPT doesn't invent entities

**Method:**

1. **Check entity provenance:**
   - For each extracted entity, verify it appears verbatim (or semantically) in source text
   - Flag any entity that doesn't match source

2. **Common hallucination patterns:**
   - Generic names ("John Doe", "Jane Smith")
   - Round numbers ("$1,000,000" when text says "$987,543")
   - Standardized dates (converting "circa 1940s" to "1945")
   - Inferred roles (assigning grantor when text doesn't specify)

3. **Automated check:**
   ```python
   def check_hallucination(entity_text, source_chunk):
       # Fuzzy match to account for OCR errors
       if fuzz.partial_ratio(entity_text, source_chunk) < 70:
           return "POTENTIAL_HALLUCINATION"
   ```

**Success Criteria:**
- ✅ <1% hallucination rate
- ✅ All flagged cases manually reviewed

---

### Phase 5: Consistency Testing (30 min)

**Goal:** Ensure deterministic extraction (temperature=0.0)

**Method:**

1. Run entity extraction 3 times on same chunk
2. Compare outputs - should be identical
3. Test with different API call timing (morning vs evening)

**Success Criteria:**
- ✅ 100% identical outputs across runs
- ✅ No variation due to OpenAI load balancing

---

## 📊 Metrics to Track

### Per-Document Metrics:
- Total entities extracted
- Entities per chunk (avg, min, max)
- Entity type distribution
- Role assignment rate (% of PERSON/PARCEL with roles)
- Confidence scores (avg, min)
- Cost per document

### Quality Metrics:
- Precision (against ground truth)
- Recall (against ground truth)
- F1 Score
- Hallucination rate
- Type accuracy
- Role accuracy

### Performance Metrics:
- Extraction time per chunk
- API latency (p50, p95, p99)
- Failure rate
- Retry rate

---

## 🔧 Recommended QA Tools

### 1. Ground Truth Builder (`build_ground_truth.py`)

```python
"""
Interactive tool to manually annotate entities in chunks.
Outputs JSON for automated validation.
"""

def annotate_chunk(chunk_text):
    """Present chunk text, allow user to mark entities"""
    # Show text with line numbers
    # User selects text spans + types + roles
    # Save as ground truth JSON
```

### 2. Entity Validator (`validate_entities.py`)

```python
"""
Compare extracted entities against ground truth.
Calculate precision, recall, F1.
"""

def compare_entities(extracted, ground_truth):
    """Calculate metrics and show mismatches"""
    # Match entities by text similarity (fuzzy)
    # Report: TP, FP, FN
    # Calculate precision, recall, F1
```

### 3. Hallucination Detector (`detect_hallucinations.py`)

```python
"""
Check if extracted entities appear in source text.
Flag potential hallucinations.
"""

def check_provenance(entity, source_text):
    """Verify entity exists in source"""
    # Fuzzy string matching
    # Return match score
```

### 4. Edge Case Tester (`test_edge_cases.py`)

```python
"""
Test specific challenging cases.
Maintain test suite of known-difficult examples.
"""

test_cases = [
    {
        "text": "Smith County conveyed to Jones...",
        "expected": [
            {"text": "Smith County", "type": "ORG", "role": "grantor"},
            {"text": "Jones", "type": "PERSON", "role": "grantee"}
        ]
    },
    # ... more cases
]
```

---

## 🚀 Implementation Priority

### MVP (Before Production):
1. ✅ **Phase 1: Manual Spot Check** (30 min) - Do this NOW
2. ✅ **Phase 4: Hallucination Detection** (1 hour) - Critical for trust
3. ⏳ **Phase 3: Edge Case Testing** (1-2 hours) - Identify failure modes

### Post-MVP (Continuous Improvement):
4. ⏳ **Phase 2: Ground Truth Validation** (2-3 hours) - Rigorous metrics
5. ⏳ **Phase 5: Consistency Testing** (30 min) - Verify determinism

### Production (Ongoing):
- Monitor hallucination rate on all extractions
- User feedback loop (flag incorrect entities)
- Quarterly prompt evaluation and refinement
- A/B test prompt variations

---

## 📋 Quick Start: Run Phase 1 Now

### Manual Spot Check Script:

```bash
# Create spot check tool
python create_spot_check.py

# Output: Shows 3 random chunks with side-by-side:
# - Source text
# - Extracted entities
# - Prompt for user validation (Y/N per entity)
```

Would you like me to:
1. **Create the spot check tool** to validate current results?
2. **Build the hallucination detector** to scan all 136 entities?
3. **Create ground truth annotations** for 5 chunks?

---

## 🎯 Recommendation

**Do Phase 1 (Manual Spot Check) RIGHT NOW:**
- Takes 30 minutes
- Catches major issues immediately
- Validates the 136 entities we just extracted
- Low effort, high value

**Then decide:**
- If spot check looks good → Move to Task 4 (Embeddings)
- If issues found → Fix prompt, retest
- For production → Complete Phases 2-5

---

**Status:** ⏳ QA Plan defined, not yet executed
**Risk Level:** 🔴 HIGH - Entity extraction not yet validated
**Action Required:** Run Phase 1 spot check before proceeding
