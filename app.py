"""
app.py – Main FastAPI application with optimized architecture.

Production-ready web server with dependency injection, proper error handling,
async operations, and comprehensive API endpoints.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Annotated, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from config import get_config
from credentials import BrowserCredentials, get_browser_credential_store
from database import DatabaseManager, get_database
from google_api import (
    GoogleMyBusinessClient,
    exchange_code_for_tokens,
    get_authorization_url,
)
from license_validator import get_license_validator
from reply_generator import BatchReplyGenerator, ReplyGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Application Lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("🚀 Starting ReviewReplyOrchestrator")
    
    # Initialize database
    db = get_database()
    logger.info("✓ Database initialized: %s", db.db_path)
    
    # Load configuration
    config = get_config()
    logger.info("✓ Configuration loaded")
    
    yield
    
    logger.info("🛑 Shutting down ReviewReplyOrchestrator")


# ---------------------------------------------------------------------------
# FastAPI Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="ReviewReplyOrchestrator",
    description="AI-powered Google My Business review reply automation",
    version="2.0.0",
    lifespan=lifespan,
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Pydantic Models
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "2.0.0"
    database: bool
    oauth_configured: bool
    stripe_configured: bool


class LicenseValidateRequest(BaseModel):
    """License validation request."""
    license_key: str = Field(..., min_length=1, description="License key to validate")


class LicenseValidateResponse(BaseModel):
    """License validation response."""
    valid: bool
    message: str


class CredentialsSaveRequest(BaseModel):
    """Browser credentials save request."""
    email: str = Field(..., min_length=1, description="Google Business email")
    password: str = Field(..., min_length=1, description="Google Business password")


class GenerateReplyRequest(BaseModel):
    """Single reply generation request."""
    review_text: str = Field(..., min_length=1, max_length=5000)
    rating: int = Field(..., ge=1, le=5)
    reviewer_name: Optional[str] = None
    business_name: str = Field(default="Our Business")
    tone: str = Field(default="Professional")
    backend: str = Field(default="ollama", pattern="^(ollama|lmstudio)$")


class GenerateReplyResponse(BaseModel):
    """Reply generation response."""
    reply: str
    model_used: str


class BatchGenerateRequest(BaseModel):
    """Batch reply generation request."""
    review_ids: list[str] = Field(..., min_items=1, max_items=100)
    backend: str = Field(default="ollama", pattern="^(ollama|lmstudio)$")


class BatchGenerateResponse(BaseModel):
    """Batch generation response."""
    total: int
    succeeded: int
    failed: int
    results: list[dict]


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None


# ---------------------------------------------------------------------------
# Dependency Injection
# ---------------------------------------------------------------------------

def get_db() -> DatabaseManager:
    """Get database dependency."""
    return get_database()


def get_gmb_client() -> GoogleMyBusinessClient:
    """Get Google My Business client dependency."""
    return GoogleMyBusinessClient()


def get_reply_gen() -> ReplyGenerator:
    """Get reply generator dependency."""
    config = get_config()
    return ReplyGenerator(
        business_name=config.automation.business_name,
        tone="Professional",
        persona="general",
    )


# ---------------------------------------------------------------------------
# Error Handlers
# ---------------------------------------------------------------------------

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            detail=str(exc.detail) if exc.detail else None,
        ).model_dump(),
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            detail=str(exc) if logger.level <= logging.DEBUG else None,
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# API Routes - Health & Status
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Render main dashboard."""
    config = get_config()
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "business_name": config.automation.business_name,
        },
    )

@app.get("/health", response_model=HealthResponse)
async def health_check(db: Annotated[DatabaseManager, Depends(get_db)]):
    """
    Health check endpoint.
    
    Returns application health status and configuration.
    """
    config = get_config()
    
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        database=db.db_path.exists(),
        oauth_configured=config.google_oauth.is_configured,
        stripe_configured=config.stripe.is_configured,
    )


# ---------------------------------------------------------------------------
# API Routes - License Management
# ---------------------------------------------------------------------------

@app.post("/api/license/validate", response_model=LicenseValidateResponse)
async def validate_license(request: LicenseValidateRequest):
    """
    Validate license key.
    
    Args:
        request: License validation request
    
    Returns:
        Validation result
    """
    validator = get_license_validator()
    is_valid, message = validator.validate(request.license_key)
    
    return LicenseValidateResponse(valid=is_valid, message=message)


# ---------------------------------------------------------------------------
# API Routes - Credentials Management
# ---------------------------------------------------------------------------

@app.post("/api/credentials/save", status_code=status.HTTP_201_CREATED)
async def save_credentials(request: CredentialsSaveRequest):
    """
    Save browser automation credentials.
    
    Args:
        request: Credentials save request
    
    Returns:
        Success message
    """
    store = get_browser_credential_store()
    credentials = BrowserCredentials(
        email=request.email,
        password=request.password,
    )
    
    store.save(credentials)
    
    return {"message": "Credentials saved successfully"}

@app.get("/api/credentials/status")
async def credentials_status():
    """
    Check if credentials are configured.
    
    Returns:
        Credential configuration status
    """
    store = get_browser_credential_store()
    creds = store.load()
    
    return {
        "configured": creds is not None,
        "email": creds.email if creds else None,
    }

@app.delete("/api/credentials", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credentials():
    """Delete stored credentials."""
    store = get_browser_credential_store()
    store.delete()


# ---------------------------------------------------------------------------
# API Routes - OAuth Flow
# ---------------------------------------------------------------------------

@app.get("/oauth/login")
async def oauth_login():
    """
    Initiate OAuth2 flow.
    
    Redirects to Google authorization page.
    """
    try:
        auth_url = get_authorization_url()
        return RedirectResponse(url=auth_url)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

@app.get("/oauth/callback")
async def oauth_callback(
    code: Annotated[Optional[str], Query()] = None,
    error: Annotated[Optional[str], Query()] = None,
):
    """
    Handle OAuth2 callback.
    
    Args:
        code: Authorization code
        error: Error message if authorization failed
    
    Returns:
        Redirect to dashboard
    """
    if error:
        logger.error("OAuth error: %s", error)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authorization failed: {error}",
        )
    
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No authorization code received",
        )
    
    try:
        exchange_code_for_tokens(code)
        return RedirectResponse(url="/?oauth=success")
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

@app.get("/oauth/status")
async def oauth_status():
    """
    Check OAuth authentication status.
    
    Returns:
        OAuth configuration and authentication status
    """
    from credentials import get_oauth_token_store
    
    config = get_config()
    token_store = get_oauth_token_store()
    tokens = token_store.load()
    
    return {
        "configured": config.google_oauth.is_configured,
        "authenticated": tokens is not None,
    }


# ---------------------------------------------------------------------------
# API Routes - Review Management
# ---------------------------------------------------------------------------

@app.get("/api/reviews")
async def list_reviews(
    db: Annotated[DatabaseManager, Depends(get_db)],
    limit: Annotated[Optional[int], Query(ge=1, le=1000)] = None,
):
    """
    List all reviews.
    
    Args:
        db: Database manager
        limit: Maximum number of reviews to return
    
    Returns:
        List of reviews
    """
    reviews = db.get_all_reviews(limit=limit)
    pending_count = db.get_pending_count()
    
    return {
        "total": len(reviews),
        "pending": pending_count,
        "reviews": reviews,
    }

@app.get("/api/reviews/pending")
async def get_pending_reviews(db: Annotated[DatabaseManager, Depends(get_db)]):
    """
    Get count of pending reviews.
    
    Args:
        db: Database manager
    
    Returns:
        Pending review count
    """
    count = db.get_pending_count()
    return {"pending": count}


# ---------------------------------------------------------------------------
# API Routes - Reply Generation
# ---------------------------------------------------------------------------

@app.post("/api/generate-reply", response_model=GenerateReplyResponse)
async def generate_reply(
    request: GenerateReplyRequest,
    generator: Annotated[ReplyGenerator, Depends(get_reply_gen)],
):
    """
    Generate AI reply for a single review.
    
    Args:
        request: Reply generation request
        generator: Reply generator dependency
    
    Returns:
        Generated reply
    """
    generator.business_name = request.business_name
    generator.tone = request.tone
    
    try:
        reply = await generator.generate_reply(
            review_text=request.review_text,
            rating=request.rating,
            reviewer_name=request.reviewer_name,
            backend=request.backend,  # type: ignore
        )
        
        return GenerateReplyResponse(
            reply=reply,
            model_used=request.backend,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

@app.post("/api/generate-batch", response_model=BatchGenerateResponse)
async def generate_batch_replies(
    request: BatchGenerateRequest,
    db: Annotated[DatabaseManager, Depends(get_db)],
    generator: Annotated[ReplyGenerator, Depends(get_reply_gen)],
):
    """
    Generate replies for multiple reviews.
    
    Args:
        request: Batch generation request
        db: Database manager
        generator: Reply generator dependency
    
    Returns:
        Batch generation results
    """
    # Fetch reviews from database
    all_reviews = db.get_all_reviews()
    review_map = {r["review_id"]: r for r in all_reviews}
    
    reviews_to_process = [
        review_map[rid]
        for rid in request.review_ids
        if rid in review_map
    ]
    
    if not reviews_to_process:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No valid review IDs found",
        )
    
    # Generate replies
    batch_gen = BatchReplyGenerator(generator, max_concurrent=5)
    results = await batch_gen.generate_replies(
        reviews_to_process,
        backend=request.backend,  # type: ignore
    )
    
    # Update database
    succeeded = 0
    failed = 0
    response_results = []
    
    for review_id, reply_text, error_msg in results:
        if reply_text:
            db.mark_replied(review_id, reply_text)
            succeeded += 1
            response_results.append({
                "review_id": review_id,
                "status": "success",
                "reply": reply_text,
            })
        else:
            db.mark_error(review_id, error_msg or "Unknown error")
            failed += 1
            response_results.append({
                "review_id": review_id,
                "status": "error",
                "error": error_msg,
            })
    
    return BatchGenerateResponse(
        total=len(results),
        succeeded=succeeded,
        failed=failed,
        results=response_results,
    )


# ---------------------------------------------------------------------------
# API Routes - Google My Business Integration
# ---------------------------------------------------------------------------

@app.get("/api/gmb/accounts")
async def list_gmb_accounts(client: Annotated[GoogleMyBusinessClient, Depends(get_gmb_client)]):
    """
    List Google My Business accounts.
    
    Args:
        client: GMB client dependency
    
    Returns:
        List of GMB accounts
    """
    try:
        accounts = client.list_accounts()
        return {"accounts": accounts}
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

@app.get("/api/gmb/locations/{account_id}")
async def list_gmb_locations(
    account_id: str,
    client: Annotated[GoogleMyBusinessClient, Depends(get_gmb_client)],
):
    """
    List locations for a GMB account.
    
    Args:
        account_id: GMB account ID
        client: GMB client dependency
    
    Returns:
        List of locations
    """
    try:
        locations = client.list_locations(account_id)
        return {"locations": locations}
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    
    config = get_config()
    uvicorn.run(
        "app:app",
        host=config.server.host,
        port=config.server.port,
        reload=True,
        log_level="info",
    )