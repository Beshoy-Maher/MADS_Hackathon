"""Scorer: turns the evidence into numbers with fixed formulas (no model)."""
import math

RECENT_DAYS = 3 * 365


def relevant(item, brief):
    hay = (item["title"] + " " + item.get("text", "")).lower()
    return any(k.lower() in hay for k in brief["keywords"] + brief.get("broader_keywords", []))


def score(brief, ledger):
    voices = [v for v in ledger["items"] if v["kind"] == "voice" and relevant(v, brief)]
    recent = [v for v in voices if v["age_days"] is not None and v["age_days"] <= RECENT_DAYS]
    comps = [c for c in ledger["items"] if c["kind"] == "competitor"]
    engagement = sum(v["engagement"] for v in recent)
    demand = min(100, 6 * len(recent) + 2 * (len(voices) - len(recent)) + min(20, engagement // 10))
    hay = " ".join([brief["idea"], brief["problem"], " ".join(brief["keywords"])]).lower()
    skill_hits = [s for s in brief.get("skills", []) if s.lower() in hay]
    fit = min(100, (40 if brief.get("founder_is_target_user") else 0) + min(30, 10 * len(skill_hits))
              + min(30, 3 * int(brief.get("hours_per_week", 0))))
    max_stars = max([c["stars"] for c in comps], default=0)
    return {"sources": len({i["url"] for i in ledger["items"]}), "voices": len(voices),
            "recent_voices": len(recent), "engagement": engagement, "demand": demand, "fit": fit,
            "skill_hits": skill_hits, "competitors": len(comps), "max_competitor_stars": max_stars,
            "competition_level": round(20 * math.log10(max_stars + 1)),
            "formulas": {"demand": "6 x recent voices + 2 x older voices + min(20, recent engagement / 10), max 100",
                         "fit": "40 if founder is a target user + 10 per matching skill (max 30) + 3 x hours/week (max 30)",
                         "competition_level": "20 x log10(top competitor stars + 1)"}}


def to_md(s):
    rows = "\n".join(f"| {k} | {v} |" for k, v in s.items() if k != "formulas")
    f = "\n".join(f"- **{k}**: {v}" for k, v in s["formulas"].items())
    return f"# Phase 1 Step 2: Scorecard\n\n_Plain code, no model._\n\n| Metric | Value |\n|---|---|\n{rows}\n\n## Formulas\n{f}\n"
