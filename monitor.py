"""
monitor.py – Google My Business review monitoring service.

Fetches reviews from Google My Business API and stores them in database
with efficient batch operations and proper error handling.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from config import get_config
from database import DatabaseManager, get_database
from google_api import GoogleMyBusinessClient

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Review Monitor
# ---------------------------------------------------------------------------

class ReviewMonitor:
    """
    Google My Business review monitor.
    
    Fetches reviews from GMB API and stores in database with deduplication.
    """

    def __init__(self, gmb_client: GoogleMyBusinessClient, db: DatabaseManager):
        """Initialize review monitor."""  
        Args:
            gmb_client: Google My Business API client
            db: Database manager
        """
        self.gmb_client = gmb_client
        self.db = db
        self.config = get_config()

    async def fetch_and_store_reviews(self) -> dict:
        """
        Fetch reviews from GMB API and store in database.
        
        Returns:
            Statistics dictionary
        """
        stats = {
            "total_fetched": 0,
            "new_reviews": 0,
            "errors": 0,
        }
        
        try:
            # Get all accounts
            accounts = self.gmb_client.list_accounts()
            logger.info("Found %d GMB accounts", len(accounts))
            
            for account in accounts:
                account_id = account["name"].split("/")[-1]
                
                # Get locations for account
                locations = self.gmb_client.list_locations(account_id)
                logger.info("Found %d locations for account %s", len(locations), account_id)
                
                for location in locations:
                    location_name = location["name"]
                    location_id = location_name.split("/")[-1]
                    
                    # Fetch reviews for location
                    try:
                        reviews = self.gmb_client.list_reviews(location_name)
                        stats["total_fetched"] += len(reviews)
                        
                        # Batch insert reviews
                        review_tuples = []
                        for review in reviews:
                            review_id = review["reviewId"]
                            rating = review.get("starRating", "FIVE")
                            rating_value = self._parse_rating(rating)
                            review_text = review.get("comment", "")
                            reviewer_name = review.get("reviewer", {}).get("displayName", "Anonymous")
                            created_at = review.get("createTime")
                            
                            review_tuples.append((
                                review_id,
                                location_id,
                                rating_value,
                                review_text,
                                reviewer_name,
                                created_at,
                            ))
                         
                        # Batch insert
                        if review_tuples:
                            new_count = self.db.batch_upsert_reviews(review_tuples)
                            stats["new_reviews"] += new_count
                            logger.info(
                                "Stored %d reviews for location %s (%d new)",
                                len(review_tuples),
                                location_id,
                                new_count,
                            )
                    
                    except Exception as exc:
                        logger.error("Failed to fetch reviews for location %s: %s", location_id, exc)
                        stats["errors"] += 1
        
        except Exception as exc:
            logger.exception("Failed to fetch reviews: %s", exc)
            stats["errors"] += 1
        
        return stats

    @staticmethod
    def _parse_rating(rating_str: str) -> int:
        """
        Parse GMB rating string to integer.
        
        Args:
            rating_str: Rating string (e.g., "FIVE", "FOUR")
        
        Returns:
            Rating value (1-5)
        """
        rating_map = {
            "ONE": 1,
            "TWO": 2,
            "THREE": 3,
            "FOUR": 4,
            "FIVE": 5,
        }
        return rating_map.get(rating_str.upper(), 5)


# ---------------------------------------------------------------------------
# Monitoring Service
# ---------------------------------------------------------------------------

class MonitoringService:
    """
    Background monitoring service.
    
    Periodically fetches reviews from GMB API and stores in database.
    """

    def __init__(self):
        """Initialize monitoring service."""
        self.config = get_config()
        self.db = get_database()
        self.gmb_client = GoogleMyBusinessClient()
        self.monitor = ReviewMonitor(self.gmb_client, self.db)
        self.running = False
        self.task: Optional[asyncio.Task] = None

    async def run_loop(self) -> None:
        """Main monitoring loop."""
        interval = self.config.monitor.check_interval_minutes * 60
        
        logger.info(
            "Monitoring service starting (interval: %d minutes)",
            self.config.monitor.check_interval_minutes,
        )
        
        self.running = True
        
        while self.running:
            try:
                logger.info("Fetching reviews...")
                
                stats = await self.monitor.fetch_and_store_reviews()
                
                logger.info("Fetch complete: %s", stats)
                
                # Sleep until next run
                if self.running:
                    await asyncio.sleep(interval)
            
            except asyncio.CancelledError:
                logger.info("Monitoring service cancelled")
                break
            
            except Exception as exc:
                logger.exception("Monitoring service error: %s", exc)
                await asyncio.sleep(60)  # Short backoff on error
        
        self.running = False
        logger.info("Monitoring service stopped")

    def start(self) -> None:
        """Start monitoring service."""
        if self.task and not self.task.done():
            logger.warning("Monitoring service already running")
            return
        
        self.task = asyncio.create_task(self.run_loop())
        logger.info("Monitoring service started")

    def stop(self) -> None:
        """Stop monitoring service."""
        self.running = False
        
        if self.task and not self.task.done():
            self.task.cancel()
        
        logger.info("Monitoring service stopped")

    def get_status(self) -> dict:
        """Get monitoring service status."""
        return {
            "running": self.running,
            "pending_reviews": self.db.get_pending_count(),
        }


# ---------------------------------------------------------------------------
# Standalone Runner
# ---------------------------------------------------------------------------

async def main() -> None:
    """Run monitoring service as standalone script."""
    service = MonitoringService()
    
    try:
        await service.run_loop()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        service.stop()


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    asyncio.run(main())
