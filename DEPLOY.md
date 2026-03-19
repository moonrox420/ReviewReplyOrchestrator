# Deployment Guide

Complete guide to deploy the DroxAI Payment Fulfillment System to production.

---

## Prerequisites

- Python 3.9+
- Stripe account (https://stripe.com)
- AWS account with S3 access
- SMTP email credentials (Gmail, SendGrid, etc.)
- Domain name with SSL certificate

---

## Option 1: VPS Deployment (Recommended)

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3.11 python3.11-venv python3-pip nginx -y

# Create app directory
sudo mkdir -p /opt/droxai-fulfillment
sudo chown $USER:$USER /opt/droxai-fulfillment
cd /opt/droxai-fulfillment
```

### 2. Clone and Setup

```bash
# Clone repository
git clone https://github.com/moonrox420/ReviewReplyOrchestrator.git .
cd ReviewReplyOrchestrator

# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements_fulfillment.txt
```

### 3. Configure Environment

```bash
cp .env.fulfillment.example .env.fulfillment
nano .env.fulfillment
```

Fill in your credentials:
```env
STRIPE_API_KEY=sk_live_your_key
STRIPE_WEBHOOK_SECRET=whsec_your_secret
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=your_secret
AWS_S3_BUCKET=droxai-products
AWS_REGION=us-east-1
DATABASE_URL=sqlite:///fulfillment.db
API_HOST=0.0.0.0
API_PORT=8000
```

### 4. Create Systemd Service

```bash
sudo nano /etc/systemd/system/droxai-fulfillment.service
```

```ini
[Unit]
Description=DroxAI Payment Fulfillment Service
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/droxai-fulfillment/ReviewReplyOrchestrator
EnvironmentFile=/opt/droxai-fulfillment/ReviewReplyOrchestrator/.env.fulfillment
ExecStart=/opt/droxai-fulfillment/ReviewReplyOrchestrator/.venv/bin/uvicorn payment_orchestration.stripe_webhook:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable droxai-fulfillment
sudo systemctl start droxai-fulfillment
```

### 5. Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/droxai-fulfillment
```

```nginx
server {
    listen 80;
    server_name api.droxai.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/droxai-fulfillment /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 6. SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d api.droxai.com
```

---

## Option 2: Docker Deployment

### 1. Build and Run

```bash
docker-compose up -d
```

### 2. View Logs

```bash
docker-compose logs -f
```

### 3. Stop

```bash
docker-compose down
```

---

## Option 3: Heroku Deployment

### 1. Create App

```bash
heroku create droxai-fulfillment
```

### 2. Configure

```bash
heroku config:set STRIPE_API_KEY=sk_live_your_key
heroku config:set STRIPE_WEBHOOK_SECRET=whsec_your_secret
heroku config:set SMTP_HOST=smtp.gmail.com
heroku config:set SMTP_PORT=587
heroku config:set SMTP_USER=your-email@gmail.com
heroku config:set SMTP_PASSWORD=your-app-password
heroku config:set AWS_ACCESS_KEY_ID=AKIA...
heroku config:set AWS_SECRET_ACCESS_KEY=your_secret
heroku config:set AWS_S3_BUCKET=droxai-products
heroku config:set AWS_REGION=us-east-1
```

### 3. Deploy

```bash
git push heroku main
```

---

## Stripe Webhook Configuration

1. Go to [Stripe Dashboard → Webhooks](https://dashboard.stripe.com/webhooks)
2. Click "Add endpoint"
3. Enter URL: `https://api.droxai.com/webhook/stripe`
4. Select events:
   - `payment_intent.succeeded`
   - `payment_intent.payment_failed`
5. Copy the signing secret to `STRIPE_WEBHOOK_SECRET` in `.env.fulfillment`

---

## Testing

### Test with Stripe CLI

```bash
# Install Stripe CLI
brew install stripe/stripe-cli/stripe  # macOS
# or download from https://stripe.com/docs/stripe-cli

# Login
stripe login

# Forward webhooks to local server
stripe listen --forward-to localhost:8000/webhook/stripe

# Trigger test event
stripe trigger payment_intent.succeeded
```

### Test with cURL

```bash
# Health check
curl https://api.droxai.com/health

# Create checkout
curl -X POST https://api.droxai.com/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "plan": "review_reply_starter",
    "customer_email": "test@example.com",
    "customer_name": "Test User",
    "success_url": "https://droxai.com/success",
    "cancel_url": "https://droxai.com/cancel"
  }'
```

---

## Monitoring

### Check Service Status

```bash
sudo systemctl status droxai-fulfillment
```

### View Logs

```bash
sudo journalctl -u droxai-fulfillment -f
```

### Check Audit Log

```bash
tail -f audit.log
```

---

## Troubleshooting

**Service won't start:**
```bash
sudo journalctl -u droxai-fulfillment -n 50
```

**Webhook not receiving:**
- Check Stripe Dashboard webhook logs
- Verify SSL certificate is valid
- Test with Stripe CLI

**Emails not sending:**
- For Gmail, use App Password: https://myaccount.google.com/apppasswords
- Check SMTP credentials

---

## Support

- Email: droxai25@outlook.com
- GitHub: https://github.com/moonrox420/ReviewReplyOrchestrator

---

Built by **DroxAI LLC**