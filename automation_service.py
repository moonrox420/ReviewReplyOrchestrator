"""
automation_service.py – Background automation service orchestration.

Manages periodic review checking and reply posting with proper
async task management, clean shutdown, and health monitoring.
"""

from __future__ import annotations

import asyncio
import logging
import signal
from datetime import datetime, timezone
from typing import Optional

from config import get_config
from browser_automation import run_automation_cycle

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Service State Management
# ---------------------------------------------------------------------------

class ServiceState:
    """
    Thread-safe service state manager.
    
    Tracks running status and provides clean shutdown mechanism.
    """

    def __init__(self):
        """Initialize service state."""
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.last_run: Optional[datetime] = None
        self.last_stats: dict = {}
        self.error_count = 0

    def start(self) -> None:
        """Mark service as running."""
        self.running = True
        logger.info("Service state: RUNNING")

    def stop(self) -> None:
        """Mark service as stopped."""
        self.running = False
        logger.info("Service state: STOPPED")

    def update_stats(self, stats: dict) -> None:
        """Update last run statistics."""
        self.last_run = datetime.now(timezone.utc)
        self.last_stats = stats
        
        if stats.get("error"):
            self.error_count += 1
        else:
            self.error_count = 0

    def get_health(self) -> dict:
        """
        Get service health status.
        
        Returns:
            Health status dictionary
        """
        return {
            "running": self.running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_stats": self.last_stats,
            "error_count": self.error_count,
            "healthy": self.running and self.error_count < 3,
        }


# Global service state
_service_state = ServiceState()


# ---------------------------------------------------------------------------
# Automation Service
# ---------------------------------------------------------------------------

async def automation_service_loop() -> None:
    """
    Main automation service loop.
    
    Runs periodic review checking and reply posting with error handling.
    """
    config = get_config()
    interval = config.automation.interval_minutes * 60  # Convert to seconds
    
    logger.info(
        "Automation service starting (interval: %d minutes)",
        config.automation.interval_minutes,
    )
    
    _service_state.start()
    
    while _service_state.running:
        try:
            logger.info("Running automation cycle...")
            
            # Run automation cycle
            stats = await run_automation_cycle()
            
            # Update state
            _service_state.update_stats(stats)
            
            logger.info("Automation cycle complete: %s", stats)
            
            # Sleep until next run
            if _service_state.running:
                logger.info("Sleeping for %d seconds...", interval)
                await asyncio.sleep(interval)
        
        except asyncio.CancelledError:
            logger.info("Automation service cancelled")
            break
        
        except Exception as exc:
            logger.exception("Automation service error: %s", exc)
            _service_state.update_stats({"error": str(exc)})
            
            # Exponential backoff on errors
            backoff = min(300, 60 * (2 ** _service_state.error_count))
            logger.warning("Backing off for %d seconds due to errors", backoff)
            await asyncio.sleep(backoff)
    
    _service_state.stop()
    logger.info("Automation service stopped")


# ---------------------------------------------------------------------------
# Service Control
# ---------------------------------------------------------------------------

def start_service() -> None:
    """Start automation service in background.
    
    Creates asyncio task and registers signal handlers.
    """
    if _service_state.task and not _service_state.task.done():
        logger.warning("Service already running")
        return
    
    # Create task
    _service_state.task = asyncio.create_task(automation_service_loop())
    
    # Register signal handlers for clean shutdown
    def signal_handler(sig, frame):
        logger.info("Received signal %s, stopping service...", sig)
        stop_service()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Automation service started")

def stop_service() -> None:
    """Stop automation service gracefully."""
    _service_state.stop()
    
    if _service_state.task and not _service_state.task.done():
        _service_state.task.cancel()
    
    logger.info("Automation service stop requested")


def get_service_status() -> dict:
    """Get current service status.
    
    Returns:
        Service status dictionary
    """
    return _service_state.get_health()


# ---------------------------------------------------------------------------
# Standalone Runner
# ---------------------------------------------------------------------------

async def main() -> None:
    """Run automation service as standalone script."""
    config = get_config()
    
    if not config.automation.enabled:
        logger.error("Automation service is disabled in configuration")
        return
    
    logger.info("Starting automation service (standalone mode)")
    
    try:
        await automation_service_loop()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    finally:
        logger.info("Automation service exiting")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    
    asyncio.run(main())