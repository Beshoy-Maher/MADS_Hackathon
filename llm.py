"""Talks to a small local open-weight model through Ollama.

Design rule: the model only WRITES text. It never decides anything: scores, gates,
prices and payments are plain code. If the model is not reachable, `generate()`
returns None and the calling agent uses its deterministic template instead, and the
step is logged with model=null and labelled TEMPLATE in its output.
"""
import json
import time
import urllib.request

import config

_STATUS = {"checked": 0.0, "available": False}
RECHECK_SECONDS = 30  # the model may finish downloading after the app starts


def available():
    if config.LLM_PROVIDER == "none":
        return False
    if time.time() - _STATUS["checked"] > RECHECK_SECONDS:
        _STATUS["checked"] = time.time()
        try:
            with urllib.request.urlopen(config.LLM_BASE_URL + "/api/tags", timeout=3) as r:
                tags = json.load(r).get("models", [])
            _STATUS["available"] = any(m.get("name", "").startswith(config.LLM_MODEL) for m in tags)
        except Exception:
            _STATUS["available"] = False
    return _STATUS["available"]


def reset():
    _STATUS.update(checked=0.0, available=False)


def generate(system, prompt, max_tokens=500):
    """Return (text, usage) or (None, None) when no model is available."""
    if not available():
        return None, None
    body = json.dumps({
        "model": config.LLM_MODEL, "system": system, "prompt": prompt, "stream": False,
        "think": False, "options": {"temperature": 0.3, "num_predict": max_tokens},
    }).encode()
    req = urllib.request.Request(config.LLM_BASE_URL + "/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=config.LLM_TIMEOUT) as r:
            out = json.load(r)
    except Exception:
        return None, None
    tokens = out.get("prompt_eval_count", 0) + out.get("eval_count", 0)
    cost = round(tokens / 1e6 * config.LLM_COST_PER_MTOK, 6)
    return out.get("response", "").strip(), {"tokens": tokens, "cost": cost}
