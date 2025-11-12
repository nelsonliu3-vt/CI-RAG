# CI-RAG Simplified App

A streamlined single-page application for competitive intelligence analysis.

## 🎯 What It Does

Upload competitor documents (slides, presentations, press releases) and get AI-powered competitive impact analysis for your program.

## 🚀 Quick Start

### 1. Start Required Services

```bash
# Start Docker (if not running)
open -a Docker

# Start Qdrant database
cd /Users/hantsungliu/CI-RAG
docker compose up -d
```

### 2. Run the App

```bash
cd /Users/hantsungliu/CI-RAG
streamlit run app_simple.py
```

The app will open at: http://localhost:8501

## 📝 How to Use

### Step 1: Enter Your Program Name
- Type your program name (e.g., "CLDN18.2 ADC for Gastric Cancer")
- Press Enter

### Step 2: Upload Competitor Documents
- Drag and drop files (PDF, PPTX, DOCX, HTML, EML)
- Max 50MB per file
- Wait for files to be indexed (shows ✓ when done)

### Step 3: Analyze Impact
- Enter your question (e.g., "Compare competitor efficacy and safety data")
- Click "🎯 Analyze Competitive Impact"
- Review the results:
  - **Answer**: Direct response to your question
  - **Impact Analysis**: Program-specific implications (4 sections)
  - **Sources**: Referenced document sections

## 📊 What's Under the Hood

The simplified app keeps all the intelligence:
- ✅ Document parsing (PDF, PPTX, DOCX, HTML, EML)
- ✅ Vector store indexing (Qdrant)
- ✅ Hybrid search (BM25 + Dense retrieval)
- ✅ Reranking for relevance
- ✅ Entity extraction (companies, trials, data)
- ✅ LLM-powered impact analysis
- ✅ Security protections (input sanitization, path traversal)

## 📁 Files

- `app_simple.py` - Simplified single-page app (411 lines)
- `app_ci_full.py` - Original full-featured app (2,085 lines) - archived
- `app_ci.py` - Can be replaced with simplified version if desired

## 🔧 Requirements

Same as the original app:
- Python 3.9+
- OpenAI API key (in .env)
- Qdrant database (via Docker)
- All backend modules in ingestion/, retrieval/, generation/, memory/, core/

## 💡 Key Differences from Full App

### Removed Features (Simplified UX)
- ❌ Classic/Focused mode toggle
- ❌ Multiple tabs
- ❌ Query templates
- ❌ Conversation mode
- ❌ Challenge mode
- ❌ Feedback system
- ❌ Gap analysis
- ❌ Report export
- ❌ Query history
- ❌ Web search fallback
- ❌ Oncology relevance checker
- ❌ Document library viewer
- ❌ Text paste input

### Kept Features (Core Functionality)
- ✅ Program name input
- ✅ File upload
- ✅ Document indexing
- ✅ Impact analysis
- ✅ Answer generation
- ✅ Source citations
- ✅ Simple feedback (thumbs up/down)

## 📈 Stats

- **Original:** 2,085 lines
- **Simplified:** 411 lines
- **Reduction:** 80% smaller
- **Functionality:** 100% of core features retained

## 🎨 UI Layout

```
┌─────────────────────────────────────┐
│  🔍 CI-RAG                          │
│  Competitive Intelligence Analysis  │
└─────────────────────────────────────┘

1️⃣ ENTER YOUR PROGRAM NAME
   [Text input]
   ✓ Program: CLDN18.2 ADC for 2L GC

2️⃣ UPLOAD COMPETITOR DOCUMENTS
   [Drag & Drop Area]
   ✓ Indexed: competitor_deck.pdf
   ✓ Indexed: press_release.docx
   Documents: 2 | Indexed: 2

3️⃣ ANALYZE COMPETITIVE IMPACT
   [Text area: What do you want to know?]
   [🎯 Analyze Competitive Impact]

───────────── RESULTS ─────────────

💡 ANSWER
[Generated answer with citations]

🎯 IMPACT ANALYSIS FOR YOUR PROGRAM
[4 sections: Efficacy, Safety, Clinical, Strategic]

📚 SOURCES
[Referenced document sections]
```

## 🔒 Security

All security protections from the original app are maintained:
- Input sanitization (prompt injection protection)
- Path traversal protection
- File size limits
- SSRF protection

## 🐛 Troubleshooting

**"Connection refused" error:**
- Make sure Docker is running: `open -a Docker`
- Start Qdrant: `docker compose up -d`
- Check containers: `docker ps`

**No results found:**
- Upload more relevant documents
- Try rephrasing your question
- Check that documents were indexed (shows ✓)

**File upload fails:**
- Check file size (max 50MB)
- Ensure file type is supported (PDF, PPTX, DOCX, HTML, EML)
- Check disk space in data/uploads/

## 📞 Support

For issues or questions, refer to the original documentation or check logs in the terminal.

---

**Built with:** Streamlit + OpenAI + Qdrant + Python
**Version:** 1.0 (Simplified)
**Date:** 2025-11-11
