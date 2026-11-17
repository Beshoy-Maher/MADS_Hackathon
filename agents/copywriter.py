"""Copywriter: landing page, store page and launch post.

Every pain bullet on a page links the public post it came from, so the validate gate can
check that 100% of claims trace to evidence. No testimonials, no counters, no timers:
the product has no customers yet, and the guardrails remove such text anyway.
"""
import html
import re

import guardrails
from agents.base import write


def _page(title, headline, sub, pains, cta, note):
    lis = "\n".join(f'    <li>{html.escape(p["title"])} <a href="{html.escape(p["url"])}">(source)</a></li>' for p in pains)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{html.escape(title)}</title></head>
<body style="font-family:sans-serif;max-width:640px;margin:40px auto;padding:0 16px">
  <h1>{html.escape(headline)}</h1>
  <p>{html.escape(sub)}</p>
  <h2>Built for problems people describe in public</h2>
  <ul>
{lis}
  </ul>
  {cta}
  <p><small>{html.escape(note)}</small></p>
</body></html>
"""


def landing_page(brief, vp):
    sub = write("copywriter", f"One sentence subheadline for {brief['product_name']}: {brief['idea']}. No numbers, no promises.",
                f"{brief['idea'][0].upper() + brief['idea'][1:]}.", max_tokens=80)
    form = ('<form><label>Email <input type="email" name="email"></label> '
            '<label><input type="checkbox" required> I agree to get one email when it launches</label> '
            '<button>Join the waitlist</button></form>\n  <p><small>Waitlist form: STUBBED (not connected; publishing needs founder approval).</small></p>')
    page = _page(brief["product_name"], brief["product_name"] + ": " + brief["tagline"], sub["text"], vp["pains"], form,
                 "No reviews or user counts are shown because there are no users yet.")
    return {"html": page, "model": sub["model"], "cost": sub["cost"], "label": sub["label"]}


def traceability(page_html, ledger):
    urls = {i["url"] for i in ledger["items"]}
    bullets = re.findall(r"<li>.*?</li>", page_html, re.S)
    if not bullets:
        return 0.0
    traced = [b for b in bullets if any(u in html.unescape(b) for u in urls)]
    return len(traced) / len(bullets)


def violations(text):
    return len(guardrails.clean(re.sub(r"<[^>]+>", " ", text))[1])


def store_page(brief, vp, price, modules):
    buy = (f'<p><strong>${price}</strong> one-time. 14-day refund, no questions.</p>\n'
           '  <button>Buy (MOCKED checkout)</button>')
    page = _page(brief["product_name"], brief["product_name"], f"What you get: {', '.join(m['title'] for m in modules)}.",
                 vp["pains"], buy, "Checkout is MOCKED: no real payment is taken.")
    return page


def launch_post(brief, vp, price):
    template = (f"I built {brief['product_name']} for {brief['audience']}. "
                f"It comes from posts like these: " + "; ".join(p["url"] for p in vp["pains"]) +
                f". It costs ${price}, with a 14-day refund. Feedback welcome.")
    post = write("copywriter", f"A short, honest launch post in the founder's own voice for {brief['product_name']} "
                 f"({brief['idea']}), price ${price}. Cite these links: {[p['url'] for p in vp['pains']]}. "
                 "No hype, no numbers that are not given, no urgency.", template, max_tokens=200)
    return post
