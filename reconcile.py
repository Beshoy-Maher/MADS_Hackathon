"""Reconciliation: orders vs. provider charges, refunds, fees and payouts.

Every paid order must have exactly one charge; every refunded order exactly
one refund; the payout must equal charges - refunds - fees. Any mismatch is
reported, never silently fixed.
"""
from __future__ import annotations

from collections import Counter

from payments import Store


def reconcile(store: Store) -> dict:
    charges = Counter(t["order_id"] for t in store.ledger if t["type"] == "charge")
    refunds = Counter(t["order_id"] for t in store.ledger if t["type"] == "refund")
    issues = []
    for oid, o in store.orders.items():
        if o["status"] in ("paid", "refunded") and charges[oid] != 1:
            issues.append(f"{oid}: {charges[oid]} charges for a {o['status']} order")
        if o["status"] == "pending" and charges[oid]:
            issues.append(f"{oid}: charged but still pending")
        if o["status"] == "refunded" and refunds[oid] != 1:
            issues.append(f"{oid}: {refunds[oid]} refunds for a refunded order")
        if o["status"] != "refunded" and refunds[oid]:
            issues.append(f"{oid}: refund recorded but order not refunded")
        active = store.access.get(oid, {}).get("active", False)
        if o["status"] == "paid" and not active:
            issues.append(f"{oid}: paid but not delivered")
        if o["status"] != "paid" and active:
            issues.append(f"{oid}: has access but is {o['status']}")
    gross = round(sum(t["amount"] for t in store.ledger if t["type"] == "charge"), 2)
    refunded = round(-sum(t["amount"] for t in store.ledger if t["type"] == "refund"), 2)
    fees = round(sum(t["fee"] for t in store.ledger), 2)
    payouts = round(sum(t["amount"] for t in store.ledger if t["type"] == "payout"), 2)
    expected_net = round(gross - refunded - fees, 2)
    if payouts and abs(payouts - expected_net) > 0.01:
        issues.append(f"payouts {payouts} != gross - refunds - fees {expected_net}")
    return {"orders": len(store.orders), "gross": gross, "refunded": refunded, "fees": fees, "payouts": payouts,
            "expected_net": expected_net, "balanced": not issues, "issues": issues}
