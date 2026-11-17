"""Pricer: a rule-based price (no model)."""


def price(brief, score, modules):
    base = 9 + 4 * (len(modules) - 1)
    reason = [f"$9 base + $4 per evidenced module ({len(modules) - 1}) = ${base} (ASSUMPTION: rule of thumb for small digital toolkits)"]
    if score["max_competitor_stars"] >= 1000:
        base -= 4
        reason.append("minus $4: a popular free open-source alternative exists (see Phase 1 competitors)")
    p = max(5, min(49, base))
    md = "# Phase 4 Step 1: Pricing\n\n_Plain code, no model._\n\n" + "\n".join(f"- {r}" for r in reason) + \
         f"\n\n**Price: ${p} one-time.** Founder can change it at the gate.\n"
    return p, md
