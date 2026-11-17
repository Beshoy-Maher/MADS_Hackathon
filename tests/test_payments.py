import pytest

import approval
import refunds
from delivery import Delivery
from payments import MockProvider
from reconcile import reconcile
from webhooks import WebhookHandler


def setup():
    p, d = MockProvider(), Delivery()
    return p, d, WebhookHandler(p, d)


def test_payment_delivers_once_even_if_webhook_repeats():
    p, d, w = setup()
    o = p.create_checkout("kit", 17, "a@example.com")
    body, sig = p.pay(o["order_id"])
    assert w.handle(body, sig) == "delivered"
    assert w.handle(body, sig) == "duplicate_ignored"
    assert len(d.sent) == 1


def test_bad_signature_rejected():
    p, d, w = setup()
    o = p.create_checkout("kit", 17, "a@example.com")
    body, _ = p.pay(o["order_id"])
    assert w.handle(body, "f" * 64) == "rejected"
    assert not d.grants


def test_refund_needs_founder_and_revokes_access(tmp_path):
    p, d, w = setup()
    run = {"id": "r", "dir": str(tmp_path), "outbound": []}
    o = p.create_checkout("kit", 17, "a@example.com")
    w.handle(*p.pay(o["order_id"]))
    pay_id = next(iter(p.payments))
    item = refunds.request_refund(run, pay_id, "asked")
    with pytest.raises(approval.ApprovalRequired):
        refunds.execute_refund(run, item["id"], p, w)
    assert p.payments[pay_id]["status"] == "succeeded"
    approval.decide(run, item["id"], True, "founder")
    assert refunds.execute_refund(run, item["id"], p, w) == "revoked"
    assert not d.can_download(d.grants[o["order_id"]]["token"])
    p.payout()
    rec = reconcile(p, d)
    assert rec["matched"] and rec["payout"] == round(17 - (17 * 0.029 + 0.30) - 17, 2)
