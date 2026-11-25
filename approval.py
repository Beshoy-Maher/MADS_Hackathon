"""Founder approval, enforced in code.

Anything that would be published, sent, spent or signed becomes a
PendingAction. It can only be executed after the founder approves it in the
dashboard or the CLI. execute_action() raises ApprovalRequired otherwise, and
there is no flag, environment variable or prompt that skips this check.

Even after approval, execution is STUBBED: the action is written to the run's
outbox file instead of being posted to any real service. The founder copies
it out and publishes it themselves.
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import decision_log

OUTBOUND_KINDS = {"publish", "send", "spend", "sign", "refund"}
FOUNDER = "founder"


class ApprovalRequired(PermissionError):
    """Raised when something tries to go out without founder approval."""


class BrokenPromise(ValueError):
    """Raised when the founder tries to approve an item the promise checker found a broken promise in."""


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def request_action(run: dict, kind: str, target: str, description: str, payload: dict | None = None,
                   agent: str = "orchestrator") -> dict:
    if kind not in OUTBOUND_KINDS:
        raise ValueError(f"unknown outbound kind: {kind}")
    action = {
        "id": "act_" + uuid.uuid4().hex[:8],
        "kind": kind,
        "target": target,
        "description": description,
        "payload": payload or {},
        "status": "pending",
        "requested_by": agent,
        "requested_at": _now(),
        "decided_at": None,
        "executed": False,
        "phase": run.get("phase"),
    }
    run.setdefault("pending_actions", []).append(action)
    decision_log.log(agent, f"request_approval:{kind}", run_id=run["id"], target=target, action_id=action["id"],
                     detail=description[:200])
    return action


def find_action(run: dict, action_id: str) -> dict:
    for a in run.get("pending_actions", []):
        if a["id"] == action_id:
            return a
    raise KeyError(action_id)


def decide_action(run: dict, action_id: str, approve: bool, actor: str, note: str = "") -> dict:
    """Only the founder can decide. Agents calling this are refused."""
    if actor != FOUNDER:
        raise ApprovalRequired(f"only the founder can approve or reject (got actor={actor!r})")
    a = find_action(run, action_id)
    if a["status"] != "pending":
        return a
    broken = (a.get("payload") or {}).get("promise_check") or {}
    if approve and broken.get("broken"):
        # A false promise to customers is never published, even with a click: the item has to be fixed first.
        decision_log.log("approval", f"blocked_broken_promise:{a['kind']}", run_id=run["id"], target=a["target"],
                         action_id=action_id, outcome="blocked")
        raise BrokenPromise(f"'{a['target']}' makes {broken['broken']} broken promise(s): "
                            + "; ".join(broken.get("broken_items", []))[:300] + ". Reject it and repeat the phase with a fix.")
    a["status"] = "approved" if approve else "rejected"
    a["decided_at"] = _now()
    a["note"] = note
    decision_log.log("founder", f"{'approve' if approve else 'reject'}:{a['kind']}", run_id=run["id"],
                     approved_by=FOUNDER, target=a["target"], action_id=action_id, outcome=a["status"])
    return a


def execute_action(run: dict, action_id: str, outbox_path=None) -> dict:
    """Carry out an approved action. STUBBED: writes to the outbox, never to the internet."""
    a = find_action(run, action_id)
    if a["status"] != "approved":
        decision_log.log("approval", f"blocked_unapproved:{a['kind']}", run_id=run["id"], target=a["target"],
                         action_id=action_id, outcome="blocked")
        raise ApprovalRequired(f"{a['kind']} '{a['target']}' has not been approved by the founder")
    if a["executed"]:
        return a  # idempotent
    a["executed"] = True
    a["executed_at"] = _now()
    a["execution"] = "STUBBED: saved to outbox, not sent to any external service"
    if outbox_path is not None:
        outbox_path.parent.mkdir(parents=True, exist_ok=True)
        with open(outbox_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({k: a[k] for k in ("id", "kind", "target", "description", "executed_at")}) + "\n")
    decision_log.log("approval", f"execute:{a['kind']}", run_id=run["id"], approved_by=FOUNDER, target=a["target"],
                     action_id=action_id, outcome="stubbed_execution")
    return a


def pending(run: dict) -> list[dict]:
    return [a for a in run.get("pending_actions", []) if a["status"] == "pending"]
