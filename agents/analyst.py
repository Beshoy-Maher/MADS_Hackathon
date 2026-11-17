"""Demand test plan (phase 2, step 3), metrics and the persevere-or-pivot memo (phase 6).

The analyst only reports numbers that exist: real waitlist sign-ups collected
by the app, and real orders. MOCKED test orders are shown separately and
never counted as real.
"""
from __future__ import annotations

import re

import gates
from agents.base import Agent, StepResult, brief_summary, community_places, footer


# Sites that forbid self-promotion, and someone else's repository (GitHub issues and discussions).
NO_PROMOTION = re.compile(r"\b(stack ?overflow|stack ?exchange|stackexchange|github (discussions?|issues?|repos?))\b", re.IGNORECASE)


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
        # Only places found in the research, and never a site that forbids self-promotion (Stack Overflow and Stack Exchange).
        allowed = {c.lower() for c in channels}
        def fits(line: str) -> bool:
            if NO_PROMOTION.search(line):
                return False
            subs = {m.lower() for m in re.findall(r"\br/\w+", line)}
            return not subs or subs <= allowed
        plan = "\n".join(l for l in plan.splitlines() if fits(l)) or fallback
        # No covert promotion, fake urgency or speaking as someone the founder is not.
        from tools import honesty
        plan = honesty.drop_covert_lines(plan)[0]
        plan = "\n".join(l for l in plan.splitlines() if not honesty.unbacked_experience(l, self.brief)
                         and not honesty.unresearched_places(l, allowed)).strip() or fallback
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

    def pivot_memo(self, candidate: dict, gate: gates.GateResult, history: list[dict], real_buyers: int = 0,
                   refund_rate: float | None = None, waitlist: dict | None = None, mock_sales: dict | None = None) -> StepResult:
        """The two evidence lists are built by code from the facts; the model writes only the short reasoning paragraph,
        with no numbers (a sentence with a digit is dropped)."""
        hist = "\n".join(f"- Phase {g['phase']} {g['gate']}: system said {g['recommendation'].upper()}, founder chose "
                         f"{(g.get('founder_decision') or 'pending').upper()}" for g in history)
        ev_for, ev_against = memo_evidence(history, real_buyers, refund_rate, (waitlist or {}).get("count"))
        orders = ((mock_sales or {}).get("reconciliation") or {}).get("orders", 0)
        t = gates.THRESHOLDS["operate"]
        change = [f"- {t['min_real_buyers_for_decision']} or more real buyers, with a refund rate under {t['min_refund_rate_to_worry']:.0%}: "
                  "the operate gate can then recommend persevering (or a pivot, if refunds are high).",
                  f"- Review again {t['review_after_days']} days after the store page is published, with the real numbers."]
        fallback = " ".join(gate.reasons)
        task = (f"Product: {candidate['title']}\nGate history:\n{hist}\nCurrent recommendation: {gate.recommendation}\n"
                "Evidence for:\n" + "\n".join(f"- {x}" for x in ev_for or ["(none)"]) +
                "\nEvidence against:\n" + "\n".join(f"- {x}" for x in ev_against or ["(none)"]) +
                "\n\nThe two lists above are already in the memo. Write ONLY the short reasoning paragraph (3-5 sentences, plain "
                "prose, no heading, no list): why this recommendation follows from that evidence, and what the founder should do "
                "next. Write it without any digits: do not restate any number or count, do not add evidence that is not listed, "
                "do not spin weak data, no income projections.")
        body = self.write(task, fallback, max_tokens=300)
        from tools import honesty
        body = honesty.clean_memo(reasoning_only(body) or "", gate.recommendation) or fallback
        from tools import claims
        body, _ = claims.check(body, self.evidence_urls())
        md = [f"# Phase 6, step 3: Persevere-or-pivot memo for '{candidate['title']}'", "",
              f"**Recommendation: {gate.recommendation.upper()}** (operate gate, computed by code). " + " ".join(gate.reasons), "",
              "## Decision history", hist, "",
              "## Evidence for", *([f"- {x}" for x in ev_for] or ["- Nothing yet."]), "",
              "## Evidence against", *([f"- {x}" for x in ev_against] or ["- Nothing recorded."]), "",
              f"Both lists are built by code from the gate history and the real numbers. MOCKED test orders ({orders}) are excluded.", "",
              "## Reasoning", body, "",
              "## What would change the decision", *change,
              footer(self.model)]
        return self.result("persevere-or-pivot", "write_pivot_memo", "\n".join(md))


# A statement that something is missing, zero or not measured is never evidence for.
MISSING = re.compile(r"(^|\s)(0|zero|no|none|nothing|missing|n/a)(\s|$|[.,;:])|\bnot (yet |been )?(measured|measurable|published|"
                     r"connected|documented|available|recorded|started)\b|\bwithout\b", re.IGNORECASE)


def memo_evidence(history: list[dict], real_buyers: int, refund_rate: float | None, signups: int | None) -> tuple[list[str], list[str]]:
    """(evidence for, evidence against), from facts only: gate history and overrides, real buyers, real sign-ups, refund rate."""
    ev_for, ev_against = [], []
    t = gates.THRESHOLDS["operate"]
    for g in history:
        if g.get("phase") == 6 or not g.get("founder_decision"):
            continue
        rec, fd = g["recommendation"].upper(), g["founder_decision"].upper()
        where = f"Phase {g['phase']} {g['gate']}"
        if rec == "GO" and fd == "GO":
            ev_for.append(f"{where}: the system recommended GO and the founder agreed.")
        elif fd != rec:
            ev_against.append(f"{where}: the system recommended {rec}; the founder overrode it with {fd}.")
        else:
            ev_against.append(f"{where}: the system recommended {rec} and the founder agreed.")
    if real_buyers > 0:
        ev_for.append(f"{real_buyers} real buyer(s) paid through a connected payment provider.")
    else:
        ev_against.append("0 real buyers: no payment provider is connected (the sale-to-cash test is MOCKED).")
    if signups is None:
        ev_against.append("Real waitlist sign-ups: not measured (the landing page has not been published).")
    elif signups > 0:
        ev_for.append(f"{signups} real waitlist sign-up(s) through the landing-page form, with consent.")
    else:
        ev_against.append("0 real waitlist sign-ups through the landing-page form.")
    if refund_rate is None:
        ev_against.append("Refund rate: not measurable (no real orders).")
    elif refund_rate < t["min_refund_rate_to_worry"]:
        ev_for.append(f"Refund rate {refund_rate:.0%}, under the {t['min_refund_rate_to_worry']:.0%} threshold.")
    else:
        ev_against.append(f"Refund rate {refund_rate:.0%}, at or above the {t['min_refund_rate_to_worry']:.0%} threshold.")
    moved = [x for x in ev_for if MISSING.search(x)]
    return [x for x in ev_for if x not in moved], ev_against + moved


def reasoning_only(text: str) -> str:
    """The model's paragraph: no headings, no lists, no bold labels, and no sentence that states a number."""
    lines = [l.strip() for l in (text or "").splitlines()]
    prose = " ".join(l for l in lines if l and not re.match(r"^(#|[-*+]\s|\d+[.)]\s|\*\*[^*]+:\*\*\s*$)", l))
    prose = re.sub(r"\*\*([^*]+)\*\*", r"\1", prose)
    sentences = re.split(r"(?<=[.!?])\s+", prose)
    out = " ".join(s for s in sentences if s and not re.search(r"\d", s)).strip()
    # A dropped sentence can leave the next one starting with a link to it ("Despite this, ..."): that link goes.
    out = re.sub(r"^(despite this|however|still|yet|but|nevertheless|that said|even so|because of this|as a result),?\s+", "", out,
                 flags=re.IGNORECASE)
    return out[:1].upper() + out[1:]
