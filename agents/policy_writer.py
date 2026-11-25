"""Phase 4, step 2 (Core step): draft terms, privacy and refund policies.

These are DRAFTS from a template, clearly marked as not legal advice. The
refund terms match what refunds.py actually does (access revoked on refund).
"""
from __future__ import annotations

from agents.base import Agent, StepResult, DETERMINISTIC, footer


class PolicyWriter(Agent):
    role = "policy_writer"

    def run_step(self, spec: dict, pricing: dict) -> StepResult:
        seller = self.brief.get("founder_name", "the seller")
        product = spec.get("product_name", "the product")
        days = pricing.get("refund_days", 14)
        terms = "\n".join([
            "## Terms of sale (DRAFT)",
            f"1. {seller} sells '{product}', a digital product delivered as a download link after payment.",
            "2. Your purchase gives you a personal, non-transferable licence to use the product. You may not resell or share it publicly.",
            f"3. The price is the one shown at checkout (USD), currently ${pricing.get('price_usd')}. Taxes may apply depending on your country.",
            "4. The product is educational material. It does not promise any specific result, income or outcome.",
            "5. Payments are handled by a third-party payment provider. The seller never sees or stores your card number.",
            "6. If you have a problem, contact the seller by email first. We aim to reply within 2 working days.",
        ])
        privacy = "\n".join([
            "## Privacy notice (DRAFT)",
            "- What we collect: your email address (to deliver the product and answer support requests) and order details.",
            "- Waitlist: only people who tick the consent box are added. One email when the product is ready; unsubscribe any time.",
            "- What we never collect: passwords or card numbers. Payments are handled by the payment provider.",
            "- We do not sell or share your data. You can ask for a copy or deletion of your data at any time by email.",
            "- Data is kept for as long as needed to provide access and handle refunds, then deleted.",
        ])
        refund = "\n".join([
            "## Refund policy (DRAFT)",
            f"- You can ask for a full refund within {days} days of purchase, no questions asked.",
            "- After a refund is issued, your download access is removed.",
            "- Refunds are approved and issued by the seller personally through the payment provider. The system never moves money by itself.",
            "- Duplicate charges are refunded in full.",
        ])
        md = "\n\n".join([f"# Phase 4, step 2: Draft policies for '{product}'",
                          "**DRAFT generated from a template. This is not legal advice. Have it reviewed by a qualified person "
                          "for your country before taking real payments.**", terms, privacy, refund, footer(DETERMINISTIC)])
        return self.result("policies", "draft_policies", md, data={"refund_days": days, "complete": True})
