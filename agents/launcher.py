"""Phase 5, step 3 (Core step): deliver automatically.

Runs the full sale-to-cash flow against the MOCKED payment provider and
checks every promise of the design: payment triggers delivery, duplicate
events don't deliver twice, unpaid orders can't download, refunds need the
founder and revoke access, and the books reconcile.

The simulated founder approval used inside this test is logged to a separate
sandbox log, never to the real decision log.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import approval
import decision_log
import delivery
import reconcile
import refunds
import webhooks
from agents.base import Agent, StepResult
from payments import MockProvider, Store


def sale_to_cash_test(product: str, price: float) -> tuple[list[dict], Store, dict]:
    store = Store()
    provider = MockProvider(store)
    results: list[dict] = []
    sandbox_run = {"id": "payment-test-sandbox", "phase": 5, "pending_actions": []}

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append({"name": name, "passed": bool(ok), "detail": detail})

    with decision_log.redirect(Path(tempfile.gettempdir()) / "payment_test_sandbox_log.json"):
        a = provider.create_checkout(product, price, "buyer-A (test)")
        b = provider.create_checkout(product, price, "buyer-B (test)")
        oa, ob = a["order_id"], b["order_id"]
        check("checkout_creates_pending_order_without_access", store.orders[oa]["status"] == "pending" and oa not in store.access)

        try:
            store.orders[ob]["status"] = store.orders[ob]["status"]
            delivery.grant_access(store, ob)
            check("unpaid_order_cannot_be_delivered", False)
        except PermissionError:
            check("unpaid_order_cannot_be_delivered", True, "PermissionError raised")

        ev = provider.simulate_payment(oa)
        r1 = webhooks.handle(store, ev)
        check("payment_triggers_delivery", r1 == "delivered" and store.access[oa]["active"], r1)

        r2 = webhooks.handle(store, ev)
        check("duplicate_event_is_ignored", r2 == "duplicate" and len(store.deliveries) == 1, r2)

        retry = dict(ev, id=ev["id"] + "_retry")
        from payments import sign
        retry["signature"] = sign(f"{retry['type']}:{retry['order_id']}:{retry['amount']:.2f}")
        webhooks.handle(store, retry)
        check("retry_with_new_event_id_does_not_double_deliver", len(store.deliveries) == 1, f"deliveries={len(store.deliveries)}")

        forged = dict(ev, id="evt_forged", signature="0" * 64)
        check("forged_webhook_rejected", webhooks.handle(store, forged) == "rejected")

        evb = provider.simulate_payment(ob)
        webhooks.handle(store, evb)
        token_a = store.access[oa]["token"]
        check("paid_buyer_can_download", delivery.can_download(store, token_a))

        act = refunds.request_refund(sandbox_run, oa, "buyer asked within the refund window (test)")
        try:
            refunds.issue_refund(sandbox_run, store, provider, act["id"])
            check("refund_blocked_without_founder_approval", False)
        except approval.ApprovalRequired:
            check("refund_blocked_without_founder_approval", True, "ApprovalRequired raised")
        try:
            approval.decide_action(sandbox_run, act["id"], True, actor="support-agent")
            check("agent_cannot_approve_its_own_refund", False)
        except approval.ApprovalRequired:
            check("agent_cannot_approve_its_own_refund", True)
        approval.decide_action(sandbox_run, act["id"], True, actor="founder", note="test approval inside MOCKED sandbox")
        r3 = refunds.issue_refund(sandbox_run, store, provider, act["id"])
        check("refund_revokes_access", r3 == "revoked" and not delivery.can_download(store, token_a), r3)

        payout = provider.payout()
        rec = reconcile.reconcile(store)
        check("books_reconcile_orders_payments_fees_payouts", rec["balanced"], "; ".join(rec["issues"]) or "balanced")
    return results, store, {"reconciliation": rec, "payout": payout}


class Launcher(Agent):
    role = "launcher"

    def run_step(self, product: str, price: float) -> tuple[StepResult, str]:
        results, store, extra = sale_to_cash_test(product, price)
        rec = extra["reconciliation"]
        passed = sum(r["passed"] for r in results)
        md = [f"# Phase 5, step 3: Automatic delivery test ({passed}/{len(results)} passed)", "",
              "Payment provider: **MOCKED** (no real payment service, no real money, no card data). "
              "Delivery emails: **STUBBED** (recorded, not sent).", "",
              "| Check | Result | Detail |", "|---|---|---|"]
        md += [f"| {r['name']} | {'PASS' if r['passed'] else 'FAIL'} | {r['detail']} |" for r in results]
        md += ["", "## Reconciliation (MOCKED amounts)", "",
               f"- Orders: {rec['orders']}", f"- Gross charged: ${rec['gross']:.2f}", f"- Refunded: ${rec['refunded']:.2f}",
               f"- Fees (ASSUMPTION: 2.9% + $0.30): ${rec['fees']:.2f}", f"- Payouts: ${rec['payouts']:.2f}",
               f"- Expected net: ${rec['expected_net']:.2f}", f"- Balanced: {'yes' if rec['balanced'] else 'NO: ' + '; '.join(rec['issues'])}"]
        log = ["# Payment test log", "", "All of this is MOCKED: a simulated provider, test buyers, no real charges, refunds or payouts.",
               f"Product: {product}. Price: ${price:.2f}.", "", "## Event trail", ""]
        log += [f"{i}. {line}" for i, line in enumerate(store.log, 1)]
        log += ["", "## Deliveries (STUBBED emails)", ""] + [f"- {d['order_id']} -> {d['to']}: {d['link']} ({d['sent']})" for d in store.deliveries]
        log += ["", "## Checks", ""] + [f"- {'PASS' if r['passed'] else 'FAIL'}: {r['name']}" for r in results]
        log += ["", "## Reconciliation", "", "```json", __import__("json").dumps(rec, indent=1), "```", ""]
        return (self.result("delivery-test", "test_sale_to_delivery", "\n".join(md), data={"tests": results, "reconciliation": rec}),
                "\n".join(log))
