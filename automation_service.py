"""
automation_service.py – Optimized background automation service.

Manages periodic review checking and reply generation with proper
async task management, graceful shutdown, and health monitoring.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from config import get_config
from browser_automation import run_automation_cycle

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Automation Service
# ---------------------------------------------------------------------------

class AutomationService:
    """
    Background service for automated review monitoring and reply generation.
    
    Runs periodic automation cycles with proper async task management.
    """

    def __init__(self):
        """Initialize automation service."""
        self.config = get_config()
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.last_run: Optional[datetime] = None
        self.last_stats: Optional[dict] = None

    async def start(self) -> None:
        """Start automation service."""
        if self.running:
            logger.warning("Automation service already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._run_loop())
        logger.info("✓ Automation service started")

    async def stop(self) -> None:
        """Stop automation service gracefully."""
        if not self.running:
            return

        self.running = False
        
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        logger.info("✓ Automation service stopped")

    async def _run_loop(self) -> None:
        """Main service loop."""
        interval_seconds = self.config.automation.interval_minutes * 60
        
        logger.info(
            "Automation loop started (interval: %d minutes)",
            self.config.automation.interval_minutes
        )

        while self.running:
            try:
                logger.info("Starting automation cycle...")
                self.last_run = datetime.now(timezone.utc)
                
                # Run automation cycle
                stats = await run_automation_cycle()
                self.last_stats = stats
                
                logger.info("Automation cycle complete: %s", stats)
                
                # Wait for next interval
                if self.running:
                    await asyncio.sleep(interval_seconds)
                    
            except asyncio.CancelledError:
                logger.info("Automation loop cancelled")
                break
            except Exception as exc:
                logger.exception("Error in automation loop: %s", exc)
                
                # Wait before retry on error
                if self.running:
                    await asyncio.sleep(60)

    def get_status(self) -> dict:
        """
        Get service status.
        
        Returns:
            Status dictionary
        """
        return {
            "running": self.running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "last_stats": self.last_stats,
            "interval_minutes": self.config.automation.interval_minutes,
        }


# ---------------------------------------------------------------------------
# Global Service Instance
# ---------------------------------------------------------------------------

_service_instance: Optional[AutomationService] = None


def get_automation_service() -> AutomationService:
    """Get singleton automation service instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = AutomationService()
    return _service_instance
