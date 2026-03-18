# ReviewReplyBot – Sellable Edition

**Standalone, license-gated review reply automation bot for resale to business customers.**

This directory contains the complete, self-contained sellable product: a single-file Python bot that customers run on their own machines. It includes license activation, subscription enforcement, browser automation, and local AI reply generation — no server required.

---

## Directory Contents

| File | Description |
|------|-------------|
| `review_bot_sellable.py` | Main bot (local Ollama / LM Studio AI) |
| `review_reply_bot_sellable.py` | Alternate bot variant (Anthropic Claude AI) |
| `license_system.py` | License key generation and subscription validation (used by `review_bot_sellable.py`) |
| `license_validator.py` | Alternate license validator (used by `review_reply_bot_sellable.py`) |
| `generate_license.py` | CLI tool: generate license key for new customer (uses `license_system.py`) |
| `generate_customer_license.py` | CLI tool: alternate license key generator (uses `license_validator.py`) |
| `requirements_sellable.txt` | Python dependencies for `review_bot_sellable.py` |
| `sellable_requirements.txt` | Python dependencies for `review_reply_bot_sellable.py` |
| `build.ps1` | PowerShell script to build `ReviewBot.exe` with PyInstaller |
| `build_executable.ps1` | PowerShell script to build `ReviewReplyBot.exe` with PyInstaller |
| `CUSTOMER_INSTRUCTIONS.txt` | End-user setup guide (local AI variant) |
| `CUSTOMER_SETUP.txt` | End-user setup guide (Anthropic API variant) |

---

## How It Works

1. **Seller** generates a license key per customer using `generate_license.py`.
2. **Customer** installs dependencies, runs the bot, and enters their license key + email.
3. **Bot** validates the license, then automatically logs into Google Business, fetches unanswered reviews, generates AI replies, and posts them — every 5 minutes.
4. If the subscription lapses, the bot locks on next launch.

---

## Building an Executable (Windows)

```powershell
cd sellable

# Variant 1: local AI (Ollama / LM Studio)
.\build.ps1
# Output: dist/ReviewBot.exe

# Variant 2: Anthropic Claude API
.\build_executable.ps1
# Output: dist/ReviewReplyBot.exe
```

Requires Python 3.11+ and PyInstaller (`pip install pyinstaller`).

---

## Generating a License Key

### Variant 1 (license_system.py)

```bash
cd sellable
python generate_license.py
# Enter customer email and Gumroad purchase ID
# Prints: MRX-XXXXXXXX-XXXXXXXX-XXXXXXXX
```

### Variant 2 (license_validator.py)

```bash
cd sellable
python generate_customer_license.py
# Enter customer email
# Prints license key — send to customer
```

> **Security note:** The master key (`MOONROX2026`) is hardcoded in both `license_system.py` and `license_validator.py`. Change it in both files before distribution. Store the real key only in a secret store or environment variable; never commit it to source control.

---

## Installation (Customer-Facing)

### Prerequisites
- Python 3.9+ (or use the pre-built `.exe`)
- Google Chrome installed
- Ollama or LM Studio running locally (Variant 1), or an Anthropic API key (Variant 2)

### Variant 1 – Local AI (Ollama / LM Studio)

```bash
pip install -r requirements_sellable.txt
python review_bot_sellable.py
```

### Variant 2 – Anthropic Claude API

```bash
pip install -r sellable_requirements.txt
python review_reply_bot_sellable.py
```

Full step-by-step instructions for customers are in:
- [`CUSTOMER_INSTRUCTIONS.txt`](CUSTOMER_INSTRUCTIONS.txt) — local AI variant
- [`CUSTOMER_SETUP.txt`](CUSTOMER_SETUP.txt) — Anthropic API / exe variant

---

## Pricing Model

| Option | Price |
|--------|-------|
| One-time purchase | \$199 |
| Monthly subscription | \$99/month (bot locks if cancelled) |

Subscription status is stored locally in `license.json` and checked on every run.

---

## Customization Before Resale

Before building and distributing to customers, update the following:

1. **`license_system.py` and `license_validator.py`** – Replace the `master_key` value (`MOONROX2026`) in both files with your own secret. Do **not** commit this secret.
2. **`CUSTOMER_INSTRUCTIONS.txt`** – Replace `your@email.com` and the Gumroad link with your real support email and store URL.
3. **`CUSTOMER_SETUP.txt`** – Replace "Contact your seller" with your actual support contact.

---

## Support

- See [`CUSTOMER_INSTRUCTIONS.txt`](CUSTOMER_INSTRUCTIONS.txt) for common troubleshooting steps.
- For licensing issues, regenerate and re-send the license key.
- Response time: within 24 hours.
