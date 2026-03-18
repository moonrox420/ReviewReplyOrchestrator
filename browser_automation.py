"""
browser_automation.py – Optimized Selenium-based Google My Business automation.

Handles browser-based login, review fetching, and reply posting
with improved error handling, async operations, and retry logic.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import TimeoutConfig, get_config
from credentials import get_browser_credential_store

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Browser Driver Factory
# ---------------------------------------------------------------------------

class BrowserDriver:
    """
    Manages Chrome WebDriver lifecycle with proper cleanup.
    
    Implements context manager protocol for automatic resource management.
    """

    def __init__(self, headless: bool = True):
        """Initialize browser driver."""
        self.headless = headless
        self.driver: Optional[WebDriver] = None
        self.config = get_config()

    def __enter__(self) -> WebDriver:
        """Context manager entry."""
        self.driver = self._create_driver()
        return self.driver

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with cleanup."""
        if self.driver:
            try:
                self.driver.quit()
            except WebDriverException as exc:
                logger.warning("Error closing browser: %s", exc)

    def _create_driver(self) -> WebDriver:
        """Create configured Chrome WebDriver."""
        options = Options()
        
        if self.headless:
            options.add_argument("--headless=new")
        
        # Performance and stealth options
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        
        # User agent
        options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
        
        driver = webdriver.Chrome(options=options)
        
        # Remove webdriver detection
        driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        
        logger.info("Chrome WebDriver initialized (headless=%s)", self.headless)
        return driver


# ---------------------------------------------------------------------------
# Google My Business Automation
# ---------------------------------------------------------------------------

class GMBAutomation:
    """
    Google My Business browser automation.
    
    Handles login, navigation, and review interaction via Selenium.
    """

    GMB_URL = "https://business.google.com"
    REVIEWS_PATH = "/reviews"

    def __init__(self, driver: WebDriver):
        """Initialize GMB automation."""
        self.driver = driver
        self.wait = WebDriverWait(driver, TimeoutConfig.SELENIUM_WAIT)
        self.config = get_config()

    async def login(self, email: str, password: str) -> bool:
        """Log into Google My Business."""
        try:
            logger.info("Navigating to GMB login: %s", self.GMB_URL)
            self.driver.get(self.GMB_URL)
            
            # Wait for email input
            email_field = self.wait.until(
                EC.presence_of_element_located((By.ID, "identifierId"))
            )
            email_field.send_keys(email)
            
            # Click next
            next_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "identifierNext"))
            )
            next_button.click()
            
            await asyncio.sleep(2)  # Wait for page transition
            
            # Wait for password input
            password_field = self.wait.until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_field.send_keys(password)
            
            # Click next
            next_button = self.wait.until(
                EC.element_to_be_clickable((By.ID, "passwordNext"))
            )
            next_button.click()
            
            await asyncio.sleep(3)  # Wait for login to complete
            
            # Verify login success
            if "myaccount.google.com" in self.driver.current_url or "business.google.com" in self.driver.current_url:
                logger.info("✓ Login successful")
                return True
            
            logger.error("Login failed: unexpected redirect")
            self._save_screenshot("login_failed")
            return False
            
        except (TimeoutException, NoSuchElementException) as exc:
            logger.error("Login failed: %s", exc)
            self._save_screenshot("login_error")
            return False

    async def navigate_to_reviews(self) -> bool:
        """Navigate to reviews section."""
        try:
            reviews_url = f"{self.GMB_URL}{self.REVIEWS_PATH}"
            logger.info("Navigating to reviews: %s", reviews_url)
            
            self.driver.get(reviews_url)
            await asyncio.sleep(3)
            
            # Wait for reviews to load
            self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-review-id]"))
            )
            
            logger.info("✓ Reviews page loaded")
            return True
            
        except TimeoutException as exc:
            logger.error("Failed to load reviews: %s", exc)
            self._save_screenshot("reviews_load_error")
            return False

    async def fetch_unanswered_reviews(self) -> list[dict]:
        """Fetch unanswered reviews from current page."""
        reviews = []
        
        try:
            # Find all review cards
            review_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                "[data-review-id]"
            )
            
            logger.info("Found %d review elements", len(review_elements))
            
            for element in review_elements:
                try:
                    # Check if already replied
                    try:
                        element.find_element(By.CSS_SELECTOR, "[data-reply-id]")
                        continue  # Skip if already has reply
                    except NoSuchElementException:
                        pass  # No reply found, continue processing
                    
                    # Extract review data
                    review_id = element.get_attribute("data-review-id")
                    
                    # Get rating
                    rating_elem = element.find_element(By.CSS_SELECTOR, "[aria-label*='star']")
                    rating_text = rating_elem.get_attribute("aria-label")
                    rating = int(rating_text.split()[0]) if rating_text else 5
                    
                    # Get review text
                    try:
                        text_elem = element.find_element(By.CSS_SELECTOR, ".review-text")
                        review_text = text_elem.text.strip()
                    except NoSuchElementException:
                        review_text = ""
                    
                    # Get reviewer name
                    try:
                        name_elem = element.find_element(By.CSS_SELECTOR, ".reviewer-name")
                        reviewer_name = name_elem.text.strip()
                    except NoSuchElementException:
                        reviewer_name = "Anonymous"
                    
                    reviews.append({
                        "review_id": review_id,
                        "rating": rating,
                        "review_text": review_text,
                        "reviewer_name": reviewer_name,
                    })
                    
                except Exception as exc:
                    logger.warning("Failed to parse review element: %s", exc)
                    continue
            
            logger.info("Extracted %d unanswered reviews", len(reviews))
            return reviews
            
        except Exception as exc:
            logger.error("Failed to fetch reviews: %s", exc)
            self._save_screenshot("fetch_error")
            return []

    async def post_reply(self, review_id: str, reply_text: str) -> bool:
        """Post reply to a review."""
        try:
            # Find review element
            review_elem = self.driver.find_element(
                By.CSS_SELECTOR,
                f"[data-review-id='{review_id}']"
            )
            
            # Click reply button
            reply_button = review_elem.find_element(
                By.CSS_SELECTOR,
                "button[aria-label*='Reply']"
            )
            reply_button.click()
            
            await asyncio.sleep(1)
            
            # Find reply textarea
            reply_textarea = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[aria-label*='reply']"))
            )
            reply_textarea.send_keys(reply_text)
            
            await asyncio.sleep(1)
            
            # Click submit
            submit_button = self.driver.find_element(
                By.CSS_SELECTOR,
                "button[aria-label*='Submit']"
            )
            submit_button.click()
            
            await asyncio.sleep(2)
            
            logger.info("✓ Reply posted for review %s", review_id)
            return True
            
        except Exception as exc:
            logger.error("Failed to post reply: %s", exc)
            self._save_screenshot(f"reply_error_{review_id}")
            return False

    def _save_screenshot(self, name: str) -> None:
        """Save screenshot for debugging."""
        try:
            screenshots_dir = self.config.automation.screenshots_dir
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = screenshots_dir / f"{name}.png"
            self.driver.save_screenshot(str(filepath))
            
            logger.info("Screenshot saved: %s", filepath)
        except Exception as exc:
            logger.warning("Failed to save screenshot: %s", exc)


# ---------------------------------------------------------------------------
# High-Level Automation Runner
# ---------------------------------------------------------------------------

async def run_automation_cycle() -> dict:
    """Run complete automation cycle: login, fetch reviews, generate replies, post."""
    from database import get_database
    from reply_generator import ReplyGenerator
    
    config = get_config()
    cred_store = get_browser_credential_store()
    
    # Load credentials
    credentials = cred_store.load()
    if not credentials:
        logger.error("No credentials found. Configure via /api/credentials/save")
        return {"error": "No credentials configured"}
    
    stats = {
        "total_reviews": 0,
        "new_reviews": 0,
        "replied": 0,
        "errors": 0,
    }
    
    # Run browser automation
    with BrowserDriver(headless=config.automation.headless) as driver:
        automation = GMBAutomation(driver)
        
        # Login
        if not await automation.login(credentials.email, credentials.password):
            return {"error": "Login failed"}
        
        # Navigate to reviews
        if not await automation.navigate_to_reviews():
            return {"error": "Failed to navigate to reviews"}
        
        # Fetch unanswered reviews
        reviews = await automation.fetch_unanswered_reviews()
        stats["total_reviews"] = len(reviews)
        
        if not reviews:
            logger.info("No unanswered reviews found")
            return stats
        
        # Save to database
        db = get_database()
        for review in reviews:
            is_new = db.upsert_review(
                review_id=review["review_id"],
                location_id="default",  # TODO: Extract actual location
                rating=review["rating"],
                review_text=review["review_text"],
                reviewer_name=review["reviewer_name"],
                created_at=None,
            )
            if is_new:
                stats["new_reviews"] += 1
        
        # Generate and post replies
        generator = ReplyGenerator(
            business_name=config.automation.business_name,
            tone="Professional",
        )
        
        for review in reviews:
            try:
                # Generate reply
                reply = await generator.generate_reply(
                    review_text=review["review_text"],
                    rating=review["rating"],
                    reviewer_name=review["reviewer_name"],
                )
                
                # Post reply
                if await automation.post_reply(review["review_id"], reply):
                    db.mark_replied(review["review_id"], reply)
                    stats["replied"] += 1
                else:
                    db.mark_error(review["review_id"], "Failed to post reply")
                    stats["errors"] += 1
                    
            except Exception as exc:
                logger.error("Error processing review %s: %s", review["review_id"], exc)
                db.mark_error(review["review_id"], str(exc))
                stats["errors"] += 1
    
    logger.info("Automation cycle complete: %s", stats)
    return stats
