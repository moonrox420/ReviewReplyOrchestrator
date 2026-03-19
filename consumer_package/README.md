# Review Reply Orchestrator

**Fully automated Google Business review reply system.**  
AI reads your Google reviews, generates professional replies, and posts them automatically — no manual copy-paste, no Google Cloud account, no API keys required.

---

## How It Works

1. You install the software on your Windows computer.  
2. You enter your Google Business email and password once (encrypted and stored locally).  
3. The software opens Chrome in the background (headless mode), logs into Google Business, and checks for new unanswered reviews.  
4. It generates AI replies using a local AI model (Ollama / LM Studio).  
5. It posts the replies directly to Google Business automatically.  
6. It repeats every 60 minutes (configurable).  

---

## Quick Start

### 1. Install Dependencies

**Windows (PowerShell):**
```powershell
cd ReviewReplyOrchestrator
.venv\Scripts\activate
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
cd ReviewReplyOrchestrator
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Install Chrome + ChromeDriver

Chrome must be installed on the computer.  
ChromeDriver is downloaded automatically by `webdriver-manager` on first run.

### 3. Configure AI Model

Edit `engine.env` and set the AI model endpoint:

```
OLLAMA_URL=http://127.0.0.1:11434          # if using Ollama
LMSTUDIO_URL=http://127.0.0.1:1234/v1/...  # if using LM Studio
REPLY_MODEL=qwen2.5:7b-instruct
```

### 4. Start the Server

**Windows:**
```powershell
.\start-orchestrator.ps1
```

**macOS / Linux:**
```bash
uvicorn app:app --host 127.0.0.1 --port 7363 --reload
```

### 5. Set Up Browser Automation

Open your browser and go to: **http://127.0.0.1:7363**

1. In the **"Automatic Review Replies"** section, enter your **Google Business email and password**.
2. Click **"Save & Start Automation"**.
3. The software encrypts your credentials and starts the automation service immediately.
4. It will check for new reviews every hour automatically.

---

## Web Interface

| URL | Description |
|-----|-------------|
| `http://127.0.0.1:7363/` | Main dashboard |
| `http://127.0.0.1:7363/automation/status` | Automation service status |
| `http://127.0.0.1:7363/automation/logs` | View automation log |
| `http://127.0.0.1:7363/healthz` | Health check |

---

## API Endpoints

### Browser Automation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/automation/setup` | Save credentials & start service |
| `POST` | `/automation/start` | Start background service |
| `POST` | `/automation/stop` | Stop background service |
| `GET`  | `/automation/status` | Current status |
| `POST` | `/automation/run-now` | Trigger an immediate run |
| `POST` | `/automation/config` | Update interval / headless setting |
| `GET`  | `/automation/logs` | Recent log lines |

**Setup example:**
```bash
curl -X POST http://127.0.0.1:7363/automation/setup \
  -H "Content-Type: application/json" \
  -d '{"email":"you@gmail.com","password":"your_password"}'
```

**Configure interval:**
```bash
curl -X POST http://127.0.0.1:7363/automation/config \
  -H "Content-Type: application/json" \
  -d '{"interval_minutes": 30, "headless": true}'
```

### Review Management (Google API, optional)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/oauth/start` | Begin Google OAuth flow |
| `POST` | `/reviews/sync` | Manual review sync |
| `GET`  | `/reviews/status` | API monitoring status |

### AI Reply Generation

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/lead-intake` | Generate 5 sample replies |

---

## Configuration Files

### `config.json`

```json
{
  "automation": {
    "enabled": true,
    "interval_minutes": 60,
    "headless": true,
    "business_name": "My Business"
  },
  "google_credentials": {
    "email": "",
    "password_enc": ""
  }
}
```

- `enabled` – turn automation on/off without stopping the service  
- `interval_minutes` – how often to check for new reviews (1–1440, default: 60)  
- `headless` – run Chrome invisibly in background (default: true)  
- `business_name` – used when generating AI reply tone/context  
- `password_enc` – Fernet-encrypted password (never stored in plain text)

### `engine.env`

```
ENGINE_HOST=127.0.0.1
ENGINE_PORT=7363
OLLAMA_URL=http://127.0.0.1:11434
REPLY_MODEL=qwen2.5:7b-instruct
REVIEW_CHECK_INTERVAL_MINUTES=60
```

---

## Logs

| File | Description |
|------|-------------|
| `logs/automation.log` | All automation activity (timestamped) |
| `logs/screenshots/` | Error screenshots for debugging |

Log entries include:
- Every review check (timestamp, reviews found)
- Every reply posted (review ID, reply text preview)
- All errors with full stack traces

---

## Error Handling

| Situation | Behavior |
|-----------|----------|
| **2FA prompt** | Automation pauses, logs warning, retries next interval |
| **CAPTCHA** | Automation pauses, logs warning, saves screenshot |
| **Network error** | Retries with exponential back-off |
| **Element not found** | Saves screenshot, logs error, continues to next review |
| **Wrong credentials** | Logs error, does not crash |

---

## Security

- Passwords are **never logged** or stored in plain text.
- Credentials are encrypted using **Fernet symmetric encryption** (AES-128-CBC + HMAC-SHA256).
- The Fernet key is stored in `tokens/fernet.key` (permissions: 0600).
- The key and encrypted token files are excluded from git (see `.gitignore`).

---

## Troubleshooting

**Chrome not found:**  
Install Google Chrome from https://www.google.com/chrome/

**`webdriver-manager` download fails:**  
Check your internet connection. The driver is downloaded once and cached.

**2FA keeps blocking automation:**  
Log into https://myaccount.google.com/security and enable "Less secure app access" or create an App Password.

**Reviews page not loading:**  
Check `logs/screenshots/` for a screenshot of the error state.

---

## Files

| File | Description |
|------|-------------|
| `app.py` | FastAPI web server & API endpoints |
| `browser_automation.py` | Selenium browser automation logic |
| `automation_service.py` | Background service thread & scheduler |
| `monitor.py` | Google API-based monitoring (optional) |
| `google_api.py` | Google OAuth & GMB API helpers (optional) |
| `config.json` | Automation configuration |
| `engine.env` | Environment variables |
| `requirements.txt` | Python dependencies |

---

Built by **DroxAI LLC** · droxai25@outlook.com
