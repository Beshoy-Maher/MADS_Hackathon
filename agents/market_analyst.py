"""Phase 1, step 3: define the market (who exactly, where they are, what they use today)."""
from __future__ import annotations

from collections import Counter

from agents.base import Agent, StepResult, brief_summary, footer


class MarketAnalyst(Agent):
    role = "market_analyst"
    check_claims = True

    def run_step(self, candidate: dict) -> StepResult:
        ev = candidate.get("evidence", [])
        communities = Counter()
        for e in ev:
            if e["source"] == "reddit" and e["title"].startswith("r/"):
                communities[e["title"].split(":")[0]] += 1
            else:
                communities[e["source"]] += 1
        existing = [e for e in ev if "existing_solution" in e.get("signals", [])][:5]
        pains = [e for e in ev if "pain" in e.get("signals", [])][:6]
        src_lines = "\n".join(f"- {e['title'][:120]} | {e['url']}" for e in (pains + existing)[:10]) or "(no sources)"
        fallback = "\n".join([
            "## Ideal customer profile",
            f"- Who: {self.brief.get('target_market', 'ASSUMPTION: not stated')} (from the founder brief).",
            f"- Problem: {candidate.get('problem') or 'ASSUMPTION: not stated'}",
            "- Trigger moment: ASSUMPTION: they look for help right before a deadline or a first attempt.",
            "",
            "## What they use today",
            *([f"- [{e['title'][:90]}]({e['url']})" for e in existing] or ["- ASSUMPTION: free blog posts and videos; no source found."]),
            "",
            "## Market size",
            "- ASSUMPTION: not estimated. No sourced figure is available, so the system does not guess one.",
        ])
        task = (f"Founder brief:\n{brief_summary(self.brief)}\n\nProduct: {candidate['title']}\nProblem: {candidate.get('problem', '')}\n\n"
                f"Evidence (title | url):\n{src_lines}\n\n"
                "Write three short Markdown sections: '## Ideal customer profile' (who, situation, trigger moment, what they "
                "tried), '## What they use today' (existing solutions and their gaps), '## Market size' (only a sourced number "
                "or the word ASSUMPTION with a way to measure it). Cite claims with the URLs above in [text](url) form, "
                "otherwise write ASSUMPTION. Only say what a cited source shows; do not generalise from one item to 'most people'. "
                "The brief's constraints describe the founder, not the customer. Max 150 words in total: short bullets, no introduction.")
        body = self.write(task, fallback, max_tokens=420)
        md = [f"# Phase 1, step 3: Market definition for '{candidate['title']}'", "", body, "",
              "## Where these people talk (from the evidence)", ""]
        md += [f"- {name}: {n} relevant item(s)" for name, n in communities.most_common(8)] or ["- No communities found (ASSUMPTION)."]
        sources = [e["url"] for e in pains + existing]
        md.append(footer(self.model, sources))
        return self.result("market", "define_market", "\n".join(md),
                           data={"communities": dict(communities), "existing": [e["url"] for e in existing]}, sources=sources)
