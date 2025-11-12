# Dependency Diagram: app_simple.py

## Visual Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         app_simple.py (Streamlit UI)                │
│                                                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐    │
│  │  Section 1  │  │  Section 2  │  │      Section 3          │    │
│  │   Program   │→ │   Upload    │→ │   Analyze Impact        │    │
│  │    Input    │  │  Documents  │  │                         │    │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘    │
└───────────┬───────────────┬─────────────────┬───────────────────────┘
            │               │                 │
            ↓               ↓                 ↓
    ┌───────────────┐ ┌──────────────┐ ┌─────────────────┐
    │ Program       │ │  Document    │ │  Query &        │
    │ Profile       │ │  Processing  │ │  Answer Gen     │
    └───────────────┘ └──────────────┘ └─────────────────┘
```

## Detailed Module Dependencies

### Layer 1: UI Layer (Streamlit)
```
app_simple.py (602 lines)
    - Streamlit UI components
    - Session state management
    - User input handling
    - Result display
```

### Layer 2: Core Services

```
┌─────────────────────────────────────────────────────────────┐
│                     CORE SERVICES                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  core/config.py                                             │
│    ├─ Environment variables (OPENAI_API_KEY, QDRANT_HOST)  │
│    ├─ Constants (CHUNK_SIZE=500, EMBEDDING_MODEL)          │
│    └─ Feature flags (WEB_SEARCH_ENABLED)                   │
│                                                             │
│  core/input_sanitizer.py ★ SECURITY                        │
│    ├─ sanitize_query() - Prompt injection protection       │
│    ├─ sanitize_filename() - Path traversal protection      │
│    └─ validate_url() - SSRF protection                     │
│                                                             │
│  core/program_profile.py                                    │
│    ├─ save_profile() - Store program metadata              │
│    ├─ load_profile() - Retrieve program data               │
│    └─ SQLite: programs table                               │
│                                                             │
│  core/llm_client.py                                         │
│    ├─ OpenAI client initialization                         │
│    ├─ Error handling (rate limits, timeouts)               │
│    └─ Retry logic                                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Layer 3: Document Processing Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                  INGESTION PIPELINE                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ingestion/parser.py                                         │
│    ├─ parse_document(path) → {text, num_pages, metadata}    │
│    ├─ _parse_pdf() - PyPDF2                                 │
│    ├─ _parse_pptx() - python-pptx                           │
│    ├─ _parse_docx() - python-docx                           │
│    ├─ _parse_html() - BeautifulSoup                         │
│    ├─ _parse_eml() - email.parser                           │
│    └─ _parse_txt() - raw text                               │
│                                                              │
│                      ↓                                       │
│                                                              │
│  ingestion/detector.py                                       │
│    ├─ detect_document_type(parsed_doc)                      │
│    ├─ Patterns: press_release, clinical_trial, earnings     │
│    ├─ Extract: company, date, topics                        │
│    └─ Returns: {detected_type, source, topics, date}        │
│                                                              │
│                      ↓                                       │
│                                                              │
│  ingestion/entity_extractor.py (OPTIONAL)                   │
│    ├─ extract(text) - LLM-based entity extraction           │
│    ├─ Entities: companies, assets, trials                   │
│    └─ Returns: {companies[], assets[], trials[]}            │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Layer 4: Storage & Indexing

```
┌──────────────────────────────────────────────────────────────┐
│                  STORAGE LAYER                               │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  DUAL STORAGE PATTERN:                                       │
│                                                              │
│  ┌─────────────────┐         ┌─────────────────┐           │
│  │   Vector Store  │         │  Metadata Store │           │
│  │    (Qdrant)     │         │    (SQLite)     │           │
│  └─────────────────┘         └─────────────────┘           │
│          ↑                            ↑                      │
│          │                            │                      │
│  ┌───────┴────────┐          ┌────────┴────────┐           │
│  │                │          │                 │           │
│  │ retrieval/     │          │ memory/         │           │
│  │ vector_store.py│          │ simple_memory.py│           │
│  │                │          │                 │           │
│  │ Methods:       │          │ Methods:        │           │
│  │ • add_docs()   │          │ • add_doc()     │           │
│  │ • search()     │          │ • log_query()   │           │
│  │ • embed_batch()│          │ • get_stats()   │           │
│  │ • delete()     │          │ • mark_indexed()│           │
│  │                │          │                 │           │
│  └────────────────┘          └─────────────────┘           │
│                                                              │
│  memory/entity_store.py (OPTIONAL)                          │
│    ├─ add_company()                                         │
│    ├─ add_asset()                                           │
│    └─ add_trial()                                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Layer 5: Retrieval Pipeline

```
┌──────────────────────────────────────────────────────────────┐
│                  RETRIEVAL PIPELINE                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  HYBRID SEARCH ARCHITECTURE:                                 │
│                                                              │
│           User Query                                         │
│                │                                             │
│                ↓                                             │
│      ┌─────────────────┐                                    │
│      │ Input Sanitizer │ ★ SECURITY                         │
│      └────────┬─────────┘                                    │
│               │                                              │
│               ↓                                              │
│      ┌─────────────────────┐                                │
│      │  retrieval/         │                                │
│      │  hybrid_search.py   │                                │
│      │                     │                                │
│      │  Parallel Search:   │                                │
│      │  ┌─────┐  ┌──────┐ │                                │
│      │  │ BM25│  │Dense │ │                                │
│      │  │Sparse│  │Vector│ │                                │
│      │  └──┬──┘  └───┬──┘ │                                │
│      │     │         │    │                                │
│      │     └────┬────┘    │                                │
│      │          │         │                                │
│      │     ┌────▼────┐    │                                │
│      │     │   RRF   │    │  (Reciprocal Rank Fusion)      │
│      │     │ Fusion  │    │                                │
│      │     └────┬────┘    │                                │
│      └──────────┼─────────┘                                │
│                 │                                            │
│                 ↓                                            │
│      ┌─────────────────────┐                                │
│      │  retrieval/         │                                │
│      │  reranker.py        │                                │
│      │                     │                                │
│      │  • Cross-encoder    │                                │
│      │  • Relevance score  │                                │
│      │  • Top-k selection  │                                │
│      └─────────┬───────────┘                                │
│                │                                             │
│                ↓                                             │
│         Ranked Results                                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Layer 6: Answer Generation

```
┌──────────────────────────────────────────────────────────────┐
│                  GENERATION PIPELINE                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  generation/analyst.py                                       │
│                                                              │
│  ┌──────────────────────────────────────────┐              │
│  │  Context Assembly                        │              │
│  │  ├─ Top-k results from reranker          │              │
│  │  ├─ Program profile from program_profile │              │
│  │  └─ Query template from query_templates  │              │
│  └─────────────────┬────────────────────────┘              │
│                    │                                         │
│                    ↓                                         │
│  ┌──────────────────────────────────────────┐              │
│  │  Prompt Engineering                      │              │
│  │  ├─ System prompt (role, constraints)    │              │
│  │  ├─ Context insertion (retrieved docs)   │              │
│  │  ├─ Query insertion (sanitized)          │              │
│  │  └─ Output format instructions           │              │
│  └─────────────────┬────────────────────────┘              │
│                    │                                         │
│                    ↓                                         │
│  ┌──────────────────────────────────────────┐              │
│  │  LLM API Call                            │              │
│  │  ├─ Model: GPT-4 (gpt-4-turbo-preview)   │              │
│  │  ├─ Temperature: 0.0 (deterministic)     │              │
│  │  ├─ Max tokens: 2000                     │              │
│  │  └─ Error handling via llm_client.py     │              │
│  └─────────────────┬────────────────────────┘              │
│                    │                                         │
│                    ↓                                         │
│  ┌──────────────────────────────────────────┐              │
│  │  Post-Processing                         │              │
│  │  ├─ Extract citations [1], [2]           │              │
│  │  ├─ Format markdown                      │              │
│  │  └─ Add metadata                         │              │
│  └─────────────────┬────────────────────────┘              │
│                    │                                         │
│                    ↓                                         │
│              Final Answer                                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow Diagram

### Upload & Index Flow

```
User Upload File
      │
      ↓
┌──────────────────────────┐
│ app_simple.py:272-433    │
│ • Validate file size     │ ← core/input_sanitizer.sanitize_filename()
│ • Sanitize filename      │
│ • Save to data/uploads/  │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ ingestion/parser.py      │
│ • Detect format          │
│ • Extract text           │
│ • Extract metadata       │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ ingestion/detector.py    │
│ • Detect doc type        │
│ • Extract topics         │
│ • Extract date           │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ Chunk Text               │
│ • CHUNK_SIZE * 4 chars   │
│ • Sliding window         │
└──────────┬───────────────┘
           │
           ├──────────────────────────┬─────────────────────┐
           │                          │                     │
           ↓                          ↓                     ↓
┌────────────────────┐  ┌──────────────────────┐  ┌───────────────────┐
│ Vector Store       │  │ BM25 Index           │  │ SQLite Metadata   │
│ (Qdrant)           │  │ (In-Memory)          │  │                   │
│                    │  │                      │  │                   │
│ retrieval/         │  │ retrieval/           │  │ memory/           │
│ vector_store.py    │  │ hybrid_search.py     │  │ simple_memory.py  │
│                    │  │                      │  │                   │
│ • embed_batch()    │  │ • index_documents()  │  │ • add_document()  │
│ • add_documents()  │  │ • tokenize()         │  │ • mark_indexed()  │
└────────────────────┘  └──────────────────────┘  └───────────────────┘
```

### Query & Answer Flow

```
User Query (Program-Specific)
      │
      ↓
┌──────────────────────────┐
│ app_simple.py:480-594    │
│ • Auto-generate query    │
│ • Sanitize input         │ ← core/input_sanitizer.sanitize_query()
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ Hybrid Search            │
│ retrieval/               │
│ hybrid_search.py         │
│                          │
│ • BM25 search (sparse)   │
│ • Vector search (dense)  │ ← retrieval/vector_store.search()
│ • RRF fusion             │
│ • Top-k=10 results       │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ Reranking                │
│ retrieval/reranker.py    │
│ • Cross-encoder scoring  │
│ • Sort by relevance      │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ Answer Generation        │
│ generation/analyst.py    │
│                          │
│ • Load program profile   │ ← core/program_profile.load_profile()
│ • Assemble context       │
│ • Call GPT-4             │ ← core/llm_client.complete()
│ • Extract citations      │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ Program Impact Analysis  │
│ generation/analyst.py    │
│ • Efficacy impact        │
│ • Safety impact          │
│ • Clinical implications  │
│ • Strategic recommends   │
└──────────┬───────────────┘
           │
           ↓
┌──────────────────────────┐
│ Display Results          │
│ app_simple.py            │
│ • Render markdown        │
│ • Show citations         │
│ • Collect feedback       │ ← memory/simple_memory.log_query()
└──────────────────────────┘
```

## Dependency Matrix

### app_simple.py Imports

| Module | Purpose | Lines Used | Critical? |
|--------|---------|------------|-----------|
| `core/config` | Configuration | Throughout | ✅ Yes |
| `core/input_sanitizer` | Security | 298, 485 | ✅ Yes |
| `core/program_profile` | Program data | 68, 524 | ✅ Yes |
| `ingestion/parser` | Doc parsing | 188, 319 | ✅ Yes |
| `ingestion/detector` | Type detection | 194, 322 | ✅ Yes |
| `ingestion/entity_extractor` | Entity extraction | 378 | ⚠️ Optional |
| `memory/simple_memory` | Metadata storage | 116, 242, 364 | ✅ Yes |
| `memory/entity_store` | Entity storage | 379 | ⚠️ Optional |
| `retrieval/vector_store` | Vector DB | 106, 216, 338 | ✅ Yes |
| `retrieval/hybrid_search` | Search | 109, 229, 489 | ✅ Yes |
| `retrieval/reranker` | Reranking | 498 | ✅ Yes |
| `generation/analyst` | Answer gen | 503, 506 | ✅ Yes |

### Transitive Dependencies

**Core modules depend on:**
- `core/llm_client.py` ← `generation/analyst.py`, `ingestion/entity_extractor.py`
- `openai` library ← All LLM and embedding operations
- `qdrant_client` library ← `retrieval/vector_store.py`
- `rank_bm25` library ← `retrieval/hybrid_search.py`

**External Services:**
- OpenAI API (embeddings + completions)
- Qdrant server (vector storage)
- SQLite (metadata storage)

## Critical Path Analysis

### Must-Have Dependencies (11 modules)
These modules are required for core functionality:

1. `core/config.py` - Without this, nothing works (API keys, constants)
2. `core/input_sanitizer.py` - Security-critical
3. `core/program_profile.py` - Stores program context
4. `core/llm_client.py` - Wraps OpenAI API
5. `ingestion/parser.py` - Can't process documents without this
6. `ingestion/detector.py` - Document type detection
7. `memory/simple_memory.py` - Metadata storage
8. `retrieval/vector_store.py` - Vector search
9. `retrieval/hybrid_search.py` - Orchestrates search
10. `retrieval/reranker.py` - Improves result quality
11. `generation/analyst.py` - Generates answers

### Optional Dependencies (2 modules)
These enhance functionality but aren't strictly required:

1. `ingestion/entity_extractor.py` - Nice-to-have for entity graphs
2. `memory/entity_store.py` - Stores extracted entities

### External Dependencies (3 services)
- **OpenAI API** - CRITICAL (no fallback)
- **Qdrant Server** - CRITICAL (no fallback)
- **SQLite** - CRITICAL (but could be replaced with in-memory)

## Security Boundary Map

```
┌─────────────────────────────────────────────────────────────┐
│                    TRUST BOUNDARY                           │
│                                                             │
│  Internet → Streamlit UI → Input Sanitizer                 │
│                                                             │
│  ┌───────────────────────────────────────────────────┐    │
│  │              UNTRUSTED INPUT ZONE                 │    │
│  │                                                   │    │
│  │  • User-uploaded files                            │    │
│  │  • User-entered queries                           │    │
│  │  • User-pasted text                               │    │
│  │                                                   │    │
│  │  ↓ SANITIZATION LAYER ↓                           │    │
│  │                                                   │    │
│  │  core/input_sanitizer.py                          │    │
│  │  • sanitize_filename()  ← Path traversal filter  │    │
│  │  • sanitize_query()     ← Prompt injection filter│    │
│  │  • validate_url()       ← SSRF filter            │    │
│  │                                                   │    │
│  └───────────────────────────────────────────────────┘    │
│                           │                               │
│                           ↓                               │
│  ┌───────────────────────────────────────────────────┐    │
│  │              TRUSTED PROCESSING ZONE              │    │
│  │                                                   │    │
│  │  • Document parsing                               │    │
│  │  • Vector embedding                               │    │
│  │  • Search & retrieval                             │    │
│  │  • Answer generation                              │    │
│  │                                                   │    │
│  └───────────────────────────────────────────────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘

EXTERNAL SERVICES (Outside Trust Boundary):
  • OpenAI API (TLS encrypted, API key auth)
  • Qdrant Server (Local/Docker, no auth by default ⚠️)
```

## Performance Bottlenecks

### Identified Bottlenecks

1. **OpenAI Embedding API** (FIXED)
   - Before: 50+ sequential calls per document (50-100s)
   - After: 1-2 batch calls (2-5s)
   - Solution: `vector_store.embed_texts_batch()`

2. **Qdrant Vector Search**
   - Current: ~100-300ms per query
   - Acceptable for <10k documents
   - May need optimization at >100k documents

3. **BM25 Tokenization**
   - Current: ~10-50ms per query
   - Acceptable, but could be cached

4. **LLM Answer Generation**
   - Current: 2-10 seconds per query
   - Depends on OpenAI API latency
   - No local optimization possible

### Optimization Opportunities

- **Caching:** Add @st.cache_data for embeddings
- **Async:** Use asyncio for parallel API calls
- **Batching:** Batch multiple queries together
- **Precomputation:** Pre-embed common queries

---

## Module Relationship Summary

**Total Modules:** 12 Python files
**Total Lines:** ~5,000 (estimated across all modules)
**Dependency Depth:** 3 layers max (app → retrieval → vector_store → openai)
**Circular Dependencies:** ❌ None detected
**Singleton Pattern:** ✅ Used for all service modules (get_* functions)

---

**Document Version:** 1.0
**Created:** 2025-11-11
**Purpose:** Code review supporting material
