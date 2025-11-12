# CI-RAG: Competitive Intelligence RAG System

**Auto-sort uploads • Smart hybrid retrieval • Cited insights**

A powerful RAG system for competitive intelligence that automatically detects document types (publications, Endpoints News, ESMO Daily, CI emails, posters, CSRs, presentations), indexes them with hybrid search (BM25 + dense embeddings), and generates cited insights using GPT-5-mini.

## Features

✅ **Auto-sort 8 document types** - Detects publications, posters, CSRs, news articles, CI emails, conference news, presentations, regulatory docs
✅ **Multi-format support** - PDF, PPTX, HTML, EML, TXT, MD
✅ **Hybrid retrieval** - BM25 (sparse) + dense embeddings + RRF fusion + cross-encoder reranking
✅ **Smart citations** - Every answer includes inline citations with doc#page references
✅ **Comparison tables** - Auto-generates comparison tables for "compare X vs Y" queries
✅ **Persistent memory** - Remembers all uploads, user corrections, query history (SQLite)
✅ **Learning over time** - Tracks feedback (thumbs up/down) to improve retrieval
✅ **Clean UI** - 2-tab Streamlit interface (Upload & Query)

## Quick Start

### 1. Prerequisites

- Python 3.9+
- Docker (for Qdrant)
- OpenAI API key (GPT-5-mini)

### 2. Installation

```bash
cd CI-RAG

# Install dependencies
pip install -r requirements.txt

# Start Qdrant vector database
docker-compose up -d

# Verify Qdrant is running
curl http://localhost:6333/health
# Should return: {"title":"qdrant - vector search engine","version":"1.7.4"}
```

### 3. Configure Environment

Your `.env` file should already have:
```bash
OPENAI_API_KEY=your-key-here
```

### 4. Run the App

```bash
streamlit run app_ci.py --server.port=8501
```

Open browser at: **http://localhost:8501**

## Usage

### Upload & Index Documents

1. Go to **Tab 1: Upload & Index**
2. Drag & drop files (PDF, PPTX, HTML, EML, etc.)
3. System auto-detects type (e.g., "Endpoints News", "Publication", "ESMO Daily")
4. Click **Index** to process
5. Document is chunked, embedded, and stored in Qdrant + BM25 index
6. See all indexed documents below

**Supported document types:**
- 📰 **News articles**: Endpoints News, STAT, FiercePharma
- 📰 **Conference news**: ESMO Daily, ASCO Daily, ASH Daily
- 📧 **CI emails**: Competitive intelligence emails (.eml, .msg)
- 📄 **Publications**: NEJM, JCO, Lancet, Nature
- 📊 **Posters**: ASCO/ESMO abstracts
- 📑 **CSRs**: Clinical Study Reports
- 📽️ **Presentations**: Slide decks (PPTX)
- 📋 **Regulatory**: FDA/EMA documents

### Query & Get Insights

1. Go to **Tab 2: Query & Insights**
2. Ask questions:
   - **Factual**: "What is the ORR for Trial X?"
   - **Comparison**: "Compare ORR across KRAS inhibitor trials"
   - **Safety**: "What are Grade ≥3 AE rates for PD-1 inhibitors?"
3. System:
   - Runs hybrid search (BM25 + dense)
   - Reranks with cross-encoder
   - Generates answer with GPT-5-mini
   - Includes inline citations
4. Click 👍 or 👎 to give feedback

## Architecture

```
CI-RAG/
├── core/               # Core infrastructure
│   ├── config.py      # Settings (GPT-5-mini config)
│   └── llm_client.py  # OpenAI wrapper
├── ingestion/          # Document processing
│   ├── parser.py      # Unstructured (PDF/PPTX/HTML/EML)
│   └── detector.py    # Auto-detect document types
├── memory/             # SQLite storage
│   └── simple_memory.py  # Documents + corrections + query log
├── retrieval/          # Hybrid search
│   ├── vector_store.py   # Qdrant (dense retrieval)
│   ├── hybrid_search.py  # BM25 + dense + RRF fusion
│   └── reranker.py       # Cross-encoder reranking
├── generation/         # LLM generation
│   ├── analyst.py        # Competitive intelligence prompt
│   └── citations.py      # Citation formatting
├── app_ci.py           # Streamlit UI
├── data/               # Data directories
│   ├── uploads/        # Uploaded files
│   └── metadata.db     # SQLite database
└── docker-compose.yml  # Qdrant container
```

### How It Works

1. **Upload** → Parser extracts text → Detector classifies type → Auto-sorted
2. **Index** → Text chunked (800 tokens) → Embedded (text-embedding-3-large) → Stored in Qdrant + BM25 index
3. **Query** → Hybrid search (BM25 top-50 + dense top-50 → RRF fusion → Rerank → top-10)
4. **Generate** → GPT-5-mini generates answer from top-10 contexts with citations
5. **Feedback** → Thumbs up/down logged for future learning

## Sample Queries

**Factual:**
- "What was the ORR in the Amgen KRAS trial?"
- "What endpoints were used in Phase 2 EGFR trials?"

**Comparison:**
- "Compare ORR and PFS for KRAS inhibitors in 2L NSCLC"
- "What are the safety differences between PD-1 monotherapy vs combo?"

**Market Intelligence:**
- "Which assets are approved for 3L colorectal cancer?"
- "What trials tested PD-1 inhibitors in 1L NSCLC?"

## Configuration

Edit `core/config.py` to customize:

```python
# Model
DEFAULT_MODEL = "gpt-5-mini"  # Or "gpt-4o", "gpt-4o-mini"

# Retrieval
BM25_TOP_K = 50        # BM25 candidates
DENSE_TOP_K = 50       # Dense candidates
RRF_K = 60            # RRF fusion constant
FINAL_TOP_K = 10      # Final results after reranking

# Chunking
CHUNK_SIZE = 800      # Tokens per chunk
CHUNK_OVERLAP = 100   # Overlap between chunks
```

## Testing Individual Modules

```bash
# Test parser
python ingestion/parser.py your_file.pdf

# Test detector
python ingestion/detector.py your_file.pdf

# Test LLM client
python core/llm_client.py

# Test vector store (requires Qdrant running)
python retrieval/vector_store.py

# Test memory
python memory/simple_memory.py
```

## Troubleshooting

**Qdrant not running:**
```bash
cd CI-RAG
docker-compose up -d
```

**Port 6333 already in use:**
```bash
docker-compose down
lsof -ti:6333 | xargs kill
docker-compose up -d
```

**Dependencies not installed:**
```bash
pip install -r requirements.txt
```

**Unstructured not working:**
```bash
# If Unstructured fails, it falls back to pypdf/beautifulsoup
# For full Unstructured support:
pip install unstructured[all-docs]
```

**OpenAI API key not found:**
```bash
# Check .env file in CI-RAG directory
cat .env
# Should show: OPENAI_API_KEY=sk-...
```

## Roadmap (Post-MVP)

**Week 2 Enhancements:**
- [ ] Comparison table generation (trial-by-trial)
- [ ] User corrections (edit answers, system remembers)
- [ ] Document library view with filters

**Week 3+ (Advanced):**
- [ ] GraphRAG for multi-hop queries
- [ ] RAPTOR for long documents (CSRs)
- [ ] RAGAS evaluation pipeline
- [ ] Learning-to-rank optimization
- [ ] ClinicalTrials.gov API integration

## Tech Stack

**Document Processing:**
- Unstructured (PDF/PPTX parsing)
- BeautifulSoup (HTML)
- email (EML parsing)

**Retrieval:**
- Qdrant (vector DB)
- OpenAI text-embedding-3-large
- rank-bm25 (sparse retrieval)
- sentence-transformers (reranking)

**Generation:**
- OpenAI GPT-5-mini
- Custom CI analyst prompts

**Infrastructure:**
- Streamlit (UI)
- SQLite (memory)
- Docker (Qdrant)

## Contributing

This is an MVP for demonstrating value. Feedback welcome!

## License

Internal use - proprietary

---

**Built with ❤️ for competitive intelligence teams**

*Auto-sort uploads • Smart hybrid retrieval • Cited insights*
