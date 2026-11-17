"""Reconciliation: orders, payments, fees, refunds and payouts must add up."""


def reconcile(provider, delivery):
    paid_orders = [o for o in provider.orders.values() if o["status"] == "paid"]
    gross = round(sum(p["amount"] for p in provider.payments.values()), 2)
    fees = round(sum(p["fee"] for p in provider.payments.values()), 2)
    refunded = round(sum(r["amount"] for r in provider.refunds.values()), 2)
    payout = round(sum(po["amount"] for po in provider.payouts), 2)
    expected = round(gross - fees - refunded, 2)
    refunded_orders = {provider.payments[r["payment"]]["order"] for r in provider.refunds.values()}
    issues = []
    for o in paid_orders:
        g = delivery.grants.get(o["id"])
        if not g:
            issues.append(f"{o['id']}: paid but not delivered")
        elif o["id"] in refunded_orders and g["active"]:
            issues.append(f"{o['id']}: refunded but access still active")
    if abs(payout - expected) > 0.009:
        issues.append(f"payout {payout} != gross {gross} - fees {fees} - refunds {refunded}")
    if len(provider.payments) != len(paid_orders):
        issues.append("payments and paid orders differ")
    return {"orders": len(provider.orders), "paid": len(paid_orders), "gross": gross, "fees": fees,
            "refunded": refunded, "payout": payout, "expected_payout": expected,
            "matched": not issues, "issues": issues}
