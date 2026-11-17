"""Phase 2, step 1 (Core step): design the business with a Lean Canvas."""
from __future__ import annotations

from agents.base import Agent, StepResult, brief_summary, budget_text, footer, hours_text

BOXES = ["problem", "customer_segments", "unique_value_proposition", "solution", "channels",
         "revenue_streams", "cost_structure", "key_metrics", "unfair_advantage"]


class Strategist(Agent):
    role = "strategist"
    check_claims = True

    def run_step(self, candidate: dict, market: dict, score: dict) -> StepResult:
        existing = market.get("existing", [])
        fb = {
            "problem": [candidate.get("problem") or "ASSUMPTION: problem not stated",
                        "Existing free material is scattered and not tailored (ASSUMPTION)"],
            "customer_segments": [self.brief.get("target_market") or "ASSUMPTION"],
            "unique_value_proposition": f"{candidate['title']}: a focused, ready-to-use digital product.",
            "solution": [candidate.get("format") or "digital guide/toolkit", "Worked examples", "Clear user guide"],
            "channels": [f"Communities where the evidence came from: {', '.join(list(market.get('communities', {}))[:3]) or 'ASSUMPTION'}",
                         "Founder's own network", "Landing page with waitlist"],
            "revenue_streams": ["One-time purchase of the digital product (price set in phase 4)"],
            "cost_structure": [f"Founder time: {hours_text(self.brief)}",
                               f"Money: {budget_text(self.brief)} (hosting/store fees)", "Model cost: $0 (local open-weight model)"],
            "key_metrics": ["Waitlist sign-ups vs. pre-set target", "Landing-page conversion", "Refund rate", "Support questions per buyer"],
            "unfair_advantage": [f"Founder skills: {', '.join(self.brief.get('skills') or []) or 'ASSUMPTION'}"],
        }
        task = (f"Founder brief:\n{brief_summary(self.brief)}\nProduct: {candidate['title']}\nProblem: {candidate.get('problem', '')}\n"
                f"Evidence scores: demand {score.get('demand_score')}, pay signals {score.get('willingness_to_pay')}, competition {score.get('competition')}.\n"
                f"Existing solutions: {existing[:4]}\n\n"
                "Fill a Lean Canvas. Keys: " + ", ".join(BOXES) + ". Each value is a list of 1-3 short strings "
                "(unique_value_proposition is one string). Mark guesses with 'ASSUMPTION:'. No income promises. "
                "revenue_streams is exactly one item: a one-time purchase of the digital product (no subscription, ads or affiliate links). "
                "channels: only the communities listed in the evidence and the founder's own network.")
        data = self.ask_json(task, fb, max_tokens=900)
        canvas = {k: data.get(k) or fb[k] for k in BOXES}
        complete = all(canvas[k] for k in BOXES)
        md = [f"# Phase 2, step 1: Lean Canvas for '{candidate['title']}'", ""]
        for k in BOXES:
            v = canvas[k]
            md.append(f"## {k.replace('_', ' ').title()}")
            md += ([f"- {x}" for x in v] if isinstance(v, list) else [str(v)]) + [""]
        md += ["Riskiest assumption to test next: that enough of the target customers will leave their email for this "
               "product (tested in step 2 and 3 with a landing page).", footer(self.model, existing)]
        return self.result("lean-canvas", "design_business_lean_canvas", "\n".join(md),
                           data={"canvas": canvas, "complete": complete}, sources=existing)
