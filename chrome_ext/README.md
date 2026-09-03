# TrustLens Chrome Extension MVP

TrustLens is a Chrome extension that will identify potentially misleading social-media content and show a small credibility badge with a verdict and reputable sources.

This is the initial browser-side foundation. It displays one demo badge and hover panel on Facebook, X, and TikTok pages. It does not inspect posts, call an API, or make real credibility judgments yet.

## MVP architecture

```text
Social media page
      |
      v
Content script: find supported posts and render badges
      |
      v
Background service worker: coordinate requests later
      |
      v
Local Python API: reuse the Telegram fact-check workflow
      |
      v
Trusted-source search -> GPT -> structured verdict
```

The content script owns page interaction because it can read and modify the displayed page. The service worker owns network requests and message passing. `api.py` reuses the existing Python `FactCheckService`, so the extension and Telegram bot follow the same search, evidence, and GPT workflow. API keys remain in Python and are never sent to the browser.

## Technology choices

- **Chrome Manifest V3**: the current Chrome extension format, with clear permissions and a service-worker background model.
- **Vanilla JavaScript**: enough for DOM detection, badge rendering, hover behavior, and `chrome.runtime` messaging. It keeps the student team focused on browser concepts instead of framework build tooling.
- **Plain CSS**: keeps the overlay easy to inspect and prevents a UI framework from becoming a dependency.
- **Existing Python application later**: the current `app/` code already contains fact-checking and trusted-source logic. A small HTTP endpoint can expose that logic after the browser prototype is proven.
- **Python standard-library HTTP server**: `chrome_ext/api.py` provides one local `/check` endpoint without adding FastAPI or another dependency.
- **No database, queue, or separate frontend framework yet**: none is needed to test the first interaction.

## Build order

1. Load this folder as an unpacked extension and verify the demo badge.
2. Choose one platform, identify its post containers, and render a badge on real posts.
3. Add a small shared post representation and prevent duplicate badges while feeds update dynamically.
4. Add a local mock verdict response through message passing.
5. Connect the service worker to the local Python endpoint.
6. Add source links, loading/error states, and support for the next platform.

Start with one platform, preferably X or Facebook, because platform-specific DOM structures and infinite scrolling are the first meaningful engineering risk. Do not support all platforms before one complete flow works.

## Load locally in Chrome

1. Open `chrome://extensions`.
2. Enable **Developer mode**.
3. Select **Load unpacked**.
4. Choose this `chrome_ext` folder.
5. Open a matching Facebook, X, or TikTok page and hover over the `?` badge in the bottom-right corner.

## Run the local verdict bridge

From the repository root, copy `.env.example` to `.env` and add `OPENAI_API_KEY` and `TAVILY_API_KEY`:

```text
cp .env.example .env
```

Then start the bridge:

```text
python3 -m chrome_ext.api
```

The extension then sends clicked claims to `http://127.0.0.1:8000/check`. The API returns the existing `FactCheckResult` as JSON. Telegram is not required to run this bridge, and its credentials are not needed.

## Files

| File | Purpose |
|------|---------|
| `manifest.json` | Declares the Manifest V3 extension, supported host pages, content script, styles, and background service worker. |
| `api.py` | Local HTTP bridge that reuses the existing Python fact-check workflow and returns structured verdict JSON. |
| `src/content/content.js` | Temporary page overlay. It creates the demo badge and hover panel; later it will detect posts and request verdicts. |
| `src/content/content.css` | Styles the badge and panel while keeping them above the host site's UI. |
| `src/background/service-worker.js` | Minimal background entry point. It is reserved for message passing and API requests once those are needed. |
| `README.md` | Records the MVP architecture, technology decisions, build order, local loading steps, and file responsibilities. |
