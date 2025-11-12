# Code Review Brief: app_simple.py

## Project Overview

**Project Name:** CI-RAG (Competitive Intelligence - Retrieval Augmented Generation)
**Primary File for Review:** `app_simple.py` (602 lines)
**Purpose:** Streamlit application for pharmaceutical competitive intelligence analysis
**Target Users:** Pharma competitive intelligence analysts and program teams

## What is app_simple.py?

`app_simple.py` is a simplified, user-friendly version of the main CI-RAG application. It provides a streamlined 3-step workflow:

1. **Enter Program Name** - User specifies their drug program
2. **Upload Documents** - Upload competitor press releases, trial results, presentations
3. **Analyze Impact** - AI-generated competitive impact analysis specific to their program

### Key Differences from Main App (app_ci.py)
- Simpler UI with single-page workflow
- Auto-analysis (no custom query required)
- Focuses on program-specific impact
- Removed advanced features (RSS feeds, PubMed, entity exploration)

## Architecture Overview

### Technology Stack

**Frontend:**
- Streamlit 1.28+ (Python web framework)
- Markdown rendering for results

**Backend:**
- **Vector Database:** Qdrant (dense embeddings)
- **Keyword Search:** BM25 (sparse retrieval)
- **LLM:** OpenAI GPT-4 (answer generation)
- **Embeddings:** OpenAI text-embedding-ada-002
- **Storage:** SQLite (document metadata, query logs)

**Document Processing:**
- PyPDF2 (PDF parsing)
- python-pptx (PowerPoint parsing)
- python-docx (Word parsing)
- BeautifulSoup (HTML parsing)

### System Architecture

```
User Input (Streamlit UI)
    ↓
Document Upload & Parsing (ingestion/)
    ↓
Chunking & Embedding (retrieval/vector_store.py)
    ↓
Dual Indexing:
    - Qdrant (dense vectors)
    - BM25 (sparse keywords)
    ↓
Query Processing (input sanitization)
    ↓
Hybrid Search (retrieval/hybrid_search.py)
    - BM25 results
    - Dense vector results
    - RRF (Reciprocal Rank Fusion)
    ↓
Reranking (retrieval/reranker.py)
    ↓
Answer Generation (generation/analyst.py)
    - Context assembly
    - LLM prompt engineering
    - Citation extraction
    ↓
Program Impact Analysis
    ↓
Display Results (Streamlit UI)
```

## Key Workflows

### 1. Document Upload Flow (lines 272-433)

**Process:**
1. User uploads files (PDF, PPTX, DOCX, HTML, EML)
2. **Security:** Filename sanitization (path traversal protection)
3. **Security:** File size validation (50MB limit)
4. Temporary storage in `data/uploads/`
5. Parse document → Extract text
6. Detect document type (press_release, clinical_trial, etc.)
7. Chunk text (CHUNK_SIZE * 4 characters per chunk)
8. Generate embeddings (OpenAI API)
9. Index to Qdrant vector store
10. Index to BM25 keyword store
11. Store metadata in SQLite
12. **Optional:** Entity extraction (companies, assets, trials)

**Key Security Features:**
- Path traversal protection via `input_sanitizer.sanitize_filename()`
- File size limits (50MB)
- Content hash-based doc IDs (SHA256)
- Path resolution validation

### 2. Text Paste Flow (lines 158-271)

**Process:**
- Alternative to file upload
- User pastes email/text content directly
- Same processing pipeline as file upload
- Useful for forwarded emails, web content

### 3. Analysis Flow (lines 480-594)

**Process:**
1. Auto-generate comprehensive query based on program name
2. **Security:** Query sanitization (prompt injection protection)
3. Hybrid search (BM25 + dense vectors, top_k=10)
4. Reranking results by relevance
5. Generate basic answer (efficacy, safety, clinical data)
6. Generate program-specific impact analysis:
   - Efficacy impact
   - Safety impact
   - Clinical & regulatory implications
   - Strategic recommendations
7. Display results with citations
8. Collect user feedback (thumbs up/down)

**Key Security Features:**
- Input sanitization via `input_sanitizer.sanitize_query()`
- Max query length: 2000 characters
- Prompt injection detection (15+ patterns)

## Module Dependencies

### Core Modules (4 files)
- `core/config.py` - Configuration constants (CHUNK_SIZE, API keys)
- `core/input_sanitizer.py` - Security utilities (NEW in security review)
- `core/program_profile.py` - Program metadata storage
- `core/llm_client.py` - OpenAI API wrapper with error handling

### Ingestion Modules (2 files)
- `ingestion/parser.py` - Document parsing (PDF, PPTX, DOCX, HTML, EML)
- `ingestion/detector.py` - Document type detection (regex + heuristics)
- `ingestion/entity_extractor.py` - Entity extraction (companies, drugs, trials)

### Memory Modules (2 files)
- `memory/simple_memory.py` - SQLite wrapper (documents, queries, feedback)
- `memory/entity_store.py` - Entity relationship storage

### Retrieval Modules (3 files)
- `retrieval/vector_store.py` - Qdrant vector DB wrapper with batch embeddings
- `retrieval/hybrid_search.py` - BM25 + dense search with RRF fusion
- `retrieval/reranker.py` - Rerank results by relevance

### Generation Modules (1 file)
- `generation/analyst.py` - LLM-based answer generation with citations

**Total Dependencies:** 12 Python modules + Streamlit + external services (Qdrant, OpenAI)

## Security Features Implemented

The application has undergone comprehensive security hardening (see `SECURITY_IMPROVEMENTS_SUMMARY.md`):

### Critical Fixes (5/6 Complete)

1. **✅ Path Traversal Protection (C1)**
   - Location: app_simple.py:298-308
   - Defense: `os.path.basename()` + character whitelist + UUID prefix + path verification

2. **✅ Batch Embedding API (C2)**
   - Location: retrieval/vector_store.py
   - Impact: 98% reduction in API calls (50+ → 1-2), 95% faster indexing

3. **✅ Prompt Injection Protection (C3)**
   - Location: core/input_sanitizer.py
   - Defense: 15+ suspicious pattern detection, control char removal, 2000 char limit

4. **⏳ Comprehensive Error Handling (C4)**
   - Status: Partially complete, medium priority

5. **✅ SSRF Protection (C5)**
   - Location: ingestion/sources/rss_fetcher.py (not used in app_simple.py)
   - Defense: Private IP blocking, localhost blocking, URL validation

6. **✅ Upload Security (C6)**
   - Location: app_simple.py:288-298
   - Defense: 50MB size limit, filename sanitization

### Input Sanitization (`core/input_sanitizer.py`)

**Capabilities:**
- **Query Sanitization:** Detects prompt injection patterns like:
  - "ignore previous instructions"
  - "system:" / "assistant:" role injection
  - Excessive repetition
  - Control characters
- **Filename Sanitization:** Strips path traversal attempts (`../`, `..\\`)
- **URL Validation:** Blocks SSRF attacks (private IPs, localhost, cloud metadata)

## Performance Optimizations

### Batch Embeddings (Critical Improvement)
**Before:** 50+ sequential OpenAI API calls per document (50-100 seconds)
**After:** 1-2 batch API calls (2-5 seconds)
**Impact:** ~95% faster document indexing

### Hybrid Search Strategy
- **BM25:** Fast keyword matching (milliseconds)
- **Dense:** Semantic similarity (hundreds of milliseconds)
- **RRF:** Combines both rankings effectively
- **Result:** Best of both worlds (speed + accuracy)

## Known Issues & Technical Debt

### From Code Analysis (See COMPREHENSIVE_CODE_ANALYSIS.md)

1. **C4: Error Handling** (Medium Priority)
   - Generic `Exception` catches in 4 locations
   - Missing specific error types for network, API, file I/O
   - Status: Partially addressed in C4_ERROR_HANDLING_COMPLETE.md

2. **Database Connection Management** (Low Priority)
   - SQLite connections not explicitly closed
   - Relies on garbage collection
   - Risk: Connection leaks in long-running sessions

3. **No Rate Limiting** (Medium Priority)
   - Unlimited document uploads per session
   - No API call throttling
   - Risk: Abuse, cost overruns

4. **No Authentication** (High Priority for Production)
   - Anyone with URL can access
   - No user separation
   - Risk: Data leakage, unauthorized access

## Code Quality Metrics

### Complexity
- **Total Lines:** 602
- **Functions:** ~8 major code blocks
- **Cyclomatic Complexity:** Low-Medium
- **Imports:** 12 local modules + 7 standard library

### Maintainability
- **Strengths:**
  - Clear 3-section structure (Program → Upload → Analyze)
  - Good use of Streamlit components
  - Comprehensive error messages

- **Weaknesses:**
  - Long functions (upload handling: 160 lines)
  - Duplicate code (upload vs. paste flows)
  - No extraction into helper functions

### Test Coverage
- **Status:** No automated tests
- **Manual Testing:** Via Playwright browser automation
- **Coverage:** ~70% of main workflows tested manually

## File Manifest for Review

### Essential Files (15 files)

**Main Application:**
1. `app_simple.py` - Primary file for review (602 lines)

**Core Modules:**
2. `core/config.py` - Configuration
3. `core/input_sanitizer.py` - Security (229 lines)
4. `core/program_profile.py` - Program metadata
5. `core/llm_client.py` - OpenAI wrapper

**Ingestion:**
6. `ingestion/parser.py` - Document parsing
7. `ingestion/detector.py` - Type detection
8. `ingestion/entity_extractor.py` - Entity extraction

**Memory:**
9. `memory/simple_memory.py` - SQLite wrapper
10. `memory/entity_store.py` - Entity storage

**Retrieval:**
11. `retrieval/vector_store.py` - Qdrant wrapper
12. `retrieval/hybrid_search.py` - BM25 + dense search
13. `retrieval/reranker.py` - Result reranking

**Generation:**
14. `generation/analyst.py` - Answer generation

**Configuration:**
15. `requirements.txt` - Dependencies

### Optional Context (8 files)

16. `README.md` - Project overview
17. `.env.example` - Environment variable template
18. `CLAUDE.md` - Development session logs (27KB)
19. `SECURITY_IMPROVEMENTS_SUMMARY.md` - Security review
20. `C4_ERROR_HANDLING_COMPLETE.md` - Error handling work
21. `COMPREHENSIVE_CODE_ANALYSIS.md` - Full code audit (27KB)
22. `DEPENDENCY_DIAGRAM.md` - Architecture visualization (you're creating this)
23. `REVIEW_QUESTIONS.md` - Focus areas for review (you're creating this)

## Development Context

### Recent Work (Past 2 Weeks)
- **Security Hardening:** 5/6 critical vulnerabilities fixed
- **Performance:** 95% faster indexing via batch embeddings
- **Error Handling:** Comprehensive try-catch blocks added
- **Documentation:** 4 major docs created (CLAUDE.md, SECURITY, C4, ANALYSIS)

### Production Readiness
- **Security:** ✅ Ready (5/6 critical fixes)
- **Performance:** ✅ Optimized
- **Error Handling:** ⚠️ Mostly complete (C4 in progress)
- **Testing:** ⚠️ Manual only (no automated tests)
- **Auth:** ❌ Not implemented

### Deployment Status
- **Environment:** Local development (Streamlit)
- **Database:** Local Qdrant instance
- **Storage:** Local SQLite + file system
- **Target:** Railway deployment planned

## Review Focus Areas

Please see `REVIEW_QUESTIONS.md` for specific questions to guide your review.

Key areas of interest:
1. **Security:** Any vulnerabilities missed in security review?
2. **Architecture:** Is the module separation appropriate?
3. **Code Quality:** Readability, maintainability, best practices
4. **Error Handling:** Are edge cases handled?
5. **Performance:** Any obvious bottlenecks?
6. **Streamlit Best Practices:** Proper use of session state, caching?

---

## Quick Start for Reviewers

### Setup (5 minutes)
```bash
cd /Users/hantsungliu/CI-RAG
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Add your OpenAI API key to .env

# Start Qdrant (Docker)
docker run -p 6333:6333 qdrant/qdrant

# Run app
streamlit run app_simple.py
```

### Test Workflow
1. Enter program name: "CLDN18.2 ADC in Gastric Cancer"
2. Upload sample document: `test_sample.txt`
3. Click "Analyze Competitive Impact"
4. Review generated analysis

---

**Document Version:** 1.0
**Created:** 2025-11-11
**Author:** CI-RAG Development Team
**Contact:** via GitHub issues
