"""
google_api.py – Google My Business OAuth2 + API helpers.

Responsibilities:
- Browser-based OAuth2 login flow for initial setup
- Secure local storage of access/refresh tokens (Fernet-encrypted)
- Automatic token refresh when expired
- Fetch new reviews from Google My Business locations
- Post AI-generated replies directly to reviews
- Rate-limit handling with exponential back-off
"""

import json
import logging
import os
import time
from typing import Optional

import httpx
from cryptography.fernet import Fernet
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config (values injected via engine.env / environment variables)
# ---------------------------------------------------------------------------
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv(
    "GOOGLE_REDIRECT_URI", "http://localhost:7363/oauth/callback"
)
TOKEN_STORAGE_PATH = os.getenv("TOKEN_STORAGE_PATH", "./tokens/google_tokens.json")
FERNET_KEY_PATH = os.getenv("FERNET_KEY_PATH", "./tokens/fernet.key")

SCOPES = ["https://www.googleapis.com/auth/business.manage"]

# Google My Business (new) API base
GMB_BASE = "https://mybusinessbusinessinformation.googleapis.com/v1"
GMB_REVIEWS_BASE = "https://mybusiness.googleapis.com/v4"

# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------


def _get_or_create_fernet_key() -> bytes:
    """Return the Fernet symmetric key, creating one if absent."""
    key_path = FERNET_KEY_PATH
    os.makedirs(os.path.dirname(key_path) or ".", exist_ok=True)
    if os.path.exists(key_path):
        with open(key_path, "rb") as f:
            return f.read().strip()
    key = Fernet.generate_key()
    with open(key_path, "wb") as f:
        f.write(key)
    # Restrict permissions on the key file (best-effort on Windows)
    try:
        os.chmod(key_path, 0o600)
    except OSError:
        pass
    return key


def _fernet() -> Fernet:
    return Fernet(_get_or_create_fernet_key())


# ---------------------------------------------------------------------------
# Token storage / retrieval
# ---------------------------------------------------------------------------


def save_tokens(creds: Credentials) -> None:
    """Encrypt and persist OAuth2 credentials to disk."""
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes) if creds.scopes else SCOPES,
    }
    plaintext = json.dumps(token_data).encode()
    encrypted = _fernet().encrypt(plaintext)
    path = TOKEN_STORAGE_PATH
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "wb") as f:
        f.write(encrypted)
    logger.info("OAuth tokens saved to %s", path)


def load_tokens() -> Optional[Credentials]:
    """Load and decrypt stored OAuth2 credentials.  Returns None if absent."""
    path = TOKEN_STORAGE_PATH
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
            encrypted = f.read()
        plaintext = _fernet().decrypt(encrypted)
        data = json.loads(plaintext)
        creds = Credentials(
            token=data["token"],
            refresh_token=data["refresh_token"],
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=data["client_id"],
            client_secret=data["client_secret"],
            scopes=data.get("scopes", SCOPES),
        )
        return creds
    except Exception as exc:
        logger.warning("Failed to load tokens: %s", exc)
        return None


def tokens_exist() -> bool:
    """Return True if encrypted token file exists on disk."""
    return os.path.exists(TOKEN_STORAGE_PATH)


# ---------------------------------------------------------------------------
# OAuth2 flow helpers
# ---------------------------------------------------------------------------


def _client_config() -> dict:
    return {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uris": [GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


def get_oauth_flow() -> Flow:
    """Build an OAuth2 Flow object."""
    flow = Flow.from_client_config(
        _client_config(),
        scopes=SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )
    return flow


def get_authorization_url() -> tuple[str, str]:
    """Return (authorization_url, state) for redirecting the user to Google."""
    flow = get_oauth_flow()
    url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return url, state


def exchange_code_for_tokens(code: str, state: str) -> Credentials:
    """Exchange an authorization code for OAuth2 credentials."""
    flow = get_oauth_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    save_tokens(creds)
    return creds


# ---------------------------------------------------------------------------
# Credentials refresh helper
# ---------------------------------------------------------------------------


def get_valid_credentials() -> Optional[Credentials]:
    """Return valid (refreshed if necessary) credentials, or None."""
    creds = load_tokens()
    if creds is None:
        return None
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            save_tokens(creds)
            logger.info("OAuth tokens refreshed successfully")
        except Exception as exc:
            logger.error("Failed to refresh tokens: %s", exc)
            return None
    return creds


# ---------------------------------------------------------------------------
# Low-level HTTP helper with exponential back-off
# ---------------------------------------------------------------------------


def _auth_headers(creds: Credentials) -> dict:
    return {"Authorization": f"Bearer {creds.token}"}


def _request_with_backoff(
    method: str,
    url: str,
    creds: Credentials,
    max_retries: int = 4,
    **kwargs,
) -> dict:
    """
    Perform an authenticated HTTP request.
    Retries on 429 / 5xx with exponential back-off.
    Raises RuntimeError on unrecoverable errors.
    """
    delay = 1.0
    for attempt in range(max_retries):
        with httpx.Client(timeout=30) as client:
            resp = client.request(
                method,
                url,
                headers=_auth_headers(creds),
                **kwargs,
            )
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (401, 429, 500, 502, 503, 504):
            if attempt < max_retries - 1:
                logger.warning(
                    "Request to %s returned %d; retrying in %.1fs",
                    url,
                    resp.status_code,
                    delay,
                )
                # Refresh token on auth errors before retrying
                if resp.status_code == 401 and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        save_tokens(creds)
                    except Exception:
                        pass
                time.sleep(delay)
                delay = min(delay * 2, 60)
                continue
        raise RuntimeError(
            f"Google API error {resp.status_code} for {url}: {resp.text[:500]}"
        )
    raise RuntimeError(f"Max retries exceeded for {url}")


# ---------------------------------------------------------------------------
# Google My Business API helpers
# ---------------------------------------------------------------------------


def list_accounts(creds: Credentials) -> list:
    """Return a list of Google My Business account resources."""
    url = "https://mybusinessaccountmanagement.googleapis.com/v1/accounts"
    data = _request_with_backoff("GET", url, creds)
    return data.get("accounts", [])


def list_locations(creds: Credentials, account_name: str) -> list:
    """Return all locations for a given account resource name."""
    url = f"https://mybusinessbusinessinformation.googleapis.com/v1/{account_name}/locations"
    params = {"readMask": "name,title"}
    data = _request_with_backoff("GET", url, creds, params=params)
    return data.get("locations", [])


def list_reviews(creds: Credentials, location_name: str) -> list:
    """Return all reviews for a given location resource name."""
    url = f"https://mybusiness.googleapis.com/v4/{location_name}/reviews"
    data = _request_with_backoff("GET", url, creds)
    return data.get("reviews", [])


def post_reply(creds: Credentials, review_name: str, reply_text: str) -> dict:
    """
    Post (or update) the owner reply on a review.

    review_name – full resource name, e.g.
        "accounts/123/locations/456/reviews/789"
    """
    url = f"https://mybusiness.googleapis.com/v4/{review_name}/reply"
    payload = {"comment": reply_text}
    data = _request_with_backoff("PUT", url, creds, json=payload)
    return data
