"""Phase 3 (Core step): build the product.

The builder turns the validated idea into a real digital product: a spec,
the product content itself (modules with steps, worked examples and
worksheets), and a user guide. The QA agent then tests it.
"""
from __future__ import annotations

import decision_log
from agents.base import Agent, StepResult, brief_summary, footer
from tools.text import keywords

MAX_MODULES = 4


def _fallback_modules(candidate: dict, brief: dict) -> list[dict]:
    topic = " ".join(keywords(candidate["title"], 3)) or "the topic"
    return [
        {"title": f"Get oriented: what good {topic} looks like", "goal": "Understand the target outcome and the common traps."},
        {"title": f"Step-by-step method for {topic}", "goal": "Follow a repeatable method from start to finish."},
        {"title": "Worked example", "goal": "See the method applied end to end on a realistic case."},
        {"title": "Checklists and worksheet", "goal": "Apply it yourself with fill-in templates."},
    ]


def _fallback_module_text(m: dict, candidate: dict, brief: dict) -> str:
    who = brief.get("target_market", "the reader")
    return "\n".join([
        f"**Goal:** {m.get('goal', '')}", "",
        f"This module is written for {who}. Read it once end to end, then use the checklist while you work. "
        "Each step says what to do, why it matters and how to know you did it well.", "",
        "**Steps**",
        "1. Write down the situation you are in today and what a good result looks like for you, in one sentence each.",
        "2. Break the work into small parts you can finish in under thirty minutes. Order them from most to least important.",
        "3. Do the first part using the template below. Do not polish yet; aim for a complete first version.",
        "4. Review it against the checklist. Fix the items that fail, then move to the next part.",
        "5. When every part is done, compare the result with your one-sentence goal and note what you would change next time.", "",
        "**Checklist**",
        "- [ ] The goal is written in one clear sentence.",
        "- [ ] Every part has a finished first version.",
        "- [ ] Each item on this list was checked honestly, not skipped.",
        "- [ ] You noted one improvement for next time.", "",
        "**Common mistakes**",
        "- Trying to make the first version perfect, which stops progress.",
        "- Skipping the review step because the work feels finished.",
        "- Copying an example without adapting it to your own situation.", "",
        "**Worksheet**",
        "| Part | What I will do | Done when | Status |",
        "|---|---|---|---|",
        "| 1 |  |  |  |",
        "| 2 |  |  |  |",
        "| 3 |  |  |  |",
    ])


class Builder(Agent):
    role = "builder"

    def spec(self, candidate: dict, canvas: dict) -> StepResult:
        fb = {"product_name": candidate["title"][:80], "format": candidate.get("format") or "digital guide with worksheets (Markdown/HTML)",
              "modules": _fallback_modules(candidate, self.brief),
              "out_of_scope": ["Personal coaching", "Anything outside the stated problem"],
              "acceptance_criteria": ["Every module has steps, a checklist and a worksheet", "No guardrail violations",
                                      "A user guide explains how to use it and how to get support"]}
        task = (f"Founder brief:\n{brief_summary(self.brief)}\nProduct: {candidate['title']}\nProblem: {candidate.get('problem', '')}\n"
                f"Lean canvas solution: {canvas.get('solution')}\n\nDesign the smallest useful version (MVP) of this digital product that the "
                f"founder can finish in {self.brief.get('hours_per_week', 5)} hours/week within 2 weeks. "
                f"JSON: {{\"product_name\": \"...\", \"format\": \"...\", \"modules\": [{{\"title\": \"...\", \"goal\": \"...\"}}] (3-{MAX_MODULES} modules), "
                "\"out_of_scope\": [\"...\"], \"acceptance_criteria\": [\"...\"]}")
        data = self.ask_json(task, fb, max_tokens=700)
        spec = {k: data.get(k) or fb[k] for k in fb}
        mods = [m for m in spec["modules"] if isinstance(m, dict) and m.get("title")][:MAX_MODULES] if isinstance(spec["modules"], list) else []
        spec["modules"] = mods or fb["modules"]
        md = [f"# Phase 3, step 1: MVP spec for '{spec['product_name']}'", "", f"**Format:** {spec['format']}", "", "## Modules"]
        md += [f"{i}. **{m['title']}**: {m.get('goal', '')}" for i, m in enumerate(spec["modules"], 1)]
        md += ["", "## Out of scope"] + [f"- {x}" for x in spec["out_of_scope"]]
        md += ["", "## Acceptance criteria (checked by the QA agent)"] + [f"- {x}" for x in spec["acceptance_criteria"]]
        md.append(footer(self.model))
        return self.result("spec", "write_mvp_spec", "\n".join(md), data={"spec": spec})

    @staticmethod
    def _clean(body: str) -> str:
        # Keep the product's heading structure: drop any top-level heading the model added.
        return "\n".join(l for l in body.splitlines() if not l.startswith("# ")).strip()

    def revise(self, index: int, module: dict, body: str, errors: list[str]) -> str:
        """One revision of a module, with the verifier's error list as feedback. Returns the old text if the rewrite is unusable."""
        task = (f"Module {index}: {module['title']} - goal: {module.get('goal', '')}\n\nYOUR DRAFT:\n{body}\n\n"
                "A reviewer found these errors in the draft:\n" + "\n".join(f"- {e}" for e in errors) + "\n\n"
                "Rewrite the whole module with every listed error fixed. If you cannot fix a statement, remove it. Change nothing else: "
                "keep the intro, the numbered steps, the worked example, the checklist with '- [ ]' items and 'Common mistakes'. "
                "Any SQL must be standard SQL that runs in SQLite. 220-320 words, Markdown, no top-level heading. "
                "No promises of results, no testimonials, no medical/financial/legal advice.")
        revised = self._clean(self.write(task, body, max_tokens=700))
        usable = len(revised.split()) >= 120
        decision_log.log("builder", "revise_module", run_id=self.run["id"], model=self.model, cost=0, step="phase3_step2_product.md",
                         outcome="revised" if usable and revised != body else "unchanged",
                         detail=f"module {index}: one revision with {len(errors)} error(s) from the verifier as feedback")
        return revised if usable else body

    def build(self, candidate: dict, spec: dict, feedback: str = "", verifier=None, on_progress=None) -> StepResult:
        parts = [f"# {spec['product_name']}", "",
                 f"A practical {spec['format']} for {self.brief.get('target_market', 'you')}. Made by {self.brief.get('founder_name', 'the founder')}.", "",
                 "## Contents"] + [f"{i}. {m['title']}" for i, m in enumerate(spec["modules"], 1)] + [""]
        reviews: list[dict] = []
        total = len(spec["modules"])
        for i, m in enumerate(spec["modules"], 1):
            if on_progress:
                on_progress(f"builder: writing module {i} of {total}")
            task = (f"Product: {spec['product_name']} for {self.brief.get('target_market', '')}.\nModule {i}: {m['title']} - goal: {m.get('goal', '')}\n"
                    f"{('Founder feedback to apply: ' + feedback) if feedback else ''}\n"
                    "Write this module's content for the buyer: a short intro, 4-6 numbered steps with concrete instructions, "
                    "one worked example, a checklist with '- [ ]' items, and 'Common mistakes'. 220-320 words, Markdown, "
                    "no top-level heading. Only state facts you are sure of; any SQL must be standard SQL that runs in SQLite. "
                    "No promises of results, no testimonials, no medical/financial/legal advice.")
            body = self._clean(self.write(task, _fallback_module_text(m, candidate, self.brief), max_tokens=700))
            if verifier is not None:
                if on_progress:
                    on_progress(f"verifier: checking module {i} of {total} for factual errors")
                review = verifier.review(i, m, body, 1)
                reviews.append(review)
                errors = review["errors"] + review["sql_errors"]
                if errors:  # one revision at most, then one last review
                    if on_progress:
                        on_progress(f"builder: revising module {i} of {total} ({len(errors)} error(s) found)")
                    revised = self.revise(i, m, body, errors)
                    if revised != body:
                        body = revised
                        if on_progress:
                            on_progress(f"verifier: checking the revised module {i} of {total}")
                        reviews.append(verifier.review(i, m, body, 2))
            parts += [f"## Module {i}: {m['title']}", "", body, ""]
        parts += ["## A note on results", "",
                  "This product gives you a method and templates. Your results depend on your situation and effort; nothing here is a promise of any outcome."]
        content = "\n".join(parts)
        return self.result("product", "build_product", content,
                           data={"modules": [m["title"] for m in spec["modules"]], "reviews": reviews if verifier is not None else None})

    def user_guide(self, spec: dict) -> StepResult:
        fallback = "\n".join([
            "## How to use this product",
            "1. Open the Contents and read Module 1 first. It takes about 15 minutes.",
            "2. Work through one module per session. Keep the worksheet open while you read.",
            "3. Use the checklist at the end of each module before you move on.", "",
            "## What you need",
            "- Any device that can open Markdown, HTML or PDF files.",
            "- About one hour per module.", "",
            "## Getting help",
            f"- Email {self.brief.get('founder_name', 'the founder')} using the address on your receipt. Replies within 2 working days (ASSUMPTION: founder's availability).",
            "- Refunds: see the refund policy. Access to the download is removed after a refund.",
        ])
        task = (f"Write the user guide for '{spec['product_name']}' ({spec['format']}). Modules: {[m['title'] for m in spec['modules']]}.\n"
                "Sections: '## How to use this product' (numbered steps), '## What you need', '## Getting help' (support by email from the "
                "founder, refunds per the refund policy). Max 220 words. Markdown.")
        body = self.write(task, fallback, max_tokens=600)
        if "## Getting help" not in body:
            body += "\n\n## Getting help\n- Email the founder using the address on your receipt.\n- Refunds: see the refund policy."
        md = f"# User guide: {spec['product_name']}\n\n{body}\n{footer(self.model)}"
        return self.result("user-guide", "write_user_docs", md)
