"""Policy writer: terms, refund and privacy drafts (template; review before use)."""


def policies(brief, price):
    data = {"refund_days": 14, "stores_cards": False}
    md = f"""# Phase 4 Step 2: Policies (drafts for the founder to review)

## Terms
- {brief['product_name']} is a digital download for personal or team use. Price ${price}, one-time.
- No results or income are promised. The toolkit is a set of checklists and templates.

## Refunds
- Full refund within {data['refund_days']} days, no questions. A refund revokes download access.
- Refunds are requested by the customer and approved by the founder; the system never refunds by itself.

## Privacy
- We keep the buyer's email and order id to deliver the download.
- Card details are handled by the payment provider. We never see or store card numbers or passwords.

_Template drafts, not legal advice._
"""
    return data, md
