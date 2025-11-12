"""
Reranker Module
Cross-encoder reranking for final result refinement
"""

import logging
from typing import List, Dict, Any, Optional

from sentence_transformers import CrossEncoder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Reranker:
    """Cross-encoder reranker"""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize reranker

        Args:
            model_name: Cross-encoder model name
        """
        try:
            self.model = CrossEncoder(model_name)
            logger.info(f"✓ Loaded reranker: {model_name}")
        except Exception as e:
            logger.warning(f"Could not load reranker: {e}")
            self.model = None

    def rerank(
        self,
        query: str,
        results: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Rerank results using cross-encoder

        Args:
            query: Query text
            results: List of search results with 'text' field
            top_k: Number of results to return

        Returns:
            Reranked results with 'rerank_score'
        """
        if not self.model or not results:
            logger.warning("Reranker not available or no results, returning original order")
            return results[:top_k]

        try:
            # Prepare query-document pairs
            pairs = [[query, result["text"]] for result in results]

            # Get scores
            scores = self.model.predict(pairs)

            # Add scores to results
            for i, result in enumerate(results):
                result["rerank_score"] = float(scores[i])

            # Sort by rerank score
            reranked = sorted(results, key=lambda x: x["rerank_score"], reverse=True)

            logger.info(f"✓ Reranked {len(results)} → {min(top_k, len(results))} results")

            return reranked[:top_k]

        except Exception as e:
            logger.error(f"Error reranking: {e}")
            return results[:top_k]


# Singleton instance
_reranker_instance: Optional[Reranker] = None


def get_reranker() -> Reranker:
    """Get or create reranker singleton"""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = Reranker()
    return _reranker_instance


if __name__ == "__main__":
    # Test reranker
    print("Testing Reranker...")

    test_query = "What is the ORR for KRAS inhibitors?"
    test_results = [
        {"text": "PD-1 inhibitors show good response rates", "score": 0.8},
        {"text": "KRAS G12C inhibitors achieve 45% ORR in NSCLC", "score": 0.75},
        {"text": "EGFR mutations are common in lung cancer", "score": 0.7}
    ]

    reranker = get_reranker()
    reranked = reranker.rerank(test_query, test_results, top_k=3)

    print(f"\n✓ Reranked {len(test_results)} results")
    print("\nTop result after reranking:")
    print(f"  {reranked[0]['text'][:60]}...")
    print(f"  Rerank score: {reranked[0]['rerank_score']:.3f}")

    print("\n✓ Reranker test successful!")
