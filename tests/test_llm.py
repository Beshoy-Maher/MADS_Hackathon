"""The model path works against an Ollama-compatible server (a local stub here)."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import config
import llm
from agents.base import write


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj):
        b = json.dumps(obj).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def do_GET(self):
        self._json({"models": [{"name": "qwen3:4b"}]})

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        self._json({"response": "Clear release notes. Join 900 happy customers today.", "prompt_eval_count": 30, "eval_count": 10})


def test_model_writes_and_guardrails_clean(monkeypatch):
    srv = HTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    monkeypatch.setattr(config, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(config, "LLM_BASE_URL", f"http://127.0.0.1:{srv.server_port}")
    monkeypatch.setattr(config, "LLM_MODEL", "qwen3:4b")
    llm.reset()
    out = write("copywriter", "task", "template")
    srv.shutdown()
    assert out["model"] == "qwen3:4b"
    assert "Clear release notes." in out["text"] and "happy customers" not in out["text"]
    assert out["removed"]


def test_fallback_is_labelled_template():
    out = write("copywriter", "task", "the template text")
    assert out["model"] is None and out["label"].startswith("TEMPLATE")
