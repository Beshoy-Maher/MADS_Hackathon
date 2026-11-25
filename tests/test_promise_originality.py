"""Promise checker (Phase 5) and originality guard (Phase 3): what we sell matches what we built, and nothing is copied."""
import json

import pytest

import approval
import decision_log
import gates
import orchestrator
from agents import promise_checker as pcm
from agents import qa
from agents.copywriter import Copywriter
from agents.promise_checker import BROKEN, KEPT, UNVERIFIABLE, PromiseChecker, code_verdict, quote_in_product
from conftest import ROOT
from tools import originality

STRONG = json.loads((ROOT / "briefs" / "strong_founder.json").read_text())
PRODUCT = """# SQL Workbook

## Module 1: Basics
1. Read the question twice before you write any SQL at all.
Question 1: List all employees with salaries over 5000.
## Module 2: Joins
1. Join the orders table to the customers table on customer_id.
Question 2: Which customers placed no orders last month?
## Module 3: Grouping
1. Every answer here is followed by a step-by-step explanation of the query.
"""


def _all_phases(decisions_after_phase1=None):
    run = orchestrator.create_run(STRONG)
    decisions = [{"decision": "accept", "default_action": "approve"},
                 {"decision": "go", "default_action": "approve", "note": "founder override for test"}] + \
                (decisions_after_phase1 or [{"decision": "accept", "default_action": "approve"}] * 4)
    return orchestrator.run_to_gate_with(run["id"], decisions)


# ------------------------------------------------------------ promise checker: code decides
@pytest.mark.parametrize("claim,verdict", [
    ("$11.99", KEPT),
    ("Yours for $9.99 today.", BROKEN),                          # not the price set in Phase 4
    ("14-day refund, no questions asked.", KEPT),
    ("30-day refund if it does not help.", BROKEN),
    ("It's free for everyone.", BROKEN),                          # a paid product called free
    ("Feel free to ask questions in the comments.", None),        # "feel free" is not a price claim
    ("Three modules that take you from basics to grouping.", KEPT),
    ("Six modules of practice.", BROKEN),                         # the product has 3
    ("Instant download after payment.", KEPT),
    ("Includes 2 questions to practise.", KEPT),                  # 2 labelled questions exist
    ("Includes 40 practice questions.", UNVERIFIABLE),            # only 2 labelled: the founder counts, code does not call it false
    ("Builds confidence through repetition.", None),              # an opinion: code cannot decide
])
def test_code_verdicts(claim, verdict):
    v = code_verdict(claim, PRODUCT, 11.99, 14, delivery_ok=True)
    assert (v["verdict"] if v else None) == verdict, v


def test_a_delivery_promise_is_broken_when_the_delivery_test_failed():
    assert code_verdict("Instant download after payment.", PRODUCT, 11.99, 14, delivery_ok=False)["verdict"] == BROKEN


def test_only_quotes_that_are_really_in_the_product_count():
    assert quote_in_product("Every answer here is followed by a step-by-step explanation", PRODUCT)
    assert quote_in_product("every  ANSWER here is followed by a step-by-step explanation.", PRODUCT)  # spacing and case
    assert not quote_in_product("Every answer here is followed by a video walkthrough", PRODUCT)       # invented
    assert not quote_in_product("step-by-step explanation", PRODUCT)                                    # too short to prove anything


def test_the_model_can_only_prove_a_promise_with_a_real_quote(monkeypatch):
    run = orchestrator.create_run(STRONG)
    checker = PromiseChecker(run)
    real = "Every answer here is followed by a step-by-step explanation of the query"
    monkeypatch.setattr(checker, "ask_json", lambda task, fb, max_tokens=0: {"proofs": [
        {"promise": 0, "quote": real}, {"promise": 1, "quote": "Each question comes with a recorded video solution"}]})
    quotes = checker._quotes(["Every question has a worked answer", "Video solutions included"], PRODUCT)
    assert quotes == {0: real}  # the invented quote is dropped, so promise 1 stays unverifiable


# ------------------------------------------------------------ approval: a broken promise is never published
def _action(run, broken):
    a = approval.request_action(run, "publish", "store page", "Publish the store page.", {}, agent="copywriter")
    a["payload"]["promise_check"] = {KEPT: 2, BROKEN: broken, UNVERIFIABLE: 0, "broken_items": ["Six modules (the product has 3)"] * broken}
    return a


def test_a_broken_promise_cannot_be_approved_but_can_be_rejected():
    run = {"id": "pc-test", "pending_actions": [], "phase": 5}
    a = _action(run, broken=1)
    with pytest.raises(approval.BrokenPromise):
        approval.decide_action(run, a["id"], True, approval.FOUNDER)
    assert a["status"] == "pending"
    with pytest.raises(approval.ApprovalRequired):
        approval.execute_action(run, a["id"])
    assert approval.decide_action(run, a["id"], False, approval.FOUNDER)["status"] == "rejected"
    assert any(e["action"] == "blocked_broken_promise:publish" for e in decision_log.read())


def test_an_item_without_broken_promises_is_approved_as_before():
    run = {"id": "pc-test2", "pending_actions": [], "phase": 5}
    a = _action(run, broken=0)
    assert approval.decide_action(run, a["id"], True, approval.FOUNDER)["status"] == "approved"


# ------------------------------------------------------------ the pipeline
def test_phase5_checks_every_promise_and_puts_the_result_on_each_approval():
    run = _all_phases()
    assert "phase5_step4_promise-check.md" in run["outputs"]
    text = (orchestrator.run_dir(run["id"]) / "outputs" / "phase5_step4_promise-check.md").read_text()
    assert "KEPT" in text and "price $" in text
    publish = [a for a in run["pending_actions"] if a["phase"] == 5 and a["kind"] == "publish"]
    assert publish and all("promise_check" in a["payload"] for a in publish)
    assert any(e["agent"] == "promise_checker" and e["action"] == "check_promises" for e in decision_log.read())
    assert [g for g in run["gates"] if g["phase"] == 5][-1]["recommendation"] == "go"  # nothing broken in the normal run


def test_a_store_page_that_overpromises_is_blocked_and_the_launch_gate_does_not_pass(monkeypatch):
    real_copy = Copywriter._copy

    def overpromise(self, candidate, canvas, purpose):
        c = real_copy(self, candidate, canvas, purpose)
        if purpose == "store":
            c["bullets"] = c["bullets"] + ["Twelve modules covering every SQL topic."]
        return c
    monkeypatch.setattr(Copywriter, "_copy", overpromise)
    run = orchestrator.create_run(STRONG)
    run = orchestrator.run_to_gate_with(run["id"], [{"decision": "accept", "default_action": "approve"},
                                                    {"decision": "go", "default_action": "approve"},
                                                    {"decision": "accept", "default_action": "approve"},
                                                    {"decision": "accept", "default_action": "approve"},
                                                    {"decision": "accept", "default_action": "approve"}])
    store = [a for a in run["pending_actions"] if a["target"] == "store page"][-1]
    assert store["payload"]["promise_check"][BROKEN] == 1 and store["status"] == "pending"
    g = orchestrator.current_gate(run)
    assert g["phase"] == 5 and g["recommendation"] != gates.GO
    assert any(e["action"] == "flag_broken_promise" for e in decision_log.read())


def test_promise_checker_has_a_prompt_file():
    assert (ROOT / "prompts" / "promise_checker.md").exists()
    assert pcm.MIN_QUOTE_WORDS >= 6


# ------------------------------------------------------------ originality guard
EVIDENCE = [
    {"source": "github", "url": "https://github.com/alice/sql-interview-workbook", "title": "Repository alice/sql-interview-workbook: practice",
     "snippet": "A curated set of SQL interview questions with answers for data analysts who want to pass technical screens quickly"},
    {"source": "hackernews", "url": "https://news.ycombinator.com/item?id=1", "title": "Show HN: QueryCoach - daily SQL drills", "snippet": ""},
    {"source": "github", "url": "https://github.com/bob/tools/issues/7", "title": "Issue: SQL practice", "snippet": "short"},
]


def test_text_copied_from_a_source_is_found_with_its_link():
    product = "Intro. A curated set of SQL interview questions with answers for data analysts who want to pass technical screens. End."
    r = originality.check(product, "Query Practice Pack", EVIDENCE)
    assert not r["passed"]
    assert r["copy"]["passages"][0]["url"] == "https://github.com/alice/sql-interview-workbook"
    assert r["copy"]["passages"][0]["words"] >= originality.COPY_MIN_WORDS


def test_a_short_common_phrase_is_not_copying():
    product = "This set of SQL interview questions with answers for data analysts is our own."  # 11 shared words at most
    assert originality.copy_check(product, EVIDENCE)["passages"] == []


def test_a_name_taken_from_an_existing_product_clashes():
    assert originality.name_check("SQL Interview Workbook", EVIDENCE)["clashes"][0]["url"].endswith("alice/sql-interview-workbook")
    assert originality.name_check("QueryCoach", EVIDENCE)["clashes"]
    assert not originality.name_check("Analyst Interview Drills for MENA", EVIDENCE)["clashes"]
    # GitHub issues are not products, so their titles are never treated as names.
    assert all("issues" not in x["url"] for x in originality.existing_names(EVIDENCE))


def test_a_brand_in_the_name_is_a_warning_not_a_failure():
    r = originality.check("Case study templates for Figma", "Case study templates for Figma", [])
    assert r["passed"] and r["name"]["brand_warnings"] == ["figma"]


def test_qa_fails_the_build_when_the_product_is_not_original():
    orig = originality.check("x " * 10, "SQL Interview Workbook", EVIDENCE)
    results = qa.run_tests(PRODUCT, "## How to use\n## Getting help", ["M1", "M2", "M3"], "SQL workbook", reviews=None,
                           originality_result=orig)
    test = [r for r in results if r["name"] == "product_is_original"][0]
    assert not test["passed"]
    assert gates.build_gate(results).recommendation != gates.GO


def test_the_qa_report_shows_the_originality_check():
    run = _all_phases([{"decision": "accept", "default_action": "approve"}])
    text = (orchestrator.run_dir(run["id"]) / "outputs" / "phase3_step4_qa-report.md").read_text()
    assert "product_is_original | PASS" in text and "## Originality" in text


def test_the_dashboard_api_refuses_to_approve_a_broken_promise():
    from fastapi.testclient import TestClient

    import app
    run = orchestrator.create_run(STRONG)
    a = _action(run, broken=1)
    orchestrator.save(run)
    client = TestClient(app.app)
    r = client.post(f"/api/runs/{run['id']}/actions/{a['id']}", json={"approve": True})
    assert r.status_code == 400 and "broken promise" in r.json()["detail"]
    assert orchestrator.load(run["id"])["pending_actions"][-1]["status"] == "pending"
    assert client.post(f"/api/runs/{run['id']}/actions/{a['id']}", json={"approve": False}).status_code == 200
