"""Red team: tries to kill the idea before the founder spends a week on it.

Each rule is a fixed question asked of the evidence. A failed rule with severity
"critical" makes the evidence gate recommend PIVOT (or STOP).
"""
from agents.base import write

DOMINANT_STARS = 20000


def challenge(brief, ledger, score):
    comps = [c for c in ledger["items"] if c["kind"] == "competitor"]
    risks, concerns = [], []
    big = [c for c in comps if c["stars"] >= DOMINANT_STARS]
    if big:
        risks.append({"risk": f"a free open-source tool already dominates ({big[0]['title']}, {big[0]['stars']} stars)",
                      "source": big[0]["url"], "severity": "critical"})
    if score["voices"] and not score["recent_voices"]:
        risks.append({"risk": "all pain voices are older than 3 years", "source": None, "severity": "critical"})
    if int(brief.get("hours_per_week", 0)) < 3:
        risks.append({"risk": "founder has under 3 hours a week", "source": None, "severity": "critical"})
    if not brief.get("founder_is_target_user"):
        concerns.append("founder is not a target user: interviews are essential (ASSUMPTION until done)")
    if score["competitors"] == 0:
        concerns.append("no existing solutions found: either a gap or no market")
    if score["recent_voices"] < 5:
        concerns.append(f"only {score['recent_voices']} recent pain voices")
    template = "Kill questions asked: dominant free tool, stale pain, founder time, founder fit, empty market."
    note = write("red_team", f"In 3 bullets, the strongest reasons '{brief['idea']}' could fail. Risks found: {risks}. Concerns: {concerns}.", template)
    md = ["# Phase 1 Step 3: Red team (try to kill the idea)\n", f"_{note['label']}_\n", note["text"], "",
          "## Critical risks (block GO)"] + ([f"- {r['risk']}" + (f" ([source]({r['source']}))" if r["source"] else "") for r in risks] or ["- none"])
    md += ["", "## Concerns (inform the founder)"] + ([f"- {c}" for c in concerns] or ["- none"])
    return {"risks": risks, "concerns": concerns, "md": "\n".join(md), "model": note["model"], "cost": note["cost"],
            "sources": [r["source"] for r in risks if r["source"]]}
