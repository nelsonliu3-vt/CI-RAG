"""
RSS Feed Fetcher
Automatically fetches CI content from FDA, EMA, ClinicalTrials.gov, and biopharma news
Includes retry logic with exponential backoff for resilience
"""

import logging
import hashlib
import time
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

import feedparser
import requests
from bs4 import BeautifulSoup
from readability import Document
import dateparser
from requests.exceptions import RequestException, Timeout, ConnectionError

from core.input_sanitizer import get_sanitizer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class FeedItem:
    """Represents a single feed item"""
    url: str
    title: str
    published: str
    publisher: str
    text: str
    summary: str = ""


# Curated RSS feeds for pharma competitive intelligence
DEFAULT_FEEDS = {
    "fda_press": {
        "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml",
        "publisher": "FDA Press Releases"
    },
    "fda_drugs": {
        "url": "https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/cder/rss.xml",
        "publisher": "FDA CDER"
    },
    # Note: EMA RSS feeds require specific topic subscriptions
    # Add custom feeds here as needed
}


class RSSFetcher:
    """Fetches and parses RSS feeds with retry logic"""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize RSS fetcher

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries (exponential backoff)
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (CI-RAG Bot; +https://github.com/your-org/ci-rag)'
        })
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Execute function with exponential backoff retry logic

        Args:
            func: Function to execute
            *args, **kwargs: Arguments to pass to function

        Returns:
            Function result

        Raises:
            Last exception if all retries fail
        """
        last_exception = None

        for attempt in range(self.max_retries):
            try:
                return func(*args, **kwargs)
            except (Timeout, ConnectionError, RequestException) as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.error(f"All {self.max_retries} attempts failed: {e}")

        raise last_exception

    def fetch_feed(self, url: str, publisher: Optional[str] = None, max_items: int = 50) -> List[FeedItem]:
        """
        Fetch and parse RSS feed

        Args:
            url: RSS feed URL
            publisher: Override publisher name
            max_items: Maximum items to fetch

        Returns:
            List of FeedItem objects
        """
        # Validate URL to prevent SSRF attacks
        sanitizer = get_sanitizer()
        if not sanitizer.validate_url(url):
            logger.error(f"URL validation failed for: {url}")
            return []

        try:
            logger.info(f"Fetching feed: {url}")
            feed_data = feedparser.parse(url)

            if feed_data.bozo:
                logger.warning(f"Feed parsing had issues: {feed_data.bozo_exception}")

            publisher_name = publisher or feed_data.feed.get("title", "Unknown")
            items = []

            for entry in feed_data.entries[:max_items]:
                try:
                    # Extract URL
                    item_url = entry.get("link", "")
                    if not item_url:
                        continue

                    # Extract title
                    title = entry.get("title", "Untitled")

                    # Extract/parse published date
                    pub_date = entry.get("published", "") or entry.get("updated", "")
                    if pub_date:
                        parsed_date = dateparser.parse(pub_date)
                        if parsed_date:
                            pub_date = parsed_date.isoformat()

                    # Extract summary
                    summary = entry.get("summary", "") or entry.get("description", "")
                    if summary:
                        summary = BeautifulSoup(summary, "lxml").get_text(" ", strip=True)[:500]

                    # Fetch full article text
                    text = self._extract_article_text(item_url)

                    if text:
                        # Oncology relevance check (auto-fetched content only)
                        from core.relevance_scorer import check_oncology_relevance

                        oncology_check = check_oncology_relevance(text)
                        oncology_score = oncology_check['oncology_score']
                        is_oncology = oncology_check['is_oncology']

                        if not is_oncology:
                            # Auto-skip non-oncology auto-fetched content
                            logger.info(f"✗ Skipped (non-oncology, score={oncology_score}): {title[:60]}...")
                            continue

                        items.append(FeedItem(
                            url=item_url,
                            title=title,
                            published=pub_date,
                            publisher=publisher_name,
                            text=text,
                            summary=summary
                        ))
                        logger.info(f"✓ Extracted (oncology score={oncology_score}): {title[:60]}...")

                except Exception as e:
                    logger.warning(f"Error processing feed entry: {e}")
                    continue

            logger.info(f"✓ Fetched {len(items)} items from {publisher_name}")
            return items

        except Exception as e:
            logger.error(f"Error fetching feed {url}: {e}")
            return []

    def _fetch_url(self, url: str, timeout: int) -> requests.Response:
        """
        Fetch URL with timeout (used by retry logic)

        Args:
            url: URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Response object
        """
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        return response

    def _extract_article_text(self, url: str, timeout: int = 20) -> str:
        """
        Extract full article text from URL with retry logic

        Args:
            url: Article URL
            timeout: Request timeout in seconds

        Returns:
            Extracted text or empty string if extraction fails
        """
        # Validate URL to prevent SSRF attacks
        sanitizer = get_sanitizer()
        if not sanitizer.validate_url(url):
            logger.warning(f"URL validation failed for article: {url}")
            return ""

        try:
            # Fetch with retry logic
            response = self._retry_with_backoff(self._fetch_url, url, timeout)

            # Try readability first (better for articles)
            try:
                doc = Document(response.text)
                html_content = doc.summary()
                text = BeautifulSoup(html_content, "lxml").get_text(" ", strip=True)
            except Exception as e:
                logger.debug(f"Readability failed, using BeautifulSoup: {e}")
                # Fallback to BeautifulSoup
                text = BeautifulSoup(response.text, "lxml").get_text(" ", strip=True)

            # Limit length
            if len(text) > 50000:
                text = text[:50000] + "... [truncated]"

            return text

        except (Timeout, ConnectionError, RequestException) as e:
            logger.warning(f"Network error extracting text from {url}: {e}")
            return ""
        except Exception as e:
            logger.warning(f"Could not extract text from {url}: {e}")
            return ""

    def fetch_all_default_feeds(self) -> List[FeedItem]:
        """
        Fetch all default feeds

        Returns:
            Combined list of all feed items
        """
        all_items = []

        for feed_name, feed_config in DEFAULT_FEEDS.items():
            items = self.fetch_feed(
                url=feed_config["url"],
                publisher=feed_config["publisher"]
            )
            all_items.extend(items)

        logger.info(f"✓ Total items fetched from all feeds: {len(all_items)}")
        return all_items

    @staticmethod
    def generate_item_hash(item: FeedItem) -> str:
        """Generate unique hash for deduplication"""
        content = f"{item.url}_{item.title}_{item.published}"
        return hashlib.md5(content.encode()).hexdigest()[:16]


# Singleton instance
_fetcher_instance: Optional[RSSFetcher] = None


def get_rss_fetcher() -> RSSFetcher:
    """Get or create RSS fetcher singleton"""
    global _fetcher_instance
    if _fetcher_instance is None:
        _fetcher_instance = RSSFetcher()
    return _fetcher_instance


if __name__ == "__main__":
    # Test RSS fetcher
    print("Testing RSS Fetcher...")

    fetcher = get_rss_fetcher()

    # Test single feed
    items = fetcher.fetch_feed(
        DEFAULT_FEEDS["fda_press"]["url"],
        DEFAULT_FEEDS["fda_press"]["publisher"],
        max_items=3
    )

    print(f"\n✓ Fetched {len(items)} items")

    if items:
        print(f"\nFirst item:")
        print(f"  Title: {items[0].title}")
        print(f"  Publisher: {items[0].publisher}")
        print(f"  Published: {items[0].published}")
        print(f"  URL: {items[0].url}")
        print(f"  Text length: {len(items[0].text)} chars")
        print(f"  Hash: {RSSFetcher.generate_item_hash(items[0])}")

    print("\n✓ RSS fetcher test successful!")
