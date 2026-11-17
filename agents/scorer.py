"""Phase 1, step 2: score the idea against the alternatives.

Scores are computed by fixed formulas from the evidence (so they are
reproducible and explainable). The model only adds a skill-fit opinion and a
short rationale. The formulas are printed in the output.
"""
from __future__ import annotations

from datetime import date

import guardrails
from agents.base import Agent, StepResult, brief_summary, budget_text, footer, hours_text
from tools import evidence_view
from tools.sources import Evidence, engagement_score
from tools.text import keywords

FORMULA = ("demand = 0.5 x engagement(log-scaled points/stars/comments; posts older than 2 years count half, older than 5 years "
           "a quarter) + 10 x min(pain posts, 5); "
           "independent voices = distinct authors or communities among discussion posts (repositories excluded); "
           "willingness_to_pay = 25 x posts mentioning paying/price (max 100); "
           "competition = 20 x existing solutions with 500+ stars/points (max 100); "
           "founder_fit = 45 x skill match + 30 x min(1, hours/8) + 25 x min(1, budget/$50); "
           "total = 0.40 demand + 0.15 willingness_to_pay + 0.30 founder_fit + 0.15 x (100 - competition)")


def _skill_match_keywords(brief: dict, cand: dict) -> float:
    skills = " ".join(brief.get("skills") or []).lower()
    skill_words = set(keywords(skills, 20))
    text = f"{cand['title']} {cand.get('problem', '')}".lower()
    if not skill_words:
        return 0.0
    hits = sum(1 for w in skill_words if w in text)
    return min(1.0, hits / max(1, min(3, len(skill_words))))


def recency_weight(created: str, today: date | None = None) -> float:
    """1.0 for posts from the last 2 years, 0.5 up to 5 years, 0.25 older; 0.5 when the date is unknown."""
    try:
        y, m, d = (int(x) for x in created[:10].split("-"))
        age_days = ((today or date.today()) - date(y, m, d)).days
    except (ValueError, TypeError):
        return 0.5
    return 1.0 if age_days <= 730 else 0.5 if age_days <= 1826 else 0.25


def score_candidate(brief: dict, cand: dict, skill_match: float) -> dict:
    ev = cand.get("evidence", [])
    # Independent voices are people or communities discussing the problem: a repository is a product, not a voice.
    # Engagement counts recent posts fully and older ones for less. Known limitation: the stars of existing
    # repositories still count toward demand engagement (they show interest in the topic, but also competition).
    talk = [e for e in ev if "existing_solution" not in e.get("signals", [])]
    items = [Evidence(**{**{k: e[k] for k in Evidence.__dataclass_fields__ if k in e},
                         "engagement": int(e.get("engagement", 0) * recency_weight(e.get("created", ""))),
                         "comments": int(e.get("comments", 0) * recency_weight(e.get("created", "")))}) for e in ev]
    pain = sum(1 for e in ev if "pain" in e.get("signals", []))
    wtp = sum(1 for e in ev if "willingness_to_pay" in e.get("signals", []))
    popular_existing = sum(1 for e in ev if "existing_solution" in e.get("signals", []) and e.get("engagement", 0) >= 500)
    demand = min(100.0, 0.5 * engagement_score(items) + 10 * min(pain, 5))
    wtp_score = min(100.0, 25.0 * wtp)
    competition = min(100.0, 20.0 * popular_existing)
    hours = float(brief.get("hours_per_week") or 0)
    budget = float(brief.get("budget_usd") or 0)
    fit = 45 * skill_match + 30 * min(1.0, hours / 8) + 25 * min(1.0, budget / 50)
    total = 0.40 * demand + 0.15 * wtp_score + 0.30 * fit + 0.15 * (100 - competition)
    excluded = not guardrails.screen_brief({"idea": cand["title"]}).allowed
    return {
        "title": cand["title"], "relevant_sources": len({e["url"] for e in ev}),
        "platforms": len({e["source"] for e in ev}), "voices": len({e.get("community") or e["url"] for e in talk}), "pain": pain, "willingness_to_pay_posts": wtp,
        "popular_existing_solutions": popular_existing, "demand_score": round(demand, 1),
        "willingness_to_pay": round(wtp_score, 1), "competition": round(competition, 1),
        "skill_match": round(skill_match, 2), "founder_fit": round(fit, 1), "total": round(total, 1), "excluded": excluded,
    }


class Scorer(Agent):
    role = "scorer"
    check_claims = True

    def run_step(self, candidates: list[dict]) -> StepResult:
        fb = {"skill_match": [round(_skill_match_keywords(self.brief, c), 2) for c in candidates],
              "rationale": ["ASSUMPTION: skill match estimated from keyword overlap between the founder's skills and the idea."] * len(candidates)}
        task = (f"Founder brief:\n{brief_summary(self.brief)}\n\nCandidates:\n" +
                "\n".join(f"{i}. {c['title']} - {c.get('problem', '')}" for i, c in enumerate(candidates)) +
                "\n\nFor each candidate, rate from 0.0 to 1.0 how well the founder's CURRENT skills let them build it "
                "without hiring anyone, and give one reason of at most 18 words. "
                'JSON: {"skill_match": [numbers in candidate order], "rationale": ["...", ...]}')
        data = self.ask_json(task, fb, max_tokens=300)
        llm_match = data.get("skill_match") if isinstance(data.get("skill_match"), list) else fb["skill_match"]
        rationale = data.get("rationale") if isinstance(data.get("rationale"), list) else fb["rationale"]
        scores = []
        for i, c in enumerate(candidates):
            kw = _skill_match_keywords(self.brief, c)
            try:
                m = float(llm_match[i])
                m = max(0.0, min(1.0, m))
                match = round((m + kw) / 2, 2) if self.model else kw
            except (IndexError, TypeError, ValueError):
                match = kw
            s = score_candidate(self.brief, c, match)
            s["rationale"] = str(rationale[i]) if i < len(rationale) else ""
            scores.append(s)
        md = ["# Phase 1, step 2: Scorecard (idea vs. alternatives)", "",
              "| Candidate | Relevant sources | Independent voices | Platforms | Pain posts | Demand | Pay signals | Competition | Founder fit | **Total** |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for i, s in enumerate(scores):
            name = ("Founder idea: " if i == 0 else f"Alt {i}: ") + s["title"][:70]
            md.append(f"| {name} | {s['relevant_sources']} | {s['voices']} | {s['platforms']} | {s['pain']} | {s['demand_score']} | "
                      f"{s['willingness_to_pay']} | {s['competition']} | {s['founder_fit']} | **{s['total']}** |")
        md += ["", "## Why", ""]
        for i, s in enumerate(scores):
            md.append(f"- **{s['title'][:80]}**: {s['rationale'] or 'No rationale.'} (skill match {s['skill_match']})")
        # Display only: the evidence behind each row, split by kind. The table above is computed before this and is unchanged.
        md += ["", "## Evidence behind each candidate", ""]
        shown: list[str] = []
        for i, c in enumerate(candidates):
            problem, existing = evidence_view.split_evidence(c.get("evidence", []))
            md += [f"### {('Founder idea: ' if i == 0 else f'Alt {i}: ') + c['title'][:80]}", ""]
            md += evidence_view.evidence_sections(c.get("evidence", []), limit=4)
            shown += [e["url"] for e in (problem[:4] + existing[:4])]
        md += ["## How the scores are calculated", "", FORMULA, "",
               "Founder fit uses the brief: skills, " f"{hours_text(self.brief)}, {budget_text(self.brief)}. "
               + ("A value that is not given counts as 0 in founder fit; it is not replaced by a typical figure. "
                  if self.brief.get("hours_per_week") is None or self.brief.get("budget_usd") is None else "") +
               "Engagement counts are public numbers from the linked sources; "
               "they show interest, not guaranteed buyers (ASSUMPTION that interest relates to demand).",
               footer(self.model, shown)]
        return self.result("scorecard", "score_ideas", "\n".join(md), data={"scores": scores}, sources=shown)
