"""Refunds: always founder-approved, never automatic.

request_refund() only queues a 'refund' action. issue_refund() refuses to run
unless that action was approved by the founder. The MOCKED provider then
sends refund.succeeded, and webhooks.py revokes access.
"""
from __future__ import annotations

import approval
import webhooks
from payments import MockProvider, Store


def request_refund(run: dict, order_id: str, reason: str) -> dict:
    return approval.request_action(run, "refund", f"refund {order_id}", f"Refund order {order_id}: {reason}",
                                   {"order_id": order_id}, agent="support")


def issue_refund(run: dict, store: Store, provider: MockProvider, action_id: str) -> str:
    action = approval.find_action(run, action_id)
    if action["status"] != "approved":
        raise approval.ApprovalRequired("refunds need the founder's approval")
    event = provider.refund(action["payload"]["order_id"])
    return webhooks.handle(store, event)
