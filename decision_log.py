"""Appends one entry per agent action to decision_log.json.

Every entry carries the five required keys: action, sources, model, cost, approved_by.
"""
import json
import threading
from datetime import datetime, timezone

import config

_LOCK = threading.Lock()


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append(agent, action, sources=None, model=None, cost=0, approved_by=None, **extra):
    entry = {"timestamp": now(), "agent": agent, "action": action,
             "sources": list(sources or []), "model": model, "cost": cost,
             "approved_by": approved_by}
    entry.update(extra)
    path = config.DECISION_LOG
    with _LOCK:
        path.parent.mkdir(parents=True, exist_ok=True)
        entries = json.loads(path.read_text()) if path.exists() else []
        entries.append(entry)
        path.write_text(json.dumps(entries, indent=1))
    return entry


def read():
    p = config.DECISION_LOG
    return json.loads(p.read_text()) if p.exists() else []
