"""Nothing goes out without the founder: enforced in code."""
import pytest

import approval
import decision_log
import orchestrator


def _run():
    return {"id": "t-run", "phase": 2, "pending_actions": []}


def test_unapproved_action_cannot_execute():
    run = _run()
    a = approval.request_action(run, "publish", "landing page", "publish it")
    with pytest.raises(approval.ApprovalRequired):
        approval.execute_action(run, a["id"])
    assert not a["executed"]


def test_agent_cannot_approve():
    run = _run()
    a = approval.request_action(run, "send", "outreach", "send it")
    with pytest.raises(approval.ApprovalRequired):
        approval.decide_action(run, a["id"], True, actor="copywriter")
    assert a["status"] == "pending"


def test_rejected_action_never_executes():
    run = _run()
    a = approval.request_action(run, "publish", "post", "post it")
    approval.decide_action(run, a["id"], False, actor="founder")
    with pytest.raises(approval.ApprovalRequired):
        approval.execute_action(run, a["id"])


def test_approved_action_is_stubbed_and_logged(tmp_path):
    run = _run()
    a = approval.request_action(run, "publish", "store page", "publish")
    approval.decide_action(run, a["id"], True, actor="founder")
    approval.execute_action(run, a["id"], outbox_path=tmp_path / "outbox.jsonl")
    assert "STUBBED" in a["execution"]
    assert (tmp_path / "outbox.jsonl").exists()
    entries = decision_log.read(run_id="t-run")
    assert any(e["approved_by"] == "founder" for e in entries)


def test_pipeline_waits_for_founder_at_gate():
    run = orchestrator.create_run({"founder_name": "Mariam", "idea": "A practice workbook of SQL interview questions for junior data analysts",
                                   "skills": ["SQL", "data analysis"], "budget_usd": 50, "hours_per_week": 10,
                                   "target_market": "junior data analysts"})
    run = orchestrator.advance(run["id"])
    assert run["status"] == "awaiting_founder" and run["phase"] == 1
    again = orchestrator.advance(run["id"])  # advancing again must not skip the gate
    assert again["phase"] == 1 and again["status"] == "awaiting_founder"
    with pytest.raises(approval.ApprovalRequired):
        orchestrator.decide(run["id"], "go", actor="orchestrator")
