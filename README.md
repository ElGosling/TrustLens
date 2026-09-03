# TrustLens

## Overview

False claims and lookalike-domain scams still travel through family chats and social feeds because checking them is slow: open a browser, guess which source is real, and hope the article is current. TrustLens is a **Telegram bot** (with a matching **Chrome extension on X**) that takes a pasted claim or forwarded link, searches only a reviewed allowlist of domains, and replies with a verdict, confidence, cited URLs, and a short explanation.

**Problem it addresses.** People forward urgency-and-authority messages (PayNow “refunds”, parcel fees, fake agency notices) before anyone has checked them. Generic chatbots make this worse if they invent sources. TrustLens never lets the model browse or cite a URL that did not already pass local trusted-domain validation. If there is no approved evidence, the answer is **Unverified**, not a guess.

**Key features**

- **Evidence-gated fact check.** Text or `http(s)` links → Tavily search restricted to `config/trusted_sources.toml` → GPT Structured Outputs over numbered evidence only. Verdicts: True, False, Misleading, Satire, Unverified.
- **Micro literacy `/quiz`.** A recap from *your* stored checks plus a curated bank, including “is this legitimate or a scam?” items grounded in named SPF / GovTech advisories — and some answers are **Legitimate**, so the quiz does not train “everything is a scam”.
- **Recurring-scam `/escalate`.** On demand, clusters similar False/Misleading (and Unverified scam/impersonation) claims **across users** and writes a local harm brief (`data/escalations/`). One person repeating the same text does not count; ≥2 unique users in 14 days does. The Telegram reply includes unique-user counts. No user IDs in the file.
- **Chrome extension (X).** A `?` badge on posts; click runs the same Python fact-check via `http://127.0.0.1:8000/check`. API keys stay on the machine, not in the browser.
- **Public website.** Explainer for the product (`website/`).

**How it stands out.** Same fact-check stack in chat and in-feed; the model cannot mint sources; literacy is personalised from real checks rather than a generic trivia pack; escalation looks for *spread*, which is what makes a scam worth a brief.

Telegram is the MVP channel. Images, voice, video, and WhatsApp are not in this build — see [Improvements](#improvements).

## Setup and run

Work from the repository root (`TrustLens/`). The bot, the Chrome extension, and the website can run independently; they share `.env` keys where noted.

### Dependencies

| What | Why | Version |
|------|-----|---------|
| Python | Bot, fact-check API, escalation CLI | **3.11 or newer** (`pyproject.toml`) |
| pip packages | `openai`, `pyTelegramBotAPI`, `tavily-python` | `pip install -e .` |
| Node.js + npm | Public website only | Node **18+** recommended |
| Google Chrome | Unpacked extension | Current stable |
| Accounts / keys | Bot token and two API keys | Step 1 |

No Docker, no PostgreSQL. SQLite is created automatically under `data/` on first bot run.

### 1. Get the three secrets

1. **Telegram bot token.** In Telegram, talk to [@BotFather](https://t.me/BotFather) → `/newbot` → copy the token.
2. **OpenAI API key.** [platform.openai.com/api-keys](https://platform.openai.com/api-keys). Default model: `gpt-5.6-luna` (`OPENAI_MODEL` in `.env`); change it only if your account cannot use that model.
3. **Tavily API key.** [tavily.com](https://tavily.com). Required for trusted-source search.

### 2. Environment file

```bash
cp .env.example .env
```

Windows (PowerShell): `Copy-Item .env.example .env`

Set at least:

```text
TELEGRAM_BOT_TOKEN=...
OPENAI_API_KEY=...
TAVILY_API_KEY=...
```

Do not commit `.env`.

| Variable | Required? | Default | Used by |
|----------|-----------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | Yes, for the bot | — | `python -m app.main` |
| `OPENAI_API_KEY` | Yes | — | Bot and `python -m chrome_ext.api` |
| `TAVILY_API_KEY` | Yes | — | Bot and Chrome bridge |
| `OPENAI_MODEL` | No | `gpt-5.6-luna` | Same |
| `TRUSTLENS_DB_PATH` | No | `data/trustlens.sqlite3` | Bot and `/escalate` |
| `TRUSTLENS_QUIZ_QUESTIONS` | No | `5` | `/quiz` |
| `TRUSTLENS_ESCALATE_WINDOW_DAYS` | No | `14` | `/escalate` |
| `TRUSTLENS_ESCALATE_MIN_USERS` | No | `2` | `/escalate` |
| `TRUSTLENS_ESCALATE_DIR` | No | `data/escalations` | `/escalate` |

The Chrome bridge does **not** need `TELEGRAM_BOT_TOKEN`. The website needs no `.env`.

### 3. Python virtual environment

macOS / Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

`pip install -e .` installs the packages in `pyproject.toml`. Re-run it if you pull new Python dependencies.

### 4. Run the Telegram bot

```bash
.venv/bin/python -m app.main
```

```powershell
.\.venv\Scripts\python.exe -m app.main
```

The terminal stays on long polling until `Ctrl+C` — that is expected. Only one process may poll the same token (Telegram error **409** otherwise).

In Telegram, open your bot and:

- Send a sentence or a forwarded `http(s)` link → verdict, confidence, sources.
- `/quiz` → recap; `/quizstop` to abort; `/stats` for counts.
- `/escalate` → writes `data/escalations/escalation-YYYYMMDD-HHMM.txt` and replies with unique-user counts. Needs **two different Telegram users** to have checked a similar False/Misleading (or Unverified scam) claim in the last 14 days.

Without Telegram:

```bash
.venv/bin/python -m app.escalate
```

### 5. Run the Chrome extension (X)

Needs steps 2–3. The Telegram bot does not have to be running.

1. From the repo root, start the bridge and leave it running (`http://127.0.0.1:8000/check`):

```bash
.venv/bin/python -m chrome_ext.api
```

```powershell
.\.venv\Scripts\python.exe -m chrome_ext.api
```

2. Chrome: menu → **Extensions** → **Manage extensions**.
3. Turn on **Developer mode** → **Load unpacked**.
4. Select the `chrome_ext` folder.
5. Open **X** (`x.com`), click the `?` badge on a post.

If the panel says the service is unavailable, the bridge in step 1 is not running.

### 6. Run the public website

Node.js 18+ and npm. No API keys.

```bash
cd website
npm install
npm run dev
```

Open the URL Vite prints (usually http://localhost:5173). Production: `npm run build` → `website/dist/`.

### 7. Tests (optional)

```bash
.venv/bin/python -m unittest discover -s tests
```

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

No API keys required.

### Folders you will use

| Path | What it is for |
|------|----------------|
| `.env.example` | Template for secrets. Copy to `.env`. |
| `app/` | Telegram bot (`python -m app.main`) and escalation CLI (`python -m app.escalate`). |
| `chrome_ext/` | Load unpacked, then run `python -m chrome_ext.api`. |
| `website/` | `npm install` / `npm run dev`. |
| `config/trusted_sources.toml` | Domains allowed as evidence. |
| `data/` | Created on first run: SQLite + `escalations/` txt files. Gitignored. |

## Improvements

Not in the MVP:

- **WhatsApp.** A Cloud API adapter for the same fact-check workflow. MVP channel is Telegram only.
- **Chrome extension.** Same badge and click-to-check on social platforms other than X.
- **Scam escalation.** Connect `/escalate` to official hotlines (for example ScamShield) so a cluster that crosses the spread threshold can be sent automatically, not only written to a local file.
