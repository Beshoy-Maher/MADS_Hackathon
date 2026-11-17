"""Founder dashboard: a tiny web server using only the Python standard library.

GET  /                      dashboard (static/index.html)
GET  /api/status            model and settings
GET  /api/runs              list runs
GET  /api/runs/<id>         one run (gate, checks, outbound queue, outputs)
GET  /api/runs/<id>/file/<name>   one output file
POST /api/runs              {"brief": {...}}            start a run
POST /api/runs/<id>/decide  {"decision", "reason"}      founder gate decision
POST /api/runs/<id>/outbound/<item>  {"approve": bool}   founder approves/rejects

Founder actions need the X-Founder-Token header when FOUNDER_TOKEN is set.
"""
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import config
import llm
import orchestrator as orch

STATIC = Path(__file__).resolve().parent / "static"
BRIEFS = Path(__file__).resolve().parent / "briefs"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else (json.dumps(body, default=str) if ctype == "application/json" else body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass

    def _founder(self):
        return not config.FOUNDER_TOKEN or self.headers.get("X-Founder-Token") == config.FOUNDER_TOKEN

    def do_GET(self):
        p = self.path.split("?")[0]
        if p == "/":
            return self._send(200, (STATIC / "index.html").read_bytes(), "text/html")
        if p == "/api/status":
            return self._send(200, {"model": config.LLM_MODEL, "model_available": llm.available(),
                                    "payment_mode": "MOCKED", "token_required": bool(config.FOUNDER_TOKEN),
                                    "briefs": sorted(f.name for f in BRIEFS.glob("*_idea.json"))})
        if p == "/api/runs":
            return self._send(200, orch.list_runs())
        m = re.fullmatch(r"/api/briefs/([\w\-]+\.json)", p)
        if m and (BRIEFS / m.group(1)).exists():
            return self._send(200, json.loads((BRIEFS / m.group(1)).read_text()))
        m = re.fullmatch(r"/api/runs/(\w+)", p)
        if m:
            try:
                return self._send(200, orch.load(m.group(1)))
            except FileNotFoundError:
                return self._send(404, {"error": "no such run"})
        m = re.fullmatch(r"/api/runs/(\w+)/file/([\w\-.]+)", p)
        if m:
            f = config.DATA_DIR / "runs" / m.group(1) / "outputs" / m.group(2)
            if f.exists():
                return self._send(200, f.read_text(), "text/plain")
        return self._send(404, {"error": "not found"})

    def do_POST(self):
        p = self.path
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n) or b"{}")
        if p != "/api/runs" and not self._founder():
            return self._send(403, {"error": "founder token required"})
        try:
            if p == "/api/runs":
                run = orch.start(body["brief"])
                return self._send(200, run)
            m = re.fullmatch(r"/api/runs/(\w+)/decide", p)
            if m:
                run = orch.decide(orch.load(m.group(1)), body.get("decision", ""), "founder", body.get("reason", ""), via="dashboard")
                return self._send(200, run)
            m = re.fullmatch(r"/api/runs/(\w+)/outbound/(\w+)", p)
            if m:
                run = orch.decide_outbound(orch.load(m.group(1)), m.group(2), bool(body.get("approve")), "founder", via="dashboard")
                return self._send(200, run)
        except (ValueError, PermissionError, KeyError) as e:
            return self._send(400, {"error": str(e)})
        return self._send(404, {"error": "not found"})


def main():
    print(f"Dashboard on http://localhost:{config.APP_PORT}  (model {config.LLM_MODEL}: "
          f"{'available' if llm.available() else 'not reachable, deterministic TEMPLATE text'})")
    ThreadingHTTPServer(("0.0.0.0", config.APP_PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
