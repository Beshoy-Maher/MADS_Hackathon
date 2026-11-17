"""MOCKED payment provider. No real payment of any kind happens here.

It behaves like a hosted checkout (Stripe/Paddle style): we never see or store card
numbers; the provider sends signed events to our webhook. Fees: 2.9% + $0.30 (ASSUMPTION,
a typical card-processing fee). Payouts are batched once per test run.
"""
import hashlib
import hmac
import json
import uuid

MODE = "MOCKED"
SECRET = b"mock-webhook-secret-not-a-real-key"
FEE_PCT, FEE_FIXED = 0.029, 0.30


class MockProvider:
    def __init__(self):
        self.orders, self.payments, self.refunds, self.payouts = {}, {}, {}, []

    def create_checkout(self, product_id, price, email):
        oid = "ord_" + uuid.uuid4().hex[:8]
        self.orders[oid] = {"id": oid, "product": product_id, "amount": price, "email": email, "status": "open"}
        return {"order_id": oid, "checkout_url": f"https://checkout.mock.invalid/{oid}", "mode": MODE}

    def _event(self, etype, data):
        body = json.dumps({"id": "evt_" + uuid.uuid4().hex[:10], "type": etype, "data": data}, sort_keys=True)
        sig = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
        return body, sig

    def pay(self, order_id):
        """Simulate the customer completing checkout. Returns a signed webhook event."""
        o = self.orders[order_id]
        fee = round(o["amount"] * FEE_PCT + FEE_FIXED, 2)
        pid = "pay_" + uuid.uuid4().hex[:8]
        self.payments[pid] = {"id": pid, "order": order_id, "amount": o["amount"], "fee": fee, "status": "succeeded"}
        o["status"] = "paid"
        return self._event("payment.succeeded", {"order_id": order_id, "payment_id": pid, "amount": o["amount"], "fee": fee})

    def refund(self, payment_id):
        """Only called by refunds.py after the founder approved the refund."""
        p = self.payments[payment_id]
        rid = "re_" + uuid.uuid4().hex[:8]
        self.refunds[rid] = {"id": rid, "payment": payment_id, "amount": p["amount"]}
        p["status"] = "refunded"
        return self._event("payment.refunded", {"order_id": p["order"], "payment_id": payment_id, "refund_id": rid, "amount": p["amount"]})

    def payout(self):
        paid = sum(p["amount"] - p["fee"] for p in self.payments.values())
        refunded = sum(r["amount"] for r in self.refunds.values())
        po = {"id": "po_" + uuid.uuid4().hex[:6], "amount": round(paid - refunded, 2)}
        self.payouts.append(po)
        return po


def verify(body, sig):
    good = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(good, sig)
