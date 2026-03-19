# Payment Fulfillment System

A production-grade payment automation system that delivers products to customers within seconds of purchase. Built for DroxAI's self-hosted AI software products.

## Overview

When a customer clicks "Buy" on the landing page, this system:

1. Processes the Stripe payment
2. Generates a cryptographic license key
3. Creates a secure download link (7-day expiry)
4. Sends a professional HTML email with license + download link
5. Logs everything for audit and compliance

**Total time: < 2 seconds from payment to delivery.**

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CUSTOMER CLICKS BUY                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │   Stripe Payment Processing  │
          │  (Card validation + charge)  │
          └──────────────┬───────────────┘
                         │
                         ▼ (success)
          ┌──────────────────────────────┐
          │   Webhook → /webhook/stripe  │
          │  (Verify signature)          │
          └──────────────┬───────────────┘
                         │
                         ▼
       ┌─────────────────────────────────┐
       │  FulfillmentOrchestrator Starts │
       └──────────────┬──────────────────┘
                      │
          ┌───────────┼───────────┬──────────────┬─────────────┐
          │           │           │              │             │
          ▼           ▼           ▼              ▼             ▼
      Create      Generate   Prepare S3     Track in      Log to
      Order       License    Download      Database      Audit Log
        │           │           │              │             │
        └───────────┴───────────┴──────────────┴─────────────┘
                         │
                         ▼
              ┌─────────────────────────┐
              │  Send Delivery Email    │
              │ + License Key + Link    │
              └──────────────┬──────────┘
                             │
                             ▼
            ┌────────────────────────────────┐
            │  Order Status: COMPLETED ✅     │
            └────────────────────────────────┘
```

---

## Project Structure

```
payment_orchestration/
├── __init__.py                  # Package initialization
├── email_service.py             # Email delivery (SMTP + Jinja2)
├── product_delivery.py          # S3 pre-signed URL generation
├── fulfillment_orchestrator.py  # Main pipeline orchestration
├── audit_logger.py              # Event logging and audit trail
├── license_service.py           # License key generation/validation
├── models.py                    # SQLAlchemy database models
├── config.py                    # Configuration management
├── stripe_webhook.py            # FastAPI endpoints
├── stripe_handler.py            # Stripe event processing
└── utils.py                     # Helper utilities

index.html                       # Landing page with checkout
success.html                     # Payment success page
cancel.html                      # Payment cancel page
requirements_fulfillment.txt     # Python dependencies
.env.fulfillment.example         # Environment config template
docker-compose.yml               # Docker deployment
FULFILLMENT_README.md            # This file
DEPLOY.md                        # Deployment guide
API_DOCS.md                      # API documentation
```

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements_fulfillment.txt
```

### 2. Configure Environment

```bash
cp .env.fulfillment.example .env.fulfillment
# Edit .env.fulfillment with your keys
```

Required configuration:
- `STRIPE_API_KEY` - Your Stripe secret key
- `STRIPE_WEBHOOK_SECRET` - Stripe webhook signing secret
- `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` - Email credentials
- `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_S3_BUCKET` - S3 credentials

### 3. Run the Server

```bash
python -m uvicorn payment_orchestration.stripe_webhook:app --host 0.0.0.0 --port 8000
```

### 4. Configure Stripe Webhook

1. Go to Stripe Dashboard → Developers → Webhooks
2. Add endpoint: `https://your-domain.com/webhook/stripe`
3. Select events: `payment_intent.succeeded`
4. Copy signing secret → `.env.fulfillment`

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/checkout` | Create Stripe checkout session |
| `POST` | `/webhook/stripe` | Stripe webhook receiver |
| `GET` | `/order/{order_id}` | Check order status |
| `GET` | `/health` | Health check |

---

## Products Configured

| Product | Plan | Price |
|---------|------|-------|
| Review Reply Sprint | Starter | $99/mo |
| Review Reply Sprint | Business | $199/mo |
| Review Reply Sprint | Enterprise | $399/mo |
| TOAD | Solo | $49/mo |
| TOAD | Team | $129/mo |
| TOAD | Enterprise | $299/mo |
| DroxCLI | Individual | $29/mo |
| DroxCLI | Team | $79/mo |
| DroxCLI | Enterprise | $149/mo |
| ProConstruct | Trade Pro | $149/mo |
| ProConstruct | Crew | $299/mo |
| ProConstruct | Enterprise | $499/mo |
| AutoCampaigns | Starter | $79/mo |
| AutoCampaigns | Growth | $149/mo |
| AutoCampaigns | Agency | $299/mo |

---

## Security Features

- **Stripe signature verification** on every webhook
- **Cryptographic license keys** using secrets + hashlib
- **Pre-signed S3 URLs** with 7-day expiration
- **Input validation** on all endpoints
- **Database audit logging** for full traceability
- **Error recovery** with automatic rollback & notifications
- **Email masking** in logs for privacy

---

## Order Statuses

| Status | Description |
|--------|-------------|
| `payment_received` | Payment confirmed by Stripe |
| `license_generated` | License key created |
| `product_prepared` | Download URL generated |
| `delivery_sent` | Email sent to customer |
| `completed` | Order fully fulfilled |
| `failed` | Order failed (with error details) |

---

## Email Templates

The system sends three types of emails:

1. **Delivery Email** - License key + download link + getting started guide
2. **Error Notification** - If order processing fails
3. **Expiration Warning** - 60 days before license expires

---

## Logging

All events are logged to:
- Python logger (console/file)
- `audit.log` (persistent JSON lines)

Audit events include:
- `payment_received`
- `license_generated`
- `order_completed`
- `order_failed`
- `email_sent`
- `checkout_created`

---

## Troubleshooting

**Emails not sending?**
- Check SMTP credentials in `.env.fulfillment`
- For Gmail, use an App Password instead of your regular password

**Webhook not receiving events?**
- Verify the webhook URL in Stripe Dashboard
- Check that `STRIPE_WEBHOOK_SECRET` is correct
- Test with Stripe CLI: `stripe listen --forward-to localhost:8000/webhook/stripe`

**S3 URLs not working?**
- Verify AWS credentials have S3 read permissions
- Check that the bucket and object keys exist

---

## Support

- Email: droxai25@outlook.com
- GitHub: https://github.com/moonrox420/ReviewReplyOrchestrator

---

Built by **DroxAI LLC** · Self-hosted AI software that pays for itself.