# GitHub Copy Guide for CI-RAG

**Purpose:** Guide for copying CI-RAG to company GitHub repository

---

## ✅ Files TO COPY

### 1. **Core Application Files**
```
app_ci.py                    # Main Streamlit application
app_ci_cli.py                # CLI interface for POC
scheduler.py                 # Background task scheduler
theme_bootstrap.py           # Theme configuration
```

### 2. **Source Code Modules**

#### Core Module (`core/`)
```
core/
├── __init__.py
├── config.py                # System configuration
├── llm_client.py            # OpenAI API client
├── program_profile.py       # Program profile management
├── query_templates.py       # Query templates
├── relevance_scorer.py      # Relevance scoring
└── input_sanitizer.py       # Security: Input validation
```

#### CI POC Module (`ci/`) ⭐ NEW
```
ci/
├── __init__.py
├── config.py                # POC configuration ⭐ NEW
├── data_contracts.py        # Data structures ⭐ NEW
├── signals.py               # Signal detection ⭐ NEW
├── stance.py                # Stance analysis ⭐ NEW
├── writer.py                # Report generation ⭐ NEW
└── critic.py                # Validation gates ⭐ NEW
```

#### Ingestion Module (`ingestion/`)
```
ingestion/
├── __init__.py
├── parser.py                # Document parsing (PDF, text)
├── chunker.py               # Text chunking
├── detector.py              # Entity detection
├── entity_extractor.py      # LLM-based extraction
└── sources/
    ├── __init__.py
    ├── indexer.py           # Document indexing
    ├── rss_fetcher.py       # RSS feed fetching
    ├── pubmed_fetcher.py    # PubMed integration
    └── session_refresh.py   # Session management
```

#### Retrieval Module (`retrieval/`)
```
retrieval/
├── __init__.py
├── vector_store.py          # Qdrant integration
├── hybrid_search.py         # BM25 + semantic search
├── reranker.py              # Result reranking
└── web_search.py            # Tavily web search ⭐ NEW
```

#### Memory Module (`memory/`)
```
memory/
├── __init__.py
├── entity_store.py          # Entity storage
├── conversation_memory.py   # Chat history
├── feedback_store.py        # User feedback
└── simple_memory.py         # Simple KV store
```

#### Analysis Module (`analysis/`)
```
analysis/
├── gap_analyzer.py          # Gap analysis
└── challenge_generator.py   # Challenge generation
```

#### Export Module (`export/`)
```
export/
└── report_generator.py      # Report export
```

#### API Module (`api/`)
```
api/
├── __init__.py
└── service.py               # API service
```

### 3. **Test Suite**
```
tests/
├── __init__.py
├── test_signals.py          # Signal detection tests ⭐ NEW
├── test_stance.py           # Stance analysis tests ⭐ NEW
├── test_critic.py           # Critic gate tests ⭐ NEW
└── test_integration_day2.py # Integration tests ⭐ NEW
```

### 4. **Configuration Files**
```
requirements.txt             # Python dependencies
docker-compose.yml           # Docker setup for Qdrant
.env.example                 # Environment variables template (NO SECRETS)
```

### 5. **Documentation**
```
README.md                    # Main project README
CI_POC_README.md             # POC-specific documentation ⭐ NEW
CRITICAL_FIXES_COMPLETE.md   # Security fixes summary ⭐ NEW
ALL_IMPROVEMENTS_COMPLETE.md # All improvements summary ⭐ NEW
```

### 6. **Optional Documentation** (Choose what's relevant)
```
COMPREHENSIVE_CODE_ANALYSIS.md      # Code review
ANALYSIS_EXECUTIVE_SUMMARY.md       # Executive summary
SECURITY_IMPROVEMENTS_SUMMARY.md    # Security improvements
C4_ERROR_HANDLING_COMPLETE.md       # Error handling details
PHASE1_ENHANCEMENTS_SUMMARY.md      # Phase 1 work
PHASE2A_SMART_DATABASE_SUMMARY.md   # Phase 2A work
INSTALL_PHASE1.md                   # Installation guide
```

---

## ❌ Files NOT TO COPY

### 1. **Local Environment Files**
```
.env                         # ⚠️ CONTAINS SECRETS - DO NOT COPY
venv/                        # Python virtual environment
.venv/                       # Alternative venv location
__pycache__/                 # Python bytecode cache
*.pyc                        # Compiled Python files
*.pyo                        # Optimized Python files
.pytest_cache/               # Pytest cache
.DS_Store                    # macOS metadata
```

### 2. **Local Data & State**
```
data/                        # Local database, uploads, feedback
  ├── qdrant_storage/        # Qdrant vector database
  ├── uploads/               # User-uploaded files
  ├── feedback/              # User feedback data
  └── entities.db            # SQLite database

ci_rag.db                    # SQLite database
program_profile.db           # Program profiles
```

### 3. **Generated Outputs**
```
reports/                     # Generated reports
reports_test/                # Test reports
*.log                        # Log files
```

### 4. **IDE & Editor Files**
```
.idea/                       # PyCharm/IntelliJ
.vscode/                     # VS Code
*.swp                        # Vim swap files
*.swo                        # Vim swap files
*~                           # Backup files
```

### 5. **Backup & Working Versions**
```
working versions/            # Old backup versions
app_ci_backup.py             # Backup files
app_ci_tabs_original.py      # Original versions
app_ci_vertical.py           # Alternative layouts
```

### 6. **Git Metadata**
```
.git/                        # Git history (will be new repo)
.gitignore                   # Copy but modify for company standards
```

---

## 📋 Step-by-Step Copy Instructions

### Step 1: Prepare .env.example
```bash
# Create .env.example from your .env but REMOVE all actual secrets
# Replace with placeholders:

OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_qdrant_api_key_if_needed
```

### Step 2: Create .gitignore for Company Repo
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
env/
ENV/

# Environment
.env
.env.local

# Data & Databases
data/
*.db
*.sqlite
*.sqlite3

# Outputs
reports/
reports_test/
*.log
logs/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~
.DS_Store

# Testing
.pytest_cache/
.coverage
htmlcov/

# Temporary
*.tmp
temp/
tmp/
```

### Step 3: Directory Structure to Create
```
your-company-repo/
├── README.md
├── CI_POC_README.md
├── requirements.txt
├── docker-compose.yml
├── .env.example
├── .gitignore
├── app_ci.py
├── app_ci_cli.py
├── scheduler.py
├── theme_bootstrap.py
├── core/
├── ci/              ⭐ NEW POC module
├── ingestion/
├── retrieval/
├── memory/
├── analysis/
├── export/
├── api/
└── tests/           ⭐ NEW test suite
```

---

## 🔒 Security Checklist Before Copying

- [ ] Remove `.env` file (contains API keys)
- [ ] Create `.env.example` with placeholders only
- [ ] Remove `data/` directory (contains local database)
- [ ] Remove any `*.db` files
- [ ] Remove `reports/` and `reports_test/` directories
- [ ] Check all Python files for hardcoded credentials
- [ ] Review documentation for any sensitive information
- [ ] Remove backup files (`app_ci_backup.py`, etc.)
- [ ] Remove `working versions/` directory

---

## 📦 Recommended Copy Command

From your CI-RAG directory:

```bash
# Create a new directory for clean copy
mkdir ~/ci-rag-github-copy

# Copy essential files
cp -r core ci ingestion retrieval memory analysis export api tests ~/ci-rag-github-copy/

# Copy application files
cp app_ci.py app_ci_cli.py scheduler.py theme_bootstrap.py ~/ci-rag-github-copy/

# Copy configuration
cp requirements.txt docker-compose.yml ~/ci-rag-github-copy/

# Copy documentation (choose relevant ones)
cp README.md CI_POC_README.md CRITICAL_FIXES_COMPLETE.md ALL_IMPROVEMENTS_COMPLETE.md ~/ci-rag-github-copy/

# Create .env.example (manually, don't copy .env)
# Create .gitignore (use template above)

# Now push to company GitHub from ~/ci-rag-github-copy
```

---

## 🎯 Essential vs Optional Files

### **MUST COPY** (Core Functionality)
- All Python modules (`core/`, `ci/`, `ingestion/`, `retrieval/`, `memory/`)
- Main apps (`app_ci.py`, `app_ci_cli.py`)
- Configuration (`requirements.txt`, `docker-compose.yml`)
- Tests (`tests/`)
- Main documentation (`README.md`, `CI_POC_README.md`)

### **RECOMMENDED** (Enhanced Documentation)
- `CRITICAL_FIXES_COMPLETE.md` - Shows security work done
- `ALL_IMPROVEMENTS_COMPLETE.md` - Shows quality improvements
- `.env.example` - Setup guide

### **OPTIONAL** (Additional Context)
- Other markdown documentation files
- API service files (if not using API mode)
- Backup files (NOT recommended)

---

## 📊 File Count Summary

**Total Essential Files:** ~60 Python files + 10 config/doc files
**Total Size:** ~15,000 lines of code
**Modules:** 8 main modules + 1 new POC module

---

## ⚠️ Important Notes

1. **NEVER copy `.env`** - Contains API keys and secrets
2. **NEVER copy `data/` directory** - Contains local database and uploads
3. **DO create new `.env.example`** - Template for others to set up
4. **DO include tests/** - Demonstrates quality (44/44 passing)
5. **DO include CI_POC_README.md** - Documents POC work
6. **DO include security docs** - Shows production-readiness

---

## 🚀 After Copying to GitHub

### Initialize New Git Repo
```bash
cd ~/ci-rag-github-copy
git init
git add .
git commit -m "Initial commit: CI-RAG production-ready version"
git remote add origin <your-company-github-url>
git push -u origin main
```

### Set Up for Team
1. Update README.md with company-specific setup instructions
2. Add team members as collaborators
3. Set up branch protection rules
4. Configure CI/CD if needed
5. Set up GitHub secrets for API keys

---

**Last Updated:** 2025-11-10
**Version:** Production-ready with all security fixes and improvements
**Test Status:** 44/44 tests passing (100%)
