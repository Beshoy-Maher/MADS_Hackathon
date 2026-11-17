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
from agents.base import Agent, StepResult, brief_summary, community_places, footer

PAGE_CSS = """body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:720px;margin:40px auto;padding:0 16px;color:#1d2433;line-height:1.55}
h1{font-size:2rem;line-height:1.2}.sub{font-size:1.15rem;color:#4a5568}.card{border:1px solid #e2e8f0;border-radius:12px;padding:16px 20px;margin:18px 0}
ul{padding-left:20px}button{background:#2d5bff;color:#fff;border:0;border-radius:8px;padding:10px 18px;font-size:1rem;cursor:pointer}
input[type=email]{padding:10px;border:1px solid #cbd5e0;border-radius:8px;width:60%}small{color:#718096}.price{font-size:1.6rem;font-weight:700}"""


def _li(items) -> str:
    return "\n".join(f"<li>{html.escape(str(i))}</li>" for i in items)


class Copywriter(Agent):
    role = "copywriter"

    def _copy(self, candidate: dict, canvas: dict, purpose: str) -> dict:
        fb = {
            "headline": candidate["title"][:90],
            "subheadline": str(canvas.get("unique_value_proposition") or candidate.get("problem", ""))[:160],
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
        # Scan every field.
        from guardrails import scan_output
        for k in ("headline", "subheadline", "who_for", "cta"):
            s = scan_output(str(out[k]))
            if s.violations:
                self.violations += s.violations
                out[k] = s.text or fb[k]
        clean_bullets = []
        for b in out["bullets"][:4]:
            s = scan_output(str(b))
            self.violations += s.violations
            if s.text.strip():
                clean_bullets.append(s.text)
        out["bullets"] = clean_bullets or fb["bullets"]
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
        return self.result("store-page", "open_store_page", page, ext="html", data={"copy": c, "publish_action": act["id"]})

    def launch_posts(self, candidate: dict, communities: dict, price: float | None = None) -> StepResult:
        places = community_places(communities, 3) or ["the founder's own network"]
        name = self.brief.get("founder_name", "the founder")
        fb_posts = {p: (f"Hi all, I'm {name}. I made {candidate['title']} because {candidate.get('problem', 'I kept seeing this problem').rstrip('.').lower()}. "
                        "It's a small digital product. I'd value honest feedback on whether it's useful. Link in comments if the rules allow it.")
                    for p in places}
        task = (f"Founder brief:\n{brief_summary(self.brief)}\nProduct: {candidate['title']}\n\n"
                f"Facts: it is a paid digital download{f' at ${price}' if price else ''}, not free and not open source. "
                f"Write one short launch post for each place: {places}. Written in first person by {name}, honest, "
                "follows community self-promotion rules, asks for feedback, no hype, no urgency, no claims of results. "
                'JSON: {"posts": {"<place>": "<post>"}}')
        data = self.ask_json(task, {"posts": fb_posts}, max_tokens=700)
        posts = data.get("posts") if isinstance(data.get("posts"), dict) else fb_posts
        md = ["# Phase 5, step 2: Launch posts (drafts)", "",
              "Each post is written for the founder to publish under their own name, after reading the community's rules. "
              "Nothing is posted by the system: each post is an approval-gated action, and posting is STUBBED.", ""]
        ids = []
        for place, post in list(posts.items())[:4]:
            from guardrails import scan_output
            s = scan_output(str(post))
            self.violations += s.violations
            if price:  # the only dollar amount a launch post may state is the price the pricing rule set
                for bad in wrong_money(s.text, [price]):
                    s.text = s.text.replace(bad, f"${price}")
                # The price is one number: "$11.99 or less", "from $11.99", "$11.99 and up" make it vague, so the hedge goes.
                s.text = re.sub(rf"(\${re.escape(str(price))})\s*(?:or (?:less|lower|under|so|more)|and (?:up|under|below)|\+)", r"\1", s.text)
                s.text = re.sub(rf"\b(?:from|starting (?:at|from)|as low as|only|just|under|up to)\s+(\${re.escape(str(price))})", r"\1", s.text,
                                flags=re.IGNORECASE)
            act = approval.request_action(self.run, "publish", f"launch post: {place}", f"Post in {place}", {"text": s.text}, agent=self.role)
            ids.append(act["id"])
            md += [f"## {place}", "", s.text, "", f"Approval: `{act['id']}` (pending)", ""]
        md.append(footer(self.model))
        return self.result("launch-posts", "write_launch_posts", "\n".join(md), data={"post_actions": ids})
