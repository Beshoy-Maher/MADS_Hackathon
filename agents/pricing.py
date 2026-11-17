"""Phase 4, step 1 (Core step): set the price.

Price anchors come from prices seen in the cited evidence. If none are found
the anchor is a labelled ASSUMPTION. The final price is a rule, not a vibe:
median of sourced comparables x 0.8 (a new, unknown product), clamped to
$5-$49, and lowered for founders whose values put affordability first.
"""
from __future__ import annotations

import re
import statistics

from tools.text import drop_sentences_with, wrong_money

from agents.base import Agent, StepResult, brief_summary, footer

PRICE_RX = re.compile(r"\$\s?(\d{1,3}(?:\.\d{2})?)\b")
DEFAULTS = {"template": 15, "checklist": 12, "guide": 12, "course": 29, "toolkit": 19, "workbook": 15}
REFUND_DAYS = 14


def find_comparables(evidence: list[dict]) -> list[dict]:
    out = []
    for e in evidence:
        for m in PRICE_RX.finditer(f"{e.get('title', '')} {e.get('snippet', '')}"):
            v = float(m.group(1))
            if 2 <= v <= 300:
                out.append({"price": v, "url": e["url"], "title": e["title"][:90]})
    return out


class Pricing(Agent):
    role = "pricing"

    def run_step(self, candidate: dict, spec: dict) -> StepResult:
        comps = find_comparables(candidate.get("evidence", []))
        fmt = (spec.get("format") or candidate.get("format") or "").lower()
        if comps:
            anchor = statistics.median(c["price"] for c in comps)
            anchor_note = f"median of {len(comps)} sourced price mention(s): ${anchor:.2f}"
        else:
            anchor = next((v for k, v in DEFAULTS.items() if k in fmt), 15)
            anchor_note = f"ASSUMPTION: no sourced price found; typical price for a small {fmt or 'digital product'} assumed at ${anchor}"
        price = anchor * 0.8 if comps else anchor
        values = " ".join(self.brief.get("values") or []).lower()
        affordable = any(w in values for w in ("afford", "cheap", "access", "students", "fair"))
        if affordable:
            price *= 0.8
        price = max(5, min(49, round(price)))
        price = price - 0.01 if price > 5 else price  # $X.99 style is fine; no fake "was $Y" anchors
        price = round(price, 2)
        fallback = (f"Start at **${price}** as a one-time purchase. This is a starting point to test, not a final answer. "
                    "If fewer than 2% of landing-page visitors buy after 100+ visits, test a lower price or a smaller first product. "
                    "If almost everyone who visits buys, the price is probably too low. Offer a fair refund so buyers carry no risk.")
        task = (f"Founder brief:\n{brief_summary(self.brief)}\nProduct: {spec.get('product_name')} ({spec.get('format')})\n"
                f"Price anchor: {anchor_note}. Steps applied: {'x0.8 new-product discount, ' if comps else ''}{'x0.8 affordability, ' if affordable else ''}clamp $5-$49. Rule-based price: ${price}.\nWrite a short pricing rationale (max 90 words): why this price fits this founder "
                "and these buyers, and why there are no discounts with fake deadlines. "
                "Do not change the price. Do not state any number other than the price and the anchor. No income projections.")
        rationale = self.write(task, fallback, max_tokens=300)
        # The price is a rule, not the model's to restate: a sentence with any other dollar amount is dropped.
        rationale = drop_sentences_with(rationale, wrong_money(rationale, [price, anchor])) or fallback
        # The next price test is a rule too, fixed before any sales data exists (a small model invents thresholds otherwise).
        lower = max(5, round(price * 0.8)) - (0.01 if price > 6 else 0)
        experiment = (f"After the first 100 real store-page visits, compare purchases per 100 visitors. If fewer than 2 in 100 buy, "
                      f"test ${lower:.2f} for the next 100 visits and keep whichever price sells more per 100 visitors. "
                      "The rule is fixed now, before any sales data exists. Visit and purchase counts must be real.")
        refund_text = f"{REFUND_DAYS}-day refund, no questions asked; download access is removed after a refund."
        md = [f"# Phase 4, step 1: Pricing for '{spec.get('product_name')}'", "",
              f"**Price: ${price} (USD), one-time.**", "", "## Anchor", f"- {anchor_note}"]
        md += [f"- [{c['title']}]({c['url']}): ${c['price']}" for c in comps[:6]]
        md += ["", "## Rule", f"- New product discount: {'x0.8 on the sourced anchor' if comps else 'not applied (anchor is an ASSUMPTION, not a sourced price)'}.",
               f"- Affordability value in brief: {'yes, x0.8' if affordable else 'no'}.", "- Clamp: $5 to $49.", "",
               "## Rationale", rationale, "", "## Next price test (pre-set rule)", f"- {experiment}", "", "## Refunds", f"- {refund_text}", "",
               "## What the system will not do", "- No fake 'was $99' anchors, no countdown discounts, no income estimates.",
               footer(self.model, [c["url"] for c in comps])]
        return self.result("pricing", "set_price", "\n".join(md),
                           data={"price_usd": price, "anchor": anchor_note, "refund_days": REFUND_DAYS, "refund_window_text": refund_text},
                           sources=[c["url"] for c in comps])
