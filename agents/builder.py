"""Builder: writes the spec and the product (a digital toolkit in Markdown).

One module per evidenced pain, plus a quick-start. The spec is the contract the QA agent
checks against.
"""
from agents.base import write


def spec(brief, vp):
    modules = [{"id": "quickstart", "title": "Quick start", "pain_url": None}]
    for i, p in enumerate(vp["pains"], 1):
        modules.append({"id": f"m{i}", "title": f"Module {i}: {p['title'][:70]}", "pain_url": p["url"]})
    md = [f"# Phase 3 Step 1: Product spec\n", f"**Product:** {brief['product_name']}, a downloadable toolkit (Markdown).",
          f"**For:** {brief['audience']}", "", "| Module | Answers this public pain |", "|---|---|"]
    md += [f"| {m['title']} | {m['pain_url'] or 'n/a'} |" for m in modules]
    md += ["", "Each module must have: a checklist (at least 5 items), a fill-in template, and a link to the pain it answers."]
    return modules, "\n".join(md)


def _template_module(brief, m):
    if m["id"] == "quickstart":
        return (f"## {m['title']}\n\n1. Read the module that matches your problem.\n2. Copy its template.\n"
                "3. Work through the checklist.\n4. Keep the filled template next to your project.\n5. Repeat it next time.\n")
    return (f"## {m['title']}\n\nWhy this module exists: {m['pain_url']}\n\n### Checklist\n"
            "- [ ] Write down the exact situation where the problem happens\n- [ ] List what you do today, step by step\n"
            "- [ ] Mark the step that wastes the most time\n- [ ] Apply the template below to that step\n"
            "- [ ] Note what changed after one week\n\n### Template\n```\nSituation:\nCurrent steps:\nSlowest step:\nNew step:\nResult after one week:\n```\n")


def build(brief, modules):
    parts, model, cost = [f"# {brief['product_name']}\n\n{brief['tagline']}\n"], None, 0
    for m in modules:
        body = _template_module(brief, m)
        if m["id"] != "quickstart":
            extra = write("builder", f"Write 3 practical tips (one line each) for {brief['audience']} about: {m['title']}. "
                          "No numbers, no promises.", "", max_tokens=200)
            if extra["text"].strip():
                body += "\n### Tips\n" + extra["text"].strip() + "\n"
                model, cost = extra["model"], cost + extra["cost"]
        parts.append(body)
    label = f"Tips written by {model}." if model else "TEMPLATE: checklists and templates are deterministic; no model reachable for tips."
    return {"md": "\n".join(parts) + f"\n\n---\n_{label}_\n", "model": model, "cost": cost}
