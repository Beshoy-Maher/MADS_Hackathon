"""Evidence shown honestly (display only) and the persevere-or-pivot memo's code-built evidence lists."""
import copy
import json

import gates
import orchestrator
from conftest import ROOT

STRONG = json.loads((ROOT / "briefs" / "strong_founder.json").read_text())

PAIN = {"source": "hackernews", "url": "https://news.example/1", "title": "Ask HN: SQL interview in 2 weeks, how to best prepare?",
        "engagement": 3, "comments": 4, "created": "2020-10-02", "snippet": "junior analyst, struggling with sql interview practice",
        "community": "a", "signals": ["pain"]}
ISSUE = {"source": "github", "url": "https://github.example/o/r/issues/1", "title": "Issue: need more SQL interview questions",
         "engagement": 1, "comments": 2, "created": "2024-01-05", "snippet": "", "community": "github:b", "signals": ["pain"]}
REPO = {"source": "github", "url": "https://github.example/o/r", "title": "Repository o/r: SQL interview preparation",
        "engagement": 600, "comments": 0, "created": "", "snippet": "", "community": "github:o", "signals": ["existing_solution"]}


def test_evidence_is_split_into_problem_posts_and_existing_solutions_with_dates():
    from tools import evidence_view
    problem, existing = evidence_view.split_evidence([REPO, PAIN, ISSUE])
    assert problem == [PAIN, ISSUE] and existing == [REPO]
    lines = "\n".join(evidence_view.evidence_sections([REPO, PAIN, ISSUE]))
    assert "People describing the problem (2):" in lines and "Existing solutions (1):" in lines
    assert "2020-10-02" in lines and "2024-01-05" in lines and "date unknown" in lines


def test_problem_and_location_without_a_fetched_source_are_assumptions():
    from tools import evidence_view
    egypt = "Junior data analysts in Egypt struggle to find affordable SQL interview practice."
    assert evidence_view.labelled(egypt, [PAIN, REPO]).startswith("ASSUMPTION (no fetched source mentions Egypt)")
    assert evidence_view.labelled("Junior analysts struggle with SQL interview practice.", [PAIN]).endswith(f"({PAIN['url']}))")
    assert evidence_view.labelled("Junior analysts struggle with SQL interview practice.", [REPO]).startswith("ASSUMPTION")
    cairo = dict(PAIN, snippet="I am in Cairo, struggling with sql interview practice")
    assert not evidence_view.labelled(egypt, [cairo]).startswith("ASSUMPTION")


def test_market_customer_line_is_labelled_without_a_source():
    from agents.market_analyst import label_customer_line
    body = "## Ideal customer profile\n- **Who:** Junior data analysts in Egypt\n- Trigger: first interview\n## Market size\n- ASSUMPTION"
    out = label_customer_line(body, [PAIN])
    assert "- **Who:** ASSUMPTION (no fetched source mentions Egypt): Junior data analysts in Egypt" in out
    assert "- Trigger: first interview" in out


def test_evidence_gate_is_the_same_before_and_after_the_display_change():
    """The split and the labels are presentation only: scores, gate numbers and recommendation do not change."""
    from agents.researcher import evidence_sections_or_none
    from agents.scorer import score_candidate
    from tools import evidence_view
    cands = [{"title": "SQL interview workbook for junior analysts in Egypt", "problem": "Junior analysts in Egypt struggle with SQL interviews.",
              "evidence": [PAIN, ISSUE, REPO] + [dict(PAIN, url=f"https://news.example/{i}", community=f"c{i}") for i in range(2, 9)]},
             {"title": "Resume guide", "problem": "Juniors need resumes.", "evidence": [REPO]}]
    before_cands = copy.deepcopy(cands)
    before = gates.evidence_gate([score_candidate(STRONG, c, 1.0) for c in cands]).as_dict()
    for c in cands:  # everything the opportunities file and the scorecard now show
        evidence_view.labelled(c["problem"], c["evidence"])
        evidence_view.evidence_sections(c["evidence"])
        evidence_sections_or_none(c["evidence"])
    assert cands == before_cands
    after = gates.evidence_gate([score_candidate(STRONG, c, 1.0) for c in cands]).as_dict()
    assert after == before


def test_phase1_outputs_show_the_split_and_the_gate_is_unchanged():
    run = orchestrator.create_run(STRONG)
    run = orchestrator.advance(run["id"])
    out = orchestrator.run_dir(run["id"]) / "outputs"
    opp = (out / "phase1_step1_opportunities.md").read_text()
    card = (out / "phase1_step2_scorecard.md").read_text()
    for text in (opp, card):
        assert "People describing the problem (" in text and "Existing solutions (" in text
    g = orchestrator.current_gate(run)
    scores = run["ctx"]["scores"]
    assert gates.evidence_gate(scores, 1, run["ctx"]["sources_ok"]).recommendation == g["recommendation"]


# ------------------------------------------------------------- persevere-or-pivot memo
HISTORY = [{"phase": 1, "gate": "evidence_gate", "recommendation": "go", "founder_decision": "go"},
           {"phase": 2, "gate": "demand_gate", "recommendation": "repeat", "founder_decision": "go"},
           {"phase": 3, "gate": "build_gate", "recommendation": "go", "founder_decision": "go"}]


def test_memo_evidence_lists_are_built_from_facts():
    from agents.analyst import MISSING, memo_evidence
    ev_for, ev_against = memo_evidence(HISTORY, real_buyers=0, refund_rate=None, signups=None)
    assert any("Phase 1 evidence_gate" in x for x in ev_for) and any("Phase 3 build_gate" in x for x in ev_for)
    assert any("Phase 2 demand_gate" in x and "overrode it with GO" in x for x in ev_against)
    assert any(x.startswith("0 real buyers") for x in ev_against)
    assert any("sign-ups: not measured" in x for x in ev_against) and any("Refund rate: not measurable" in x for x in ev_against)
    assert not any(MISSING.search(x) for x in ev_for)
    ev_for, ev_against = memo_evidence([], real_buyers=12, refund_rate=0.05, signups=0)
    assert any("12 real buyer" in x for x in ev_for) and any("Refund rate 5%" in x for x in ev_for)
    assert any("0 real waitlist sign-ups" in x for x in ev_against)


def test_memo_model_writes_only_reasoning_without_numbers(monkeypatch):
    import llm
    from agents.analyst import MISSING, Analyst
    run = orchestrator.create_run(STRONG)
    spun = ("**Evidence For:**\n- Demand signals such as sign-ups are not documented.\n- 5 gates passed.\n\n"
            "The product is built, but nobody has bought it yet. We had 0 buyers. Keep operating and talk to real users.")
    monkeypatch.setattr(llm, "complete", lambda *a, **k: llm.LLMResult(text=spun, model="fake-model"))
    g = gates.operate_gate(real_buyers=0, refund_rate=None, waitlist=None)
    res = Analyst(run).pivot_memo({"title": "SQL workbook"}, g, HISTORY, real_buyers=0, refund_rate=None, waitlist={"count": None},
                                  mock_sales={"reconciliation": {"orders": 3}})
    text = res.content
    ev_for = text.split("## Evidence for")[1].split("## Evidence against")[0]
    reasoning = text.split("## Reasoning")[1].split("## What would change")[0]
    assert "not documented" not in text and "5 gates" not in text and "0 buyers" not in reasoning
    assert "nobody has bought it yet" in reasoning and not any(ch.isdigit() for ch in reasoning)
    assert not any(MISSING.search(l) for l in ev_for.splitlines() if l.startswith("- "))
    assert "MOCKED test orders (3) are excluded" in text


def test_memo_evidence_lists_are_not_debated():
    from agents.critic import _apply_problem, doc_text
    run = orchestrator.create_run(STRONG)
    from agents.analyst import Analyst
    g = gates.operate_gate(real_buyers=0, refund_rate=None, waitlist=None)
    res = Analyst(run).pivot_memo({"title": "SQL workbook"}, g, HISTORY)
    debated = doc_text(res.content)
    assert "Evidence for" not in debated and "overrode it with GO" not in debated and "0 real buyers" not in debated
    path = orchestrator.run_dir(run["id"]) / "memo.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(res.content)
    why = _apply_problem("the founder overrode it with GO.", "the founder chose GO.", path, set())
    assert why == "the quote is on a line computed by code"


def test_debate_never_removes_an_assumption_label(tmp_path):
    from agents.critic import _apply_problem
    doc = tmp_path / "phase1_step1_opportunities.md"
    doc.write_text("## Idea\n\n- Problem: ASSUMPTION (no fetched source mentions Egypt): Analysts in Egypt struggle with SQL.\n")
    why = _apply_problem("ASSUMPTION (no fetched source mentions Egypt): Analysts in Egypt struggle",
                         "Analysts struggle", doc, set())
    assert why == "the replacement would remove an ASSUMPTION label"


def test_memo_reasoning_has_no_dangling_link_after_a_dropped_sentence():
    from agents.analyst import reasoning_only
    out = reasoning_only("We have 0 buyers. Despite this, the founder chose to go on. Talk to real users.")
    assert out == "The founder chose to go on. Talk to real users."
