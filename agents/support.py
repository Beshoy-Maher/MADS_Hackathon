"""Phase 6, step 1: support kit (FAQ, reply drafts, escalation rules).

Replies are drafts for the founder. Refunds are queued for founder approval,
never issued by the agent.
"""
from __future__ import annotations

from agents.base import Agent, StepResult, footer


class Support(Agent):
    role = "support"

    def run_step(self, spec: dict, pricing: dict) -> StepResult:
        name = self.brief.get("founder_name", "the founder")
        fallback = "\n".join([
            "## FAQ",
            f"- **What format is it?** {spec.get('format', 'A digital download')}. It opens on any device.",
            "- **I didn't get my download link.** Check spam first; reply to your receipt and we'll resend it.",
            f"- **Can I get a refund?** Yes, within {pricing.get('refund_days', 14)} days, no questions asked. Access is removed after the refund.",
            "- **Will this guarantee a result?** No. It gives you a method and templates; results depend on you.", "",
            "## Reply drafts (founder reviews before sending)",
            f"- Missing link: 'Hi, sorry about that! Here is your link again: <link>. {name}'",
            f"- Refund request: 'Hi, no problem. I've started your refund; you'll see it within a few days. {name}' (refund queued for founder approval)",
            "- Feature idea: 'Thanks, that's useful. I've noted it for the next update.'", "",
            "## Escalation rules",
            "- Payment problems, refunds and anything legal go to the founder. The agent never decides them.",
            "- Health, money or legal questions from buyers: reply that the product does not give that advice.",
        ])
        task = (f"Product: {spec.get('product_name')} ({spec.get('format')}), modules {[m['title'] for m in spec.get('modules', [])]}.\n"
                f"Refund: {pricing.get('refund_window_text')}\nWrite a support kit: '## FAQ' (5 Q&As), '## Reply drafts (founder reviews before sending)' "
                f"(3 short replies signed by {name}), '## Escalation rules' (refunds/payments/legal always go to the founder). Max 280 words.")
        body = self.write(task, fallback, max_tokens=700)
        return self.result("support", "write_support_kit", f"# Phase 6, step 1: Support kit\n\n{body}\n{footer(self.model)}")
