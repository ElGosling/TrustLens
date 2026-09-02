# TrustLens

TrustLens will help Telegram and WhatsApp users check suspicious text, images, videos, and voice notes. The current milestone is a deliberately small Telegram-to-GPT bot so the team can learn one boundary at a time.

## MVP architecture

```text
Telegram / WhatsApp
        |
        v
Channel adapters (receive and send messages)
        |
        v
Fact-check workflow
  1. extract text from message or media
  2. identify the checkable claim
  3. search only trusted sources
  4. retrieve relevant evidence
  5. ask the AI to produce a structured verdict
        |
        +--> PostgreSQL (users, checks, source records)
        +--> pgvector (embeddings for retrieved evidence)
        |
        v
Verified-card response in the user's preferred language
```

The service in `app/main.py` is the future entry point for webhook endpoints and internal workflow calls. Each channel adapter should translate a platform-specific message into one common internal format; the fact-check workflow should not need to know whether a message came from Telegram or WhatsApp.

## Technology choices

- **Python 3.11+**: approachable for a student team and well supported by AI, media, database, and bot libraries.
- **pyTelegramBotAPI (current milestone)**: a lightweight Telegram client library. Long polling lets the bot run locally without exposing a public web address; move to webhooks when deploying.
- **OpenAI Python SDK (current milestone)**: sends each text message through the Responses API and returns the response text. The code sets `store=False` and does not add web-search tools.
- **FastAPI (when webhooks are added)**: a small, typed HTTP layer with automatic request validation and documentation. Add it when Telegram and WhatsApp need public webhook endpoints.
- **WhatsApp Cloud API (later)**: Meta's official API, connected through a separate adapter so it cannot complicate the Telegram learning path.
- **OpenAI API with structured JSON output (later)**: produces a verdict in a fixed schema, but must only summarize evidence retrieved by the system rather than invent sources.
- **PostgreSQL + pgvector (later)**: use one database for user preferences, audit records, sources, and vector search. Add it only when checks need to be saved or evidence retrieval is real.
- **Trusted-domain search (later)**: search results are filtered against a version-controlled allowlist before evidence reaches the model. Begin with a short list of primary sources and established fact-checkers.

Avoid a separate queue, cache, microservices, or a standalone vector database until actual traffic makes one necessary.

## Build order

1. **Current step — Telegram text round trip:** receive a text message in Telegram, send it to GPT, and reply in the same Telegram chat.
2. Define the claim, evidence, and verdict data models; save a check in PostgreSQL.
3. Add trusted-source search and evidence retrieval for text claims.
4. Add the AI verdict generator, citations, language preference, and verified-card formatting.
5. Add media extraction (OCR, transcription, video frames), then WhatsApp.

This order makes it possible to test and understand each boundary before the next one is added.

## Current milestone: Telegram → GPT → reply

```text
Telegram user
     |
     v
Receive text message
     |
     v
Send text to GPT
     |
     v
Reply in the same Telegram chat
```

**Goal:** prove that one text message can travel through the full path from Telegram to GPT and back to the user.

**Done when:** a user can send a normal text message to the development bot and receive GPT's response in the same chat.

**Not included yet:** fact-check verdicts, web search, source links, user-language preferences, databases, images, voice notes, videos, WhatsApp, or shareable cards. Keeping these out of this milestone makes failures easier to understand: the problem will be either receiving Telegram messages, calling GPT, or sending the reply.

## Milestone 2 progress: trusted-source search boundary

The trusted-source registry is `config/trusted_sources.toml`. The search adapter sends its configured domains to Tavily as `include_domains`, then independently parses each returned URL and accepts only an exact configured domain or an explicitly approved subdomain. For example, allowing `bbc.com` accepts `news.bbc.com`, but rejects `fake-bbc.com` and `bbc.com.scam.net`.

The accepted `EvidenceSource` objects preserve each source's title, URL, actual hostname, and result snippet. They are not connected to Telegram or GPT yet. The next increment will send only these accepted objects to GPT using Structured Outputs (JSON Schema), and will return a deterministic `Unverified` result when none are found.

To prepare the real search integration, add a `TAVILY_API_KEY` to `.env` and reinstall packages:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

## Text fact-checking workflow

This milestone keeps Telegram text input but changes the reply from general chat to evidence-based fact checking:

```text
Telegram text -> trusted-domain search -> local URL validation -> GPT verdict -> cited Telegram reply
```

`config/trusted_sources.toml` is the single source registry. `FactCheckService` returns `Unverified` without calling GPT when no approved evidence is found. When evidence is found, GPT receives only numbered claim evidence and returns source IDs; Python maps those IDs back to the original validated URLs before replying.

### Add a trusted source

1. Verify the organisation's ownership, editorial or evidence standards, correction practice, and a sample result URL.
2. Add one `[[sources]]` entry to `config/trusted_sources.toml`, including its `id`, `name`, `domain`, category, tier, and a plain-language scope note.
3. Set `include_subdomains = true` only if every real subdomain should be trusted. Leave it `false` for a deliberately narrow site such as `factcheck.afp.com`.
4. Run the automated tests. No changes to the search, GPT, or Telegram code should be needed.

## Run the current milestone

1. Install Python 3.11 or newer.
2. Create a Telegram bot with BotFather and copy its bot token.
3. Create an OpenAI API key.
4. Copy `.env.example` to `.env`, then fill in `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, and `TAVILY_API_KEY`. Do not share or commit this file.
5. Create a virtual environment and install the two project packages. These commands deliberately do **not** activate the environment, so they work even when PowerShell blocks scripts:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

6. Start the bot:

```powershell
.\.venv\Scripts\python.exe -m app.main
```

Open your Telegram bot's chat and send a text message or forwarded link. It should reply in the same chat. Stop the bot with `Ctrl+C`.

Run the automated check with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Application modules (`app/`)

Every Python module under `app/` and what it does. Read these in roughly this order when onboarding.

### Entry point

| File | Purpose |
|------|---------|
| `main.py` | Loads settings and the trusted-source registry, wires search, article fetch, GPT, and the fact-check service, creates the Telegram bot, clears any webhook, and starts long polling. Also validates at startup that `trusted_domains.py` is not an outdated partial copy. |

### Configuration

| File | Purpose |
|------|---------|
| `settings.py` | Loads `.env`, validates required secrets (`TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, `TAVILY_API_KEY`), and exposes the OpenAI model name with a sensible default. |

### Telegram adapter

| File | Purpose |
|------|---------|
| `telegram_bot.py` | Thin pyTelegramBotAPI wrapper. Registers a text handler, passes `message.text` to the fact-check responder, and replies in the same chat. Keeps Telegram-specific code separate from search and GPT logic. |

### Message routing

| File | Purpose |
|------|---------|
| `message_input.py` | Parses incoming text for HTTP(S) URLs and optional user notes. Routes each message as plain text, a trusted whitelisted URL, or an untrusted URL so the fact-check service can choose the right evidence path. |

### Fact-check orchestration

| File | Purpose |
|------|---------|
| `fact_check.py` | Central workflow coordinator. Plain text → trusted search → GPT verdict. Trusted URLs → fetch article (or search fallback) → optional corroboration → GPT. Untrusted URLs → extract claim from page → standard trusted search. Returns formatted Telegram replies without changing the plain-text path when no URL is present. |

### Trusted sources and search

| File | Purpose |
|------|---------|
| `trusted_domains.py` | Loads `config/trusted_sources.toml` and enforces hostname policy: exact domain or approved subdomain only. Provides helpers for official-news categories, primary-event domains, and URL trust checks used by search and fetch code. |
| `web_search.py` | Tavily search adapter with defense in depth. Runs primary-event, trusted-domain, and web-wide official-news passes; filters results locally; deduplicates URLs; applies relevance rules. Exposes `search(claim)` for text claims and `search_for_url(url)` when direct article fetch fails. |
| `search_queries.py` | Expands a user claim into multiple Tavily queries (entity hints, registry primary-event sources, Singapore-focused terms) so search is less dependent on the exact wording of the message. |
| `url_search.py` | Builds URL-targeted search queries from a forwarded link (full URL, path slug, `site:domain` variants) and derives a checkable claim from search snippets when article extract is unavailable. |
| `claim_terms.py` | Shared tokenisation for claims: strips generic words like “championship” and “hosting” so relevance checks focus on distinctive terms. Used by search filtering and query expansion. |

### Article fetch (forwarded links)

| File | Purpose |
|------|---------|
| `article_fetcher.py` | Reads a specific URL through Tavily `extract` when the user forwards a link. Returns title and body for trusted articles. Used as primary evidence before corroborating search runs. |
| `url_claims.py` | Converts a fetched article into an `EvidenceSource` and builds the claim string GPT should assess (from headline, lede, or the user’s accompanying note such as “Is this true?”). |

### Data models

| File | Purpose |
|------|---------|
| `evidence.py` | Defines `EvidenceSource`: title, URL, hostname, and snippet for each search or fetch result that passed local trusted-domain validation. |
| `verdict.py` | Defines `Verdict` labels (`True`, `False`, `Misleading`, `Satire`, `Unverified`) and `FactCheckResult` (verdict, confidence, explanation, cited sources). |

### AI and user-facing output

| File | Purpose |
|------|---------|
| `gpt_responder.py` | Calls the OpenAI Responses API with structured JSON output. Sends only numbered evidence records; maps model-selected source IDs back to validated URLs; caps confidence for `Unverified` results. Does not browse or use background knowledge. |
| `response_formatter.py` | Renders `FactCheckResult` as Telegram HTML: verdict symbol, confidence label, explanation, and clickable source links with untrusted text escaped. |

### Debugging (temporary)

| File | Purpose |
|------|---------|
| `fetch_debug.py` | Diagnostic logging for Straits Times URL fetches: direct HTTP status and body preview, plus Tavily extract metadata. Remove after paywall/JS-shell issues are resolved. |

### Package marker

| File | Purpose |
|------|---------|
| `__init__.py` | Marks `app` as a Python package. |

### How the modules connect

```text
telegram_bot.py
       |
       v
fact_check.py  <--- message_input.py (URL vs text routing)
       |
       +-- text claim -----> web_search.py ---> search_queries.py
       |                         ^                  claim_terms.py
       |                         |                  trusted_domains.py
       |
       +-- trusted URL ---> article_fetcher.py
       |       | fail              |
       |       v                   v
       |   url_search.py ----> web_search.py.search_for_url()
       |       |
       |       +--> url_claims.py
       |
       +-- untrusted URL -> article_fetcher.py -> url_claims.py -> web_search.py
       |
       v
gpt_responder.py  (uses evidence.py, verdict.py)
       |
       v
response_formatter.py
```

`main.py` constructs all of the above. `settings.py` and `trusted_domains.py` are loaded first.

## Other project files

- `config/trusted_sources.toml` — reviewed source registry (domains, categories, tiers, scope notes).
- `tests/` — unit tests for settings, search, GPT request shape, URL routing, and fact-check flows.
- `pyproject.toml` — project metadata, Python version, and runtime dependencies.
- `.env.example` — required secret names and configurable model without storing values.
- `.gitignore` — excludes virtual environments, caches, secrets, and egg-info from Git.
