"""Refunds never happen by themselves.

`request_refund` only queues an outbound item. `execute_refund` refuses unless the
founder approved that item; then the MOCKED provider refunds and its webhook revokes access.
"""
import approval


def request_refund(run, payment_id, reason):
    return approval.request(run, "refund", f"Refund {payment_id}", {"payment_id": payment_id, "reason": reason})


def execute_refund(run, item_id, provider, webhook):
    item = approval.find(run, item_id)
    if item["status"] != "approved" or item["decided_by"] != approval.FOUNDER:
        raise approval.ApprovalRequired("refund needs founder approval")
    body, sig = provider.refund(item["payload"]["payment_id"])
    return webhook.handle(body, sig)
