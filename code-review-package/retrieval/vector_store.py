"""
Qdrant Vector Store Module
Handles vector storage and dense retrieval
"""

import logging
import uuid
from typing import List, Dict, Any, Optional
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue
)
from qdrant_client.http.exceptions import UnexpectedResponse as QdrantException
from openai import OpenAI, APIError, RateLimitError, APIConnectionError, APITimeoutError

from core.config import (
    QDRANT_HOST, QDRANT_PORT, QDRANT_COLLECTION_NAME,
    EMBEDDING_MODEL, EMBEDDING_DIMENSION, OPENAI_API_KEY
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VectorStore:
    """Qdrant vector store for document embeddings"""

    def __init__(
        self,
        host: str = QDRANT_HOST,
        port: int = QDRANT_PORT,
        collection_name: str = QDRANT_COLLECTION_NAME
    ):
        """Initialize Qdrant client"""
        try:
            self.client = QdrantClient(host=host, port=port)
            self.collection_name = collection_name
            logger.info(f"✓ Qdrant client initialized: {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client at {host}:{port}: {e}")
            raise ConnectionError(f"Cannot connect to Qdrant at {host}:{port}") from e

        try:
            self.embedding_client = OpenAI(api_key=OPENAI_API_KEY)
            logger.info("✓ OpenAI embedding client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise ValueError("Invalid OpenAI API key or configuration") from e

        # Create collection if doesn't exist
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                logger.info(f"Creating collection: {self.collection_name}")
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=EMBEDDING_DIMENSION,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✓ Collection created: {self.collection_name}")
            else:
                logger.info(f"✓ Collection exists: {self.collection_name}")

        except QdrantException as e:
            logger.error(f"Qdrant error ensuring collection: {e}")
            raise ConnectionError(f"Failed to create/verify collection '{self.collection_name}'") from e
        except Exception as e:
            logger.error(f"Unexpected error ensuring collection: {e}")
            raise

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI (single text)"""
        try:
            response = self.embedding_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text,
                timeout=30.0
            )
            return response.data[0].embedding
        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise RuntimeError("API rate limit exceeded. Please try again in a moment.") from e
        except APITimeoutError as e:
            logger.error(f"OpenAI API timeout: {e}")
            raise TimeoutError("Embedding generation timed out. Please try again.") from e
        except APIConnectionError as e:
            logger.error(f"OpenAI connection error: {e}")
            raise ConnectionError("Cannot connect to OpenAI API. Check your network.") from e
        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise RuntimeError(f"OpenAI API error: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}")
            raise

    def embed_texts_batch(self, texts: List[str], batch_size: int = 50) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batches (efficient)

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (max 2048 for OpenAI)

        Returns:
            List of embeddings in same order as input texts
        """
        all_embeddings = []

        # Process in batches to avoid API limits
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                response = self.embedding_client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=batch,  # OpenAI supports batch input
                    timeout=60.0  # Longer timeout for batches
                )

                # Extract embeddings in correct order
                batch_embeddings = [item.embedding for item in response.data]
                all_embeddings.extend(batch_embeddings)

                logger.info(f"✓ Generated {len(batch)} embeddings (batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1})")

            except RateLimitError as e:
                logger.error(f"OpenAI rate limit on batch {i//batch_size + 1}: {e}")
                raise RuntimeError("API rate limit exceeded during batch processing. Try reducing batch size.") from e
            except APITimeoutError as e:
                logger.error(f"OpenAI timeout on batch {i//batch_size + 1}: {e}")
                raise TimeoutError(f"Batch embedding timed out. Processed {len(all_embeddings)}/{len(texts)} texts.") from e
            except APIConnectionError as e:
                logger.error(f"OpenAI connection error on batch {i//batch_size + 1}: {e}")
                raise ConnectionError(f"Lost connection to OpenAI. Processed {len(all_embeddings)}/{len(texts)} texts.") from e
            except APIError as e:
                logger.error(f"OpenAI API error on batch {i//batch_size + 1}: {e}")
                raise RuntimeError(f"OpenAI API error in batch processing: {str(e)}") from e
            except Exception as e:
                logger.error(f"Unexpected error in batch {i//batch_size + 1}: {e}")
                raise

        return all_embeddings

    def add_documents(
        self,
        chunks: List[str],
        doc_id: str,
        metadata: Dict[str, Any]
    ) -> List[str]:
        """
        Add document chunks to vector store (using batch embeddings for efficiency)

        Args:
            chunks: List of text chunks
            doc_id: Document ID
            metadata: Document metadata (type, source, topics, etc.)

        Returns:
            List of chunk IDs
        """
        if not chunks:
            logger.warning(f"No chunks provided for doc {doc_id}")
            return []

        # Generate all embeddings in batches (MUCH faster than sequential)
        logger.info(f"Generating embeddings for {len(chunks)} chunks in batches...")
        embeddings = self.embed_texts_batch(chunks, batch_size=50)

        # Create points with embeddings
        points = []
        chunk_ids = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = f"{doc_id}_chunk_{i}"
            chunk_ids.append(chunk_id)

            # Create payload (include chunk_id as a field in payload)
            payload = {
                "chunk_id": chunk_id,  # Store string ID in payload
                "doc_id": doc_id,
                "chunk_index": i,
                "text": chunk,
                **metadata  # Include all metadata (type, source, topics, etc.)
            }

            # Create point with integer ID (hash the chunk_id to get a consistent integer)
            point_id = abs(hash(chunk_id)) % (2**63)  # Convert to positive 64-bit int

            point = PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            points.append(point)

        # Upload to Qdrant
        try:
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"✓ Added {len(chunks)} chunks for doc {doc_id}")
            return chunk_ids

        except Exception as e:
            logger.error(f"Error adding documents: {e}")
            raise

    def search(
        self,
        query: str,
        top_k: int = 50,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Dense vector search

        Args:
            query: Query text
            top_k: Number of results
            filters: Optional filters (e.g., {"doc_type": "publication"})

        Returns:
            List of search results with text, score, metadata
        """
        # Generate query embedding
        query_embedding = self.embed_text(query)

        # Build filter if provided
        qdrant_filter = None
        if filters:
            conditions = []
            for key, value in filters.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value)
                    )
                )
            if conditions:
                qdrant_filter = Filter(must=conditions)

        # Search
        try:
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=qdrant_filter
            )

            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "id": result.payload.get("chunk_id", str(result.id)),  # Use chunk_id from payload
                    "score": result.score,
                    "text": result.payload.get("text", ""),
                    "doc_id": result.payload.get("doc_id", ""),
                    "chunk_index": result.payload.get("chunk_index", 0),
                    "doc_type": result.payload.get("detected_type", ""),
                    "source": result.payload.get("source", ""),
                    "topics": result.payload.get("topics", []),
                    "metadata": result.payload
                })

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching: {e}")
            raise

    def delete_document(self, doc_id: str):
        """Delete all chunks for a document"""
        try:
            # Delete by filter
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=Filter(
                    must=[
                        FieldCondition(
                            key="doc_id",
                            match=MatchValue(value=doc_id)
                        )
                    ]
                )
            )
            logger.info(f"✓ Deleted chunks for doc {doc_id}")

        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics"""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                "total_points": info.points_count,
                "vector_dimension": EMBEDDING_DIMENSION,
                "embedding_model": EMBEDDING_MODEL
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {}


# Singleton instance
_vector_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create vector store singleton"""
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance


if __name__ == "__main__":
    # Test vector store
    print("Testing Vector Store...")

    # Note: Requires Qdrant running (docker-compose up -d)
    try:
        store = get_vector_store()
        print("✓ Connected to Qdrant")

        # Test embedding
        embedding = store.embed_text("This is a test")
        print(f"✓ Embedding dimension: {len(embedding)}")

        # Get stats
        stats = store.get_stats()
        print(f"✓ Stats: {stats}")

        print("\n✓ Vector store test successful!")

    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nMake sure Qdrant is running:")
        print("  cd CI-RAG && docker-compose up -d")
