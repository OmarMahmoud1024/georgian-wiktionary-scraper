"""
A tiny local HTTP server that mimics ka.wiktionary.org's MediaWiki API and
wiki page structure closely enough to exercise the real scraper code
end-to-end, without any external network access.

This is used instead of live network calls because the sandbox this was
verified in has restricted outbound access - the fixtures reproduce the
real inconsistent-structure problem (see fixtures/page_*.html) that the
scraper is designed to handle.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

FIXTURES = Path(__file__).parent / "fixtures"

_PAGE_MAP = {
    "სახლი": "page_house.html",
    "წიგნი": "page_book.html",
    "მზე": "page_sun.html",
}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # keep test output quiet

    def do_GET(self):
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/w/api.php":
            cmcontinue = query.get("cmcontinue", [None])[0]
            fixture = "category_page2.json" if cmcontinue else "category_page1.json"
            self._send_json(FIXTURES / fixture)
            return

        if parsed.path.startswith("/wiki/"):
            title = unquote(parsed.path[len("/wiki/"):]).replace("_", " ")
            fixture_name = _PAGE_MAP.get(title)
            if fixture_name:
                self._send_html(FIXTURES / fixture_name)
                return

        self.send_response(404)
        self.end_headers()

    def _send_json(self, path: Path):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def _send_html(self, path: Path):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(path.read_bytes())


class LocalSite:
    def __init__(self):
        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.port = self.server.server_port
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"
