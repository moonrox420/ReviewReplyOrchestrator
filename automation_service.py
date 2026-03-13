"""
automation_service.py – Background automation service.

Runs on a configurable interval, checks for new Google Business reviews via
Selenium browser automation, generates AI replies using the app.py pipeline,
and posts them automatically.

The service can be started and stopped via the FastAPI endpoints in app.py:
    POST /automation/start   – start background loop
    POST /automation/stop    – stop background loop
    GET  /automation/status  – current status + recent log lines
    POST /automation/setup   – save Google credentials (encrypted)
    POST /automation/config  – update interval / headless setting
"""

from __future__ import annotations

import asyncio
import json
import logging
import logging.handlers
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Automation logger (writes to automation.log in addition to console)
# ---------------------------------------------------------------------------

LOG_PATH = os.getenv("AUTOMATION_LOG_PATH", "./logs/automation.log")

Path(os.path.dirname(LOG_PATH) or ".").mkdir(parents=True, exist_ok=True)

auto_logger = logging.getLogger("automation_service")
auto_logger.setLevel(logging.INFO)

_file_handler = logging.handlers.RotatingFileHandler(
    LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
_file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
)
auto_logger.addHandler(_file_handler)

# Also propagate to root logger (console)
auto_logger.propagate = True

# ---------------------------------------------------------------------------
# Service state
# ---------------------------------------------------------------------------

_service_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_service_running = False
_last_run: Optional[datetime] = None
_last_result: Optional[dict] = None


def _get_interval_minutes() -> int:
    """Read interval from config.json."""
    from browser_automation import load_config  # noqa: PLC0415
    cfg = load_config()
    return int(cfg.get("automation", {}).get("interval_minutes", 60))


def _is_enabled() -> bool:
    from browser_automation import load_config  # noqa: PLC0415
    cfg = load_config()
    return bool(cfg.get("automation", {}).get("enabled", True))


# ---------------------------------------------------------------------------
# AI reply generation (sync wrapper around app.py's async pipeline)
# ---------------------------------------------------------------------------

def _generate_reply_sync(rating: int, review_text: str) -> str:
    """
    Synchronous wrapper: generate an AI reply for a single review.
    Runs the async generate_replies function in a new event loop.
    """
    try:
        from app import Job, Review, generate_replies  # noqa: PLC0415
        from browser_automation import load_config  # noqa: PLC0415

        cfg = load_config()
        business_name = cfg.get("automation", {}).get("business_name", "Our Business")

        job = Job(
            business_name=business_name,
            signoff="-",
            tone_style="Professional",
            persona="trades",
            compliance_profile="General",
            reviews=[Review(rating=rating, text=review_text or "No review text provided")],
        )

        # Run async function in a dedicated event loop
        loop = asyncio.new_event_loop()
        try:
            replies = loop.run_until_complete(generate_replies(job))
        finally:
            loop.close()

        return replies[0] if replies else "Thank you for your feedback!"
    except Exception as exc:
        auto_logger.error("Reply generation failed: %s", exc)
        return "Thank you for your feedback!"


# ---------------------------------------------------------------------------
# Single automation pass
# ---------------------------------------------------------------------------

def run_once() -> dict:
    """
    Execute one full automation pass: login → scrape reviews → post replies.
    Returns a summary dict and logs all actions.
    """
    global _last_run, _last_result

    from browser_automation import run_browser_automation  # noqa: PLC0415

    auto_logger.info("=== Automation pass starting ===")
    start_ts = datetime.now(timezone.utc)

    result = run_browser_automation(generate_reply_fn=_generate_reply_sync)

    _last_run = datetime.now(timezone.utc)
    _last_result = result

    duration = (datetime.now(timezone.utc) - start_ts).total_seconds()

    if result.get("ok"):
        auto_logger.info(
            "Pass complete in %.1fs – reviews found: %d, replies posted: %d, errors: %d",
            duration,
            result.get("reviews_found", 0),
            result.get("replies_posted", 0),
            result.get("errors", 0),
        )
    else:
        auto_logger.error("Pass failed: %s", result.get("error", "unknown error"))

    return result


# ---------------------------------------------------------------------------
# Background thread loop
# ---------------------------------------------------------------------------

def _service_loop() -> None:
    """Thread target: repeatedly run automation at the configured interval."""
    global _service_running

    auto_logger.info("Automation service started.")
    _service_running = True

    while not _stop_event.is_set():
        if _is_enabled():
            try:
                run_once()
            except Exception as exc:
                auto_logger.error("Unhandled exception in automation loop: %s", exc)
        else:
            auto_logger.info("Automation disabled in config – skipping pass.")

        interval_seconds = _get_interval_minutes() * 60
        auto_logger.info(
            "Next run in %d minutes. Waiting…", _get_interval_minutes()
        )

        # Sleep in small increments so we can respond to stop requests quickly
        from browser_automation import STOP_CHECK_INTERVAL_SECONDS  # noqa: PLC0415
        slept = 0
        while slept < interval_seconds and not _stop_event.is_set():
            time.sleep(min(STOP_CHECK_INTERVAL_SECONDS, interval_seconds - slept))
            slept += STOP_CHECK_INTERVAL_SECONDS

    _service_running = False
    auto_logger.info("Automation service stopped.")


# ---------------------------------------------------------------------------
# Public start / stop API
# ---------------------------------------------------------------------------

def start_service() -> dict:
    """Start the background automation thread (no-op if already running)."""
    global _service_thread, _stop_event

    if _service_running and _service_thread and _service_thread.is_alive():
        return {"ok": False, "message": "Automation service is already running."}

    _stop_event.clear()
    _service_thread = threading.Thread(
        target=_service_loop, name="automation-service", daemon=True
    )
    _service_thread.start()
    auto_logger.info("Automation service start requested.")
    return {"ok": True, "message": "Automation service started."}


def stop_service() -> dict:
    """Signal the background thread to stop after the current pass finishes."""
    global _stop_event

    if not _service_running:
        return {"ok": False, "message": "Automation service is not running."}

    _stop_event.set()
    auto_logger.info("Automation service stop requested.")
    return {"ok": True, "message": "Automation service stopping after current pass."}


# ---------------------------------------------------------------------------
# Status & log helpers
# ---------------------------------------------------------------------------

def get_status() -> dict:
    return {
        "running": _service_running,
        "interval_minutes": _get_interval_minutes(),
        "last_run": _last_run.isoformat() if _last_run else None,
        "last_result": _last_result,
    }


def get_recent_logs(lines: int = 100) -> list[str]:
    """Return the last *lines* entries from automation.log."""
    try:
        if not os.path.exists(LOG_PATH):
            return []
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
        return [ln.rstrip() for ln in all_lines[-lines:]]
    except Exception as exc:
        return [f"Error reading log: {exc}"]
