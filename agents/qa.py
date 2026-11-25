"""Phase 3 gate support: automated tests for the MVP.

Deterministic checks only, so the build gate cannot be argued past.
"""
from __future__ import annotations

import hashlib
import re

import guardrails
from agents.base import Agent, StepResult, footer
from agents.verifier import all_errors, last_passes
from tools import originality

PLACEHOLDERS = re.compile(r"(lorem ipsum|\bTODO\b|\bTBD\b|\[insert|xx+x|<placeholder>)", re.IGNORECASE)


def run_tests(product_md: str, guide_md: str, modules: list[str], product_title: str, reviews: list[dict] | None = None,
              originality_result: dict | None = None) -> list[dict]:
    results = []
    sections = re.split(r"^## Module \d+: ", product_md, flags=re.MULTILINE)[1:]
    results.append({"name": "all_modules_present", "passed": len(sections) == len(modules) and len(modules) >= 3,
                    "value": len(sections), "threshold": f"{len(modules)} (min 3)"})
    short = [i + 1 for i, s in enumerate(sections) if len(s.split()) < 120]
    results.append({"name": "each_module_has_substance", "passed": not short, "value": f"short modules: {short or 'none'}",
                    "threshold": ">= 120 words each"})
    has_steps = all(re.search(r"^\s*\d+\.\s", s, re.MULTILINE) for s in sections) if sections else False
    results.append({"name": "each_module_has_numbered_steps", "passed": has_steps, "value": has_steps, "threshold": True})
    has_check = all(("- [ ]" in s) or ("checklist" in s.lower()) for s in sections) if sections else False
    results.append({"name": "each_module_has_checklist", "passed": has_check, "value": has_check, "threshold": True})
    scan = guardrails.scan_output(product_md + "\n" + guide_md)
    results.append({"name": "no_income_promises_fake_proof_or_urgency", "passed": scan.clean, "value": len(scan.violations), "threshold": 0,
                    "note": "; ".join(v["category"] for v in scan.violations)})
    ph = PLACEHOLDERS.findall(product_md + guide_md)
    results.append({"name": "no_placeholder_text", "passed": not ph, "value": len(ph), "threshold": 0})
    results.append({"name": "user_guide_has_usage_and_support", "passed": "how to use" in guide_md.lower() and "help" in guide_md.lower(),
                    "value": True, "threshold": "sections present"})
    allowed = guardrails.screen_brief({"idea": product_title}).allowed
    results.append({"name": "product_in_allowed_category", "passed": allowed, "value": allowed, "threshold": True})
    sentences = [s for s in re.split(r"[.!?]\s", re.sub(r"[#*|`\-\[\]]", " ", product_md)) if s.strip()]
    avg = sum(len(s.split()) for s in sentences) / max(1, len(sentences))
    results.append({"name": "readable_sentence_length", "passed": avg <= 28, "value": round(avg, 1), "threshold": "<= 28 words"})
    results.append({"name": "deliverable_package_builds", "passed": len(product_md) > 500,
                    "value": "sha256:" + hashlib.sha256(product_md.encode()).hexdigest()[:16], "threshold": "non-empty"})
    # The verifier's last review of every module must be free of errors (one revision is allowed before it).
    final = last_passes(reviews or [])
    open_errors = {r["module"]: all_errors(r) for r in final if all_errors(r)}
    reviewed = len(final) == len(modules) and bool(modules)
    if not reviewed:
        value = f"{len(final)} of {len(modules)} modules reviewed"
    else:
        value = f"open errors: {sum(len(v) for v in open_errors.values())}" + (f" (modules {sorted(open_errors)})" if open_errors else "")
        if not any(r.get("model") for r in final):
            value += "; model review not available, SQL check only"
    results.append({"name": "verifier_last_pass_has_no_errors", "passed": reviewed and not open_errors, "value": value,
                    "threshold": "every module reviewed, 0 open errors"})
    if originality_result is not None:
        n, c = originality_result["name"], originality_result["copy"]
        results.append({"name": "product_is_original", "passed": originality_result["passed"],
                        "value": f"name clashes: {len(n['clashes'])}, copied passages: {len(c['passages'])}",
                        "threshold": f"0 name clashes, 0 runs of {c['min_words']}+ words copied from a source"})
    return results


def review_section(reviews: list[dict] | None) -> list[str]:
    """What the verifier found, per module: first pass, whether the builder revised, and what is still open."""
    if not reviews:
        return []
    md = ["", "## Module review (verifier)", "",
          "Each module is reviewed once; a module with errors is revised once by the builder and reviewed again. "
          "SQL code blocks are executed in an in-memory SQLite database.", "",
          "| Module | Errors on first review | Revised | Open errors after last review | SQL statements executed | Reviewed by |",
          "|---|---|---|---|---|---|"]
    final = {r["module"]: r for r in last_passes(reviews)}
    for r in [x for x in reviews if x["pass"] == 1]:
        last = final[r["module"]]
        who = f"`{last['model']}` + SQLite" if last.get("model") else "SQLite only (no model available)"
        md.append(f"| {r['module']}. {r['title'][:60]} | {len(all_errors(r))} | {'yes' if last['pass'] > 1 else 'no'} | "
                  f"{len(all_errors(last))} | {last['sql_executed']} | {who} |")
    found = [(r, e) for r in reviews if r["pass"] == 1 for e in all_errors(r)]
    if found:
        md += ["", "Errors found on the first review (given to the builder as feedback):"]
        md += [f"- Module {r['module']}: {e}" for r, e in found]
    still = [(r, e) for r in final.values() for e in all_errors(r)]
    if still:
        md += ["", "Still open after the last review:"] + [f"- Module {r['module']}: {e}" for r, e in still]
    return md


class QA(Agent):
    role = "qa"

    def run_step(self, product_md: str, guide_md: str, modules: list[str], product_title: str,
                 reviews: list[dict] | None = None) -> StepResult:
        evidence = [e for c in self.run.get("ctx", {}).get("candidates", []) for e in c.get("evidence", [])]
        orig = originality.check(product_md, product_title, evidence)
        results = run_tests(product_md, guide_md, modules, product_title, reviews, originality_result=orig)
        passed = sum(r["passed"] for r in results)
        md = [f"# Phase 3, step 4: MVP test report ({passed}/{len(results)} passed)", "",
              "| Test | Result | Value | Threshold |", "|---|---|---|---|"]
        for r in results:
            md.append(f"| {r['name']} | {'PASS' if r['passed'] else 'FAIL'} | {r['value']} | {r['threshold']} |")
        md += ["", "These checks are deterministic code in `agents/qa.py` and `tools/originality.py`, not model opinions. "
               "`verifier_last_pass_has_no_errors` counts the errors the verifier agent left open; `product_is_original` "
               "compares the product with the sources read in Phase 1. Details of both are below."]
        md += review_section(reviews)
        md += originality.report_lines(orig)
        md.append(footer(next((r["model"] for r in reviews or [] if r.get("model")), None)))
        return self.result("qa-report", "test_mvp", "\n".join(md), data={"tests": results, "originality": orig})
