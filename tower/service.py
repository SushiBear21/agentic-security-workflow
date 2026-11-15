"""Read-only synthetic dashboard service for staging deployment exercises."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tower.core import empty, transition, metrics

def payload(path):
    if path == "/health":
        return 200, {"status": "ok", "scope": "synthetic_read_only", "ai_quality": "blocked"}
    if path == "/metrics":
        fixtures = json.loads((Path(__file__).parent / "fixtures.json").read_text())
        state, _ = transition(empty(), "ingest", {"findings": fixtures}, "synthetic-service", 0)
        return 200, {"synthetic": True, "metrics": metrics(state)}
    return 404, {"error": "not found"}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        code, value = payload(self.path)
        body = json.dumps(value, allow_nan=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers(); self.wfile.write(body)
    def log_message(self, *args): pass

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--host", default="127.0.0.1"); p.add_argument("--port", type=int, default=8080)
    a = p.parse_args()
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()
