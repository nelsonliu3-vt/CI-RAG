"""
CI-RAG Configuration Module
Handles environment variables and o1-mini model configuration
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
PROCESSED_DIR = DATA_DIR / "processed"
QDRANT_STORAGE_DIR = DATA_DIR / "qdrant_storage"

# Ensure directories exist
for dir_path in [DATA_DIR, UPLOADS_DIR, PROCESSED_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables. Please add it to .env file.")

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")  # Optional, for web search

# GPT-5-mini Model Configuration (uses max_completion_tokens + reasoning_effort like o1-mini)
MODEL_CONFIG = {
    "gpt-5-mini": {
        "model": "gpt-5-mini",  # GPT-5 family - small, fast, cost-efficient
        "max_completion_tokens": 3000,  # Uses max_completion_tokens (like o1-mini)
        "reasoning_effort": "low",  # reasoning_effort parameter (like o1-mini)
        "provider": "openai"
    },
    # Fallback models
    "gpt-4o": {
        "model": "gpt-4o",
        "max_tokens": 4000,
        "temperature": 0.7,
        "provider": "openai"
    },
    "gpt-4o-mini": {
        "model": "gpt-4o-mini",
        "max_tokens": 4000,
        "temperature": 0.7,
        "provider": "openai"
    }
}

# Default model
DEFAULT_MODEL = "gpt-5-mini"

# Qdrant Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
QDRANT_COLLECTION_NAME = "ci_rag_documents"

# Embedding Configuration
EMBEDDING_MODEL = "text-embedding-3-large"  # OpenAI embedding model
EMBEDDING_DIMENSION = 3072  # text-embedding-3-large dimension
CHUNK_SIZE = 800  # tokens per chunk
CHUNK_OVERLAP = 100  # token overlap between chunks

# Retrieval Configuration
BM25_TOP_K = 50  # Top K for BM25 retrieval
DENSE_TOP_K = 50  # Top K for dense retrieval
RRF_K = 60  # RRF fusion constant
FINAL_TOP_K = 10  # Final number of documents to return after reranking

# Document Types (for auto-detection)
DOCUMENT_TYPES = {
    "publication": "Scientific publication (NEJM, JCO, Lancet, etc.)",
    "poster": "Conference poster/abstract",
    "csr": "Clinical Study Report",
    "presentation": "Slide deck / presentation",
    "regulatory": "FDA/EMA document",
    "news_article": "News article (Endpoints, STAT, Fierce)",
    "conference_news": "Conference newsletter (ESMO Daily, ASCO Daily)",
    "ci_email": "Competitive intelligence email",
    "other": "Uncategorized document"
}

# News Sources
NEWS_SOURCES = {
    "endpoints": ["endpts.com", "endpoints news"],
    "stat": ["statnews.com", "stat news"],
    "fierce": ["fiercepharma.com", "fierce pharma", "fierce biotech"]
}

# Conference News
CONFERENCE_NEWS = ["esmo daily", "asco daily", "ash daily", "aacr daily"]

# Journal Names (for publication detection)
JOURNAL_NAMES = [
    "nejm", "new england journal",
    "jco", "journal of clinical oncology",
    "lancet", "lancet oncology",
    "nature", "nature medicine",
    "science", "cell",
    "blood", "jama", "bmj"
]

# Competitive Intelligence Prompt Template
CI_ANALYST_PROMPT = """You are a competitive intelligence analyst specializing in pharmaceutical development.

Your task is to answer questions about clinical trials, competitive assets, and market positioning based on the provided source documents.

IMPORTANT RULES:
1. Always cite sources using [doc#page] format (e.g., [doc1#5])
2. Be specific with data - include percentages, confidence intervals, sample sizes
3. When comparing trials, note key differences (indication, line of therapy, biomarker selection)
4. For safety data, focus on Grade ≥3 AEs and discontinuation rates
5. If information is not in the sources, say "Information not found in provided sources"
6. Do not make up or invent information

SOURCES:
{sources}

QUESTION:
{question}

ANSWER:"""

# Comparison Table Prompt
COMPARISON_PROMPT = """You are a competitive intelligence analyst. Generate a comparison table for the given trials/assets.

Extract and compare the following information:
- Trial/Study name
- Indication (specific line of therapy)
- Sample size (n)
- Primary endpoint (ORR, PFS, OS with values and 95% CI)
- Key secondary endpoints
- Grade ≥3 AEs (%)
- Discontinuation rate (%)
- Key differentiators

Format as a markdown table. Always include source citations [doc#page].

SOURCES:
{sources}

QUERY:
{question}

COMPARISON TABLE:"""

# Program Impact Analysis Prompt (used when program profile exists)
CI_IMPACT_PROMPT = """You are a competitive intelligence analyst specializing in pharmaceutical development.

Your task is to analyze competitive intelligence and determine the IMPACT on YOUR PROGRAM.

YOUR PROGRAM CONTEXT:
{program_profile}

COMPETITIVE INTELLIGENCE (Retrieved Documents):
{sources}

QUESTION:
{question}

Provide a structured impact analysis with EXACTLY the following sections. Each section MUST be under 75 words and include specific data points.

## 🔬 Efficacy Impact
Compare competitive efficacy data to your program's metrics. Provide:
- Specific numbers (ORR, PFS, OS) with confidence intervals
- Direct comparison to YOUR program's data
- Assessment: POSITIVE / NEUTRAL / NEGATIVE for your program
- Cite sources [doc#page]

Limit: 75 words maximum.

## ⚠️ Safety Impact
Compare competitive safety profile to yours. Provide:
- Grade ≥3 AEs (%) - competitive vs. yours
- Discontinuation rates - competitive vs. yours
- Key differentiation opportunities or concerns
- Assessment: POSITIVE / NEUTRAL / NEGATIVE for your program
- Cite sources [doc#page]

Limit: 75 words maximum.

## 📋 Strategic & Regulatory Impact
What does this mean for your clinical and regulatory strategy? Provide:
- Specific actions to consider (trial design, endpoints, patient population)
- Regulatory implications (FDA approval bar, comparator choice)
- Timeline implications
- Priority level: HIGH / MEDIUM / LOW
- Cite sources [doc#page]

Limit: 75 words maximum.

---

CRITICAL FORMATTING REQUIREMENTS:
1. Use EXACTLY three sections with emoji headers as shown above
2. Each section MUST be ≤75 words (strictly enforced)
3. Each section MUST include an assessment rating
4. Always cite sources using [doc#page] format
5. Be specific with numbers - no vague statements
6. If data not in sources, state "Data not found in sources [specific metric]"
7. Do not make up or invent information
8. Do not add additional sections or commentary

Output format:
## 🔬 Efficacy Impact
[Your 75-word analysis here with citations]

## ⚠️ Safety Impact
[Your 75-word analysis here with citations]

## 📋 Strategic & Regulatory Impact
[Your 75-word analysis here with citations]

IMPACT ANALYSIS:"""

# SQLite Database Paths
DB_PATH = DATA_DIR / "metadata.db"  # Document metadata
DATABASE_PATH = DATA_DIR / "entities.db"  # Competitive intelligence entities

# Corrections File (JSON)
CORRECTIONS_FILE = DATA_DIR / "corrections.json"

# Document Curation & Relevance Scoring Configuration
RELEVANCE_THRESHOLDS = {
    "high_relevance": 0.7,
    "medium_relevance": 0.4,
    "low_relevance": 0.0,
}

RELEVANCE_WEIGHTS = {
    "indication_match": 0.30,
    "stage_alignment": 0.20,
    "target_match": 0.20,
    "competitor_signals": 0.15,
    "regulatory_relevance": 0.10,
    "clinical_relevance": 0.05,
}

DOCUMENT_TYPE_RELEVANCE_BOOST = {
    "regulatory": 1.2,
    "publication": 1.0,
    "csr": 1.0,
    "poster": 0.9,
    "presentation": 0.8,
    "conference_news": 0.7,
    "news_article": 0.6,
    "ci_email": 0.5,
    "other": 0.3,
}

# Show pre-upload warning if score below this threshold
PRE_UPLOAD_RELEVANCE_WARNING_THRESHOLD = 0.3

# Auto-archive documents below this threshold (None = disabled)
AUTO_ARCHIVE_THRESHOLD = None

# Search filtering defaults
DEFAULT_SEARCH_MIN_RELEVANCE = 0.0
ENABLE_RELEVANCE_BOOST_IN_SEARCH = True

# Oncology Focus Configuration
ONCOLOGY_KEYWORDS = {
    # Cancer types
    'cancer_types': [
        'cancer', 'tumor', 'tumour', 'carcinoma', 'sarcoma', 'melanoma', 'leukemia', 'leukaemia',
        'lymphoma', 'myeloma', 'glioma', 'blastoma', 'mesothelioma', 'oncology', 'oncological',
        'nsclc', 'sclc', 'crc', 'hcc', 'tnbc', 'aml', 'cll', 'all', 'cml', 'dlbcl', 'mcl',
        'glioblastoma', 'astrocytoma', 'neuroblastoma', 'hepatoblastoma', 'nephroblastoma'
    ],

    # Indications
    'indications': [
        'lung cancer', 'breast cancer', 'colorectal', 'prostate cancer', 'pancreatic cancer',
        'ovarian cancer', 'renal cell', 'hepatocellular', 'gastric cancer', 'esophageal',
        'bladder cancer', 'head and neck', 'thyroid cancer', 'endometrial', 'cervical cancer',
        'multiple myeloma', 'hodgkin', 'non-hodgkin', 'acute myeloid', 'chronic lymphocytic',
        'metastatic', 'advanced cancer', 'refractory', 'relapsed'
    ],

    # Treatments
    'treatments': [
        'chemotherapy', 'immunotherapy', 'radiotherapy', 'targeted therapy', 'hormone therapy',
        'car-t', 'car t', 'checkpoint inhibitor', 'pd-1', 'pd-l1', 'ctla-4', 'antibody-drug conjugate',
        'adc', 'kinase inhibitor', 'tyrosine kinase', 'monoclonal antibody', 'bispecific',
        'anti-cancer', 'anticancer', 'antineoplastic', 'cytotoxic', 'radiation', 'radiosurgery'
    ],

    # Biomarkers & Targets
    'biomarkers': [
        'kras', 'egfr', 'alk', 'ros1', 'braf', 'her2', 'erbb2', 'met', 'ret', 'ntrk',
        'brca', 'pik3ca', 'ras', 'tp53', 'atr', 'atm', 'pd-l1', 'msi', 'tmb', 'microsatellite',
        'bcr-abl', 'flt3', 'idh', 'jak', 'parp', 'vegf', 'vegfr', 'fgfr', 'igf1r'
    ],

    # Clinical terms
    'clinical': [
        'progression-free survival', 'overall survival', 'objective response', 'complete response',
        'partial response', 'disease control', 'recist', 'adverse event', 'dose-limiting toxicity',
        'maximum tolerated dose', 'phase 1', 'phase 2', 'phase 3', 'clinical trial', 'pfs', 'os', 'orr'
    ]
}

# Oncology relevance threshold (0-1)
ONCOLOGY_RELEVANCE_THRESHOLD = 0.3  # Warn if below this

# Web Search Configuration (Tavily)
WEB_SEARCH_ENABLED = bool(TAVILY_API_KEY)  # Auto-enable if API key present
WEB_SEARCH_MIN_DOC_THRESHOLD = int(os.getenv("WEB_SEARCH_MIN_DOC_THRESHOLD", "0"))  # Trigger when doc count ≤ this
TAVILY_SEARCH_DEPTH = os.getenv("TAVILY_SEARCH_DEPTH", "advanced")  # "basic" or "advanced"
TAVILY_MAX_RESULTS = int(os.getenv("TAVILY_MAX_RESULTS", "10"))
TAVILY_INCLUDE_ANSWER = os.getenv("TAVILY_INCLUDE_ANSWER", "true").lower() == "true"  # Get AI-synthesized answer
TAVILY_INCLUDE_RAW_CONTENT = os.getenv("TAVILY_INCLUDE_RAW_CONTENT", "true").lower() == "true"  # Get full page content
