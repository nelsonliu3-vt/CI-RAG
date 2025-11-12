"""
Background Scheduler for Auto-Fetching CI Content
Runs hourly fetch + index jobs in the background
"""

import logging
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from ingestion.sources.indexer import get_feed_indexer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FeedScheduler:
    """Background scheduler for RSS feed fetching"""

    def __init__(self, interval_minutes: int = 60):
        """
        Initialize scheduler

        Args:
            interval_minutes: Fetch interval in minutes (default: 60)
        """
        self.scheduler = BackgroundScheduler()
        self.interval_minutes = interval_minutes
        self.is_running = False
        self.indexer = get_feed_indexer()
        self.last_run: Optional[datetime] = None
        self.last_stats: Optional[dict] = None

    def _fetch_job(self):
        """Background job to fetch and index feeds"""
        try:
            logger.info("🔄 Starting scheduled feed fetch...")
            stats = self.indexer.fetch_and_index_all_feeds(force=False)

            self.last_run = datetime.now()
            self.last_stats = stats

            logger.info(f"✓ Scheduled fetch complete: {stats['indexed']} new items indexed")

        except Exception as e:
            logger.error(f"Error in scheduled fetch job: {e}")

    def start(self):
        """Start the scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        # Add hourly job
        self.scheduler.add_job(
            self._fetch_job,
            trigger=IntervalTrigger(minutes=self.interval_minutes),
            id="feed_fetch_job",
            name="Fetch and index RSS feeds",
            replace_existing=True,
            max_instances=1  # Prevent overlapping runs
        )

        self.scheduler.start()
        self.is_running = True

        logger.info(f"✓ Scheduler started (interval: {self.interval_minutes} minutes)")

        # Run immediately on start
        self._fetch_job()

    def stop(self):
        """Stop the scheduler"""
        if not self.is_running:
            return

        self.scheduler.shutdown(wait=False)
        self.is_running = False
        logger.info("✓ Scheduler stopped")

    def get_status(self) -> dict:
        """Get scheduler status"""
        return {
            "is_running": self.is_running,
            "interval_minutes": self.interval_minutes,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_stats": self.last_stats
        }


# Singleton instance
_scheduler_instance: Optional[FeedScheduler] = None


def get_scheduler(interval_minutes: int = 60) -> FeedScheduler:
    """Get or create scheduler singleton"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = FeedScheduler(interval_minutes=interval_minutes)
    return _scheduler_instance


if __name__ == "__main__":
    # Test scheduler
    import time

    print("Testing Feed Scheduler...")

    scheduler = get_scheduler(interval_minutes=1)  # Every 1 minute for testing

    print("Starting scheduler...")
    scheduler.start()

    print(f"Status: {scheduler.get_status()}")

    print("\nScheduler is running. Press Ctrl+C to stop.")
    print("Waiting 65 seconds to see second run...")

    try:
        time.sleep(65)
        print(f"\nStatus after wait: {scheduler.get_status()}")
    except KeyboardInterrupt:
        print("\nStopping...")

    scheduler.stop()
    print("✓ Scheduler test successful!")
