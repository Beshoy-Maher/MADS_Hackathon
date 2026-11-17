"""Phase 3 verifier: module review, one revision, SQL execution, the QA test and the decision log.

Runs with LLM_PROVIDER=none (see conftest). Where a model answer is needed, llm.complete / llm.complete_json are replaced by fakes.
"""
import json

import decision_log
import llm
import orchestrator
from agents import qa
from agents import verifier as v
from conftest import ROOT

STRONG = json.loads((ROOT / "briefs" / "strong_founder.json").read_text())
SIX = [{"decision": "accept", "default_action": "approve"},
       {"decision": "go", "default_action": "approve", "note": "founder override for test"}] + \
      [{"decision": "accept", "default_action": "approve"}] * 4

GOOD_SQL = """Count orders per customer:

```sql
SELECT c.name, COUNT(o.id) AS orders
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.id
WHERE o.created_at >= '2024-01-01'
GROUP BY c.name
HAVING COUNT(o.id) > 2
ORDER BY orders DESC;
```
"""
BAD_SQL = """```sql
SELECT name, FROM employees WHERE salary > 1000;
```
"""
FILLER = " ".join(["Write the query, run it, and compare the result with the expected rows."] * 14)


def _module(text: str) -> str:
    return f"Intro.\n\n1. Read the question.\n2. Write the query.\n\n{text}\n\n- [ ] Checked the result\n\n{FILLER}"


# ----------------------------------------------------------------- SQL check
def test_valid_sql_runs_with_inferred_tables():
    r = v.check_sql(GOOD_SQL)
    assert r == {"blocks": 1, "executed": 1, "errors": []}


def test_sql_syntax_error_is_reported():
    r = v.check_sql(BAD_SQL)
    assert r["executed"] == 1 and len(r["errors"]) == 1 and "syntax error" in r["errors"][0]


def test_aggregate_in_where_is_reported():
    r = v.check_sql("```sql\nSELECT dept FROM staff WHERE COUNT(*) > 3 GROUP BY dept;\n```")
    assert r["errors"] and "aggregate" in r["errors"][0]


def test_sql_that_cannot_be_judged_is_skipped_silently():
    text = ("```sql\nSELECT DATE_TRUNC('month', created_at) FROM sales.orders;\n```\n"      # schema-qualified table, dialect function
            "```sql\nSELECT ... FROM orders;\n```\n"                                         # a sketch, not code
            "```sql\nWITH t AS (SELECT 1 AS a) SELECT t.missing FROM t;\n```\n"              # column of a CTE: not inferable
            "```sql\nEXPLAIN ANALYZE SELECT 1;\n```\n"                                      # not a statement we run
            "```python\nprint('not sql')\n```")
    assert v.check_sql(text)["errors"] == []


def test_tables_defined_by_the_example_are_used():
    text = ("```sql\nCREATE TABLE users (id INTEGER, name TEXT);\nINSERT INTO users VALUES (1, 'A');\n"
            "SELECT name FROM users WHERE id = 1;\n```")
    assert v.check_sql(text) == {"blocks": 1, "executed": 3, "errors": []}


def test_sql_check_cannot_touch_the_disk(tmp_path):
    target = tmp_path / "leak.db"
    v.check_sql(f"```sql\nATTACH DATABASE '{target}' AS x;\nCREATE TABLE x.t (a);\nSELECT 1;\n```")
    assert not target.exists()


def test_no_sql_blocks_means_nothing_to_report():
    assert v.check_sql("Plain text with no code.") == {"blocks": 0, "executed": 0, "errors": []}


# --------------------------------------------------- pipeline, without a model
def test_pipeline_logs_a_review_for_every_module_without_a_model():
    run = orchestrator.create_run(STRONG)
    run = orchestrator.run_to_gate_with(run["id"], SIX)
    log = decision_log.read(run_id=run["id"])
    reviews = [e for e in log if e["agent"] == "verifier" and e["action"] == "review_module"]
    assert len(reviews) == len(run["ctx"]["spec"]["modules"]) >= 3
    assert not decision_log.validate(log)
    assert all(e["model"] is None and e["outcome"] == "clean" for e in reviews)
    assert not [e for e in log if e["action"] == "revise_module"]  # nothing to revise
    build = [g for g in run["gates"] if g["phase"] == 3][-1]
    check = next(c for c in build["checks"] if c["name"] == "verifier_last_pass_has_no_errors")
    assert check["passed"] and "model review not available" in str(check["value"])
    report = (orchestrator.run_dir(run["id"]) / "outputs" / "phase3_step4_qa-report.md").read_text()
    assert "## Module review (verifier)" in report and "SQLite only (no model available)" in report


# ------------------------------------------------------ pipeline, fake model
def _fake_model(monkeypatch, first_draft: str, revised: str, verdicts: list[dict]):
    """Builder writes `first_draft`, rewrites to `revised`; the verifier answers with `verdicts` in turn (then: no errors)."""
    calls = {"review": 0, "revise": 0}

    def complete(system, user, fallback, *, json_mode=False, max_tokens=1200):
        if "A reviewer found these errors" in user:
            calls["revise"] += 1
            return llm.LLMResult(text=revised, model="fake-model")
        if "Write this module's content" in user:
            return llm.LLMResult(text=first_draft, model="fake-model")
        return llm.LLMResult(text=fallback, model=None)

    def complete_json(system, user, fallback, *, max_tokens=1200):
        if "List the factual errors" in user:
            calls["review"] += 1
            data = verdicts.pop(0) if verdicts else {"errors": []}
            return data, llm.LLMResult(text=json.dumps(data), model="fake-model")
        return fallback, llm.LLMResult(text=json.dumps(fallback), model=None)

    monkeypatch.setattr(llm, "complete", complete)
    monkeypatch.setattr(llm, "complete_json", complete_json)
    return calls


def _to_build_gate(run_id: str) -> dict:
    return orchestrator.run_to_gate_with(run_id, SIX[:3])


def test_module_with_errors_is_revised_once_and_reviewed_again(monkeypatch):
    wrong = _module("COUNT(*) ignores NULL rows in every database.")
    fixed = _module("COUNT(*) counts every row; COUNT(column) skips NULL values.")
    verdicts = [{"errors": [{"quote": "COUNT(*) ignores NULL rows in every database", "problem": "COUNT(*) counts all rows."}]}]
    calls = _fake_model(monkeypatch, wrong, fixed, verdicts)
    run = orchestrator.create_run(STRONG)
    run = _to_build_gate(run["id"])
    n = len(run["ctx"]["spec"]["modules"])
    log = decision_log.read(run_id=run["id"])
    reviews = [e for e in log if e["action"] == "review_module"]
    assert calls["revise"] == 1 and len(reviews) == n + 1       # only module 1 had an error; it got exactly one more review
    assert [e["outcome"] for e in reviews[:2]] == ["errors", "clean"]
    assert all(e["agent"] == "verifier" and e["model"] == "fake-model" for e in reviews)
    assert len([e for e in log if e["agent"] == "builder" and e["action"] == "revise_module"]) == 1
    assert not decision_log.validate(log)
    product = (orchestrator.run_dir(run["id"]) / "outputs" / "phase3_step2_product.md").read_text()
    assert "COUNT(column) skips NULL values" in product
    build = [g for g in run["gates"] if g["phase"] == 3][-1]
    assert build["recommendation"] == "go"


def test_errors_left_after_the_revision_fail_the_qa_test(monkeypatch):
    wrong = _module("A primary key may contain duplicate values.")
    bad = {"errors": [{"quote": "A primary key may contain duplicate values", "problem": "Primary keys are unique."}]}
    calls = _fake_model(monkeypatch, wrong, wrong + "\n\nOne more line.", [bad, dict(bad)])
    run = orchestrator.create_run(STRONG)
    run = _to_build_gate(run["id"])
    assert calls["revise"] == 1                                 # one revision at most, even though the error is still there
    build = [g for g in run["gates"] if g["phase"] == 3][-1]
    check = next(c for c in build["checks"] if c["name"] == "verifier_last_pass_has_no_errors")
    assert not check["passed"] and build["recommendation"] == "repeat"
    report = (orchestrator.run_dir(run["id"]) / "outputs" / "phase3_step4_qa-report.md").read_text()
    assert "Still open after the last review" in report


def test_sql_syntax_error_goes_to_the_builder_as_feedback(monkeypatch):
    seen = {}
    calls = _fake_model(monkeypatch, _module(BAD_SQL), _module(GOOD_SQL), [])
    original = llm.complete

    def spy(system, user, fallback, **kw):
        if "A reviewer found these errors" in user:
            seen["feedback"] = user
        return original(system, user, fallback, **kw)
    monkeypatch.setattr(llm, "complete", spy)
    run = orchestrator.create_run(STRONG)
    run = _to_build_gate(run["id"])
    assert "syntax error" in seen["feedback"] and calls["revise"] >= 1
    assert [g for g in run["gates"] if g["phase"] == 3][-1]["recommendation"] == "go"


def test_an_error_whose_quote_is_not_in_the_module_is_dropped(monkeypatch):
    invented = [{"errors": [{"quote": "the moon is made of cheese and tables", "problem": "not in the text"}]}]
    calls = _fake_model(monkeypatch, _module("Use GROUP BY to count rows per group."), "unused", invented)
    run = orchestrator.create_run(STRONG)
    run = _to_build_gate(run["id"])
    assert calls["revise"] == 0
    assert all(e["outcome"] == "clean" for e in decision_log.read(run_id=run["id"]) if e["action"] == "review_module")


# ------------------------------------------------------------------- QA test
def test_qa_fails_when_a_module_was_never_reviewed():
    product = "\n".join(f"## Module {i}: M{i}\n\n" + _module("text") for i in (1, 2, 3))
    results = qa.run_tests(product, "## How to use\n## Getting help", ["M1", "M2", "M3"], "SQL workbook", reviews=None)
    assert not next(r for r in results if r["name"] == "verifier_last_pass_has_no_errors")["passed"]
    clean = [{"module": i, "title": f"M{i}", "pass": 1, "errors": [], "sql_errors": [], "sql_blocks": 0, "sql_executed": 0, "model": None}
             for i in (1, 2, 3)]
    results = qa.run_tests(product, "## How to use\n## Getting help", ["M1", "M2", "M3"], "SQL workbook", reviews=clean)
    assert next(r for r in results if r["name"] == "verifier_last_pass_has_no_errors")["passed"]


# ------------------------------------------------- format slips and unfenced SQL
def test_broken_checkbox_and_split_number_are_reported():
    text = "- [ ] fine\n- [_ ] 3 employee records inserted\n\n| name | salary |\n|---|---|\n| Ahmed | 500 0  |\n| Sara | 7000 |"
    errs = v.format_errors(text)
    assert len(errs) == 2 and "checklist box" in errs[0] and "500 0" in errs[1]
    assert v.format_errors("- [ ] a\n- [x] b\n| 1 | 5000 |\n```\n- [_ ] inside code is left alone\n```") == []


def test_a_query_written_outside_a_code_block_is_still_executed():
    text = "Query:\nSELECT users.name, orders.amount\nFROM users\nINNER JOIN orders\nON users.user_id = orders.user_id;\n\nResult: two rows."
    assert v.check_sql(text) == {"blocks": 1, "executed": 1, "errors": []}
    bad = "Query:\nSELECT name FROM users WHERE COUNT(*) > 1;\n"
    assert "aggregate" in v.check_sql(bad)["errors"][0]


def test_format_slips_reach_the_builder_and_fail_qa_if_left(monkeypatch):
    broken = _module("| name | salary |\n|---|---|\n| Ahmed | 500 0 |")
    calls = _fake_model(monkeypatch, broken, broken + "\n\nStill broken.", [])
    run = orchestrator.create_run(STRONG)
    run = _to_build_gate(run["id"])
    assert calls["revise"] >= 1
    build = [g for g in run["gates"] if g["phase"] == 3][-1]
    assert build["recommendation"] == "repeat"


def test_a_stray_character_in_a_checklist_box_is_repaired():
    from agents.builder import Builder
    assert Builder._clean("- [_ ] one\n- [- ] two\n- [ ] three\n- [x] done") == "- [ ] one\n- [ ] two\n- [ ] three\n- [x] done"
