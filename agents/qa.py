"""QA: fixed checks that the product matches its spec (no model)."""
import re

import guardrails


def check(modules, product_md, ledger):
    urls = {i["url"] for i in ledger["items"]}
    checks = []
    for m in modules:
        sec = product_md.split(f"## {m['title']}", 1)
        present = len(sec) == 2
        body = sec[1].split("\n## ", 1)[0] if present else ""
        checks.append({"name": f"{m['id']} present", "passed": present})
        if m["id"] != "quickstart":
            checks.append({"name": f"{m['id']} checklist has >= 5 items", "passed": len(re.findall(r"- \[ \]", body)) >= 5})
            checks.append({"name": f"{m['id']} has a template", "passed": "```" in body})
            checks.append({"name": f"{m['id']} cites a fetched source", "passed": m["pain_url"] in urls and m["pain_url"] in body})
    checks.append({"name": "no rule violations in product", "passed": not guardrails.clean(product_md)[1]})
    passed = sum(c["passed"] for c in checks)
    md = "# Phase 3 Step 3: QA report\n\n_Plain code, no model._\n\n| Check | Result |\n|---|---|\n" + "\n".join(
        f"| {c['name']} | {'PASS' if c['passed'] else 'FAIL'} |" for c in checks) + f"\n\n**{passed}/{len(checks)} passed.**\n"
    return {"checks": checks, "passed": passed, "total": len(checks), "md": md}
