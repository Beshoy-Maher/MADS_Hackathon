"""Client for a local open-weight model (Ollama by default).

Every call returns an LLMResult that says which model actually produced the
text. If the model is not reachable (still downloading, laptop too slow, no
Ollama), the caller's deterministic fallback text is used instead and
`model` is None, so the decision log and the UI show honestly that no AI
was involved in that step.
"""
from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import dataclass

import httpx

import config

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)


@dataclass
class LLMResult:
    text: str
    model: str | None  # None when the deterministic fallback was used
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost: float = 0.0
    error: str | None = None

    @property
    def used_fallback(self) -> bool:
        return self.model is None


class _Stats:
    """Process-wide token counters, used for the cost-per-run figure."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.calls = 0
        self.fallbacks = 0

    def add(self, r: LLMResult) -> None:
        with self.lock:
            self.calls += 1
            self.prompt_tokens += r.prompt_tokens
            self.completion_tokens += r.completion_tokens
            if r.used_fallback:
                self.fallbacks += 1


STATS = _Stats()
_status_cache: dict = {"t": 0.0, "value": None}


def strip_thinking(text: str) -> str:
    text = _THINK_RE.sub("", text or "")
    if "</think>" in text:  # unterminated opening tag cut off by the server
        text = text.split("</think>", 1)[1]
    return text.strip()


def model_status(force: bool = False) -> dict:
    """Is the configured model ready? Cached for 10 seconds."""
    now = time.time()
    if not force and _status_cache["value"] and now - _status_cache["t"] < 10:
        return _status_cache["value"]
    status = {"provider": config.LLM_PROVIDER, "model": config.LLM_MODEL, "ready": False, "detail": ""}
    if config.LLM_PROVIDER == "none":
        status["detail"] = "No model configured: deterministic fallback only."
    elif config.LLM_PROVIDER == "ollama":
        try:
            r = httpx.get(f"{config.LLM_BASE_URL}/api/tags", timeout=3)
            names = {m.get("name", "") for m in r.json().get("models", [])}
            for cand in [config.LLM_MODEL] + config.LLM_FALLBACK_MODELS:
                if (cand if ":" in cand else cand + ":latest") in names:
                    status.update(ready=True, model=cand, detail="ready")
                    break
            else:
                status["detail"] = (f"Ollama is up; model {config.LLM_MODEL} is not downloaded yet "
                                    "(the first start downloads it; see the model-pull container logs).")
        except Exception:
            status["detail"] = "Ollama is not reachable yet."
    else:
        try:
            headers = {"Authorization": f"Bearer {config.LLM_API_KEY}"} if config.LLM_API_KEY else {}
            r = httpx.get(f"{config.LLM_BASE_URL.rstrip('/')}/models", headers=headers, timeout=5)
            status["ready"] = r.status_code == 200
            status["detail"] = "ready" if status["ready"] else f"HTTP {r.status_code}"
        except Exception as e:  # pragma: no cover - network dependent
            status["detail"] = f"Endpoint not reachable: {type(e).__name__}"
    _status_cache.update(t=now, value=status)
    return status


def _cost(prompt_tokens: int, completion_tokens: int) -> float:
    return round((prompt_tokens + completion_tokens) / 1_000_000 * config.LLM_COST_PER_MTOK, 6)


def complete(system: str, user: str, fallback: str, *, json_mode: bool = False, max_tokens: int = 1200,
             temperature: float | None = None) -> LLMResult:
    """Ask the model. On any failure return `fallback` with model=None."""
    st = model_status()
    if config.LLM_PROVIDER == "none" or not st["ready"]:
        result = LLMResult(text=fallback, model=None, error="model not ready")
        STATS.add(result)
        return result
    model_name = st["model"]
    temp = config.LLM_TEMPERATURE if temperature is None else temperature
    try:
        if config.LLM_PROVIDER == "ollama":
            body = {
                "model": model_name,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "stream": False,
                "think": False,
                "options": {"temperature": temp, "num_predict": max_tokens, "num_ctx": 8192},
            }
            if json_mode:
                body["format"] = "json"
            r = httpx.post(f"{config.LLM_BASE_URL}/api/chat", json=body, timeout=config.LLM_TIMEOUT_SECONDS)
            r.raise_for_status()
            data = r.json()
            text = strip_thinking(data.get("message", {}).get("content", ""))
            pt, ct = int(data.get("prompt_eval_count", 0)), int(data.get("eval_count", 0))
        else:
            headers = {"Authorization": f"Bearer {config.LLM_API_KEY}"} if config.LLM_API_KEY else {}
            body = {
                "model": model_name,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "temperature": temp,
                "max_tokens": max_tokens,
            }
            if json_mode:
                body["response_format"] = {"type": "json_object"}
            url = f"{config.LLM_BASE_URL.rstrip('/')}/chat/completions"
            r = None
            for attempt in range(4):
                r = httpx.post(url, json=body, headers=headers, timeout=config.LLM_TIMEOUT_SECONDS)
                if r.status_code == 429 and attempt < 3:
                    # Free tiers limit tokens per minute. Wait as long as the server asks (at most 20 s), then try again.
                    try:
                        wait = float(r.headers.get("retry-after", "") or 0)
                    except ValueError:
                        wait = 0.0
                    time.sleep(min(20.0, max(2.0, wait)))
                    continue
                if r.status_code == 400 and "response_format" in body:
                    body.pop("response_format")  # endpoint without JSON mode: the prompt already asks for JSON only
                    continue
                break
            r.raise_for_status()
            data = r.json()
            text = strip_thinking(data["choices"][0]["message"]["content"])
            usage = data.get("usage", {})
            pt, ct = int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
        if not text:
            raise ValueError("empty completion")
        result = LLMResult(text=text, model=model_name, prompt_tokens=pt, completion_tokens=ct, cost=_cost(pt, ct))
    except Exception as e:
        result = LLMResult(text=fallback, model=None, error=f"{type(e).__name__}: {e}"[:200])
    STATS.add(result)
    return result


def complete_json(system: str, user: str, fallback: dict, *, max_tokens: int = 1200,
                  temperature: float | None = None) -> tuple[dict, LLMResult]:
    """Ask for a JSON object. Falls back to `fallback` if the reply does not parse."""
    res = complete(system, user, json.dumps(fallback), json_mode=True, max_tokens=max_tokens, temperature=temperature)
    if res.used_fallback:
        return fallback, res
    text = res.text.strip()
    m = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        parsed = json.loads(m.group(0) if m else text)
        if not isinstance(parsed, dict):
            raise ValueError("not an object")
        return parsed, res
    except Exception as e:
        res = LLMResult(text=json.dumps(fallback), model=None, prompt_tokens=res.prompt_tokens,
                        completion_tokens=res.completion_tokens, error=f"unparseable JSON: {e}"[:200])
        return fallback, res
