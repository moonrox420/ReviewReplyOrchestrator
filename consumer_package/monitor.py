"""
monitor.py – Background review monitoring loop.

Runs continuously (default every 60 minutes), checks Google My Business for
new reviews, generates AI replies via the existing app.py logic, posts them
directly to Google, and logs everything to a SQLite database.
"""

import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv

load_dotenv("engine.env")

from google_api import (
    get_valid_credentials,
    list_accounts,
    list_locations,
    list_reviews,
    post_reply,
)

logger = logging.getLogger(__name__)

DEFAULT_REPLY_TEXT = "Thank you for your feedback!"

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
REVIEW_CHECK_INTERVAL_MINUTES = int(os.getenv("REVIEW_CHECK_INTERVAL_MINUTES", "60"))
REVIEW_DB_PATH = os.getenv("REVIEW_DB_PATH", "./data/reviews.db")

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

_DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    review_id   TEXT PRIMARY KEY,
    location_id TEXT NOT NULL,
    rating      INTEGER NOT NULL,
    review_text TEXT,
    reviewer_name TEXT,
    created_at  TIMESTAMP,
    replied_at  TIMESTAMP,
    reply_text  TEXT,
    status      TEXT DEFAULT 'pending'
);
"""


def _get_conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(REVIEW_DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(REVIEW_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(_DB_SCHEMA)
    conn.commit()
    return conn


def upsert_review(
    review_id: str,
    location_id: str,
    rating: int,
    review_text: Optional[str],
    reviewer_name: Optional[str],
    created_at: Optional[str],
) -> bool:
    """Insert a review record if it doesn't exist yet.  Returns True if new."""
    conn = _get_conn()
    try:
        conn.execute(
            """
            INSERT OR IGNORE INTO reviews
                (review_id, location_id, rating, review_text, reviewer_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (review_id, location_id, rating, review_text, reviewer_name, created_at),
        )
        conn.commit()
        return conn.total_changes > 0
    finally:
        conn.close()


def mark_replied(review_id: str, reply_text: str) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            """
            UPDATE reviews
            SET replied_at = ?, reply_text = ?, status = 'replied'
            WHERE review_id = ?
            """,
            (datetime.now(timezone.utc).isoformat(), reply_text, review_id),
        )
        conn.commit()
    finally:
        conn.close()


def mark_error(review_id: str, error_msg: str) -> None:
    conn = _get_conn()
    try:
        conn.execute(
            "UPDATE reviews SET status = 'error', reply_text = ? WHERE review_id = ?",
            (error_msg[:500], review_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_all_reviews() -> list:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT * FROM reviews ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_pending_count() -> int:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM reviews WHERE status = 'pending'"
        ).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Core monitoring logic
# ---------------------------------------------------------------------------


async def _generate_reply_for_review(
    business_name: str, rating: int, review_text: str
) -> str:
    """
    Reuse the existing AI reply generation pipeline from app.py.
    Import lazily to avoid circular imports at module level.
    """
    from app import Job, Review, generate_replies  # noqa: PLC0415

    job = Job(
        business_name=business_name,
        signoff="-",
        tone_style="Professional",
        persona="trades",
        compliance_profile="General",
        reviews=[Review(rating=rating, text=review_text or "No text provided")],
    )
    replies = await generate_replies(job)
    return replies[0] if replies else DEFAULT_REPLY_TEXT


async def process_single_review(
    creds,
    location_name: str,
    review: dict,
) -> None:
    """Generate a reply and post it for one review."""
    review_name = review.get("name", "")
    review_id = review_name  # resource name is the stable unique ID
    star_rating_raw = review.get("starRating", 3)
    # Google returns starRating as "FIVE", "FOUR", etc.
    star_map = {"ONE": 1, "TWO": 2, "THREE": 3, "FOUR": 4, "FIVE": 5}
    rating_int = star_map.get(str(star_rating_raw).upper(), 3)

    comment_payload = review.get("comment", "")
    reviewer = review.get("reviewer", {}).get("displayName", "Anonymous")
    create_time = review.get("createTime", "")

    is_new = upsert_review(
        review_id=review_id,
        location_id=location_name,
        rating=rating_int,
        review_text=comment_payload,
        reviewer_name=reviewer,
        created_at=create_time,
    )

    if not is_new:
        logger.debug("Review %s already processed, skipping.", review_id)
        return

    # Skip reviews that already have a reply
    if review.get("reviewReply"):
        logger.debug("Review %s already has a reply, skipping.", review_id)
        mark_replied(review_id, review["reviewReply"].get("comment", ""))
        return

    logger.info(
        "Generating reply for new review: %s (rating=%d)", review_id, rating_int
    )
    try:
        reply_text = await _generate_reply_for_review(
            business_name=location_name,
            rating=rating_int,
            review_text=comment_payload,
        )
        post_reply(creds, review_name, reply_text)
        mark_replied(review_id, reply_text)
        logger.info("Reply posted for review %s", review_id)
    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.error("Failed to reply to review %s: %s", review_id, error_msg)
        mark_error(review_id, error_msg)


async def run_sync_once() -> dict:
    """
    Single pass: fetch all reviews from all locations and reply to new ones.
    Returns a summary dict.
    """
    creds = get_valid_credentials()
    if creds is None:
        return {"ok": False, "error": "Not authenticated. Complete OAuth setup first."}

    summary = {
        "locations_checked": 0,
        "reviews_found": 0,
        "new_replies_posted": 0,
        "errors": 0,
    }

    try:
        accounts = list_accounts(creds)
        if not accounts:
            return {"ok": False, "error": "No Google My Business accounts found."}

        for account in accounts:
            account_name = account.get("name", "")
            locations = list_locations(creds, account_name)

            for location in locations:
                location_name = location.get("name", "")
                summary["locations_checked"] += 1

                reviews = list_reviews(creds, location_name)
                summary["reviews_found"] += len(reviews)

                for review in reviews:
                    review_id = review.get("name", "")
                    # Check if already in DB as replied
                    conn = _get_conn()
                    row = conn.execute(
                        "SELECT status FROM reviews WHERE review_id = ?", (review_id,)
                    ).fetchone()
                    conn.close()

                    if row and row["status"] == "replied":
                        continue

                    try:
                        await process_single_review(creds, location_name, review)
                        summary["new_replies_posted"] += 1
                    except Exception as exc:
                        logger.error("Error processing review %s: %s", review_id, exc)
                        summary["errors"] += 1

    except Exception as exc:
        logger.error("Sync failed: %s", exc)
        return {"ok": False, "error": str(exc)}

    return {"ok": True, **summary}


# ---------------------------------------------------------------------------
# Background scheduler loop (called from app.py startup)
# ---------------------------------------------------------------------------

_last_sync: Optional[datetime] = None
_sync_running: bool = False


async def monitor_loop() -> None:
    """
    Infinite async loop that runs a review sync every
    REVIEW_CHECK_INTERVAL_MINUTES minutes.
    """
    global _last_sync, _sync_running
    interval_seconds = REVIEW_CHECK_INTERVAL_MINUTES * 60
    logger.info(
        "Review monitor started – checking every %d minutes.",
        REVIEW_CHECK_INTERVAL_MINUTES,
    )
    while True:
        _sync_running = True
        logger.info("Starting scheduled review sync…")
        result = await run_sync_once()
        _last_sync = datetime.now(timezone.utc)
        _sync_running = False
        logger.info("Sync complete: %s", result)
        await asyncio.sleep(interval_seconds)


def get_monitor_status() -> dict:
    """Return current monitoring status for the /reviews/status endpoint."""
    return {
        "monitoring_active": True,
        "interval_minutes": REVIEW_CHECK_INTERVAL_MINUTES,
        "last_sync": _last_sync.isoformat() if _last_sync else None,
        "sync_running": _sync_running,
        "pending_reviews": get_pending_count(),
    }
