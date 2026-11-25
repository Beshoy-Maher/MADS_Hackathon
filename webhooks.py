"""Webhook handler: the provider's events drive delivery and revocation.

* Signature checked on every event (forged events are rejected).
* Each event id is processed once (event-level idempotency).
* Delivery itself is idempotent per order (order-level idempotency), so a
  provider retry with a new event id still cannot deliver twice.
"""
from __future__ import annotations

import delivery
import payments
from payments import Store


def handle(store: Store, event: dict) -> str:
    if not payments.verify(event):
        store.note(f"rejected event {event.get('id')}: bad signature")
        return "rejected"
    if event["id"] in store.processed_events:
        store.note(f"ignored duplicate event {event['id']}")
        return "duplicate"
    store.processed_events.add(event["id"])
    order = store.orders.get(event["order_id"])
    if order is None:
        store.note(f"event {event['id']} for unknown order {event['order_id']}")
        return "unknown_order"
    if event["type"] == "payment.succeeded":
        if order["status"] == "pending":
            order["status"] = "paid"
        delivery.grant_access(store, order["id"])
        return "delivered"
    if event["type"] == "refund.succeeded":
        order["status"] = "refunded"
        order["refunded"] = True
        delivery.revoke_access(store, order["id"])
        return "revoked"
    store.note(f"ignored event type {event['type']}")
    return "ignored"
