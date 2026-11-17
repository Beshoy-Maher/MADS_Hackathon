"""Digital delivery: an access token per paid order. A refund revokes it.

Delivery emails are STUBBED (recorded in `sent`, never sent).
"""
import uuid


class Delivery:
    def __init__(self):
        self.grants = {}   # order_id -> {"token", "active"}
        self.sent = []     # STUBBED emails

    def grant(self, order_id, email):
        if order_id in self.grants:          # idempotent: one delivery per order
            return self.grants[order_id], False
        g = {"token": "dl_" + uuid.uuid4().hex[:12], "active": True}
        self.grants[order_id] = g
        self.sent.append({"to": email, "order": order_id, "status": "STUBBED: not sent"})
        return g, True

    def revoke(self, order_id):
        if order_id in self.grants:
            self.grants[order_id]["active"] = False

    def can_download(self, token):
        return any(g["token"] == token and g["active"] for g in self.grants.values())
