"""Webhook handler: payment triggers delivery, refund revokes access.

Idempotency: every event id is stored; a repeated event (providers retry) does nothing.
Events with a bad signature are rejected.
"""
import json

import payments


class WebhookHandler:
    def __init__(self, provider, delivery):
        self.provider, self.delivery = provider, delivery
        self.seen = set()
        self.log = []

    def handle(self, body, sig):
        if not payments.verify(body, sig):
            self.log.append(("rejected", "bad signature"))
            return "rejected"
        evt = json.loads(body)
        if evt["id"] in self.seen:
            self.log.append(("duplicate", evt["id"]))
            return "duplicate_ignored"
        self.seen.add(evt["id"])
        d = evt["data"]
        if evt["type"] == "payment.succeeded":
            email = self.provider.orders[d["order_id"]]["email"]
            _, new = self.delivery.grant(d["order_id"], email)
            self.log.append(("delivered" if new else "already_delivered", d["order_id"]))
            return "delivered" if new else "already_delivered"
        if evt["type"] == "payment.refunded":
            self.delivery.revoke(d["order_id"])
            self.log.append(("revoked", d["order_id"]))
            return "revoked"
        return "ignored"
