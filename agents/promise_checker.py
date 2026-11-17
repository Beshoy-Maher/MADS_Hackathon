"""Phase 5, step 4: the promise checker. Does what we sell match what we built?

The store page and launch posts are written from the plan (the Lean Canvas);
the product is written later, in Phase 3. The two can drift apart. Before the
founder approves publishing, every promise on the page and in the posts is
checked against the product, the price, the refund policy and the delivery test.

Each promise gets one verdict:

* kept: proven by code (a count, the price, the refund days, the delivery test)
  or by a passage of the product. The model may only offer that passage; code
  checks it is really in the product, word for word, or it does not count.
* broken: code found a contradiction (wrong number of modules, a dollar amount
  that is not the price, wrong refund days, "free" for a paid product, a
  delivery promise the delivery test does not support). Only code can mark a
  promise broken. approval.py refuses to publish an item with a broken promise.
* unverifiable: no proof found. The founder confirms, rewords or removes it.

The checker never rewrites the page and never changes a gate.
"""
from __future__ import annotations

import html
import re

import approval
import decision_log
from agents.base import Agent, StepResult, footer

KEPT, BROKEN, UNVERIFIABLE = "kept", "broken", "unverifiable"
MAX_PRODUCT_CHARS = 14000  # what the model sees; code checks quotes against the whole product
MIN_QUOTE_WORDS = 6

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "hundred": 100}
NUM = r"(\d{1,4}|" + "|".join(NUMBER_WORDS) + r")"
MODULE_COUNT = re.compile(rf"\b{NUM}\+?\s+(?:[a-z-]+\s+)?(modules?|chapters?|lessons?|units?)\b", re.IGNORECASE)
ITEM_COUNT = re.compile(rf"\b{NUM}\+?\s+(?:[a-z-]+\s+)?(questions?|exercises?|examples?|worksheets?|templates?|challenges?|problems?|queries)\b",
                        re.IGNORECASE)
MONEY = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")
REFUND_DAYS = re.compile(r"\b(\d{1,3})[- ]day\b[^.]{0,30}\brefund|\brefund[^.]{0,30}\b(\d{1,3})\s+days\b", re.IGNORECASE)
FREE = re.compile(r"\b(?:it'?s|is|for|completely|totally|100%|absolutely)\s+free\b|\bfree\s+(?:download|product|workbook|guide|"
                  r"pack|course|ebook|resource|copy|access)\b|\bat no cost\b|\bfree of charge\b", re.IGNORECASE)
DELIVERY = re.compile(r"\binstant(?:ly)? (?:download|access|delivery)\b|\bdownload (?:right )?after payment\b|"
                      r"\bdelivered (?:instantly|automatically|immediately|right away)\b|\bimmediate (?:download|access)\b", re.IGNORECASE)
FEATURE_CUE = re.compile(r"\b(includ\w*|cover\w*|contain\w*|you(?:'ll| will)? (?:get|learn|find|practi[cs]e)|inside|every|each|"
                         r"step-by-step|solutions?|answers?|exercises?|examples?|questions?|worksheets?|checklists?|templates?|"
                         r"modules?|queries|practice|walkthroughs?|explained|explanations?)\b", re.IGNORECASE)


def _n(word: str) -> int:
    return int(word) if word.isdigit() else NUMBER_WORDS[word.lower()]


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9$%']+", text.lower()))


def sentences(text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 3]


def module_count(product_md: str) -> int:
    return len(re.findall(r"^## Module \d+:", product_md, flags=re.MULTILINE))


def labelled_items(product_md: str, noun: str) -> int:
    """Items the product labels as such: 'Question 3:', '*Exercise:*', '### Example 2'. Plain mentions are not counted."""
    sing = {"queries": "query"}.get(noun.lower(), noun.lower().rstrip("s"))
    return len(re.findall(rf"^[\s#>*_\-]*(?:\d+[.)]\s*)?{sing}\b\s*\d*\s*[:.)*_]", product_md, flags=re.IGNORECASE | re.MULTILINE))


def quote_in_product(quote: str, product_md: str) -> bool:
    q = _norm(quote)
    return len(q.split()) >= MIN_QUOTE_WORDS and q in _norm(product_md)


def code_verdict(claim: str, product_md: str, price: float | None, refund_days: int | None, delivery_ok: bool) -> dict | None:
    """What code alone can decide about one promise. None: code cannot decide, a quote is needed."""
    findings = []
    for m in MONEY.finditer(claim):
        amount = float(m.group(1))
        if price is not None and abs(amount - float(price)) > 0.005:
            return {"verdict": BROKEN, "proof": f"states ${m.group(1)}, but the price set in Phase 4 is ${price}"}
        findings.append(f"price ${price} matches Phase 4")
    m = REFUND_DAYS.search(claim)
    if m and refund_days is not None:
        days = int(m.group(1) or m.group(2))
        if days != int(refund_days):
            return {"verdict": BROKEN, "proof": f"states a {days}-day refund, but the policy and refunds.py give {refund_days} days"}
        findings.append(f"{days}-day refund matches the policy")
    if FREE.search(claim) and price:
        return {"verdict": BROKEN, "proof": f"calls the product free, but it is sold at ${price}"}
    if DELIVERY.search(claim):
        if not delivery_ok:
            return {"verdict": BROKEN, "proof": "promises delivery after payment, but the delivery test did not pass"}
        findings.append("delivery after payment passes the MOCKED sale-to-cash test")
    for m in MODULE_COUNT.finditer(claim):
        claimed, have = _n(m.group(1)), module_count(product_md)
        if claimed != have:
            return {"verdict": BROKEN, "proof": f"promises {claimed} {m.group(2)}, the product has {have} modules"}
        findings.append(f"{have} modules, as promised")
    for m in ITEM_COUNT.finditer(claim):
        claimed, have = _n(m.group(1)), labelled_items(product_md, m.group(2))
        if have >= claimed:
            findings.append(f"{have} labelled {m.group(2)} found")
        else:
            return {"verdict": UNVERIFIABLE, "proof": f"promises {claimed} {m.group(2)}; only {have} are labelled as such in the product. "
                    "Count them yourself, then confirm or change the number"}
    return {"verdict": KEPT, "proof": "; ".join(findings)} if findings else None


def store_page_claims(copy: dict, pricing: dict) -> list[str]:
    out = [str(copy.get("subheadline", ""))] + [str(b) for b in copy.get("bullets", [])]
    out += [f"${pricing.get('price_usd')}", "Instant download after payment.", str(pricing.get("refund_window_text", ""))]
    return [c.strip() for c in out if c and c.strip()]


def post_claims(text: str) -> list[str]:
    return [s for s in sentences(text) if MONEY.search(s) or FREE.search(s) or REFUND_DAYS.search(s) or DELIVERY.search(s)
            or MODULE_COUNT.search(s) or ITEM_COUNT.search(s) or FEATURE_CUE.search(s)]


class PromiseChecker(Agent):
    role = "promise_checker"

    def _quotes(self, claims: list[str], product_md: str) -> dict[int, str]:
        """Ask the model for one proving quote per promise. Returns only the quotes found in the product."""
        if not claims:
            return {}
        listing = "\n".join(f"{i}. {c}" for i, c in enumerate(claims))
        task = (f"PRODUCT (as built):\n<<<\n{product_md[:MAX_PRODUCT_CHARS]}\n>>>\n\nPROMISES:\n{listing}\n\n"
                "For each promise, copy the passage of the product that proves it, word for word (at least 6 words), or \"\". "
                'JSON: {"proofs": [{"promise": <number>, "quote": "..."}]}')
        data = self.ask_json(task, {"proofs": []}, max_tokens=900)
        out = {}
        for p in data.get("proofs", []) if isinstance(data.get("proofs"), list) else []:
            try:
                i, q = int(p.get("promise")), str(p.get("quote") or "")
            except (TypeError, ValueError, AttributeError):
                continue
            if 0 <= i < len(claims) and quote_in_product(q, product_md):
                out[i] = q
        return out

    def run_step(self, product_md: str, store_page: StepResult, post_actions: list[dict], pricing: dict,
                 payment_tests: list[dict]) -> StepResult:
        price, refund_days = pricing.get("price_usd"), pricing.get("refund_days")
        by_name = {t["name"]: t["passed"] for t in payment_tests}
        delivery_ok = bool(by_name.get("payment_triggers_delivery")) and bool(by_name.get("paid_buyer_can_download"))
        items = [{"where": "store page", "action": store_page.data.get("publish_action"), "claim": c}
                 for c in store_page_claims(store_page.data.get("copy", {}), pricing)]
        for a in post_actions:
            items += [{"where": a["target"], "action": a["id"], "claim": c} for c in post_claims(a["payload"].get("text", ""))]
        need_quote = []
        for it in items:
            v = code_verdict(it["claim"], product_md, price, refund_days, delivery_ok)
            if v:
                it.update(v, by="code")
            else:
                need_quote.append(it)
        quotes = self._quotes([it["claim"] for it in need_quote], product_md)
        for i, it in enumerate(need_quote):
            if i in quotes:
                it.update(verdict=KEPT, proof=f'product says: "{quotes[i]}"', by="model quote, checked by code")
            else:
                it.update(verdict=UNVERIFIABLE, proof="no passage of the product proves it. Confirm, reword or remove it",
                          by="model found no quote" if self.model else "no model available to look for a quote")
        summary = self._attach(items)
        return self.result("promise-check", "check_promises", self._markdown(items, summary),
                           data={"items": items, "summary": summary})

    def _attach(self, items: list[dict]) -> dict:
        """Put each item's result on its approval request, so the founder sees it beside Approve / Reject."""
        summary = {}
        for it in items:
            s = summary.setdefault(it["action"], {KEPT: 0, BROKEN: 0, UNVERIFIABLE: 0, "broken_items": [], "unverifiable_items": []})
            s[it["verdict"]] += 1
            if it["verdict"] in (BROKEN, UNVERIFIABLE):
                s[f"{it['verdict']}_items"].append(f"{it['claim'][:160]} ({it['proof'][:160]})")
        for a in self.run.get("pending_actions", []):
            if a["id"] in summary:
                a["payload"]["promise_check"] = dict(summary[a["id"]], file="phase5_step4_promise-check.md")
                if summary[a["id"]][BROKEN]:
                    decision_log.log(self.role, "flag_broken_promise", run_id=self.run["id"], target=a["target"], action_id=a["id"],
                                     outcome="publishing blocked until fixed", detail="; ".join(summary[a["id"]]["broken_items"])[:200])
        return summary

    def _markdown(self, items: list[dict], summary: dict) -> str:
        total = {k: sum(1 for it in items if it["verdict"] == k) for k in (KEPT, BROKEN, UNVERIFIABLE)}
        md = ["# Phase 5, step 4: Promise check (does what we sell match what we built?)", "",
              f"**{len(items)} promises checked: {total[KEPT]} kept, {total[BROKEN]} broken, {total[UNVERIFIABLE]} unverifiable.**", "",
              "Every promise on the store page and in the launch posts is checked against the product built in Phase 3, the price "
              "and refund policy from Phase 4 and the delivery test in step 3. Counts, prices, refund days and delivery are checked "
              "by code. For other promises the model may only quote the product; code keeps the quote only if it is in the product "
              "word for word. Only code can mark a promise broken, and an item with a broken promise cannot be approved for "
              "publishing (`approval.py`). Unverifiable promises are for you to confirm, reword or remove.", "",
              "| Where | Promise | Verdict | Proof | Checked by |", "|---|---|---|---|---|"]
        cell = lambda t: html.escape(str(t)).replace("|", "\\|").replace("\n", " ")
        for it in items:
            md.append(f"| {cell(it['where'])} | {cell(it['claim'][:200])} | **{it['verdict'].upper()}** | {cell(it['proof'][:240])} | {cell(it['by'])} |")
        blocked = [a for a in self.run.get("pending_actions", []) if summary.get(a["id"], {}).get(BROKEN)]
        md += ["", "## What happens next",
               (f"- {len(blocked)} item(s) cannot be approved until the broken promise is fixed: "
                + ", ".join(a["target"] for a in blocked) + ". Reject them, then repeat Phase 5 with a note on what to change.")
               if blocked else "- No broken promise: every item can be approved or rejected by you.",
               "- The checker does not rewrite the page or change the launch gate.", footer(self.model)]
        return "\n".join(md)

