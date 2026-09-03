"""Small local HTTP bridge for the Chrome extension."""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from app.article_fetcher import create_tavily_article_fetcher
from app.fact_check import FactCheckService
from app.gpt_responder import GPTResponder
from app.settings import DEFAULT_OPENAI_MODEL, load_local_env_file
from app.trusted_domains import TrustedDomainPolicy
from app.web_search import create_tavily_search

PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOST = "127.0.0.1"
PORT = 8000


def create_fact_checker() -> FactCheckService:
    """Build the same trusted-search and GPT workflow used by the Telegram bot."""
    load_local_env_file(PROJECT_ROOT / ".env")
    tavily_api_key = os.environ["TAVILY_API_KEY"]
    source_file = PROJECT_ROOT / "config" / "trusted_sources.toml"
    policy = TrustedDomainPolicy.from_toml(source_file)
    searcher = create_tavily_search(api_key=tavily_api_key, policy=policy)
    article_fetcher = create_tavily_article_fetcher(
        api_key=tavily_api_key, policy=policy
    )
    generator = GPTResponder(model=os.environ.get("OPENAI_MODEL", DEFAULT_OPENAI_MODEL))
    return FactCheckService(
        searcher=searcher,
        generator=generator,
        policy=policy,
        article_fetcher=article_fetcher,
    )


class ExtensionRequestHandler(BaseHTTPRequestHandler):
    """Accept extension claims and return a browser-friendly result object."""

    fact_checker = None

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._send_cors_headers()
        self.end_headers()

    def do_POST(self) -> None:
        if self.path != "/check":
            self._send_json({"error": "Not found."}, 404)
            return

        try:
            payload = json.loads(self._read_body())
            claim = payload.get("claim", "").strip()
            if not claim:
                raise ValueError("Claim must be a non-empty string.")
            result = self.fact_checker.check_message(claim)
            response = {
                "verdict": result.verdict.value,
                "confidence": result.confidence,
                "explanation": result.explanation,
                "sources": [
                    {"title": source.title, "url": source.url}
                    for source in result.sources
                ],
            }
            self._send_json(response)
        except (json.JSONDecodeError, AttributeError, KeyError, ValueError) as error:
            self._send_json({"error": str(error)}, 400)
        except Exception as error:
            print(f"Could not check extension claim: {error}")
            self._send_json({"error": "Fact-checking failed."}, 500)

    def _read_body(self) -> str:
        length = int(self.headers.get("Content-Length", "0"))
        return self.rfile.read(length).decode("utf-8")

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")

    def log_message(self, format: str, *args) -> None:
        print(f"Extension API: {format % args}")


def run() -> None:
    """Start the local API used by the unpacked extension."""
    ExtensionRequestHandler.fact_checker = create_fact_checker()
    server = ThreadingHTTPServer((HOST, PORT), ExtensionRequestHandler)
    print(f"TrustLens extension API running at http://{HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping TrustLens extension API.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run()
