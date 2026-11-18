"""Serve the portfolio evidence tracker. Defaults to a local-only listener."""
import argparse
import json
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from secrets import token_hex

from tracker.store import Tracker, authenticate, load_principals

ROUTES = {("GET", "/api/evidence"): "list", ("GET", "/api/export"): "export",
          ("POST", "/api/evidence"): "submit", ("POST", "/api/review"): "review"}
STATIC = {"/": ("index.html", "text/html"), "/tracker.css": ("tracker.css", "text/css"),
          "/tracker.js": ("tracker.js", "text/javascript")}


class Handler(BaseHTTPRequestHandler):
    def __init__(self, *args, tracker, accounts, **kwargs):
        self.tracker = tracker
        self.accounts = accounts
        super().__init__(*args, **kwargs)

    def respond(self, status, value, mime="application/json"):
        body = json.dumps(value, allow_nan=False).encode() if mime == "application/json" else value
        self.send_response(status)
        self.send_header("Content-Type", mime + "; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; object-src 'none'")
        self.end_headers()
        self.wfile.write(body)

    def dispatch(self):
        if self.command == "GET" and self.path in STATIC:
            name, mime = STATIC[self.path]
            return self.respond(200, (Path(__file__).parent / name).read_bytes(), mime)
        if self.command == "GET" and self.path == "/health":
            return self.respond(200, {"status": "ok", "scope": "synthetic evidence tracker"})
        action = ROUTES.get((self.command, self.path))
        if action is None and (self.command, self.path) != ("GET", "/api/session"):
            return self.respond(404, {"error": "Unknown route"})
        principal = authenticate(self.accounts, self.headers.get("Authorization", ""))
        if principal is None:
            return self.respond(401, {"error": "Bearer token required"})
        if action is None:
            return self.respond(200, vars(principal))
        try:
            body = None
            if self.command == "POST":
                size = int(self.headers.get("Content-Length", "0"))
                if not 1 <= size <= 16_384 or self.headers.get_content_type() != "application/json":
                    return self.respond(400, {"error": "Expected a bounded JSON body"})
                body = json.loads(self.rfile.read(size))
            self.respond(200, self.tracker.run(principal, action, body))
        except PermissionError:
            self.respond(403, {"error": "Role cannot perform this action"})
        except KeyError:
            self.respond(404, {"error": "Evidence unavailable"})
        except (ValueError, TypeError, RecursionError) as exc:
            self.respond(400, {"error": str(exc)})

    do_GET = dispatch
    do_POST = dispatch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8090, type=int)
    parser.add_argument("--db", required=True)
    parser.add_argument("--credentials", required=True)
    parser.add_argument("--init-demo-credentials", action="store_true")
    args = parser.parse_args()
    if args.init_demo_credentials:
        principals = [{"workspace": "demo", "name": "Casey", "role": "contributor", "token": token_hex(32)},
                      {"workspace": "demo", "name": "Drew", "role": "reviewer", "token": token_hex(32)}]
        with open(args.credentials, "x", encoding="utf-8", opener=private_file) as target:
            json.dump(principals, target, indent=2)
        print("Created demo credentials in", args.credentials)
        return
    handler = partial(Handler, tracker=Tracker(args.db), accounts=load_principals(args.credentials))
    ThreadingHTTPServer((args.host, args.port), handler).serve_forever()


def private_file(path, flags):
    import os

    return os.open(path, flags, 0o600)


if __name__ == "__main__":
    main()
