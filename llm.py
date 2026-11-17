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
        self.errors: list[str] = []  # why calls fell back (model, error), for the demo script's report

    def add(self, r: LLMResult) -> None:
        with self.lock:
            self.calls += 1
            self.prompt_tokens += r.prompt_tokens
            self.completion_tokens += r.completion_tokens
            if r.used_fallback:
                self.fallbacks += 1
                self.errors.append(r.error or "unknown")


STATS = _Stats()
_status_cache: dict = {"t": 0.0, "value": None}


def strip_thinking(text: str) -> str:
    text = _THINK_RE.sub("", text or "")
    if "</think>" in text:  # unterminated opening tag cut off by the server
        text = text.split("</think>", 1)[1]
    return text.strip()


ROLES = ("writer", "fast", "judge", "critic")
_FAILED_FOR_SECONDS = 600
_failed: dict[str, float] = {}  # model -> time it failed to load; skipped for a while, then tried again


def role_model(role: str) -> str:
    """The model configured for a kind of work (before availability is checked)."""
    if config.LLM_PROVIDER != "ollama":
        return config.LLM_MODEL  # a free-tier endpoint serves one model for everything
    return {"writer": config.LLM_MODEL, "fast": config.LLM_FAST_MODEL, "judge": config.LLM_JUDGE_MODEL,
            "critic": config.LLM_CRITIC_MODEL}.get(role, config.LLM_MODEL)


def _candidates(role: str) -> list[str]:
    out = []
    for m in [role_model(role)] + config.LLM_FALLBACK_MODELS:
        if m and m not in out:
            out.append(m)
    return out


def _mark_failed(model: str) -> None:
    _failed[model] = time.time()


def _recently_failed(model: str) -> bool:
    t = _failed.get(model)
    return t is not None and time.time() - t < _FAILED_FOR_SECONDS


def _installed() -> set[str]:
    r = httpx.get(f"{config.LLM_BASE_URL}/api/tags", timeout=3)
    return {m.get("name", "") for m in r.json().get("models", [])}


def _pick(role: str, names: set[str]) -> str | None:
    for cand in _candidates(role):
        if (cand if ":" in cand else cand + ":latest") in names and not _recently_failed(cand):
            return cand
    return None


def model_status(force: bool = False) -> dict:
    """Is a model ready? Cached for 10 seconds. `model` is the writer's; `roles` says which model each kind of work uses now."""
    now = time.time()
    if not force and _status_cache["value"] and now - _status_cache["t"] < 10:
        return _status_cache["value"]
    status = {"provider": config.LLM_PROVIDER, "model": config.LLM_MODEL, "ready": False, "detail": "",
              "roles": {r: None for r in ROLES}, "configured": {r: role_model(r) for r in ROLES}}
    if config.LLM_PROVIDER == "none":
        status["detail"] = "No model configured: deterministic fallback only."
    elif config.LLM_PROVIDER == "ollama":
        try:
            names = _installed()
            status["roles"] = {r: _pick(r, names) for r in ROLES}
            if status["roles"]["writer"]:
                status.update(ready=True, model=status["roles"]["writer"], detail="ready")
                missing = sorted({role_model(r) for r in ROLES if status["roles"][r] != role_model(r)})
                if missing:
                    status["detail"] = ("ready; still downloading or not loadable here: " + ", ".join(missing)
                                        + " (those steps use " + status["roles"]["writer"] + " meanwhile)")
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
            if status["ready"]:
                status["roles"] = {r: config.LLM_MODEL for r in ROLES}
        except Exception as e:  # pragma: no cover - network dependent
            status["detail"] = f"Endpoint not reachable: {type(e).__name__}"
    _status_cache.update(t=now, value=status)
    return status


def _think_value(model: str):
    """gpt-oss always reasons and takes a level, not off; the Qwen3 instruct models take false.
    Medium, not low: at low effort gpt-oss skims and, as the critic, returned no objections to documents with clear
    unsupported claims; at medium it finds them in a few seconds on a GPU."""
    return "medium" if model.startswith("gpt-oss") else False


def warm_up(wait_seconds: int = 900) -> bool:
    """Load the local models into memory so the founder's first step does not pay for it.

    Waits until the writer model is there, then sends a one-token request to each distinct model in use.
    Not counted in STATS: no agent did any work.
    """
    if config.LLM_PROVIDER != "ollama":
        return False
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        st = model_status(force=True)
        if st["ready"]:
            ok = False
            for m in dict.fromkeys(x for x in (st["roles"]["fast"], st["roles"]["judge"], st["roles"]["writer"]) if x):
                try:
                    r = httpx.post(f"{config.LLM_BASE_URL}/api/chat", timeout=config.LLM_TIMEOUT_SECONDS, json={
                        "model": m, "messages": [{"role": "user", "content": "ok"}], "stream": False, "think": _think_value(m),
                        "keep_alive": "60m", "options": {"num_predict": 1, "num_ctx": 8192}})
                    if r.status_code >= 400:
                        _mark_failed(m)
                        _status_cache["value"] = None
                    else:
                        ok = True
                except Exception:
                    pass
            return ok
        time.sleep(5)
    return False


def _cost(prompt_tokens: int, completion_tokens: int) -> float:
    return round((prompt_tokens + completion_tokens) / 1_000_000 * config.LLM_COST_PER_MTOK, 6)


class _LoadError(Exception):
    """Ollama could not load or run this model (e.g. not enough memory): try the next one."""


def _ollama_chat(model_name: str, system: str, user: str, json_mode: bool, max_tokens: int, temp: float, _retry: bool = True):
    think = _think_value(model_name)
    body = {
        "model": model_name,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "think": think,
        "keep_alive": "60m",  # keep the model in memory between steps; reloading it costs many seconds
        # A reasoning model spends part of the budget on its (hidden) reasoning: give it room for the answer too.
        "options": {"temperature": temp, "num_predict": max_tokens + (4000 if think else 0), "num_ctx": 8192},
    }
    if json_mode:
        body["format"] = "json"
    r = httpx.post(f"{config.LLM_BASE_URL}/api/chat", json=body, timeout=config.LLM_TIMEOUT_SECONDS)
    if r.status_code >= 400:
        raise _LoadError(f"HTTP {r.status_code}: {r.text[:160]}")
    data = r.json()
    text = strip_thinking(data.get("message", {}).get("content", ""))
    if not text and think and _retry:
        # A reasoning model can spend the whole budget thinking and leave no answer: try once more with twice the room.
        return _ollama_chat(model_name, system, user, json_mode, max_tokens * 2 + 4000, temp, _retry=False)
    return text, int(data.get("prompt_eval_count", 0)), int(data.get("eval_count", 0))


def complete(system: str, user: str, fallback: str, *, json_mode: bool = False, max_tokens: int = 1200,
             temperature: float | None = None, role: str = "writer") -> LLMResult:
    """Ask the model for this kind of work (`role`: writer, fast, judge, critic).

    If the role's model is missing or cannot be loaded, the next available model is used and the result says which.
    On any other failure return `fallback` with model=None."""
    st = model_status()
    if config.LLM_PROVIDER == "none" or not st["ready"]:
        result = LLMResult(text=fallback, model=None, error="model not ready")
        STATS.add(result)
        return result
    model_name = (st.get("roles") or {}).get(role) or st["model"]
    temp = config.LLM_TEMPERATURE if temperature is None else temperature
    try:
        if config.LLM_PROVIDER == "ollama":
            tried: list[str] = []
            while True:
                try:
                    text, pt, ct = _ollama_chat(model_name, system, user, json_mode, max_tokens, temp)
                    break
                except _LoadError:
                    tried.append(model_name)
                    _mark_failed(model_name)
                    _status_cache["value"] = None
                    names = _installed()
                    nxt = next((c for c in _candidates(role) if c not in tried and not _recently_failed(c)
                                and (c if ":" in c else c + ":latest") in names), None)
                    if not nxt:
                        raise
                    model_name = nxt
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
        result = LLMResult(text=fallback, model=None, error=f"{role} {model_name}: {type(e).__name__}: {e}"[:300])
    STATS.add(result)
    return result


def complete_json(system: str, user: str, fallback: dict, *, max_tokens: int = 1200,
                  temperature: float | None = None, role: str = "writer") -> tuple[dict, LLMResult]:
    """Ask for a JSON object. Falls back to `fallback` if the reply does not parse."""
    res = complete(system, user, json.dumps(fallback), json_mode=True, max_tokens=max_tokens, temperature=temperature,
                   role=role)
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
