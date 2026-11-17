"""Strategist: picks the three strongest recent pains and writes the value proposition."""
from agents.base import write
from agents.scorer import RECENT_DAYS, relevant


def top_pains(brief, ledger, n=3):
    voices = [v for v in ledger["items"] if v["kind"] == "voice" and relevant(v, brief)
              and v["age_days"] is not None and v["age_days"] <= RECENT_DAYS]
    return sorted(voices, key=lambda v: -v["engagement"])[:n]


def value_prop(brief, ledger):
    pains = top_pains(brief, ledger)
    template = (f"For {brief['audience']} who struggle with {brief['problem']}, "
                f"{brief['product_name']} is a digital toolkit that turns the job into a repeatable checklist. "
                "Unlike general-purpose tools, every part answers a pain people described in public.")
    vp = write("strategist", f"One-paragraph value proposition for {brief['product_name']} ({brief['idea']}) "
               f"for {brief['audience']}. Pains: {[p['title'] for p in pains]}. No numbers, no promises.", template)
    md = [f"# Phase 2 Step 1: Value proposition\n", f"_{vp['label']}_\n", vp["text"], "", "## Pains it answers (with evidence)"]
    md += [f"{i+1}. [{p['title']}]({p['url']})" for i, p in enumerate(pains)]
    md += ["", "## Lean canvas (short)", f"- **Customer:** {brief['audience']}", f"- **Problem:** {brief['problem']}",
           f"- **Solution:** {brief['idea']}", "- **Channel:** the communities where the evidence came from (see sources)",
           "- **Revenue:** one-time purchase, price set in Phase 4", "- **Unfair advantage:** ASSUMPTION: founder's own experience"]
    return {"pains": pains, "text": vp["text"], "md": "\n".join(md), "model": vp["model"], "cost": vp["cost"],
            "sources": [p["url"] for p in pains]}
