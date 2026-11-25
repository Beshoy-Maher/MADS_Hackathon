# Launcher agent (Phase 5, step 3: deliver automatically)

Runs the sale-to-cash flow against the MOCKED payment provider and checks:
payment triggers delivery; duplicate and retried webhooks never deliver twice; forged webhooks are rejected;
unpaid orders cannot download; refunds need the founder's approval and revoke access; orders, payments, fees and payouts reconcile.
