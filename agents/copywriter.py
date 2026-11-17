"""Copy for the landing page (phase 2), the store page and launch posts (phase 5).

Everything is scanned by the guardrails. Pages carry no testimonials, no
counters, no countdowns and no income claims. Publishing is an approval-gated,
STUBBED action.
"""
from __future__ import annotations

import re

import html

import approval
from tools.text import wrong_money
from agents.base import Agent, StepResult, brief_summary, footer, launch_places

PAGE_CSS = """body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:720px;margin:40px auto;padding:0 16px;color:#1d2433;line-height:1.55}
h1{font-size:2rem;line-height:1.2}.sub{font-size:1.15rem;color:#4a5568}.card{border:1px solid #e2e8f0;border-radius:12px;padding:16px 20px;margin:18px 0}
ul{padding-left:20px}button{background:#2d5bff;color:#fff;border:0;border-radius:8px;padding:10px 18px;font-size:1rem;cursor:pointer}
input[type=email]{padding:10px;border:1px solid #cbd5e0;border-radius:8px;width:60%}small{color:#718096}.price{font-size:1.6rem;font-weight:700}"""


def _li(items) -> str:
    return "\n".join(f"<li>{html.escape(str(i))}</li>" for i in items)


def whole_sentences(text: str, limit: int) -> str:
    """As many whole sentences as fit in `limit` characters; never a sentence cut in the middle.
    If the first sentence alone is longer, it is kept whole."""
    sents = [x for x in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if x]
    out = ""
    for x in sents:
        if out and len(out) + 1 + len(x) > limit:
            break
        out = f"{out} {x}".strip()
    return out


class Copywriter(Agent):
    role = "copywriter"

    def _copy(self, candidate: dict, canvas: dict, purpose: str) -> dict:
        fb = {
            "headline": candidate["title"][:90],
            "subheadline": whole_sentences(str(canvas.get("unique_value_proposition") or candidate.get("problem", "")), 160),
            "bullets": (canvas.get("solution") or ["Ready-to-use", "Worked examples", "Clear guide"])[:3],
            "who_for": self.brief.get("target_market", ""),
            "cta": "Join the early-access list" if purpose == "landing" else "Get the product",
        }
        task = (f"Founder brief:\n{brief_summary(self.brief)}\nProduct: {candidate['title']}\nProblem: {candidate.get('problem', '')}\n"
                f"Value proposition: {canvas.get('unique_value_proposition')}\n\nWrite {'landing page' if purpose == 'landing' else 'store page'} copy. "
                'JSON: {"headline": "...", "subheadline": "...", "bullets": ["...", "...", "..."], "who_for": "...", "cta": "..."}. '
                "Plain, honest, specific. No testimonials, no numbers of users, no urgency, no promises of results.")
        data = self.ask_json(task, fb, max_tokens=500)
        out = {k: data.get(k) or fb[k] for k in fb}
        if not isinstance(out["bullets"], list):
            out["bullets"] = fb["bullets"]
        # Scan every field. The page is read by visitors: a link that was never fetched becomes its plain text.
        from guardrails import scan_output
        from tools import claims
        allowed = self.evidence_urls()
        for k in ("headline", "subheadline", "who_for", "cta"):
            out[k], _ = claims.strip_unverified(str(out[k]), allowed)
            s = scan_output(str(out[k]))
            if s.violations:
                self.violations += s.violations
                out[k] = s.text or fb[k]
        clean_bullets = []
        for b in out["bullets"][:4]:
            s = scan_output(claims.strip_unverified(str(b), allowed)[0])
            self.violations += s.violations
            if s.text.strip():
                clean_bullets.append(s.text)
        out["bullets"] = clean_bullets or fb["bullets"]
        # Code, not the model, decides what the page may claim: counts and formats the product cannot back
        # ("15 questions", "PDF, 45 pages") and experience the brief does not state are removed.
        from tools import honesty
        removed = 0
        for k in ("headline", "subheadline", "who_for"):
            t, a = honesty.strip_counts(str(out[k]))
            t, b = honesty.strip_experience(t, self.brief)
            removed += a + b
            out[k] = t or honesty.strip_counts(str(fb[k]))[0]
        bullets = []
        for b0 in out["bullets"]:
            t, a = honesty.strip_counts(str(b0))
            t, b = honesty.strip_experience(t, self.brief)
            removed += a + b
            if t.strip():
                bullets.append(t)
        out["bullets"] = bullets or [honesty.strip_counts(str(x))[0] for x in fb["bullets"]]
        self.copy_removed = getattr(self, "copy_removed", 0) + removed
        return out

    def landing_page(self, candidate: dict, canvas: dict) -> StepResult:
        c = self._copy(candidate, canvas, "landing")
        # The product does not exist yet: the page offers a place on the list, never a download.
        c["cta"] = "Join the early-access list"
        run_id = self.run["id"]
        page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(c['headline'])}</title><style>{PAGE_CSS}</style></head>
<body>
<h1>{html.escape(c['headline'])}</h1>
<p class="sub">{html.escape(c['subheadline'])}</p>
<div class="card"><strong>What you get</strong><ul>{_li(c['bullets'])}</ul></div>
<p><strong>Who it is for:</strong> {html.escape(str(c['who_for']))}</p>
<div class="card">
<form method="post" action="/api/waitlist/{run_id}">
<p><strong>{html.escape(c['cta'])}</strong></p>
<input type="email" name="email" required placeholder="you@example.com">
<label><input type="checkbox" name="consent" value="yes" required> I agree to be emailed about this product. I can unsubscribe any time.</label>
<p><button type="submit">Notify me</button></p>
<small>The product is still being built. We'll email you once, when it is ready. No spam, no sharing your email.</small>
</form></div>
<p><small>Made by {html.escape(self.brief.get('founder_name', 'the founder'))}.</small></p>
</body></html>
"""
        act = approval.request_action(self.run, "publish", "landing page with waitlist",
                                      "Publish the landing page so real visitors can join the waitlist.", {"file": "phase2_step2_landing-page.html"},
                                      agent=self.role)
        return self.result("landing-page", "write_landing_page", page, ext="html", data={"copy": c, "publish_action": act["id"]})

    def store_page(self, candidate: dict, canvas: dict, pricing: dict, policies_file: str) -> StepResult:
        c = self._copy(candidate, canvas, "store")
        price = pricing.get("price_usd")
        # The button states what happens, nothing about pages or file formats.
        c["cta"] = "Buy and download"
        page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(c['headline'])}</title><style>{PAGE_CSS}</style></head>
<body>
<h1>{html.escape(c['headline'])}</h1>
<p class="sub">{html.escape(c['subheadline'])}</p>
<div class="card"><strong>What's inside</strong><ul>{_li(c['bullets'])}</ul></div>
<p><strong>Who it is for:</strong> {html.escape(str(c['who_for']))}</p>
<div class="card"><p class="price">${price}</p>
<p>One-time purchase. Instant download after payment. {html.escape(pricing.get('refund_window_text', '14-day refund, no questions asked.'))}</p>
<form method="post" action="/api/checkout/{self.run['id']}"><button type="submit">{html.escape(c['cta'])}</button></form>
<small>Checkout in this prototype is MOCKED: no real payment is taken.</small></div>
<p><small>Terms, privacy and refund policy: see {html.escape(policies_file)}. Sold by {html.escape(self.brief.get('founder_name', 'the founder'))}.</small></p>
</body></html>
"""
        act = approval.request_action(self.run, "publish", "store page", f"Publish the store page at ${price}.",
                                      {"file": "phase5_step1_store-page.html"}, agent=self.role)
        return self.result("store-page", "open_store_page", page, ext="html",
                           data={"copy": c, "publish_action": act["id"], "claims_removed_by_code": getattr(self, "copy_removed", 0)})

    def _one_post(self, place: str, candidate: dict, price: float | None, avoid: list[str] | None = None) -> str | None:
        """One post, written for this one community. None when no model answered: posts are never filled from a template."""
        import llm
        from guardrails import scan_output
        from tools import claims
        name = self.brief.get("founder_name", "the founder")
        rules = {"Hacker News (Show HN)": "Show HN rules: the title starts with 'Show HN:', the text says what you made and why, "
                                         "plainly, for a technical audience, and invites criticism. No marketing language."}
        task = (f"Founder brief:\n{brief_summary(self.brief)}\nProduct: {candidate['title']}\nFormat: {candidate.get('format', '')}\n"
                f"Facts: it is a paid digital download{f' at ${price}' if price else ''}, not free and not open source.\n\n"
                f"Write ONE short launch post (60-120 words) for {place} only. {rules.get(place, 'Follow that community’s rules for sharing your own work.')} "
                f"Write it as {name}, in first person, in their own plain voice: why they made it, from their own skills and "
                "experience in the brief, what is inside, and one specific question asking for feedback. Your own sentences: do not "
                "copy the problem statement or the brief word for word, no greeting formula like 'Hi all', no hype, no urgency, "
                "no claims of results, no statistics, no links. Do not state how many questions, modules, templates or pages "
                "it has, and claim only the experience the brief states: do not say you have seen, encountered or used these questions, "
                "or what you wished for when starting out. Plain text only, no heading.")
        if avoid:
            task += "\n\nThese sentences are already used in another post; do not use them or anything close to them:\n" + "\n".join(f"- {a}" for a in avoid)
        res = llm.complete(self.system(), task, "", max_tokens=400)
        self._track(res)
        if not res.model or not res.text.strip():
            return None
        scan = scan_output(res.text.strip())
        self.violations += scan.violations
        text, _ = claims.strip_unverified(scan.text, self.evidence_urls())
        if price:  # the only dollar amount a launch post may state is the price the pricing rule set
            for bad in wrong_money(text, [price]):
                text = text.replace(bad, f"${price}")
            # The price is one number: "$11.99 or less", "from $11.99", "$11.99 and up" make it vague, so the hedge goes.
            text = re.sub(rf"(\${re.escape(str(price))})\s*(?:or (?:less|lower|under|so|more)|and (?:up|under|below)|\+)", r"\1", text)
            text = re.sub(rf"\b(?:from|starting (?:at|from)|as low as|only|just|under|up to)\s+(\${re.escape(str(price))})", r"\1", text,
                          flags=re.IGNORECASE)
        from tools import honesty
        text, _ = honesty.strip_counts(text)
        text, _ = honesty.strip_experience(text, self.brief)
        return honesty.complete_sentences(text).strip()

    def launch_posts(self, candidate: dict, communities: dict, price: float | None = None) -> StepResult:
        places = launch_places(communities)
        md = ["# Phase 5, step 2: Launch posts (drafts)", "",
              "Each post is written for one community, for the founder to publish under their own name after reading that "
              "community's rules. Nothing is posted by the system: each post is an approval-gated action, and posting is STUBBED.", ""]
        if not places:
            md += ["## No launch place found in the research", "",
                   "None of the communities found in the evidence allow posting about your own work, so no launch post was drafted. "
                   "Start with your own network instead: people you know who fit the customer profile, in your own words.", "",
                   footer(None)]
            return self.result("launch-posts", "write_launch_posts", "\n".join(md), data={"post_actions": [], "notes": []},
                               buyer_facing=True)
        posts: dict[str, str] = {}
        notes: list[str] = []
        problem = candidate.get("problem", "")
        for place in places:
            text = self._one_post(place, candidate, price)
            if text is None:
                notes.append(f"{place}: no model answered, so no post was written (posts are never filled from a template).")
                continue
            clash = shared_sentences(text, list(posts.values())) + pasted_lines(text, problem)
            if clash:
                text = self._one_post(place, candidate, price, avoid=clash)
                if text is None or shared_sentences(text, list(posts.values())) or pasted_lines(text, problem):
                    notes.append(f"{place}: dropped. After one rewrite it still repeated a sentence of another post or the "
                                 "problem statement, so it was not kept.")
                    continue
            posts[place] = text
        ids = []
        for place, text in posts.items():
            act = approval.request_action(self.run, "publish", f"launch post: {place}", f"Post in {place}", {"text": text}, agent=self.role)
            ids.append(act["id"])
            md += [f"## {place}", "", text, "", f"Approval: `{act['id']}` (pending)", ""]
        if notes:
            md += ["## Notes", ""] + [f"- {n}" for n in notes] + [""]
        md.append(footer(self.model))
        return self.result("launch-posts", "write_launch_posts", "\n".join(md), data={"post_actions": ids, "notes": notes},
                           buyer_facing=True)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text or "")
    return [p.strip() for p in parts if re.sub(r"\W+", "", p)]


def _norm_sentence(s: str) -> str:
    return " ".join(re.sub(r"[^\w$.]+", " ", s.lower()).replace(".", " ").split())


def shared_sentences(text: str, others: list[str]) -> list[str]:
    """Sentences of `text` that also appear (same words, any case or punctuation) in one of `others`."""
    seen = {_norm_sentence(s) for o in others for s in _sentences(o)}
    return [s for s in _sentences(text) if _norm_sentence(s) in seen]


def pasted_lines(text: str, problem: str, window: int = 8) -> list[str]:
    """Sentences that paste the research's problem statement (any run of `window` of its words in a row)."""
    words = _norm_sentence(problem).split()
    if len(words) < window:
        return []
    grams = {" ".join(words[i:i + window]) for i in range(len(words) - window + 1)}
    return [s for s in _sentences(text) if any(g in _norm_sentence(s) for g in grams)]
