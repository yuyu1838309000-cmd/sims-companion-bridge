"""Localhost-only HTTP server and static UI host."""

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .app import BridgeApp
from .mock_backend import MockCompanionBackend
from .store import EventConflictError, WorldStore
from .validation import ValidationError

HOST = "127.0.0.1"
MAX_BODY_BYTES = 16 * 1024
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "[::1]", "::1"}
ALLOWED_ORIGIN_HOSTS = {"127.0.0.1", "localhost", "::1"}
MIME_TYPES = {".html": "text/html; charset=utf-8", ".css": "text/css; charset=utf-8", ".js": "text/javascript; charset=utf-8"}


def reject_json_constant(value):
    raise ValueError("non-finite JSON number: " + value)


def default_web_root():
    return Path(__file__).resolve().parents[3] / "web"


def make_handler(app, web_root):
    web_root = Path(web_root).resolve()

    class Handler(BaseHTTPRequestHandler):
        server_version = "SimsCompanionBridge/0.1"

        def log_message(self, fmt, *args):
            sys.stderr.write("gateway: " + (fmt % args) + "\n")

        def _discard_request_body(self, limit=64 * 1024):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return
            if 0 < length <= limit:
                self.rfile.read(length)
            elif length > limit:
                self.close_connection = True

        def _request_allowed(self):
            host_header = self.headers.get("Host", "").lower()
            host = host_header.split("]", 1)[0] + "]" if host_header.startswith("[") else host_header.split(":", 1)[0]
            if host not in ALLOWED_HOSTS:
                self._discard_request_body()
                self._json(403, {"error": "host_not_allowed"})
                return False
            origin = self.headers.get("Origin")
            if origin:
                parsed = urlparse(origin)
                if parsed.scheme != "http" or parsed.hostname not in ALLOWED_ORIGIN_HOSTS:
                    self._discard_request_body()
                    self._json(403, {"error": "origin_not_allowed"})
                    return False
            return True

        def _json(self, status, data):
            body = json.dumps(data, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def _read_json(self):
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                raise ValidationError("invalid content length")
            if length <= 0 or length > MAX_BODY_BYTES:
                raise ValidationError("request body must be between 1 and {} bytes".format(MAX_BODY_BYTES))
            if self.headers.get("Content-Type", "").split(";", 1)[0].strip() != "application/json":
                self.rfile.read(length)
                raise ValidationError("content type must be application/json")
            try:
                return json.loads(
                    self.rfile.read(length).decode("utf-8"),
                    parse_constant=reject_json_constant,
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                raise ValidationError("invalid JSON")

        def do_GET(self):
            if not self._request_allowed():
                return
            parsed = urlparse(self.path)
            try:
                if parsed.path == "/api/v0.1/health":
                    return self._json(200, app.health())
                if parsed.path == "/api/v0.1/diagnostics":
                    return self._json(200, app.diagnostics())
                if parsed.path == "/api/v0.1/world":
                    query = parse_qs(parsed.query)
                    world_id = query.get("world_id", [None])[0]
                    branch_id = query.get("branch_id", [None])[0]
                    return self._json(200, app.world_snapshot(world_id, branch_id))
                if parsed.path == "/api/v0.1/chat/history":
                    conversation_id = parse_qs(parsed.query).get("conversation_id", ["demo-conversation"])[0]
                    return self._json(200, app.chat_history(conversation_id))
                self._serve_static(parsed.path)
            except ValidationError as exc:
                self._json(400, {"error": "invalid_request", "message": str(exc)})
            except Exception:
                self._json(500, {"error": "internal_error", "message": "The gateway could not complete the request."})

        def do_POST(self):
            if not self._request_allowed():
                return
            path = urlparse(self.path).path
            try:
                if path == "/api/v0.1/chat":
                    return self._json(200, app.chat(self._read_json()))
                if path == "/api/v0.1/game/events":
                    result = app.ingest_game_event(self._read_json())
                    return self._json(200 if result["duplicate"] else 201, result)
                return self._json(404, {"error": "not_found"})
            except EventConflictError as exc:
                self._json(409, {"error": "event_conflict", "message": str(exc)})
            except ValidationError as exc:
                self._json(400, {"error": "invalid_request", "message": str(exc)})
            except Exception:
                if path == "/api/v0.1/chat":
                    self._json(502, {"error": "backend_error", "message": "The companion response was rejected or unavailable."})
                else:
                    self._json(500, {"error": "internal_error", "message": "The gateway could not complete the request."})

        def _serve_static(self, path):
            relative = "index.html" if path in ("", "/") else path.lstrip("/")
            candidate = (web_root / relative).resolve()
            if web_root not in candidate.parents and candidate != web_root:
                return self._json(404, {"error": "not_found"})
            if not candidate.is_file() or candidate.suffix not in MIME_TYPES:
                return self._json(404, {"error": "not_found"})
            body = candidate.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", MIME_TYPES[candidate.suffix])
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

    return Handler


def create_server(database, port=8765, web_root=None, backend=None):
    store = WorldStore(database)
    app = BridgeApp(store, backend or MockCompanionBackend())
    server = ThreadingHTTPServer((HOST, port), make_handler(app, web_root or default_web_root()))
    server.app = app
    server.store = store
    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the Sims Companion Bridge public demo")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--database", default=os.environ.get("SCB_DATABASE", ".local/companion-demo.sqlite3"))
    args = parser.parse_args(argv)
    server = create_server(args.database, args.port)
    print("Sims Companion Bridge is ready at http://127.0.0.1:{}".format(server.server_port))
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        server.store.close()


if __name__ == "__main__":
    main()
