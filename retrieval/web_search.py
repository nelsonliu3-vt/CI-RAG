"""
Web Search Module - Tavily Integration for CI-RAG

Provides web search capability for competitive intelligence analysis when
the vector store has insufficient documents. Uses Tavily API to fetch
relevant results and formats them for the analyst.

Features:
- Oncology-focused search queries
- Structured data extraction (efficacy, safety metrics)
- Strategic narrative analysis
- Format compatible with existing RAG pipeline
"""

import logging
from typing import List, Dict, Any, Optional
import re
from datetime import datetime

from core.config import (
    TAVILY_API_KEY,
    TAVILY_SEARCH_DEPTH,
    TAVILY_MAX_RESULTS,
    TAVILY_INCLUDE_ANSWER,
    TAVILY_INCLUDE_RAW_CONTENT,
    ONCOLOGY_KEYWORDS
)
from core.input_sanitizer import get_sanitizer

# Setup logging
logger = logging.getLogger(__name__)

# Global instance for singleton pattern
_web_search_instance = None


class TavilyWebSearch:
    """
    Web search integration using Tavily API for competitive intelligence.

    Automatically searches for oncology-focused CI data when the vector store
    is empty or has insufficient documents.
    """

    def __init__(self, api_key: str):
        """
        Initialize Tavily web search client.

        Args:
            api_key: Tavily API key
        """
        if not api_key:
            raise ValueError("Tavily API key is required for web search")

        try:
            from tavily import TavilyClient
            self.client = TavilyClient(api_key=api_key)
            self.sanitizer = get_sanitizer()
            logger.info("Tavily web search initialized successfully")
        except ImportError:
            raise ImportError(
                "tavily-python package not installed. "
                "Run: pip install tavily-python"
            )

    def search(
        self,
        query: str,
        top_k: int = 10,
        include_oncology_context: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search the web for competitive intelligence and format results
        for the analyst.

        Args:
            query: User's search query
            top_k: Maximum number of results to return
            include_oncology_context: Whether to add oncology-specific keywords

        Returns:
            List of formatted results compatible with analyst.generate_answer()
            Format: [{"text": str, "metadata": dict, "chunk_index": int, "doc_type": str}]
        """
        try:
            # Enhance query with oncology context if needed
            enhanced_query = self._enhance_query(query, include_oncology_context)

            logger.info(f"Searching web with Tavily: '{enhanced_query}'")

            # Call Tavily API
            search_results = self.client.search(
                query=enhanced_query,
                search_depth=TAVILY_SEARCH_DEPTH,
                max_results=min(top_k, TAVILY_MAX_RESULTS),
                include_answer=TAVILY_INCLUDE_ANSWER,
                include_raw_content=TAVILY_INCLUDE_RAW_CONTENT,
                include_domains=[
                    "clinicaltrials.gov",
                    "fda.gov",
                    "ema.europa.eu",
                    "nejm.org",
                    "thelancet.com",
                    "nature.com",
                    "asco.org",
                    "esmo.org",
                    "ncbi.nlm.nih.gov",
                    "pubmed.ncbi.nlm.nih.gov"
                ],
                # Exclude: blogs, forums, unreliable sources
                exclude_domains=[
                    "reddit.com",
                    "quora.com",
                    "medium.com",
                    "wikipedia.org"  # Prefer primary sources
                ]
            )

            # Format results for analyst
            formatted_results = []

            # Add Tavily's AI-synthesized answer if available
            if TAVILY_INCLUDE_ANSWER and search_results.get("answer"):
                formatted_results.append({
                    "text": f"[Tavily AI Summary]\n{search_results['answer']}",
                    "metadata": {
                        "file_name": "Web Search: AI-Synthesized Summary",
                        "detected_type": "web_search_summary",
                        "source": "Tavily AI",
                        "topics": self._extract_topics(query),
                        "url": "https://tavily.com",
                        "search_query": query,
                        "published": datetime.now().strftime("%Y-%m-%d")
                    },
                    "chunk_index": 0,
                    "doc_type": "web_search_summary"
                })

            # Process individual search results
            for idx, result in enumerate(search_results.get("results", []), start=1):
                # Validate URL for security
                url = result.get("url", "")
                if not self.sanitizer.validate_url(url):
                    logger.warning(f"Skipping invalid URL: {url}")
                    continue

                # Check oncology relevance
                content = result.get("content", "")
                if not self._is_oncology_relevant(content):
                    logger.info(f"Skipping non-oncology result: {url}")
                    continue

                # Extract structured data (efficacy, safety) if present
                structured_data = self._extract_structured_data(content)

                # Build formatted result
                formatted_result = {
                    "text": content,
                    "metadata": {
                        "file_name": f"Web Search Result: {result.get('title', 'Untitled')}",
                        "detected_type": self._detect_source_type(url),
                        "source": self._extract_domain(url),
                        "topics": self._extract_topics(content),
                        "url": url,
                        "title": result.get("title", ""),
                        "search_query": query,
                        "published": result.get("published_date", "Unknown"),
                        "score": result.get("score", 0.0),
                        **structured_data  # Add efficacy/safety if found
                    },
                    "chunk_index": idx,
                    "doc_type": self._detect_source_type(url)
                }

                formatted_results.append(formatted_result)

            logger.info(f"Retrieved {len(formatted_results)} relevant web search results")
            return formatted_results

        except Exception as e:
            logger.error(f"Web search failed: {str(e)}", exc_info=True)
            return []

    def _enhance_query(self, query: str, include_oncology_context: bool) -> str:
        """
        Enhance query with oncology-specific keywords for better results.

        Args:
            query: Original user query
            include_oncology_context: Whether to add oncology terms

        Returns:
            Enhanced query string
        """
        if not include_oncology_context:
            return query

        # Check if query already mentions oncology/cancer
        query_lower = query.lower()
        has_oncology_term = any(
            keyword in query_lower
            for category in ONCOLOGY_KEYWORDS.values()
            for keyword in category[:5]  # Check first 5 keywords per category
        )

        if has_oncology_term:
            return query  # Already has oncology context

        # Add oncology context
        return f"{query} oncology cancer clinical trial"

    def _is_oncology_relevant(self, text: str) -> bool:
        """
        Check if text content is relevant to oncology.

        Args:
            text: Content to check

        Returns:
            True if oncology-relevant, False otherwise
        """
        if not text:
            return False

        text_lower = text.lower()

        # Count oncology keyword matches
        matches = 0
        for category_keywords in ONCOLOGY_KEYWORDS.values():
            for keyword in category_keywords[:10]:  # Check first 10 per category
                if keyword in text_lower:
                    matches += 1

        # Require at least 3 keyword matches for relevance
        return matches >= 3

    def _extract_structured_data(self, content: str) -> Dict[str, Any]:
        """
        Extract structured efficacy and safety data from content.

        Looks for patterns like:
        - ORR: 45% (95% CI: 38-52%)
        - PFS: 8.2 months
        - Grade ≥3 AEs: 40%

        Args:
            content: Text content to parse

        Returns:
            Dictionary with extracted metrics
        """
        structured_data = {}

        # ORR pattern
        orr_match = re.search(
            r'ORR[:\s]+(\d+(?:\.\d+)?)\s*%',
            content,
            re.IGNORECASE
        )
        if orr_match:
            structured_data["orr"] = f"{orr_match.group(1)}%"

        # PFS pattern
        pfs_match = re.search(
            r'PFS[:\s]+(\d+(?:\.\d+)?)\s*months?',
            content,
            re.IGNORECASE
        )
        if pfs_match:
            structured_data["pfs"] = f"{pfs_match.group(1)} months"

        # OS pattern
        os_match = re.search(
            r'OS[:\s]+(\d+(?:\.\d+)?)\s*months?',
            content,
            re.IGNORECASE
        )
        if os_match:
            structured_data["os"] = f"{os_match.group(1)} months"

        # Grade ≥3 AEs pattern
        ae_match = re.search(
            r'Grade\s*[≥>=]+\s*3\s*AEs?[:\s]+(\d+(?:\.\d+)?)\s*%',
            content,
            re.IGNORECASE
        )
        if ae_match:
            structured_data["grade3_aes"] = f"{ae_match.group(1)}%"

        return structured_data

    def _detect_source_type(self, url: str) -> str:
        """
        Detect document type from URL.

        Args:
            url: Source URL

        Returns:
            Document type string
        """
        url_lower = url.lower()

        if "clinicaltrials.gov" in url_lower:
            return "clinical_trial_registry"
        elif any(domain in url_lower for domain in ["fda.gov", "ema.europa.eu"]):
            return "regulatory"
        elif any(domain in url_lower for domain in ["nejm.org", "thelancet.com", "nature.com", "pubmed"]):
            return "publication"
        elif any(domain in url_lower for domain in ["asco.org", "esmo.org"]):
            return "conference_abstract"
        else:
            return "news_article"

    def _extract_domain(self, url: str) -> str:
        """
        Extract clean domain name from URL.

        Args:
            url: Full URL

        Returns:
            Domain name (e.g., "nejm.org")
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path
            # Remove www.
            return domain.replace("www.", "")
        except:
            return "unknown"

    def _extract_topics(self, text: str) -> List[str]:
        """
        Extract relevant topics/keywords from text.

        Args:
            text: Content to analyze

        Returns:
            List of topic strings
        """
        topics = []
        text_lower = text.lower()

        # Check each oncology keyword category
        for category_name, keywords in ONCOLOGY_KEYWORDS.items():
            for keyword in keywords[:5]:  # First 5 keywords per category
                if keyword in text_lower:
                    topics.append(keyword)
                    if len(topics) >= 5:  # Limit to 5 topics
                        return topics

        return topics if topics else ["oncology"]


def get_web_search() -> Optional[TavilyWebSearch]:
    """
    Get singleton instance of TavilyWebSearch.

    Returns:
        TavilyWebSearch instance or None if API key not configured
    """
    global _web_search_instance

    if not TAVILY_API_KEY:
        logger.warning("Tavily API key not configured - web search disabled")
        return None

    if _web_search_instance is None:
        try:
            _web_search_instance = TavilyWebSearch(api_key=TAVILY_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialize web search: {str(e)}")
            return None

    return _web_search_instance


if __name__ == "__main__":
    # Test the module
    print("Testing Tavily Web Search Integration...")

    web_search = get_web_search()
    if web_search:
        print("✓ Web search initialized")

        # Test search
        results = web_search.search("CLDN18.2 ADC clinical trials efficacy safety", top_k=5)
        print(f"✓ Retrieved {len(results)} results")

        for i, result in enumerate(results[:3], 1):
            print(f"\nResult {i}:")
            print(f"  Title: {result['metadata'].get('title', 'N/A')}")
            print(f"  Source: {result['metadata'].get('source', 'N/A')}")
            print(f"  Type: {result['doc_type']}")
            print(f"  Content preview: {result['text'][:150]}...")
    else:
        print("✗ Web search not available (missing API key)")
