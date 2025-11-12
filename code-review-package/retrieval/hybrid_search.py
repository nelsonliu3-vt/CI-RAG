"""
Hybrid Search Module
Combines BM25 (sparse) + Dense embeddings with RRF fusion
"""

import logging
from typing import List, Dict, Any, Optional
from collections import defaultdict
import math
import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi
import tiktoken

from core.config import BM25_TOP_K, DENSE_TOP_K, RRF_K, FINAL_TOP_K
from retrieval.vector_store import get_vector_store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HybridSearch:
    """Hybrid search combining BM25 + dense retrieval with RRF fusion"""

    def __init__(self):
        self.vector_store = get_vector_store()
        self.bm25_index = None
        self.corpus = []  # List of {id, text, metadata}
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Persistence paths for BM25 index
        self.index_dir = Path("data/bm25")
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.index_dir / "bm25_index.pkl"
        self.corpus_path = self.index_dir / "bm25_corpus.pkl"

        # Load existing index if available
        self._load_index()

    def index_documents(self, documents: List[Dict[str, Any]]):
        """
        Build BM25 index for documents

        Args:
            documents: List of dicts with 'id', 'text', 'metadata'
        """
        self.corpus = documents

        # Tokenize documents
        tokenized_corpus = []
        for doc in documents:
            tokens = self.tokenizer.encode(doc["text"])
            # Decode back to get token strings for BM25
            token_strings = [self.tokenizer.decode([t]) for t in tokens]
            tokenized_corpus.append(token_strings)

        # Build BM25 index
        self.bm25_index = BM25Okapi(tokenized_corpus)
        logger.info(f"✓ Built BM25 index with {len(documents)} documents")

        # Persist index to disk
        self._save_index()

    def bm25_search(self, query: str, top_k: int = BM25_TOP_K) -> List[Dict[str, Any]]:
        """
        BM25 sparse retrieval

        Args:
            query: Query text
            top_k: Number of results

        Returns:
            List of results with id, text, score, metadata
        """
        if self.bm25_index is None:
            logger.warning("BM25 index not built, returning empty results")
            return []

        # Tokenize query
        query_tokens = self.tokenizer.encode(query)
        query_token_strings = [self.tokenizer.decode([t]) for t in query_tokens]

        # Get scores
        scores = self.bm25_index.get_scores(query_token_strings)

        # Get top-k indices
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

        # Format results
        results = []
        for idx in top_indices:
            if scores[idx] > 0:  # Only include non-zero scores
                results.append({
                    "id": self.corpus[idx]["id"],
                    "text": self.corpus[idx]["text"],
                    "score": float(scores[idx]),
                    "metadata": self.corpus[idx].get("metadata", {}),
                    "source": "bm25"
                })

        return results

    def dense_search(
        self,
        query: str,
        top_k: int = DENSE_TOP_K,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Dense vector search

        Args:
            query: Query text
            top_k: Number of results
            filters: Optional filters

        Returns:
            List of results with id, text, score, metadata
        """
        results = self.vector_store.search(query, top_k=top_k, filters=filters)

        # Add source tag
        for result in results:
            result["source"] = "dense"

        return results

    def rrf_fusion(
        self,
        bm25_results: List[Dict[str, Any]],
        dense_results: List[Dict[str, Any]],
        k: int = RRF_K
    ) -> List[Dict[str, Any]]:
        """
        Reciprocal Rank Fusion

        RRF score = sum(1 / (k + rank)) for each retrieval method

        Args:
            bm25_results: Results from BM25
            dense_results: Results from dense retrieval
            k: RRF constant (default: 60)

        Returns:
            Fused and ranked results
        """
        # Build rank maps
        bm25_ranks = {result["id"]: i for i, result in enumerate(bm25_results)}
        dense_ranks = {result["id"]: i for i, result in enumerate(dense_results)}

        # Collect all unique document IDs
        all_doc_ids = set(bm25_ranks.keys()) | set(dense_ranks.keys())

        # Build document map (id -> full result)
        doc_map = {}
        for result in bm25_results + dense_results:
            if result["id"] not in doc_map:
                doc_map[result["id"]] = result

        # Calculate RRF scores
        rrf_scores = {}
        for doc_id in all_doc_ids:
            score = 0.0

            # BM25 contribution
            if doc_id in bm25_ranks:
                score += 1.0 / (k + bm25_ranks[doc_id])

            # Dense contribution
            if doc_id in dense_ranks:
                score += 1.0 / (k + dense_ranks[doc_id])

            rrf_scores[doc_id] = score

        # Sort by RRF score
        sorted_doc_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # Build final results
        fused_results = []
        for doc_id in sorted_doc_ids:
            result = doc_map[doc_id].copy()
            result["rrf_score"] = rrf_scores[doc_id]
            result["bm25_rank"] = bm25_ranks.get(doc_id)
            result["dense_rank"] = dense_ranks.get(doc_id)
            fused_results.append(result)

        return fused_results

    def hybrid_search(
        self,
        query: str,
        top_k: int = FINAL_TOP_K,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: BM25 + Dense + RRF fusion

        Args:
            query: Query text
            top_k: Number of final results
            filters: Optional filters for dense search

        Returns:
            Top-k fused results
        """
        logger.info(f"Hybrid search for: {query[:50]}...")

        # BM25 retrieval
        bm25_results = self.bm25_search(query, top_k=BM25_TOP_K)
        logger.info(f"  BM25: {len(bm25_results)} results")

        # Dense retrieval
        dense_results = self.dense_search(query, top_k=DENSE_TOP_K, filters=filters)
        logger.info(f"  Dense: {len(dense_results)} results")

        # RRF fusion
        fused_results = self.rrf_fusion(bm25_results, dense_results, k=RRF_K)
        logger.info(f"  Fused: {len(fused_results)} results")

        # Return top-k
        return fused_results[:top_k]

    def _save_index(self):
        """Save BM25 index and corpus to disk"""
        try:
            with open(self.index_path, 'wb') as f:
                pickle.dump(self.bm25_index, f)
            with open(self.corpus_path, 'wb') as f:
                pickle.dump(self.corpus, f)
            logger.info(f"✓ Persisted BM25 index to {self.index_path}")
        except Exception as e:
            logger.error(f"Failed to save BM25 index: {e}")

    def _load_index(self):
        """Load BM25 index and corpus from disk if available"""
        if self.index_path.exists() and self.corpus_path.exists():
            try:
                with open(self.index_path, 'rb') as f:
                    self.bm25_index = pickle.load(f)
                with open(self.corpus_path, 'rb') as f:
                    self.corpus = pickle.load(f)
                logger.info(f"✓ Loaded BM25 index from disk ({len(self.corpus)} documents)")
            except Exception as e:
                logger.error(f"Failed to load BM25 index: {e}")
                # Reset to empty if load fails
                self.bm25_index = None
                self.corpus = []
        else:
            logger.info("No existing BM25 index found, starting with empty index")


# Singleton instance
_hybrid_search_instance: Optional[HybridSearch] = None


def get_hybrid_search() -> HybridSearch:
    """Get or create hybrid search singleton"""
    global _hybrid_search_instance
    if _hybrid_search_instance is None:
        _hybrid_search_instance = HybridSearch()
    return _hybrid_search_instance


if __name__ == "__main__":
    # Test hybrid search
    print("Testing Hybrid Search...")

    # Create test documents
    test_docs = [
        {
            "id": "doc1",
            "text": "KRAS G12C inhibitor shows 45% ORR in NSCLC patients",
            "metadata": {"source": "test"}
        },
        {
            "id": "doc2",
            "text": "PD-1 inhibitor pembrolizumab approved for melanoma",
            "metadata": {"source": "test"}
        },
        {
            "id": "doc3",
            "text": "EGFR mutation positive NSCLC responds to osimertinib",
            "metadata": {"source": "test"}
        }
    ]

    search = get_hybrid_search()

    # Index documents
    search.index_documents(test_docs)

    # Test BM25
    bm25_results = search.bm25_search("KRAS inhibitor NSCLC", top_k=3)
    print(f"\n✓ BM25 results: {len(bm25_results)}")
    if bm25_results:
        print(f"  Top result: {bm25_results[0]['text'][:50]}... (score: {bm25_results[0]['score']:.3f})")

    print("\n✓ Hybrid search test successful!")
    print("\nNote: Dense search requires Qdrant running and documents indexed in vector store")
