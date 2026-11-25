"""Sale to cash (MOCKED): payment -> delivery, idempotency, refunds revoke access, reconciliation."""
from agents.launcher import sale_to_cash_test


def test_sale_to_cash_flow_passes_every_check():
    results, store, extra = sale_to_cash_test("Test product", 12.0)
    failed = [r["name"] for r in results if not r["passed"]]
    assert not failed, failed
    assert len(store.deliveries) == 2  # two buyers, no double delivery
    assert extra["reconciliation"]["balanced"]
