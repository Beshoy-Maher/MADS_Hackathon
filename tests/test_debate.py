"""Debate before each gate (critic vs. authors) and per-role model routing. No model, no network."""
import json

import pytest

import config
import llm
import orchestrator
from agents import critic as critic_mod
from agents.base import StepResult
from agents.critic import Critic

@pytest.fixture(autouse=True)
def _fresh_model_status():
    """Routing tests fake an Ollama server; never let their cached status leak into other tests."""
    llm._status_cache["value"] = None
    llm._failed.clear()
    yield
    llm._status_cache["value"] = None
    llm._failed.clear()


DOC = ("The market for SQL interview prep is worth $2 billion and growing fast. "
       "Junior analysts ask for practice sets on Hacker News every week.")


def _run():
    return {"id": "debate-test", "brief": {"idea": "SQL interview workbook", "target_market": "junior analysts"},
            "ctx": {"candidates": [{"evidence": [{"url": "https://news.ycombinator.com/item?id=1"}]}]}}


def _fake_models(calls):
    """critic: one real quote, one invented quote; author: defends without a source; critic: says resolved."""
    def fake(system, user, fallback, *, max_tokens=1200, temperature=None, role="writer"):
        calls.append(role)
        res = llm.LLMResult(text="{}", model=f"{role}-model")
        if role == "critic" and '"objections"' in user:
            return {"objections": [
                {"document": 1, "quote": "is worth $2 billion and growing fast", "problem": "No source for the market size.",
                 "severity": "high", "evidence": "https://invented.example/report"},
                {"document": 1, "quote": "words that are not in the document at all", "problem": "Invented.", "severity": "low"},
            ]}, res
        if role == "writer":
            return {"responses": [{"id": 1, "stance": "defend", "reply": "Everyone knows this market is big.", "evidence": ""}]}, res
        return {"verdicts": [{"id": 1, "status": "resolved", "reason": "Fine."}]}, res
    return fake


def test_debate_keeps_only_quoted_objections_and_unsourced_defences_stay_open(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(llm, "complete_json", _fake_models(calls))
    res = Critic(_run()).debate(1, [{"file": "phase1_step3_market.md", "author": "market_analyst", "text": DOC}])
    d = res.data
    assert d["ran"] and d["objections"] == 1  # the invented quote was dropped by code
    o = d["items"][0]
    assert o["status"] == "open" and o["stance"] == "defend"  # "resolved" without a fetched source is not accepted
    assert "no fetched source" in o["verdict"]
    assert "invented.example" not in res.content  # a URL the researcher never fetched is not repeated
    assert calls == ["critic", "writer", "critic"]  # critic and author run on their own roles' models
    assert "critic-model" in res.model and "writer-model" in res.model


def test_conceded_objection_is_resolved_with_a_correction(monkeypatch):
    def fake(system, user, fallback, *, max_tokens=1200, temperature=None, role="writer"):
        res = llm.LLMResult(text="{}", model=role)
        if role == "critic":
            return {"objections": [{"document": 1, "quote": "Junior analysts ask for practice sets", "problem": "Overstated.",
                                    "severity": "medium", "evidence": "https://news.ycombinator.com/item?id=1"}]}, res
        return {"responses": [{"id": 1, "stance": "concede", "reply": "Fair.", "fix": "Some junior analysts ask for practice sets."}]}, res
    monkeypatch.setattr(llm, "complete_json", fake)
    d = Critic(_run()).debate(1, [{"file": "f.md", "author": "researcher", "text": DOC}]).data
    assert d["conceded"] == 1 and d["open"] == 0 and d["items"][0]["fix"].startswith("Some junior")
    assert d["items"][0]["status"] == "resolved"


def test_no_model_means_no_debate_and_no_invented_objections():
    res = Critic(_run()).debate(1, [{"file": "f.md", "author": "researcher", "text": DOC}])
    assert res.data["ran"] is False and res.data["items"] == [] and res.model is None


def _fake_debate(self, phase, docs, opposite=False):
    items = [{"id": 1, "file": docs[0]["file"], "severity": "high", "quote": "q", "problem": "Weak evidence.",
              "status": "open", "stance": "defend", "fix": "", "verdict": "open"}]
    return StepResult(name="debate", agent="critic", action=f"debate_phase{phase}", content="# debate\n", model="critic-model",
                      data={"ran": True, "objections": 1, "open": 1, "high_open": 1, "conceded": 0, "items": items,
                            "models": ["critic-model"]})


def test_debate_runs_before_the_gate_and_never_changes_its_recommendation(monkeypatch, strong_brief=None):
    brief = json.loads((config.ROOT / "briefs" / "strong_founder.json").read_text())
    monkeypatch.setattr(config, "DEBATE", False)
    plain = orchestrator.advance(orchestrator.create_run(brief)["id"])
    monkeypatch.setattr(config, "DEBATE", True)
    monkeypatch.setattr(Critic, "debate", _fake_debate)
    run = orchestrator.advance(orchestrator.create_run(brief)["id"])
    g = orchestrator.current_gate(run)
    assert g["recommendation"] == orchestrator.current_gate(plain)["recommendation"]
    assert g["debate"]["open"] == 1 and g["debate"]["file"] == "phase1_step6_debate.md"
    assert "phase1_step6_debate.md" in run["outputs"]
    md = (orchestrator.run_dir(run["id"]) / "outputs" / "phase1_gate_decision.md").read_text()
    assert "Debate before this gate" in md and "does not change the recommendation" in md
    # REPEAT without a note: the next attempt works from the debate's open points.
    if "repeat" in g["allowed"]:
        run = orchestrator.decide(run["id"], "repeat", "founder")
        assert "Weak evidence." in run["ctx"]["feedback"]["1"]


def test_refused_brief_has_no_debate(monkeypatch):
    monkeypatch.setattr(Critic, "debate", _fake_debate)
    brief = json.loads((config.ROOT / "briefs" / "excluded_founder.json").read_text())
    run = orchestrator.advance(orchestrator.create_run(brief)["id"])
    assert "debate" not in orchestrator.current_gate(run)


def test_doc_text_strips_html_and_footer():
    t = critic_mod.doc_text("<html><style>x{}</style><h1>Store</h1><p>Price $9</p></html>\n---\nGenerated by the pipeline. Model")
    assert "Store" in t and "Price $9" in t and "<" not in t and "Generated" not in t


# ------------------------------------------------------------------ per-role models
def test_each_role_uses_its_model_and_falls_back_when_missing(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(config, "LLM_MODEL", "big:30b")
    monkeypatch.setattr(config, "LLM_FAST_MODEL", "small:4b")
    monkeypatch.setattr(config, "LLM_JUDGE_MODEL", "small:4b")
    monkeypatch.setattr(config, "LLM_CRITIC_MODEL", "other:20b")
    monkeypatch.setattr(config, "LLM_FALLBACK_MODELS", ["small:4b"])
    monkeypatch.setattr(llm, "_installed", lambda: {"big:30b", "small:4b"})  # critic model not downloaded yet
    llm._failed.clear()
    st = llm.model_status(force=True)
    assert st["ready"] and st["roles"] == {"writer": "big:30b", "fast": "small:4b", "judge": "small:4b", "critic": "small:4b"}
    assert "other:20b" in st["detail"]


def test_a_model_that_cannot_load_hands_over_to_the_next(monkeypatch):
    monkeypatch.setattr(config, "LLM_PROVIDER", "ollama")
    monkeypatch.setattr(config, "LLM_MODEL", "big:30b")
    monkeypatch.setattr(config, "LLM_FALLBACK_MODELS", ["small:4b"])
    monkeypatch.setattr(llm, "_installed", lambda: {"big:30b", "small:4b"})
    llm._failed.clear()
    llm._status_cache["value"] = None

    def chat(model, *a):
        if model == "big:30b":
            raise llm._LoadError("HTTP 500: model requires more system memory")
        return "hello", 5, 2
    monkeypatch.setattr(llm, "_ollama_chat", chat)
    res = llm.complete("s", "u", "fallback", role="writer")
    assert res.text == "hello" and res.model == "small:4b"  # the log shows the model that really answered
    assert llm.model_status(force=True)["roles"]["writer"] == "small:4b"  # remembered: not retried on every call
    llm._failed.clear()
    llm._status_cache["value"] = None


def test_gpt_oss_reasons_at_low_effort_and_qwen_does_not_think():
    assert llm._think_value("gpt-oss:20b") == "low"
    assert llm._think_value("qwen3:30b-a3b-instruct-2507-q4_K_M") is False


def test_answers_renumbered_by_the_model_are_matched_by_order(monkeypatch):
    def fake(system, user, fallback, *, max_tokens=1200, temperature=None, role="writer"):
        res = llm.LLMResult(text="{}", model=role)
        if role == "critic" and '"objections"' in user:
            return {"objections": [
                {"document": 1, "quote": "Junior analysts ask for practice sets", "problem": "A.", "severity": "low"},
                {"document": 2, "quote": "is worth $2 billion and growing fast", "problem": "B.", "severity": "high"}]}, res
        return {"responses": [{"id": 1, "stance": "concede", "reply": "ok", "fix": "fixed"}]}, res
    monkeypatch.setattr(llm, "complete_json", fake)
    d = Critic(_run()).debate(1, [{"file": "a.md", "author": "researcher", "text": DOC},
                                  {"file": "b.md", "author": "market_analyst", "text": DOC}]).data
    assert [o["stance"] for o in d["items"]] == ["concede", "concede"]  # objection 2 answered as "1" still counts
    assert "computed by code" in critic_mod.COMPUTED


def test_lines_computed_by_code_and_fetched_evidence_are_not_debated(monkeypatch):
    doc = critic_mod.doc_text("## Idea\n- Search queries: sql interview\n- Relevant items found: 24 (of 44 results)\n"
                              "| check | value |\nEvidence:\n- [Medium-hard SQL interview questions](https://news.ycombinator.com/item?id=1) (hn)\n"
                              "They often feel unprepared [guide](https://news.ycombinator.com/item?id=1) in interviews.")
    assert "Relevant items found" not in doc and "Search queries" not in doc and "| check" not in doc

    def fake(system, user, fallback, *, max_tokens=1200, temperature=None, role="writer"):
        res = llm.LLMResult(text="{}", model=role)
        if role == "critic" and '"objections"' in user:
            return {"objections": [
                {"document": 1, "quote": "Medium-hard SQL interview questions", "problem": "Old post.", "severity": "low"},
                {"document": 1, "quote": "They often feel unprepared guide", "problem": "The link does not exist.", "severity": "high"}]}, res
        return {"responses": []}, res
    monkeypatch.setattr(llm, "complete_json", fake)
    d = Critic(_run()).debate(1, [{"file": "a.md", "author": "researcher", "text": doc}]).data
    assert d["objections"] == 0  # an evidence title and a doubt about a fetched link are both dropped


def test_evidence_lists_and_pipeline_sentences_are_left_out_of_the_debate():
    raw = ("## Idea\nThe researcher searched public discussions. Every item below links to its source.\n\nEvidence:\n"
           + "".join(f"- [Repository user{i}/sql-practice: SQL problems](https://github.com/user{i}/sql-practice) (github, 2 pts)\n"
                     for i in range(60))
           + "- No sources found. Every market statement below is an ASSUMPTION.\n## Source coverage\n- reddit: 0 queries ok\n"
           + "Junior analysts say they freeze on window functions.")
    t = critic_mod.doc_text(raw)
    assert "github.com" not in t and "Every item below" not in t and "No sources found" not in t and "reddit: 0" not in t
    assert "freeze on window functions" in t  # the author's own claim is still debated
