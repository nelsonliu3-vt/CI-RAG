"""
FastAPI Service for SAB App Integration
Exposes CI-RAG functionality via REST API
Includes API key authentication for security
"""

import logging
import os
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, Security, Depends
from fastapi.security import APIKeyHeader
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from generation.briefs import get_brief_generator
from generation.trial_comparator import get_trial_comparator
from generation.analyst import get_analyst
from retrieval.hybrid_search import get_hybrid_search
from core.program_profile import get_program_profile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API Key Authentication
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def get_allowed_api_keys() -> set:
    """Get allowed API keys from environment"""
    keys_str = os.getenv("ALLOWED_API_KEYS", "")
    if not keys_str:
        logger.warning("No ALLOWED_API_KEYS set in .env - API authentication disabled!")
        return set()
    return set(k.strip() for k in keys_str.split(",") if k.strip())

def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Verify API key from request header"""
    allowed_keys = get_allowed_api_keys()

    # If no keys configured, allow access (dev mode)
    if not allowed_keys:
        logger.warning("API authentication disabled - configure ALLOWED_API_KEYS in .env")
        return "dev-mode"

    # Verify key
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include 'X-API-Key' header."
        )

    if api_key not in allowed_keys:
        logger.warning(f"Invalid API key attempt: {api_key[:8]}...")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    return api_key

# FastAPI app
app = FastAPI(
    title="CI-RAG API",
    description="Competitive Intelligence RAG API for SAB Integration",
    version="1.0.0"
)

# CORS middleware (configure for production)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in CORS_ORIGINS],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class QueryRequest(BaseModel):
    query: str
    program_id: Optional[str] = None
    top_k: int = 10


class QueryResponse(BaseModel):
    answer: str
    sources: list
    program_context: Optional[str] = None


@app.get("/")
def root():
    """API root"""
    return {
        "service": "CI-RAG API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": ["/api/brief", "/api/trials", "/api/query"]
    }


@app.get("/health")
def health():
    """Health check"""
    return {"status": "healthy"}


@app.get("/api/brief")
def get_brief(
    program_id: Optional[str] = Query(None, description="Program ID (optional)"),
    weeks_back: int = Query(2, description="Weeks to look back"),
    api_key: str = Depends(verify_api_key)
):
    """
    Generate SAB Pre-Read brief (requires authentication)

    Args:
        program_id: Program identifier (currently uses active profile)
        weeks_back: Number of weeks to look back

    Returns:
        SAB Pre-Read brief with structured sections
    """
    try:
        generator = get_brief_generator()
        brief = generator.generate_preread(weeks_back=weeks_back)

        if "error" in brief:
            raise HTTPException(status_code=400, detail=brief["error"])

        return brief

    except Exception as e:
        logger.error(f"Error generating brief: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/trials")
def get_trials(
    program_id: Optional[str] = Query(None, description="Program ID (optional)"),
    query: str = Query("compare trials", description="Comparison query"),
    api_key: str = Depends(verify_api_key)
):
    """
    Generate trial comparison table (requires authentication)

    Args:
        program_id: Program identifier
        query: Comparison query

    Returns:
        Trial comparison table
    """
    try:
        # Retrieve relevant documents
        hybrid_search = get_hybrid_search()
        contexts = hybrid_search.hybrid_search(query, top_k=10)

        # Generate comparison
        comparator = get_trial_comparator()
        table = comparator.generate_comparison_table(query, contexts)

        return table

    except Exception as e:
        logger.error(f"Error generating trial comparison: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/query")
def query(request: QueryRequest, api_key: str = Depends(verify_api_key)):
    """
    Query CI-RAG with program context (requires authentication)

    Args:
        request: Query request with query text and optional program_id

    Returns:
        Answer with sources and citations
    """
    try:
        # Retrieve contexts
        hybrid_search = get_hybrid_search()
        contexts = hybrid_search.hybrid_search(request.query, top_k=request.top_k)

        # Generate answer (uses program profile automatically)
        analyst = get_analyst()
        answer = analyst.generate_answer(request.query, contexts)

        # Get program context if exists
        profile_manager = get_program_profile()
        program_context = None
        if profile_manager.has_profile():
            program_context = profile_manager.format_profile_context()

        return QueryResponse(
            answer=answer,
            sources=contexts,
            program_context=program_context
        )

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    print("Starting CI-RAG API server...")
    print("API docs available at: http://localhost:8503/docs")

    uvicorn.run(
        "api.service:app",
        host="0.0.0.0",
        port=8503,
        reload=True,
        log_level="info"
    )
