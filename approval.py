"""The approval lock for anything that leaves the system.

Publishing a page, sending a post or email, issuing a refund: each one becomes an
OutboundItem with status "pending". `release()` refuses to act unless the founder
approved that exact item. Even then, the action is only written to an outbox file
(STUBBED): no network call publishes or sends anything.
"""
import json
import uuid

import decision_log

FOUNDER = "founder"


class ApprovalRequired(Exception):
    pass


def request(run, kind, title, payload):
    item = {"id": uuid.uuid4().hex[:8], "kind": kind, "title": title,
            "payload": payload, "status": "pending", "decided_by": None}
    run.setdefault("outbound", []).append(item)
    decision_log.append("approval", f"request_{kind}", run_id=run["id"], item=item["id"])
    return item


def find(run, item_id):
    for it in run.get("outbound", []):
        if it["id"] == item_id:
            return it
    raise KeyError(item_id)


def decide(run, item_id, approve, actor, via="dashboard or CLI"):
    if actor != FOUNDER:
        raise PermissionError("only the founder can approve or reject outbound items")
    item = find(run, item_id)
    if item["status"] != "pending":
        raise ValueError(f"item {item_id} is already {item['status']}")
    item["status"] = "approved" if approve else "rejected"
    item["decided_by"] = actor
    decision_log.append("approval", f"{item['status']}_{item['kind']}", approved_by=FOUNDER,
                        run_id=run["id"], item=item_id, via=via)
    if approve:
        release(run, item_id, outbox_dir=run.get("dir"))
    return item


def release(run, item_id, outbox_dir=None):
    """Perform the outbound action. Refuses unless the founder approved it."""
    item = find(run, item_id)
    if item["status"] != "approved" or item["decided_by"] != FOUNDER:
        raise ApprovalRequired(f"{item['kind']} '{item['title']}' needs founder approval first")
    if outbox_dir and item["kind"] != "refund":  # STUBBED: written to a local outbox, never sent
        # (a refund is executed by refunds.execute_refund against the MOCKED provider)
        from pathlib import Path
        p = Path(outbox_dir) / "outbox.jsonl"
        with p.open("a") as f:
            f.write(json.dumps({"id": item_id, "kind": item["kind"], "title": item["title"],
                                "status": "STUBBED: written to outbox, not sent"}) + "\n")
    item["released"] = True
    return item


def pending(run):
    return [i for i in run.get("outbound", []) if i["status"] == "pending"]
