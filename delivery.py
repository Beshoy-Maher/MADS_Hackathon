"""Automatic delivery: a paid order gets a download link, a refunded one loses it.

Idempotent per order: however many times a payment event arrives, the buyer
gets exactly one delivery. Sending the delivery email is STUBBED (recorded,
not sent).
"""
from __future__ import annotations

import uuid

from payments import Store


def grant_access(store: Store, order_id: str) -> dict:
    order = store.orders[order_id]
    if order["status"] != "paid":
        raise PermissionError("cannot deliver an unpaid order")
    existing = store.access.get(order_id)
    if existing and existing["active"]:
        store.note(f"delivery skipped for {order_id}: already delivered (idempotent)")
        return existing
    grant = {"token": "dl_" + uuid.uuid4().hex[:12], "active": True}
    store.access[order_id] = grant
    store.deliveries.append({"order_id": order_id, "to": order["buyer_ref"], "link": f"/download/{grant['token']}",
                             "sent": "STUBBED: email recorded, not sent"})
    store.note(f"delivered {order_id}: download token issued, delivery email STUBBED")
    return grant


def revoke_access(store: Store, order_id: str) -> None:
    grant = store.access.get(order_id)
    if grant:
        grant["active"] = False
    store.note(f"access revoked for {order_id}")


def can_download(store: Store, token: str) -> bool:
    return any(g["token"] == token and g["active"] for g in store.access.values())
