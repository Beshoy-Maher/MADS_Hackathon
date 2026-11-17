"""Support: FAQ built from the policies and the product (no model needed)."""


def kit(brief, price, modules):
    mods = "\n".join(f"- {m['title']}" for m in modules)
    return f"""# Phase 6 Step 2: Support kit

## FAQ
**What do I get?** A Markdown toolkit with these parts:
{mods}

**How much?** ${price}, one time.

**Can I get a refund?** Yes, within 14 days. The founder approves it, and your download link stops working.

**Do you store my card?** No. The payment provider handles the card.

## Escalation
Anything about money, refunds or account access goes to the founder. The system drafts replies; sending one needs founder approval.
"""
