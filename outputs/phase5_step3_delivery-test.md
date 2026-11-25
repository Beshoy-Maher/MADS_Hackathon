# Phase 5, step 3: Automatic delivery test (11/11 passed)

Payment provider: **MOCKED** (no real payment service, no real money, no card data). Delivery emails: **STUBBED** (recorded, not sent).

| Check | Result | Detail |
|---|---|---|
| checkout_creates_pending_order_without_access | PASS |  |
| unpaid_order_cannot_be_delivered | PASS | PermissionError raised |
| payment_triggers_delivery | PASS | delivered |
| duplicate_event_is_ignored | PASS | duplicate |
| retry_with_new_event_id_does_not_double_deliver | PASS | deliveries=1 |
| forged_webhook_rejected | PASS |  |
| paid_buyer_can_download | PASS |  |
| refund_blocked_without_founder_approval | PASS | ApprovalRequired raised |
| agent_cannot_approve_its_own_refund | PASS |  |
| refund_revokes_access | PASS | revoked |
| books_reconcile_orders_payments_fees_payouts | PASS | balanced |

## Reconciliation (MOCKED amounts)

- Orders: 2
- Gross charged: $23.98
- Refunded: $11.99
- Fees (ASSUMPTION: 2.9% + $0.30): $1.30
- Payouts: $10.69
- Expected net: $10.69
- Balanced: yes