"""Append-only decision log: one entry per agent action.

Every entry carries the five required keys (action, sources, model, cost,
approved_by) plus timestamp and agent. Extra keys (run_id, step, outcome,
detail) make the log easy to follow.
"""
from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

import config
import guardrails

REQUIRED_KEYS = ("timestamp", "agent", "action", "sources", "model", "cost", "approved_by")
_lock = threading.Lock()
_redirect: list[Path] = []  # stack of temporary log paths (used by sandboxed tests)


class redirect:
    """Send log entries to another file for the duration of a with-block.

    Used by the MOCKED payment test, whose simulated founder approvals must
    not appear in the real decision log as if the founder had made them.
    """

    def __init__(self, path: Path):
        self.path = path

    def __enter__(self):
        _redirect.append(self.path)
        return self.path

    def __exit__(self, *exc):
        _redirect.pop()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8") or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def log(agent: str, action: str, *, sources: list[str] | None = None, model: str | None = None,
        cost: float = 0, approved_by: str | None = None, run_id: str | None = None,
        path: Path | None = None, **extra) -> dict:
    if approved_by not in (None, "founder"):
        raise ValueError("approved_by must be 'founder' or None")
    entry = {
        "timestamp": now_iso(),
        "agent": agent,
        "action": action,
        "sources": sorted(set(s for s in (sources or []) if isinstance(s, str) and s.startswith("http"))),
        "model": model,
        "cost": float(cost or 0),
        "approved_by": approved_by,
    }
    if run_id:
        entry["run_id"] = run_id
    for k, v in extra.items():
        if v is not None:
            # Free text (a request, a note) may contain a pasted password or card number: never write it down.
            entry[k] = guardrails.redact_secrets(v) if isinstance(v, str) else v
    target = path or (_redirect[-1] if _redirect else config.DECISION_LOG_PATH)
    with _lock:
        target.parent.mkdir(parents=True, exist_ok=True)
        entries = _read(target)
        entries.append(entry)
        target.write_text(json.dumps(entries, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return entry


def read(path: Path | None = None, run_id: str | None = None) -> list[dict]:
    entries = _read(path or config.DECISION_LOG_PATH)
    if run_id:
        entries = [e for e in entries if e.get("run_id") == run_id]
    return entries


def validate(entries: list[dict]) -> list[str]:
    """Return a list of problems (empty when the log is valid)."""
    problems = []
    for i, e in enumerate(entries):
        for k in REQUIRED_KEYS:
            if k not in e:
                problems.append(f"entry {i}: missing key {k}")
        if not isinstance(e.get("action"), str):
            problems.append(f"entry {i}: action must be a string")
        if not isinstance(e.get("sources"), list):
            problems.append(f"entry {i}: sources must be a list")
        if e.get("model") is not None and not isinstance(e.get("model"), str):
            problems.append(f"entry {i}: model must be a string or null")
        if not isinstance(e.get("cost"), (int, float)):
            problems.append(f"entry {i}: cost must be a number")
        if e.get("approved_by") not in (None, "founder"):
            problems.append(f"entry {i}: approved_by must be 'founder' or null")
    return problems
