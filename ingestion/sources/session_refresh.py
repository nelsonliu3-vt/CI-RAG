"""
Session Refresh Orchestrator
Coordinates intelligence gathering from all sources
"""

import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from ingestion.sources.pubmed_fetcher import get_pubmed_fetcher, PubMedArticle
from ingestion.sources.rss_fetcher import get_rss_fetcher, FeedItem
from ingestion.sources.indexer import get_feed_indexer
from core.program_profile import get_program_profile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SessionRefresh:
    """Orchestrate intelligence refresh from all sources"""

    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Initialize session refresh

        Args:
            progress_callback: Optional callback for progress updates (message: str)
        """
        self.pubmed_fetcher = get_pubmed_fetcher()
        self.rss_fetcher = get_rss_fetcher()
        self.indexer = get_feed_indexer()
        self.profile_manager = get_program_profile()
        self.progress_callback = progress_callback

    def _update_progress(self, message: str):
        """Send progress update"""
        logger.info(message)
        if self.progress_callback:
            self.progress_callback(message)

    def refresh_all(
        self,
        max_papers: int = 20,
        max_rss_items: int = 50,
        days_back: int = 90
    ) -> Dict[str, Any]:
        """
        Perform complete intelligence refresh

        Args:
            max_papers: Maximum papers to fetch from PubMed (1-500)
            max_rss_items: Maximum items per RSS feed (1-500)
            days_back: Only fetch content from last N days (1-3650)

        Returns:
            Statistics dict with counts from each source

        Raises:
            ValueError: If input parameters are out of valid range
        """
        # Input validation
        if not isinstance(max_papers, int) or max_papers < 1 or max_papers > 500:
            raise ValueError(f"max_papers must be an integer between 1 and 500, got: {max_papers}")

        if not isinstance(max_rss_items, int) or max_rss_items < 1 or max_rss_items > 500:
            raise ValueError(f"max_rss_items must be an integer between 1 and 500, got: {max_rss_items}")

        if not isinstance(days_back, int) or days_back < 1 or days_back > 3650:
            raise ValueError(f"days_back must be an integer between 1 and 3650 (10 years), got: {days_back}")

        stats = {
            "started_at": datetime.now().isoformat(),
            "pubmed": {"fetched": 0, "indexed": 0, "updated": 0, "skipped": 0},
            "rss": {"fetched": 0, "indexed": 0, "updated": 0, "skipped": 0},
            "total_new": 0,
            "total_updated": 0,
            "errors": []
        }

        # Get program profile for scoped search
        profile = self.profile_manager.get_profile()
        if not profile:
            self._update_progress("⚠️  No program profile set. Using default search.")
            search_query = "cancer clinical trial"
        else:
            # Build program-scoped query
            program_name = profile.get("program_name", "")
            indication = profile.get("indication", "")
            search_query = f"{program_name} {indication}".strip()
            self._update_progress(f"🎯 Program: {program_name}")

        # 1. Fetch from PubMed (program-scoped)
        try:
            self._update_progress(f"📚 Fetching from PubMed ({search_query})...")
            pubmed_stats = self._refresh_pubmed(search_query, max_papers, days_back)
            stats["pubmed"] = pubmed_stats
            self._update_progress(f"✓ PubMed: {pubmed_stats['indexed']} new, {pubmed_stats['updated']} updated")
        except Exception as e:
            error_msg = f"Error fetching PubMed: {str(e)}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
            self._update_progress(f"❌ PubMed error: {str(e)}")

        # 2. Fetch from RSS feeds (broad)
        try:
            self._update_progress("📰 Fetching from RSS feeds (FDA, EMA)...")
            rss_stats = self._refresh_rss(max_rss_items)
            stats["rss"] = rss_stats
            self._update_progress(f"✓ RSS: {rss_stats['indexed']} new, {rss_stats['updated']} updated")
        except Exception as e:
            error_msg = f"Error fetching RSS: {str(e)}"
            logger.error(error_msg)
            stats["errors"].append(error_msg)
            self._update_progress(f"❌ RSS error: {str(e)}")

        # Calculate totals
        stats["total_new"] = stats["pubmed"]["indexed"] + stats["rss"]["indexed"]
        stats["total_updated"] = stats["pubmed"]["updated"] + stats["rss"]["updated"]
        stats["finished_at"] = datetime.now().isoformat()

        self._update_progress(f"🎉 Refresh complete! {stats['total_new']} new, {stats['total_updated']} updated")
        return stats

    def _refresh_pubmed(
        self,
        query: str,
        max_results: int,
        days_back: int
    ) -> Dict[str, int]:
        """Refresh from PubMed"""
        stats = {"fetched": 0, "indexed": 0, "updated": 0, "skipped": 0, "failed": 0}

        # Fetch articles
        articles = self.pubmed_fetcher.search(query, max_results, days_back)
        stats["fetched"] = len(articles)

        if not articles:
            return stats

        # Convert to FeedItem and index
        for article in articles:
            try:
                feed_item = self._pubmed_to_feed_item(article)

                # Check if exists
                if self.indexer.is_already_indexed(feed_item):
                    # Update existing
                    result = self.indexer.update_item(feed_item, detected_type="publication")
                    if result:
                        stats["updated"] += 1
                    else:
                        stats["failed"] += 1
                else:
                    # Index as new
                    result = self.indexer.index_item(feed_item, detected_type="publication")
                    if result:
                        stats["indexed"] += 1
                    else:
                        stats["failed"] += 1

            except Exception as e:
                logger.warning(f"Error processing article PMID {article.pmid}: {e}")
                stats["failed"] += 1

        return stats

    def _refresh_rss(self, max_items: int) -> Dict[str, int]:
        """Refresh from RSS feeds"""
        stats = {"fetched": 0, "indexed": 0, "updated": 0, "skipped": 0, "failed": 0}

        # Fetch from all RSS feeds
        all_items = self.rss_fetcher.fetch_all_default_feeds()
        stats["fetched"] = len(all_items)

        if not all_items:
            return stats

        # Index items
        for item in all_items:
            try:
                # Check if exists
                if self.indexer.is_already_indexed(item):
                    # Update existing
                    result = self.indexer.update_item(item, detected_type="news_article")
                    if result:
                        stats["updated"] += 1
                    else:
                        stats["failed"] += 1
                else:
                    # Index as new
                    result = self.indexer.index_item(item, detected_type="news_article")
                    if result:
                        stats["indexed"] += 1
                    else:
                        stats["failed"] += 1

            except Exception as e:
                logger.warning(f"Error processing RSS item {item.url}: {e}")
                stats["failed"] += 1

        return stats

    def _pubmed_to_feed_item(self, article: PubMedArticle) -> FeedItem:
        """Convert PubMedArticle to FeedItem for indexing"""
        # Use abstract as text (or full text if available)
        text = article.full_text if article.full_text else article.abstract

        # Add metadata to text
        full_text = f"{article.title}\n\n"
        full_text += f"Authors: {', '.join(article.authors)}\n"
        full_text += f"Journal: {article.journal}\n"
        full_text += f"Published: {article.pub_date}\n"
        if article.doi:
            full_text += f"DOI: {article.doi}\n"
        full_text += f"\nAbstract:\n{text}"

        return FeedItem(
            url=article.url,
            title=article.title,
            published=article.pub_date,
            publisher=article.journal,
            text=full_text,
            summary=article.abstract[:200] + "..." if len(article.abstract) > 200 else article.abstract
        )


# Singleton
_session_refresh: Optional[SessionRefresh] = None


def get_session_refresh(progress_callback: Optional[Callable] = None) -> SessionRefresh:
    """Get or create session refresh singleton"""
    global _session_refresh
    if _session_refresh is None or progress_callback:
        _session_refresh = SessionRefresh(progress_callback=progress_callback)
    return _session_refresh


if __name__ == "__main__":
    print("Testing Session Refresh...")

    def progress_printer(message: str):
        print(f"  {message}")

    refresher = get_session_refresh(progress_callback=progress_printer)
    stats = refresher.refresh_all(max_papers=5, max_rss_items=10)

    print(f"\n✓ Session refresh test complete!")
    print(f"  PubMed: {stats['pubmed']['indexed']} indexed, {stats['pubmed']['updated']} updated")
    print(f"  RSS: {stats['rss']['indexed']} indexed, {stats['rss']['updated']} updated")
    print(f"  Total: {stats['total_new']} new, {stats['total_updated']} updated")
