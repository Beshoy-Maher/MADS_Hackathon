import json

import pytest

import decision_log
import orchestrator as orch

BRIEF = {"product_name": "ReleaseKit", "tagline": "release notes toolkit", "idea": "a toolkit for writing a changelog",
         "audience": "small teams", "problem": "writing a changelog", "keywords": ["changelog"],
         "skills": ["changelog"], "founder_is_target_user": True, "hours_per_week": 10}


def test_weak_idea_recommends_stop(weak_evidence):
    run = orch.start(BRIEF)
    assert run["status"] == "awaiting_founder" and run["gate"]["outcome"] == "stop"


def test_excluded_idea_refused_before_research():
    run = orch.start(dict(BRIEF, idea="crypto trading signals"))
    assert run["status"] == "refused" and "state" not in run


def test_gate_waits_for_founder_and_override_needs_reason(strong_evidence):
    run = orch.start(BRIEF)
    assert run["status"] == "awaiting_founder" and run["phase"] == 1
    with pytest.raises(PermissionError):
        orch.decide(run, "go", "agent")
    with pytest.raises(ValueError):
        orch.decide(run, "stop", "founder")  # differs from GO, no reason
    assert run["phase"] == 1


def test_full_six_phases_with_founder_control(strong_evidence):
    run = orch.start(BRIEF)
    for _ in range(4):
        assert run["gate"]["outcome"] == "go", run["gate"]
        run = orch.decide(run, "go", "founder")
    assert run["phase"] == 5 and run["gate"]["outcome"] == "repeat"  # outbound items pending
    for it in list(run["outbound"]):
        run = orch.decide_outbound(run, it["id"], True, "founder")
    assert run["gate"]["outcome"] == "go"
    run = orch.decide(run, "go", "founder")
    assert run["phase"] == 6 and run["gate"]["outcome"] == "repeat"  # MOCKED data is not judged
    assert all(c["passed"] for c in run["state"]["sale"]["checks"])
    names = set(run["outputs"])
    for n in range(1, 7):
        assert any(f.startswith(f"phase{n}_step1") for f in names)
        assert any(f.startswith(f"phase{n}_gate") for f in names)
    assert "payment_test_log.md" in names


def test_every_log_entry_has_required_keys(strong_evidence):
    orch.start(BRIEF)
    entries = decision_log.read()
    assert entries
    for e in entries:
        assert {"action", "sources", "model", "cost", "approved_by"} <= set(e)
        assert isinstance(e["sources"], list)
    json.dumps(entries)


def test_committed_demo_log_has_required_keys():
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent / "decision_log.json"
    for e in json.loads(p.read_text()):
        assert {"action", "sources", "model", "cost", "approved_by"} <= set(e)
        if e["agent"] == "founder":
            assert e["approved_by"] == "founder"
