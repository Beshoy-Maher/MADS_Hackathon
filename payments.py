"""MOCKED payment provider.

No real payment service is called and no money exists anywhere in this
module. It imitates the shape of a hosted-checkout provider (checkout
session -> signed webhook event -> payout) so the sale-to-cash flow can be
built and tested end to end. The fee model (2.9% + $0.30) is an ASSUMPTION
modelled on common card-processing pricing.

The system never stores card numbers: checkout is hosted by the provider,
and this module only ever sees order ids and amounts.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from dataclasses import dataclass, field

MOCKED = True
FEE_PERCENT = 0.029
FEE_FIXED = 0.30
WEBHOOK_SECRET = "mock-webhook-secret-not-a-real-key"


def fee_for(amount: float) -> float:
    return round(amount * FEE_PERCENT + FEE_FIXED, 2)


def sign(payload: str) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()


@dataclass
class Store:
    """All sale-to-cash state for one run (orders, provider ledger, access grants)."""
    orders: dict = field(default_factory=dict)          # order_id -> order
    ledger: list = field(default_factory=list)          # provider-side transactions
    processed_events: set = field(default_factory=set)  # webhook idempotency
    access: dict = field(default_factory=dict)          # order_id -> {"token", "active"}
    deliveries: list = field(default_factory=list)      # every delivery email (STUBBED)
    log: list = field(default_factory=list)

    def note(self, msg: str) -> None:
        self.log.append(msg)


class MockProvider:
    """MOCKED hosted checkout. Methods return the events a real provider would send."""

    name = "mock-provider (MOCKED)"

    def __init__(self, store: Store):
        self.store = store

    def create_checkout(self, product: str, amount: float, buyer_ref: str) -> dict:
        order_id = "ord_" + uuid.uuid4().hex[:8]
        self.store.orders[order_id] = {"id": order_id, "product": product, "amount": round(amount, 2), "buyer_ref": buyer_ref,
                                       "status": "pending", "refunded": False}
        self.store.note(f"checkout created {order_id} for ${amount:.2f} (MOCKED hosted checkout; no card data touches our system)")
        return {"checkout_id": "cs_" + uuid.uuid4().hex[:8], "order_id": order_id, "url": f"https://checkout.mock.invalid/{order_id}"}

    def _event(self, etype: str, order_id: str, amount: float, event_id: str | None = None) -> dict:
        body = f"{etype}:{order_id}:{amount:.2f}"
        return {"id": event_id or "evt_" + uuid.uuid4().hex[:10], "type": etype, "order_id": order_id,
                "amount": round(amount, 2), "signature": sign(body)}

    def simulate_payment(self, order_id: str) -> dict:
        """What the provider sends after the buyer pays on the hosted page (MOCKED)."""
        amount = self.store.orders[order_id]["amount"]
        fee = fee_for(amount)
        self.store.ledger.append({"type": "charge", "order_id": order_id, "amount": amount, "fee": fee})
        return self._event("payment.succeeded", order_id, amount)

    def refund(self, order_id: str) -> dict:
        """Called only by refunds.py after founder approval (MOCKED)."""
        amount = self.store.orders[order_id]["amount"]
        self.store.ledger.append({"type": "refund", "order_id": order_id, "amount": -amount, "fee": 0.0})
        return self._event("refund.succeeded", order_id, amount)

    def payout(self) -> dict:
        net = round(sum(t["amount"] - t["fee"] for t in self.store.ledger if t["type"] in ("charge", "refund")), 2)
        paid_out = round(sum(t["amount"] for t in self.store.ledger if t["type"] == "payout"), 2)
        amount = round(net - paid_out, 2)
        self.store.ledger.append({"type": "payout", "order_id": None, "amount": amount, "fee": 0.0})
        return {"payout": amount}


def verify(event: dict) -> bool:
    body = f"{event['type']}:{event['order_id']}:{event['amount']:.2f}"
    return hmac.compare_digest(sign(body), event.get("signature", ""))
