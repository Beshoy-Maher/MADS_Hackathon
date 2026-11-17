"""Demand test plan (phase 2, step 3), metrics and the persevere-or-pivot memo (phase 6).

The analyst only reports numbers that exist: real waitlist sign-ups collected
by the app, and real orders. MOCKED test orders are shown separately and
never counted as real.
"""
from __future__ import annotations

import gates
from agents.base import Agent, StepResult, brief_summary, community_places, footer


class Analyst(Agent):
    role = "analyst"

    def demand_plan(self, candidate: dict, communities: dict, waitlist: dict) -> StepResult:
        t = gates.THRESHOLDS["demand"]
        target = int(self.brief.get("waitlist_target") or t["default_waitlist_target"])
        window = int(self.brief.get("waitlist_window_days") or t["default_window_days"])
        channels = community_places(communities) or ["founder's own network (ASSUMPTION)"]
        fallback = "\n".join([f"- Share the landing page personally in: {', '.join(channels)} (following each community's rules).",
                              "- Ask the people interviewed in phase 1 whether they want to be notified.",
                              "- One honest post per channel; no paid ads (budget is kept for the product)."])
        task = (f"Founder brief:\n{brief_summary(self.brief)}\nProduct: {candidate['title']}\nChannels found in research: {channels}\n"
                "Write 3-5 bullets: how the founder can bring real, relevant visitors to the waitlist page in 14 days, without "
                "spam, paid ads or fake accounts. One short sentence per bullet. Do not write post titles, links or sources, and do "
                "not call the product free. Markdown bullets only.")
        plan = self.write(task, fallback, max_tokens=400)
        from tools import claims
        plan, _ = claims.check(plan, self.evidence_urls())
        # A bullet that still leans on a link the checker removed says nothing the founder can use.
        plan = "\n".join(l for l in plan.splitlines() if "(unverified link removed)" not in l) or fallback
        signups = waitlist.get("count")
        md = [f"# Phase 2, step 3: Demand test for '{candidate['title']}'", "",
              "## Pre-registered target (set before any data comes in)",
              f"- Target: **{target} real waitlist sign-ups in {window} days**.",
              f"- Below {int(t['pivot_below_share'] * 100)}% of target at the end of the window: recommend pivot or stop.",
              "- Only sign-ups with consent, through the real form, count.", "", "## How to get real visitors", plan, "",
              "## Result so far",
              (f"- Real sign-ups recorded: **{signups}** (from the app's waitlist endpoint)." if signups is not None else
               "- Real sign-ups recorded: **none yet**. The landing page has not been published, so the test has not started. "
               "Waitlist collection is STUBBED in this demo (no public hosting)."),
              footer(self.model)]
        return self.result("demand-test", "plan_demand_test", "\n".join(md),
                           data={"target": target, "window_days": window, "signups": signups, "days_elapsed": waitlist.get("days_elapsed")})

    def metrics(self, real_orders: int, mock_test: dict, waitlist: dict) -> StepResult:
        rec = mock_test.get("reconciliation", {})
        md = ["# Phase 6, step 2: Metrics", "",
              "| Metric | Real value | Source |", "|---|---|---|",
              f"| Waitlist sign-ups | {waitlist.get('count') if waitlist.get('count') is not None else 'not measured yet'} | app waitlist endpoint |",
              f"| Real paid orders | {real_orders} | payment provider (none connected: MOCKED) |",
              "| Refund rate | n/a (no real orders) | - |",
              "| Support tickets per buyer | n/a (no real buyers) | - |", "",
              "## MOCKED test numbers (not real, shown for transparency only)",
              f"- Test orders: {rec.get('orders', 0)}, gross ${rec.get('gross', 0):.2f}, refunded ${rec.get('refunded', 0):.2f}. "
              "These come from the sale-to-cash test and are excluded from every decision.", "",
              "## What we will track once real",
              "- Visitor to sign-up rate, sign-up to buyer rate, refund rate, support questions per buyer, module completion (self-reported).",
              footer(None)]
        return self.result("metrics", "report_metrics", "\n".join(md), data={"real_orders": real_orders})

    def pivot_memo(self, candidate: dict, gate: gates.GateResult, history: list[dict]) -> StepResult:
        hist = "\n".join(f"- Phase {g['phase']} {g['gate']}: system said {g['recommendation'].upper()}, founder chose "
                         f"{(g.get('founder_decision') or 'pending').upper()}" for g in history)
        fallback = (f"**Recommendation: {gate.recommendation.upper()}.** " + " ".join(gate.reasons) +
                    "\n\nWhat would change our mind: 10+ real buyers with a refund rate under 15%, or repeated unprompted requests "
                    "for the product in support and interviews.")
        task = (f"Product: {candidate['title']}\nGate history:\n{hist}\nCurrent recommendation: {gate.recommendation} because {gate.reasons}\n"
                "Write a persevere-or-pivot memo (max 200 words): the recommendation, the evidence for and against, what would "
                "change the decision, and the date-free next review trigger. Honest; do not spin weak data; no income projections.")
        body = self.write(task, fallback, max_tokens=500)
        from tools import claims
        body, _ = claims.check(body, self.evidence_urls())
        md = [f"# Phase 6, step 3: Persevere-or-pivot memo for '{candidate['title']}'", "", "## Decision history", hist, "", "## Memo", body,
              footer(self.model)]
        return self.result("persevere-or-pivot", "write_pivot_memo", "\n".join(md))
