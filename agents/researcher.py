"""Phase 1, step 1 (Core step): find opportunities.

Sharpens the founder's starting idea, proposes alternatives that fit the
founder, and collects public evidence for each one from Hacker News, Reddit,
GitHub and Stack Exchange. Every item keeps its URL.
"""
from __future__ import annotations

from agents.base import Agent, StepResult, brief_summary, bullet_sources, footer
from tools import sources as src
from tools.text import keywords, short_market, short_query, topic_keywords

MIN_RELEVANCE = 0.34


def fallback_candidates(brief: dict) -> list[dict]:
    idea = brief.get("idea", "").strip().rstrip(".")
    market = short_market(brief.get("target_market", ""), 5)
    skills = brief.get("skills") or []
    top_skill = skills[0] if skills else "the founder's main skill"
    topic = " ".join(topic_keywords(idea, 3)) or idea[:40]
    return [
        {"title": idea[:200], "problem": f"{market} find {topic} hard to get right on their own.", "format": "as described by the founder",
         "queries": [topic, " ".join(topic_keywords(idea, 2) + ["help"])]},
        {"title": f"{topic.capitalize()} templates and checklists for {market}"[:120],
         "problem": f"{market} need a faster, structured way to handle {topic}.", "format": "templates + checklists",
         "queries": [" ".join(topic_keywords(idea, 2) + ["template"])]},
        {"title": f"{top_skill} starter toolkit for {market}"[:120],
         "problem": f"{market} want practical {top_skill} skills for their work.", "format": "self-paced toolkit",
         "queries": [" ".join(topic_keywords(top_skill, 2) + ["beginners"])]},
    ]


class Researcher(Agent):
    role = "researcher"

    def candidates(self) -> list[dict]:
        fb = {"candidates": fallback_candidates(self.brief)}
        attempt = int(self.run.get("attempts", {}).get("1", 1))
        broaden = ("\nA previous search with narrow queries found almost nothing. Use BROADER queries this time: 2 words, "
                   "the plain topic plus a community word (e.g. 'arabic tutors', 'teaching kids online').\n") if attempt > 1 else ""
        if attempt > 1:
            for c in fb["candidates"]:
                c["queries"] = [" ".join(topic_keywords(c["title"], 2))]
        task = (f"Founder brief:\n{brief_summary(self.brief)}\n{broaden}\n"
                "1) Rewrite the founder's starting idea as one sharp, specific digital product (who, what problem, what format).\n"
                "2) Propose 2 alternative digital products that fit this founder's skills, time, budget and values better or "
                "serve the same people differently. No physical goods, finance/crypto, health or legal advice.\n"
                "For each, give 1-2 short web search queries (2-4 words each) that would find people discussing the PROBLEM.\n"
                'JSON shape: {"candidates": [{"title": "...", "problem": "...", "format": "...", "queries": ["...", "..."]}]} '
                "with the sharpened founder idea first.")
        data = self.ask_json(task, fb)
        cands = data.get("candidates") if isinstance(data.get("candidates"), list) else fb["candidates"]
        clean = []
        for c in cands[:3]:
            if not isinstance(c, dict) or not c.get("title"):
                continue
            qs = [" ".join(str(q).split()[:4]) for q in (c.get("queries") or []) if str(q).strip()][:2]
            clean.append({"title": str(c["title"])[:200], "problem": str(c.get("problem", ""))[:300],
                          "format": str(c.get("format", ""))[:80], "queries": qs or [short_query(c["title"], 3)]})
        if not clean:
            clean = fb["candidates"]
        # The founder's own idea always stays in the comparison, under its own words.
        clean[0]["original_idea"] = self.brief.get("idea", "")
        return clean

    def gather(self, cand: dict, main: bool) -> dict:
        queries = list(cand["queries"])
        if main:
            extra = " ".join(topic_keywords(self.brief.get("idea", ""), 3))
            if extra and extra not in queries:
                queries.append(extra)
        evidence, report = src.search(queries[:3] if main else queries[:1])
        kw = keywords(cand["title"] + " " + cand.get("problem", "") + " " + " ".join(queries), 8)
        # The subject itself must be in the item ("sql"), not only words every nearby topic shares ("interview questions").
        core = topic_keywords(self.brief.get("idea", "") if main else cand["title"], 2) or topic_keywords(cand["title"], 2)
        scored = []
        for ev in evidence:
            r = src.relevance(ev, kw)
            text = f"{ev.title} {ev.snippet}".lower()
            matched = sum(1 for k in kw if k in text)
            on_topic = not core or any(k in text for k in core)
            if on_topic and (r >= MIN_RELEVANCE or matched >= 2):
                d = ev.as_dict()
                d["relevance"] = round(r, 2)
                scored.append(d)
        scored.sort(key=lambda d: (d["relevance"], d["engagement"] + d["comments"]), reverse=True)
        return {"queries": queries, "keywords": kw, "evidence": scored[:25], "raw_found": len(evidence), "source_report": report}

    def run_step(self) -> StepResult:
        cands = self.candidates()
        all_sources: list[str] = []
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=len(cands)) as pool:  # the candidates are searched side by side
            gathered = list(pool.map(lambda ic: self.gather(ic[1], main=(ic[0] == 0)), enumerate(cands)))
        for c, got in zip(cands, gathered):
            c.update(got)
            all_sources += [e["url"] for e in c["evidence"]]
        reports = [c["source_report"] for c in cands]
        sources_ok = any(r.get("ok") for rep in reports for r in rep.values())
        md = [f"# Phase 1, step 1: Opportunities for {self.brief.get('founder_name', 'the founder')}", "",
              f"**Starting idea (founder's words):** {self.brief.get('idea', '')}", "",
              "The researcher sharpened the idea, proposed alternatives that fit the founder, and searched public "
              "discussions for evidence that people have this problem. Every item below links to its source.", ""]
        for i, c in enumerate(cands):
            label = "Sharpened founder idea" if i == 0 else f"Alternative {i}"
            md += [f"## {label}: {c['title']}", "", f"- Problem: {c['problem'] or 'ASSUMPTION: not stated'}",
                   f"- Format: {c['format'] or 'ASSUMPTION: not stated'}",
                   f"- Search queries: {', '.join(c['queries'])}",
                   f"- Relevant items found: {len(c['evidence'])} (of {c['raw_found']} results)", "", "Evidence:",
                   bullet_sources(c["evidence"]), ""]
        md += ["## Source coverage", ""]
        for name, r in reports[0].items():
            status = f"{r['ok']} queries ok" + (f", error: {r['error']}" if r["error"] else "")
            md.append(f"- {name}: {status}")
        if not sources_ok:
            md += ["", "No public source could be reached. All market statements in this run are ASSUMPTION until research is repeated."]
        md.append(footer(self.model, all_sources))
        return self.result("opportunities", "find_opportunities", "\n".join(md),
                           data={"candidates": cands, "sources_ok": sources_ok}, sources=all_sources)
