# API Documentation

Complete API reference for the DroxAI Payment Fulfillment System.

---

## Base URL

```
https://api.droxai.com
```

Local development:
```
http://localhost:8000
```

---

## Authentication

Most endpoints are public. Webhook endpoints verify Stripe signatures.

---

## Endpoints

### POST /checkout

Create a Stripe checkout session for a product purchase.

**Request Body:**
```json
{
  "plan": "review_reply_business",
  "customer_email": "john@example.com",
  "customer_name": "John Doe",
  "success_url": "https://droxai.com/success",
  "cancel_url": "https://droxai.com/cancel"
}
```

**Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| plan | string | Yes | Product plan ID (see Products section) |
| customer_email | string | Yes | Customer email address |
| customer_name | string | Yes | Customer full name |
| success_url | string | Yes | Redirect URL after successful payment |
| cancel_url | string | Yes | Redirect URL after cancelled payment |

**Response:**
```json
{
  "checkout_url": "https://checkout.stripe.com/c/pay/cs_test_...",
  "session_id": "cs_test_..."
}
```

**Error Response:**
```json
{
  "detail": "Invalid plan ID"
}
```

---

### POST /webhook/stripe

Stripe webhook endpoint. Receives payment events and triggers fulfillment.

**Headers:**
```
Stripe-Signature: t=1234567890,v1=abc123...
```

**Request Body:** (Stripe event payload)

**Response:**
```json
{
  "status": "success"
}
```

**Events Handled:**
- `payment_intent.succeeded` - Triggers order fulfillment
- `payment_intent.payment_failed` - Logs failure

---

### GET /order/{order_id}

Get the status of an order.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| order_id | string | Order identifier |

**Response:**
```json
{
  "order_id": "ORD-ABC12345",
  "customer_email": "john@example.com",
  "customer_name": "John Doe",
  "plan": "review_reply_business",
  "status": "completed",
  "amount_cents": 19900,
  "created_at": "2025-03-19T01:30:00",
  "completed_at": "2025-03-19T01:30:02",
  "error_message": null
}
```

**Order Statuses:**
| Status | Description |
|--------|-------------|
| payment_received | Payment confirmed |
| license_generated | License key created |
| product_prepared | Download URL generated |
| delivery_sent | Email sent to customer |
| completed | Order fully fulfilled |
| failed | Order failed |

**Error Response:**
```json
{
  "detail": "Order not found"
}
```

---

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-03-19T01:30:00"
}
```

---

## Products

All available product plans:

| Plan ID | Product | Price |
|---------|---------|-------|
| review_reply_starter | Review Reply Sprint - Starter | $99/mo |
| review_reply_business | Review Reply Sprint - Business | $199/mo |
| review_reply_enterprise | Review Reply Sprint - Enterprise | $399/mo |
| toad_solo | TOAD - Solo | $49/mo |
| toad_team | TOAD - Team | $129/mo |
| toad_enterprise | TOAD - Enterprise | $299/mo |
| droxcli_individual | DroxCLI - Individual | $29/mo |
| droxcli_team | DroxCLI - Team | $79/mo |
| droxcli_enterprise | DroxCLI - Enterprise | $149/mo |
| proconstruct_trade | ProConstruct - Trade Pro | $149/mo |
| proconstruct_crew | ProConstruct - Crew | $299/mo |
| proconstruct_enterprise | ProConstruct - Enterprise | $499/mo |
| autocampaigns_starter | AutoCampaigns - Starter | $79/mo |
| autocampaigns_growth | AutoCampaigns - Growth | $149/mo |
| autocampaigns_agency | AutoCampaigns - Agency | $299/mo |

---

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 404 | Not Found - Order not found |
| 422 | Validation Error - Missing required fields |
| 500 | Internal Server Error |

---

## Rate Limits

- No rate limits currently enforced
- Stripe webhooks have built-in retry logic

---

## Example: JavaScript Integration

```javascript
async function handleCheckout(planId) {
  const name = prompt("Your name:");
  const email = prompt("Your email:");
  
  if (!name || !email) return;
  
  const response = await fetch('https://api.droxai.com/checkout', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      plan: planId,
      customer_name: name,
      customer_email: email,
      success_url: window.location.origin + '/success',
      cancel_url: window.location.origin + '/cancel'
    })
  });
  
  const data = await response.json();
  window.location.href = data.checkout_url;
}
```

---

## Example: Python Integration

```python
import requests

response = requests.post('https://api.droxai.com/checkout', json={
    'plan': 'review_reply_business',
    'customer_email': 'john@example.com',
    'customer_name': 'John Doe',
    'success_url': 'https://droxai.com/success',
    'cancel_url': 'https://droxai.com/cancel'
})

data = response.json()
print(f"Checkout URL: {data['checkout_url']}")
```

---

## Example: cURL

```bash
curl -X POST https://api.droxai.com/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "review_reply_business",
    "customer_email": "john@example.com",
    "customer_name": "John Doe",
    "success_url": "https://droxai.com/success",
    "cancel_url": "https://droxai.com/cancel"
  }'
```

---

Built by **DroxAI LLC** · droxai25@outlook.com