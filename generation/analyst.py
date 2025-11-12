"""
Competitive Intelligence Analyst Module
Generates insights from retrieved documents
"""

import logging
from typing import List, Dict, Any, Optional

from core.llm_client import get_llm_client
from core.config import CI_ANALYST_PROMPT, COMPARISON_PROMPT, CI_IMPACT_PROMPT
from core.program_profile import get_program_profile
from core.input_sanitizer import get_sanitizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CompetitiveAnalyst:
    """Generate competitive intelligence insights"""

    def __init__(self, model_name: str = "gpt-5-mini"):
        """Initialize analyst with LLM"""
        self.llm = get_llm_client(model_name)
        self.model_name = model_name

    def generate_answer(
        self,
        query: str,
        contexts: List[Dict[str, Any]]
    ) -> str:
        """
        Generate answer from retrieved contexts

        Args:
            query: User query
            contexts: List of retrieved documents with text and metadata

        Returns:
            Generated answer with citations (personalized if profile exists)
        """
        # Sanitize query to prevent prompt injection
        sanitizer = get_sanitizer()
        try:
            sanitized_query = sanitizer.sanitize_query(query, max_length=2000, strict=False)
            if sanitized_query != query:
                logger.warning("Query was sanitized for security")
        except ValueError as e:
            logger.error(f"Query rejected: {e}")
            return f"Error: Invalid query. {str(e)}"

        # Format sources
        sources_text = self._format_sources(contexts)

        # Check if program profile exists
        profile_manager = get_program_profile()
        has_profile = profile_manager.has_profile()

        # Choose prompt based on whether profile exists
        if has_profile:
            # Use impact analysis prompt with program context
            program_context = profile_manager.format_profile_context()
            prompt = CI_IMPACT_PROMPT.format(
                program_profile=program_context,
                sources=sources_text,
                question=sanitized_query  # Use sanitized query
            )
            logger.info("Using personalized impact analysis mode")
        else:
            # Use standard CI analyst prompt
            prompt = CI_ANALYST_PROMPT.format(
                sources=sources_text,
                question=sanitized_query  # Use sanitized query
            )
            logger.info("Using general CI Q&A mode (no program profile)")

        try:
            # Generate answer
            answer = self.llm.generate_with_context(
                prompt_template="{prompt}",
                context={"prompt": prompt}
            )

            logger.info(f"✓ Generated answer ({len(answer)} chars)")
            return answer

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return f"Error generating answer: {str(e)}"

    def generate_comparison(
        self,
        query: str,
        contexts: List[Dict[str, Any]]
    ) -> str:
        """
        Generate comparison table from retrieved contexts

        Args:
            query: Comparison query
            contexts: List of retrieved documents

        Returns:
            Markdown comparison table with citations
        """
        # Sanitize query to prevent prompt injection
        sanitizer = get_sanitizer()
        try:
            sanitized_query = sanitizer.sanitize_query(query, max_length=2000, strict=False)
            if sanitized_query != query:
                logger.warning("Comparison query was sanitized for security")
        except ValueError as e:
            logger.error(f"Query rejected: {e}")
            return f"Error: Invalid query. {str(e)}"

        # Format sources
        sources_text = self._format_sources(contexts)

        # Fill in prompt
        prompt = COMPARISON_PROMPT.format(
            sources=sources_text,
            question=sanitized_query  # Use sanitized query
        )

        try:
            # Generate comparison
            comparison = self.llm.generate_with_context(
                prompt_template="{prompt}",
                context={"prompt": prompt}
            )

            logger.info(f"✓ Generated comparison table")
            return comparison

        except Exception as e:
            logger.error(f"Error generating comparison: {e}")
            return f"Error generating comparison: {str(e)}"

    def _format_sources(self, contexts: List[Dict[str, Any]]) -> str:
        """Format retrieved contexts as numbered sources"""
        sources = []

        for i, ctx in enumerate(contexts, 1):
            text = ctx.get("text", "")
            metadata = ctx.get("metadata", {})

            # Get document info
            filename = metadata.get("file_name", "Unknown")
            page = ctx.get("chunk_index", 0) + 1  # Page number (chunk index + 1)
            doc_type = ctx.get("doc_type", "")
            source = ctx.get("source", "")

            # Format source
            source_text = f"[{i}] **{filename}** (Page {page})\n"
            if doc_type:
                source_text += f"   Type: {doc_type}\n"
            if source:
                source_text += f"   Source: {source}\n"
            source_text += f"   Content: {text}\n"

            sources.append(source_text)

        return "\n".join(sources)

    def is_comparison_query(self, query: str) -> bool:
        """Detect if query is asking for comparison"""
        comparison_keywords = [
            "compare", "comparison", "versus", "vs", "vs.",
            "difference", "differences", "how do", "which is better",
            "across", "between"
        ]

        query_lower = query.lower()
        return any(kw in query_lower for kw in comparison_keywords)


# Singleton instance
_analyst_instance: Optional[CompetitiveAnalyst] = None


def get_analyst(model_name: str = "gpt-5-mini") -> CompetitiveAnalyst:
    """Get or create analyst singleton"""
    global _analyst_instance
    if _analyst_instance is None or _analyst_instance.model_name != model_name:
        _analyst_instance = CompetitiveAnalyst(model_name)
    return _analyst_instance


if __name__ == "__main__":
    # Test analyst
    print("Testing Competitive Analyst...")

    # Test comparison query detection
    analyst = get_analyst()

    test_queries = [
        "What is the ORR for Trial X?",
        "Compare ORR across KRAS inhibitor trials",
        "What are the differences between drug A and drug B?"
    ]

    for query in test_queries:
        is_comp = analyst.is_comparison_query(query)
        print(f"\nQuery: {query}")
        print(f"Is comparison: {is_comp}")

    # Test answer generation
    test_contexts = [
        {
            "text": "Trial X showed 45% ORR (95% CI: 35-55%) in 120 patients with NSCLC.",
            "metadata": {"file_name": "trial_x.pdf"},
            "chunk_index": 2,
            "doc_type": "publication",
            "source": "NEJM"
        }
    ]

    answer = analyst.generate_answer(
        "What is the ORR for Trial X?",
        test_contexts
    )

    print(f"\n✓ Generated answer:")
    print(answer[:200] + "..." if len(answer) > 200 else answer)

    print("\n✓ Analyst test successful!")
