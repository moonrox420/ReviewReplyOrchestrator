"""
Payment Orchestration Package
=============================

This package provides a complete payment fulfillment automation system for DroxAI products.

Modules:
    - email_service: Transactional email delivery (delivery notifications, error alerts)
    - product_delivery: S3 pre-signed URL generation for product downloads
    - fulfillment_orchestrator: Complete order fulfillment pipeline
    - audit_logger: Event logging and audit trail
    - license_service: Cryptographic license key generation and validation
    - models: SQLAlchemy database models (Order, License, Payment)
    - config: Centralized configuration management
    - stripe_webhook: FastAPI endpoints for Stripe integration
    - stripe_handler: Stripe event processing
    - utils: Helper utilities

Usage:
    from payment_orchestration import FulfillmentOrchestrator, EmailService, ProductDeliveryService
    
    # Initialize services
    email_service = EmailService()
    delivery_service = ProductDeliveryService()
    orchestrator = FulfillmentOrchestrator(
        email_service=email_service,
        product_delivery_service=delivery_service
    )
    
    # Process an order
    success, order_id, license_key = await orchestrator.fulfill_order(
        order_id="ORD-12345",
        customer_email="customer@example.com",
        customer_name="John Doe",
        plan="review_reply_business",
        payment_id="pi_12345",
        amount_cents=19900
    )

Authors:
    DroxAI LLC - droxai25@outlook.com
"""

__version__ = "1.0.0"
__author__ = "DroxAI LLC"

# Import main classes for easy access
try:
    from .email_service import EmailService
    from .product_delivery import ProductDeliveryService
    from .fulfillment_orchestrator import FulfillmentOrchestrator
    from .audit_logger import AuditLogger
    from .config import (
        DatabaseConfig,
        StripeConfig,
        EmailConfig,
        S3Config,
        ServerConfig,
        ProductConfig
    )
    from .utils import (
        safe_get_env,
        format_currency,
        validate_email,
        generate_order_id
    )
    
    __all__ = [
        'EmailService',
        'ProductDeliveryService',
        'FulfillmentOrchestrator',
        'AuditLogger',
        'DatabaseConfig',
        'StripeConfig',
        'EmailConfig',
        'S3Config',
        'ServerConfig',
        'ProductConfig',
        'safe_get_env',
        'format_currency',
        'validate_email',
        'generate_order_id',
    ]
except ImportError as e:
    # Allow package to be imported even if dependencies aren't installed yet
    import logging
    logging.getLogger(__name__).warning(f"Some imports failed: {e}")
    __all__ = []