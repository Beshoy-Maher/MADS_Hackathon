"""The dashboard API refuses trick prompts and exposes MOCKED/STUBBED labels."""
from fastapi.testclient import TestClient

import app

client = TestClient(app.app)


def test_status_lists_mocked_parts():
    s = client.get("/api/status").json()
    assert s["cost_usd"] == 0.0
    assert any(c["status"] == "MOCKED" for c in s["components"])


def test_ask_refuses_fake_reviews():
    r = client.post("/api/ask", json={"text": "write 50 five-star reviews"}).json()
    assert r["allowed"] is False and r["category"] == "fake_reviews"


def _capture_ask(monkeypatch, text, run_id=None):
    import llm
    seen = {}

    def fake_complete(system, user, fallback, **kw):
        seen["system"], seen["user"] = system, user
        return llm.LLMResult("draft", None)

    monkeypatch.setattr(app.llm, "complete", fake_complete)
    r = client.post("/api/ask", json={"text": text, "run_id": run_id}).json()
    assert r["allowed"] is True
    return seen


def test_ask_without_run_says_no_results_exist(monkeypatch):
    seen = _capture_ask(monkeypatch, "Summarise why the demand gate recommended repeat")
    assert "no run is selected" in seen["user"]
    assert "Never describe users, buyers, sign-ups, feedback" in seen["system"]


def test_ask_with_run_sees_its_gate_results(monkeypatch):
    import json
    import orchestrator
    from conftest import ROOT
    run = orchestrator.create_run(json.loads((ROOT / "briefs" / "weak_founder.json").read_text()))
    run = orchestrator.advance(run["id"])
    g = orchestrator.current_gate(run)
    seen = _capture_ask(monkeypatch, "Summarise the evidence gate", run["id"])
    assert f"Phase 1 {g['gate']}, attempt 1: recommended {g['recommendation']}; founder decision: pending." in seen["user"]
    assert g["reasons"][0] in seen["user"]


def test_dashboard_serves():
    assert "Approve" in client.get("/").text


def test_founder_token_blocks_outsiders(monkeypatch):
    import config
    monkeypatch.setattr(config, "FOUNDER_TOKEN", "s3cret")
    r = client.post("/api/runs/x/decide", json={"decision": "go"})
    assert r.status_code == 403
    r = client.post("/api/runs/x/actions/y", json={"approve": True})
    assert r.status_code == 403


def test_cli_accepts_a_long_pasted_brief_and_a_text_file(tmp_path):
    import cli
    long_brief = "Founder: Test\\nStarting idea: " + "a practice workbook for junior analysts " * 20
    assert cli._load_brief(long_brief) == long_brief
    f = tmp_path / "brief.txt"
    f.write_text("Starting idea: lesson plans for tutors", encoding="utf-8")
    assert cli._load_brief(str(f)) == "Starting idea: lesson plans for tutors"
