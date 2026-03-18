# ReviewReplyOrchestrator

**AI-powered Google Business review reply automation — two systems in one repo.**

This repository contains:

| System | Directory | Purpose |
|--------|-----------|---------|
| **Production Orchestrator** | *(root)* | Self-hosted FastAPI server; manages OAuth, browser automation, and scheduled review replies for your own business |
| **Sellable Bot** | [`sellable/`](sellable/) | Standalone, license-gated Python bot for resale to customers; runs locally with no server required |

Both systems are fully independent — you can build, run, or ship either one without touching the other.

---

## Repository Layout

```
ReviewReplyOrchestrator/
│
├── app.py                        # FastAPI web server & API endpoints
├── browser_automation.py         # Selenium browser automation
├── automation_service.py         # Background automation scheduler
├── monitor.py                    # Google My Business API monitor
├── google_api.py                 # Google OAuth & GMB API helpers
├── config.json                   # Runtime automation configuration
├── requirements.txt              # Production orchestrator dependencies
├── engine.env                    # Local environment config (git-ignored)
├── .env.example                  # Environment variable template (copy → engine.env)
├── start-orchestrator.ps1        # Windows quick-start script
├── run-uvicorn.bat               # Windows uvicorn launcher
├── submit-reviews.ps1            # Manual review submission helper
├── test-full.ps1                 # Full integration test script
├── test-lead.ps1                 # Lead intake test script
├── README.md                     # This file
│
└── sellable/                     # ── Sellable Bot (independent product) ──
    ├── review_bot_sellable.py        # Main bot (local AI: Ollama / LM Studio)
    ├── review_reply_bot_sellable.py  # Alternate bot (Anthropic Claude API)
    ├── license_system.py             # License generation & subscription validation (local-AI variant)
    ├── license_validator.py          # Alternate license validator (Claude API variant)
    ├── generate_license.py           # CLI: generate license key for a customer
    ├── generate_customer_license.py  # CLI: alternate license key generator
    ├── requirements_sellable.txt     # Dependencies for local-AI variant
    ├── sellable_requirements.txt     # Dependencies for Claude API variant
    ├── build.ps1                     # Build ReviewBot.exe (PyInstaller)
    ├── build_executable.ps1          # Build ReviewReplyBot.exe (PyInstaller)
    ├── CUSTOMER_INSTRUCTIONS.txt     # End-user guide (local AI variant)
    ├── CUSTOMER_SETUP.txt            # End-user guide (Claude API / exe variant)
    └── README.md                     # Sellable bot documentation
```

---

## Branch Strategy

| Branch | Purpose |
|--------|---------|
| `main` | Stable, production-ready code for both systems |
| `refactor/production-optimization` | Active production orchestrator refactor |
| `copilot/*` | Automated Copilot improvement branches |

New features targeting the orchestrator go on `refactor/production-optimization` and are merged to `main` after review.  
Sellable bot changes are made directly to `sellable/` on `main` or a dedicated `feature/sellable-*` branch.

---

## 1 · Production Orchestrator

A self-hosted FastAPI web server that monitors your own Google Business reviews and automatically posts AI-generated replies via browser automation.

### Features

- Automated review monitoring (Google My Business API or browser scraping)
- AI reply generation (local Ollama or LM Studio — no cloud API costs)
- Fernet-encrypted credential storage
- Configurable automation schedule (default: every 60 minutes)
- Stripe payment webhook support for hosted subscription plans
- Health check and status API

### Installation

**Prerequisites:** Python 3.11+, Google Chrome, Ollama or LM Studio

```bash
# 1. Clone repository
git clone https://github.com/moonrox420/ReviewReplyOrchestrator.git
cd ReviewReplyOrchestrator

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example engine.env
# Edit engine.env with your credentials

# 4. Start AI backend (choose one)
ollama pull qwen2.5:7b-instruct && ollama serve   # Ollama
# — or —
# Start LM Studio and enable local server on port 1234

# 5. Start server
python app.py
# or on Windows: .\start-orchestrator.ps1
```

### Usage

Open **http://127.0.0.1:7363** in your browser.

1. In the **"Automatic Review Replies"** section, enter your Google Business email and password.
2. Click **"Save & Start Automation"**.
3. The system encrypts your credentials and starts checking for new reviews on the configured interval.

### Key API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Main dashboard |
| `GET` | `/healthz` | Health check |
| `POST` | `/automation/setup` | Save credentials & start service |
| `GET` | `/automation/status` | Automation service status |
| `POST` | `/automation/run-now` | Trigger immediate run |
| `POST` | `/automation/config` | Update interval / headless setting |
| `GET` | `/automation/logs` | Recent log lines |
| `GET` | `/oauth/start` | Begin Google OAuth flow |
| `POST` | `/lead-intake` | Generate sample replies |

### Configuration

Copy `.env.example` to `engine.env` and set the required values:

```
ENGINE_HOST=127.0.0.1
ENGINE_PORT=7363
OLLAMA_URL=http://127.0.0.1:11434
REPLY_MODEL=qwen2.5:7b-instruct
GOOGLE_CLIENT_ID=<from Google Cloud Console>
GOOGLE_CLIENT_SECRET=<from Google Cloud Console>
```

See `.env.example` for all available settings.

### Deployment (Production)

```ini
# /etc/systemd/system/review-orchestrator.service
[Unit]
Description=ReviewReplyOrchestrator
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/review-orchestrator
EnvironmentFile=/opt/review-orchestrator/engine.env
ExecStart=/opt/review-orchestrator/.venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
```

**Production checklist:**
- [ ] Set all required variables in `engine.env` (never commit this file)
- [ ] Restrict file permissions: `chmod 600 engine.env tokens/fernet.key`
- [ ] Configure HTTPS reverse proxy (nginx / Caddy)
- [ ] Enable systemd service and set up log rotation
- [ ] Back up `./data/` directory regularly

### Support

- **Email:** droxai25@outlook.com
- **GitHub Issues:** available to licensed users

---

## 2 · Sellable Bot

A self-contained, license-gated Python bot intended for resale. Customers run it on their own machine — no server needed.

> **Full documentation:** [`sellable/README.md`](sellable/README.md)

### Quick Overview

| Variant | Bot file | AI backend | Build output |
|---------|----------|------------|--------------|
| Local AI | `sellable/review_bot_sellable.py` | Ollama / LM Studio | `ReviewBot.exe` |
| Cloud AI | `sellable/review_reply_bot_sellable.py` | Anthropic Claude API | `ReviewReplyBot.exe` |

### Generating a Customer License

```bash
cd sellable
python generate_license.py
# Enter customer email + Gumroad purchase ID → prints MRX-XXXXXXXX-XXXXXXXX-XXXXXXXX
```

### Building an Executable

```powershell
cd sellable
.\build.ps1              # builds dist/ReviewBot.exe (local AI variant)
.\build_executable.ps1   # builds dist/ReviewReplyBot.exe (Claude API variant)
```

### Customer Installation

Customers follow the instructions in:
- [`sellable/CUSTOMER_INSTRUCTIONS.txt`](sellable/CUSTOMER_INSTRUCTIONS.txt) — local AI variant
- [`sellable/CUSTOMER_SETUP.txt`](sellable/CUSTOMER_SETUP.txt) — Claude API / exe variant

### Customizing Before Resale

1. **Change the master key** in both `sellable/license_system.py` and `sellable/license_validator.py` (replace `MOONROX2026` with your secret — do **not** commit it).
2. **Update support contact** in `CUSTOMER_INSTRUCTIONS.txt` and `CUSTOMER_SETUP.txt`.
3. **Update your store URL** in `CUSTOMER_INSTRUCTIONS.txt`.

---

## Security Notes

- `engine.env` and `.env` are git-ignored — never commit real credentials.
- `tokens/fernet.key` and `tokens/google_tokens.json` are git-ignored.
- The sellable bot's `LICENSE_MASTER_KEY` must be kept secret; rotate it before distribution.
- See `.gitignore` for the full list of excluded sensitive files.

---

## Troubleshooting

**AI not responding:**
```bash
curl http://127.0.0.1:11434/api/tags   # Ollama health check
```

**OAuth callback fails:**
- Ensure `GOOGLE_REDIRECT_URI` in `engine.env` matches the URI registered in Google Cloud Console.

**Browser automation crashes:**
- Check `logs/screenshots/` for a screenshot of the error state.
- Verify Chrome and ChromeDriver versions are compatible.

**License validation fails (sellable bot):**
- Regenerate and re-send the license key to the customer.
- Ensure `LICENSE_MASTER_KEY` in the bot matches the key used when the license was generated.

---

Built by **DroxAI LLC** · droxai25@outlook.com
