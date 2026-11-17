"""Interview notes: only the founder adds them, only the notes are quoted, hypotheticals are compliments."""
import json

import pytest
from fastapi.testclient import TestClient

import app
import approval
import decision_log
import llm
import orchestrator
from agents import notes_analyst as na
from conftest import ROOT

STRONG = json.loads((ROOT / "briefs" / "strong_founder.json").read_text())
NOTES = """Ahmed (junior analyst): showed me his practice spreadsheet and booked a second call for Thursday.
Sara: said it sounds great and she would definitely buy it.
Karim: pre-ordered and paid $10 on the spot.
Mona introduced me to two classmates who are preparing for interviews.
Youssef: let me know when it is ready."""


def _run_after_phase1():
    run = orchestrator.create_run(STRONG)
    return orchestrator.advance(run["id"])


def test_rules_separate_commitments_from_compliments():
    out = na.classify_by_rules(NOTES)
    kinds = sorted(c["kind"] for c in out["commitments"])
    assert kinds == ["introduction", "money", "time"]
    assert any("would definitely buy" in c["quote"] for c in out["compliments"])
    assert not any("would definitely buy" in c["quote"] for c in out["commitments"])


def test_notes_are_stored_in_the_run_folder_and_analysed():
    run = _run_after_phase1()
    run = orchestrator.save_interview_notes(run["id"], NOTES, approval.FOUNDER)
    d = orchestrator.run_dir(run["id"])
    assert (d / "interview_notes.txt").read_text() == NOTES
    assert "phase1_step5_interview-notes.md" in run["outputs"]
    md = (d / "outputs" / "phase1_step5_interview-notes.md").read_text()
    assert "Commitments: 3" in md and "paid $10 on the spot" in md and "keyword rules (no model was available)" in md
    assert md.index("Compliments (these do not count") < md.index("would definitely buy")
    log = decision_log.read(run_id=run["id"])
    assert not decision_log.validate(log)
    assert any(e["agent"] == "notes_analyst" and e["action"] == "analyse_interview_notes" for e in log)
    added = next(e for e in log if e["action"] == "add_interview_notes")
    assert added["approved_by"] == "founder" and "Ahmed" not in json.dumps(log)  # the notes themselves are not logged
    assert orchestrator.current_gate(run)["gate"] == "evidence_gate"  # the gate is untouched


def test_only_the_founder_can_add_notes():
    run = _run_after_phase1()
    with pytest.raises(approval.ApprovalRequired):
        orchestrator.save_interview_notes(run["id"], NOTES, "agent")
    assert orchestrator.interview_notes(run["id"]) == ""


def test_notes_need_a_researched_idea_and_some_text():
    run = orchestrator.create_run(STRONG)
    with pytest.raises(ValueError):
        orchestrator.save_interview_notes(run["id"], NOTES, approval.FOUNDER)
    run = orchestrator.advance(run["id"])
    with pytest.raises(ValueError):
        orchestrator.save_interview_notes(run["id"], "ok", approval.FOUNDER)


def test_quotes_a_model_invents_are_dropped_and_hypotheticals_demoted(monkeypatch):
    def model(system, user, fallback, *, max_tokens=1200):
        data = {"commitments": [{"quote": "Karim: pre-ordered and paid $10 on the spot.", "kind": "money"},
                                {"quote": "Layla signed a contract for 50 licences.", "kind": "money"},        # not in the notes
                                {"quote": "she would definitely buy it", "kind": "money"}],                     # hypothetical
                "compliments": [{"quote": "Youssef: let me know when it is ready."},
                                {"quote": "Everyone loved the idea and wants it now."}]}                        # not in the notes
        return data, llm.LLMResult(text=json.dumps(data), model="fake-model")
    monkeypatch.setattr(llm, "complete_json", model)
    run = _run_after_phase1()
    run = orchestrator.save_interview_notes(run["id"], NOTES, approval.FOUNDER)
    md = (orchestrator.run_dir(run["id"]) / "outputs" / "phase1_step5_interview-notes.md").read_text()
    assert "Layla" not in md and "Everyone loved" not in md
    assert "Commitments: 1" in md and "2 quote(s) proposed by the model were dropped" in md
    assert md.index("Compliments (these do not count") < md.index("she would definitely buy it")


def test_secrets_in_notes_are_not_stored():
    run = _run_after_phase1()
    orchestrator.save_interview_notes(run["id"], NOTES + "\nHe gave me his login, password: hunter2 for the test account.", approval.FOUNDER)
    assert "hunter2" not in orchestrator.interview_notes(run["id"])


def test_api_adds_notes_and_respects_the_founder_token(monkeypatch):
    import config
    client = TestClient(app.app)
    run = _run_after_phase1()
    r = client.post(f"/api/runs/{run['id']}/interview-notes", json={"notes": NOTES})
    assert r.status_code == 200 and r.json()["summary"]["commitments"] == 3
    assert client.get(f"/api/runs/{run['id']}/interview-notes").json()["notes"] == NOTES
    assert client.get(f"/api/runs/{run['id']}").json()["run"]["interview_notes"]["compliments"] >= 1
    assert client.post("/api/runs/nope/interview-notes", json={"notes": NOTES}).status_code == 404
    monkeypatch.setattr(config, "FOUNDER_TOKEN", "s3cret")
    assert client.post(f"/api/runs/{run['id']}/interview-notes", json={"notes": NOTES}).status_code == 403


def test_what_people_already_do_is_problem_evidence_not_a_compliment():
    out = na.classify_by_rules("Omar: spent three weekends on LeetCode before his interview.\nSara: sounds great, I would buy it.")
    assert any("three weekends" in p["quote"] for p in out["problems"])
    assert not any("three weekends" in c["quote"] for c in out["compliments"])
    assert not any("three weekends" in c["quote"] for c in out["commitments"])


def test_a_model_compliment_about_past_effort_is_moved_to_problem_evidence(monkeypatch):
    notes = "Omar: spent three weekends on LeetCode before his interview.\nSara: sounds great."
    monkeypatch.setattr(llm, "complete_json", lambda *a, **k: (
        {"commitments": [], "compliments": [{"quote": "Omar: spent three weekends on LeetCode before his interview."},
                                            {"quote": "Sara: sounds great."}]},
        llm.LLMResult(text="{}", model="m")))
    run = _run_after_phase1()
    res = na.NotesAnalyst(run).run_step(notes, "SQL workbook")
    assert [p["quote"] for p in res.data["problems"]] == ["Omar: spent three weekends on LeetCode before his interview."]
    assert [c["quote"] for c in res.data["compliments"]] == ["Sara: sounds great."]
    assert "Problem evidence: 1" in res.content
