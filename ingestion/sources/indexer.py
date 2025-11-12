"""
Auto-Indexer for RSS Feed Items
Indexes fetched items into existing Qdrant + BM25 + SQLite memory
"""

import logging
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

from ingestion.sources.rss_fetcher import FeedItem, RSSFetcher
from retrieval.vector_store import get_vector_store
from retrieval.hybrid_search import get_hybrid_search
from memory.simple_memory import get_memory
from ingestion.chunker import chunk_text
from core.config import CHUNK_SIZE, CHUNK_OVERLAP

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeedIndexer:
    """Indexes RSS feed items into vector store + BM25 + memory"""

    def __init__(self):
        self.vector_store = get_vector_store()
        self.hybrid_search = get_hybrid_search()
        self.memory = get_memory()
        self.fetcher = RSSFetcher()

    def is_already_indexed(self, item: FeedItem) -> bool:
        """
        Check if item is already indexed (deduplication)

        Args:
            item: Feed item to check

        Returns:
            True if already indexed, False otherwise
        """
        doc_id = self._generate_doc_id(item)

        # Check if doc_id exists in memory
        existing_doc = self.memory.get_document(doc_id)
        return existing_doc is not None

    def index_item(
        self,
        item: FeedItem,
        detected_type: str = "news_article",
        force: bool = False
    ) -> Optional[str]:
        """
        Index a single feed item

        Args:
            item: Feed item to index
            detected_type: Document type classification
            force: Force re-indexing even if already exists

        Returns:
            Document ID if indexed, None if skipped
        """
        doc_id = self._generate_doc_id(item)

        # Skip if already indexed (unless force=True)
        if not force and self.is_already_indexed(item):
            logger.info(f"⏭️  Skipping (already indexed): {item.title[:60]}...")
            return None

        try:
            # Chunk the text
            chunks = chunk_text(item.text, CHUNK_SIZE, CHUNK_OVERLAP)

            if not chunks:
                logger.warning(f"No chunks generated for {item.title}")
                return None

            # Prepare metadata
            metadata = {
                "detected_type": detected_type,
                "source": item.publisher,
                "topics": [],  # Could add auto-topic extraction here
                "file_name": item.title,
                "source_url": item.url,
                "published_date": item.published,
                "summary": item.summary
            }

            # Index into vector store
            chunk_ids = self.vector_store.add_documents(
                chunks=chunks,
                doc_id=doc_id,
                metadata=metadata
            )

            # Index into BM25
            chunk_dicts = [
                {
                    "id": cid,
                    "text": chunk,
                    "metadata": metadata
                }
                for cid, chunk in zip(chunk_ids, chunks)
            ]
            self.hybrid_search.index_documents(chunk_dicts)

            # Save to memory
            self.memory.add_document(
                doc_id=doc_id,
                filename=item.title,
                detected_type=detected_type,
                source=item.publisher,
                topics=[],
                file_size=len(item.text),
                num_pages=1,
                date_in_doc=item.published,
                metadata={
                    "url": item.url,
                    "published_date": item.published,
                    "summary": item.summary
                }
            )

            # Mark as indexed
            self.memory.mark_indexed(doc_id)

            logger.info(f"✓ Indexed: {item.title[:60]}... ({len(chunks)} chunks)")
            return doc_id

        except Exception as e:
            logger.error(f"Error indexing item {item.url}: {e}")
            return None

    def update_item(
        self,
        item: FeedItem,
        detected_type: str = "news_article"
    ) -> Optional[str]:
        """
        Update an existing document with new content

        Args:
            item: Feed item with updated content
            detected_type: Document type classification

        Returns:
            Document ID if updated, None if failed
        """
        doc_id = self._generate_doc_id(item)

        try:
            # Check if document exists
            existing_doc = self.memory.get_document(doc_id)
            if not existing_doc:
                logger.info(f"Document not found, indexing as new: {item.title[:60]}...")
                return self.index_item(item, detected_type, force=False)

            # Re-index with force=True to replace content
            logger.info(f"🔄 Updating: {item.title[:60]}...")
            result = self.index_item(item, detected_type, force=True)

            if result:
                logger.info(f"✓ Updated: {item.title[:60]}...")

            return result

        except Exception as e:
            logger.error(f"Error updating item {item.url}: {e}")
            return None

    def index_items(
        self,
        items: List[FeedItem],
        detected_type: str = "news_article",
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Index multiple feed items

        Args:
            items: List of feed items
            detected_type: Document type classification
            force: Force re-indexing

        Returns:
            Statistics dict
        """
        indexed_count = 0
        skipped_count = 0
        failed_count = 0

        for item in items:
            doc_id = self.index_item(item, detected_type, force)

            if doc_id:
                indexed_count += 1
            elif self.is_already_indexed(item):
                skipped_count += 1
            else:
                failed_count += 1

        stats = {
            "total": len(items),
            "indexed": indexed_count,
            "skipped": skipped_count,
            "failed": failed_count
        }

        logger.info(f"✓ Indexing complete: {indexed_count} indexed, {skipped_count} skipped, {failed_count} failed")
        return stats

    def fetch_and_index_all_feeds(self, force: bool = False) -> Dict[str, Any]:
        """
        Fetch and index all default RSS feeds

        Args:
            force: Force re-indexing

        Returns:
            Statistics dict
        """
        # Fetch items
        items = self.fetcher.fetch_all_default_feeds()

        # Index items
        stats = self.index_items(items, detected_type="news_article", force=force)

        return stats

    @staticmethod
    def _generate_doc_id(item: FeedItem) -> str:
        """Generate unique document ID from feed item"""
        # Use URL hash as doc_id
        url_hash = hashlib.md5(item.url.encode()).hexdigest()[:12]
        return f"feed_{url_hash}"


# Singleton instance
_indexer_instance: Optional[FeedIndexer] = None


def get_feed_indexer() -> FeedIndexer:
    """Get or create feed indexer singleton"""
    global _indexer_instance
    if _indexer_instance is None:
        _indexer_instance = FeedIndexer()
    return _indexer_instance


if __name__ == "__main__":
    # Test feed indexer
    print("Testing Feed Indexer...")

    indexer = get_feed_indexer()

    # Fetch and index
    print("\nFetching and indexing feeds...")
    stats = indexer.fetch_and_index_all_feeds()

    print(f"\n✓ Indexing stats:")
    print(f"  Total items: {stats['total']}")
    print(f"  Indexed: {stats['indexed']}")
    print(f"  Skipped (duplicates): {stats['skipped']}")
    print(f"  Failed: {stats['failed']}")

    print("\n✓ Feed indexer test successful!")
