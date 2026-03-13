"""
browser_automation.py – Selenium-based Google My Business browser automation.

Logs into Google My Business using stored credentials, navigates to the
Reviews section, identifies unanswered reviews, and posts AI-generated
replies automatically.  No Google API key required.

Usage (standalone test):
    python browser_automation.py

Environment / config:
    Credentials are read from config.json (encrypted with Fernet).
    See automation_service.py for the background scheduling loop.
"""

from __future__ import annotations

import json
import logging
import os
import time
import traceback
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

CONFIG_PATH = os.getenv("CONFIG_PATH", "config.json")
FERNET_KEY_PATH = os.getenv("FERNET_KEY_PATH", "./tokens/fernet.key")
SCREENSHOTS_DIR = os.getenv("SCREENSHOTS_DIR", "./logs/screenshots")

# Maximum number of characters to take from a review card's text content
# when a dedicated review-text element cannot be found.
MAX_REVIEW_TEXT_LENGTH = 500

# How many seconds to sleep between stop-event checks inside the service loop.
STOP_CHECK_INTERVAL_SECONDS = 5

# ---------------------------------------------------------------------------
# Selenium imports (lazy-loaded so the rest of the app works without Selenium)
# ---------------------------------------------------------------------------

def _get_driver(headless: bool = True):
    """Return a configured Chrome WebDriver instance."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager
    except ImportError as exc:
        raise RuntimeError(
            "Selenium or webdriver-manager is not installed. "
            "Run: pip install selenium webdriver-manager"
        ) from exc

    options = Options()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------

def _get_or_create_fernet_key() -> bytes:
    key_path = Path(FERNET_KEY_PATH)
    key_path.parent.mkdir(parents=True, exist_ok=True)
    if key_path.exists():
        return key_path.read_bytes().strip()
    key = Fernet.generate_key()
    key_path.write_bytes(key)
    try:
        os.chmod(key_path, 0o600)
    except OSError as exc:
        logger.warning("Could not set restrictive permissions on key file %s: %s", key_path, exc)
    return key


def _fernet() -> Fernet:
    return Fernet(_get_or_create_fernet_key())


def load_config() -> dict:
    """Load config.json, returning defaults if file is absent."""
    defaults: dict = {
        "automation": {
            "enabled": True,
            "interval_minutes": 60,
            "headless": True,
        },
        "google_credentials": {
            "email": "",
            "password_enc": "",
        },
    }
    if not os.path.exists(CONFIG_PATH):
        return defaults
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge defaults for any missing keys
        for k, v in defaults.items():
            data.setdefault(k, v)
        return data
    except Exception as exc:
        logger.warning("Failed to load config.json: %s", exc)
        return defaults


def save_config(cfg: dict) -> None:
    """Persist config (without plaintext password) to config.json."""
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def get_credentials() -> tuple[str, str]:
    """Return (email, password) from config.  Password is decrypted."""
    cfg = load_config()
    creds = cfg.get("google_credentials", {})
    email: str = creds.get("email", "")
    password_enc: str = creds.get("password_enc", "")
    if not password_enc:
        return email, ""
    try:
        password = _fernet().decrypt(password_enc.encode()).decode()
    except (InvalidToken, Exception) as exc:
        logger.error("Failed to decrypt password: %s", exc)
        password = ""
    return email, password


def save_credentials(email: str, password: str) -> None:
    """Encrypt and persist Google Business credentials to config.json."""
    cfg = load_config()
    encrypted = _fernet().encrypt(password.encode()).decode()
    cfg["google_credentials"] = {
        "email": email,
        "password_enc": encrypted,
    }
    # Never write plaintext password
    save_config(cfg)
    logger.info("Credentials saved for %s", email)


def credentials_configured() -> bool:
    """Return True if both email and encrypted password are present."""
    email, password = get_credentials()
    return bool(email and password)


# ---------------------------------------------------------------------------
# Screenshot helper
# ---------------------------------------------------------------------------

def _screenshot(driver, label: str) -> Optional[str]:
    """Save a screenshot and return the file path (None on failure)."""
    try:
        Path(SCREENSHOTS_DIR).mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d-%H%M%S")
        path = os.path.join(SCREENSHOTS_DIR, f"{ts}-{label}.png")
        driver.save_screenshot(path)
        logger.info("Screenshot saved: %s", path)
        return path
    except Exception as exc:
        logger.warning("Could not save screenshot: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Login helper
# ---------------------------------------------------------------------------

def _wait_for_element(driver, by, value, timeout: int = 20):
    """Wait up to *timeout* seconds for an element to be present."""
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    return WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((by, value))
    )


def _login(driver, email: str, password: str) -> bool:
    """
    Log into Google with the supplied credentials.

    Returns True on success, False on failure.
    Pauses for manual intervention if 2FA / CAPTCHA is detected.
    """
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException, NoSuchElementException

    try:
        logger.info("Navigating to Google sign-in…")
        driver.get("https://accounts.google.com/signin")

        # Enter email
        email_field = _wait_for_element(driver, By.ID, "identifierId")
        email_field.clear()
        email_field.send_keys(email)

        next_btn = _wait_for_element(driver, By.ID, "identifierNext")
        next_btn.click()
        time.sleep(2)

        # Enter password (Google uses 'Passwords' or 'password' depending on flow version)
        password_field = None
        for pw_selector in [
            (By.NAME, "Passwords"),
            (By.NAME, "password"),
            (By.CSS_SELECTOR, 'input[type="password"]'),
        ]:
            try:
                password_field = _wait_for_element(driver, pw_selector[0], pw_selector[1], timeout=8)
                break
            except Exception:
                continue
        if password_field is None:
            logger.error("Password field not found on login page.")
            _screenshot(driver, "login-no-password-field")
            return False
        password_field.send_keys(password)

        pass_next = _wait_for_element(driver, By.ID, "passwordNext")
        pass_next.click()
        time.sleep(3)

        # Detect 2FA / CAPTCHA
        page_src = driver.page_source.lower()
        if any(kw in page_src for kw in ("2-step", "two-step", "verify it's you", "phone", "authenticator")):
            logger.warning(
                "2FA detected – automation paused. "
                "Complete the 2FA challenge in the browser window, then the "
                "service will retry on the next scheduled run."
            )
            _screenshot(driver, "2fa-detected")
            return False

        if "captcha" in page_src or "unusual traffic" in page_src:
            logger.warning(
                "CAPTCHA detected – automation paused. "
                "Resolve the CAPTCHA manually and restart the service."
            )
            _screenshot(driver, "captcha-detected")
            return False

        # Confirm we are logged in by checking for account chooser or dashboard
        try:
            _wait_for_element(driver, By.XPATH,
                              '//*[@aria-label="Google Account"]', timeout=10)
        except TimeoutException:
            # Some flows redirect directly; check URL instead
            if "myaccount.google.com" in driver.current_url or "google.com" in driver.current_url:
                pass
            else:
                _screenshot(driver, "login-unknown-state")
                logger.error("Login may have failed. Current URL: %s", driver.current_url)
                return False

        logger.info("Login successful.")
        return True

    except Exception as exc:
        logger.error("Login error: %s\n%s", exc, traceback.format_exc())
        _screenshot(driver, "login-error")
        return False


# ---------------------------------------------------------------------------
# Review scraping & reply posting
# ---------------------------------------------------------------------------

def _navigate_to_reviews(driver) -> bool:
    """
    Navigate to the Google Business reviews management page.
    Returns True on success.
    """
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import TimeoutException

    try:
        logger.info("Navigating to Google Business Profile…")
        driver.get("https://business.google.com")
        time.sleep(3)

        # Try the direct reviews URL pattern
        current_url = driver.current_url
        logger.debug("Business profile URL: %s", current_url)

        # Look for "Reviews" link or navigate directly
        try:
            reviews_link = _wait_for_element(
                driver, By.XPATH,
                '//a[contains(@href,"reviews") or contains(text(),"Reviews") '
                'or contains(@aria-label,"Reviews")]',
                timeout=10,
            )
            reviews_link.click()
            time.sleep(2)
        except TimeoutException:
            # Fall back: navigate directly
            driver.get("https://business.google.com/reviews")
            time.sleep(3)

        logger.info("Reviews page loaded: %s", driver.current_url)
        return True

    except Exception as exc:
        logger.error("Failed to navigate to reviews: %s", exc)
        _screenshot(driver, "reviews-nav-error")
        return False


def scrape_unanswered_reviews(driver) -> list[dict]:
    """
    Scrape unanswered reviews from the current Google Business reviews page.

    Returns a list of dicts with keys: element, text, rating, review_id.
    Only reviews that have a "Reply" button (no existing reply) are returned.
    """
    from selenium.webdriver.common.by import By

    unanswered: list[dict] = []

    try:
        time.sleep(2)
        # Find all review cards
        review_cards = driver.find_elements(
            By.XPATH,
            '//*[contains(@class,"review") or contains(@data-reviewid,"")]'
            '[.//*[contains(text(),"Reply") or contains(@aria-label,"Reply")]]',
        )

        if not review_cards:
            # Alternative selector set
            review_cards = driver.find_elements(
                By.XPATH,
                '//div[contains(@jsaction,"click:") and '
                './/span[contains(@class,"star") or @aria-label]]',
            )

        logger.info("Found %d potential review cards.", len(review_cards))

        for card in review_cards:
            try:
                # Check for Reply button (means unanswered)
                reply_btns = card.find_elements(
                    By.XPATH,
                    './/button[contains(text(),"Reply") or '
                    'contains(@aria-label,"Reply") or '
                    'contains(@data-value,"Reply")]',
                )
                if not reply_btns:
                    continue

                # Extract review text
                text_el = card.find_elements(
                    By.XPATH, './/span[contains(@class,"review-text") or @data-review-text]'
                )
                review_text = text_el[0].text if text_el else card.text[:MAX_REVIEW_TEXT_LENGTH]

                # Extract star rating (look for aria-label with "stars")
                rating = 3  # default
                star_el = card.find_elements(
                    By.XPATH, './/*[@aria-label and contains(@aria-label,"star")]'
                )
                if star_el:
                    label = star_el[0].get_attribute("aria-label")
                    for n in range(1, 6):
                        if str(n) in (label or ""):
                            rating = n
                            break
                else:
                    logger.warning(
                        "Could not extract star rating for review card; defaulting to 3 stars."
                    )

                review_id = card.get_attribute("data-reviewid") or str(id(card))
                unanswered.append({
                    "element": card,
                    "reply_button": reply_btns[0],
                    "text": review_text,
                    "rating": rating,
                    "review_id": review_id,
                })
            except Exception as exc:
                logger.debug("Skipping malformed review card: %s", exc)
                continue

    except Exception as exc:
        logger.error("Error scraping reviews: %s", exc)
        _screenshot(driver, "scrape-error")

    return unanswered


def post_reply_to_review(driver, review: dict, reply_text: str) -> bool:
    """
    Click the Reply button on a review card, type the reply, and submit it.

    Returns True on success.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

    try:
        reply_btn = review["reply_button"]
        driver.execute_script("arguments[0].scrollIntoView(true);", reply_btn)
        time.sleep(0.5)
        reply_btn.click()
        time.sleep(1.5)

        # Find the reply text area
        text_area = None
        for selector in [
            (By.XPATH, '//textarea[@placeholder or contains(@aria-label,"reply") or contains(@aria-label,"Reply")]'),
            (By.CSS_SELECTOR, 'textarea[aria-label*="reply" i], textarea[placeholder*="reply" i]'),
            (By.TAG_NAME, 'textarea'),
        ]:
            try:
                text_area = _wait_for_element(driver, selector[0], selector[1], timeout=8)
                break
            except TimeoutException:
                continue

        if text_area is None:
            logger.error("Could not find reply text area for review %s", review.get("review_id"))
            _screenshot(driver, f"no-textarea-{review.get('review_id', 'unknown')}")
            return False

        # Clear and type reply
        text_area.click()
        text_area.send_keys(Keys.CONTROL + "a")
        text_area.send_keys(Keys.DELETE)
        text_area.send_keys(reply_text)
        time.sleep(0.5)

        # Submit – look for "Post reply" / "Submit" button
        submitted = False
        for submit_xpath in [
            '//button[contains(text(),"Post reply") or contains(text(),"Reply") or '
            'contains(text(),"Submit") or contains(text(),"Post")]',
            '//button[@type="submit"]',
        ]:
            try:
                submit_btn = _wait_for_element(driver, By.XPATH, submit_xpath, timeout=6)
                submit_btn.click()
                submitted = True
                break
            except TimeoutException:
                continue

        if not submitted:
            logger.error("Could not find submit button for review %s", review.get("review_id"))
            _screenshot(driver, f"no-submit-{review.get('review_id', 'unknown')}")
            return False

        # Wait for confirmation (the reply area should disappear or a success banner appear)
        time.sleep(2)
        logger.info("Reply posted for review %s", review.get("review_id"))
        return True

    except StaleElementReferenceException:
        logger.warning("Stale element for review %s – page may have refreshed.", review.get("review_id"))
        return False
    except Exception as exc:
        logger.error(
            "Error posting reply for review %s: %s\n%s",
            review.get("review_id"), exc, traceback.format_exc(),
        )
        _screenshot(driver, f"reply-error-{review.get('review_id', 'unknown')}")
        return False


# ---------------------------------------------------------------------------
# Main public API
# ---------------------------------------------------------------------------

def run_browser_automation(
    generate_reply_fn,  # callable(rating: int, text: str) -> str
) -> dict:
    """
    Full automation pass:
      1. Load credentials.
      2. Launch Chrome (headless or not, per config).
      3. Log into Google.
      4. Navigate to reviews.
      5. For each unanswered review: generate + post reply.
      6. Return summary dict.

    ``generate_reply_fn`` is injected so this module stays decoupled from
    app.py's async machinery.
    """
    cfg = load_config()
    headless: bool = cfg.get("automation", {}).get("headless", True)
    email, password = get_credentials()

    if not email or not password:
        return {
            "ok": False,
            "error": "No credentials configured. Call /automation/setup first.",
        }

    summary = {
        "ok": True,
        "reviews_found": 0,
        "replies_posted": 0,
        "errors": 0,
        "skipped": 0,
    }

    driver = None
    try:
        driver = _get_driver(headless=headless)

        if not _login(driver, email, password):
            summary["ok"] = False
            summary["error"] = (
                "Login failed. Check credentials, or 2FA/CAPTCHA intervention required."
            )
            return summary

        if not _navigate_to_reviews(driver):
            summary["ok"] = False
            summary["error"] = "Failed to navigate to reviews page."
            return summary

        reviews = scrape_unanswered_reviews(driver)
        summary["reviews_found"] = len(reviews)
        logger.info("%d unanswered reviews found.", len(reviews))

        for review in reviews:
            try:
                reply_text = generate_reply_fn(review["rating"], review["text"])
                success = post_reply_to_review(driver, review, reply_text)
                if success:
                    summary["replies_posted"] += 1
                else:
                    summary["errors"] += 1
            except Exception as exc:
                logger.error("Unhandled error for review %s: %s", review.get("review_id"), exc)
                summary["errors"] += 1

    except Exception as exc:
        logger.error("Browser automation crashed: %s\n%s", exc, traceback.format_exc())
        if driver:
            _screenshot(driver, "crash")
        summary["ok"] = False
        summary["error"] = str(exc)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    return summary
