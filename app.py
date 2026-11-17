"""Web dashboard and API: the founder's control panel.

    uvicorn app:app --host 0.0.0.0 --port 8000   (docker compose up does this)

The founder starts a run from a brief, watches each phase, and decides at
every gate with Go / Repeat / Pivot / Stop. Anything that would be published
or sent waits in the approval queue for Approve / Reject.
"""
from __future__ import annotations

import json
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Body, FastAPI, Form, Header, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse

import approval
import config
import decision_log
import guardrails
import llm
import orchestrator
from agents.base import GLOBAL_RULES, load_prompt

@asynccontextmanager
async def _lifespan(_: FastAPI):
    # In the background: the dashboard is usable at once, and the model is in memory before the first brief.
    threading.Thread(target=llm.warm_up, daemon=True).start()
    yield


app = FastAPI(title="Venture Builder", version="1.0.0", lifespan=_lifespan)
STATIC = config.ROOT / "static"
BRIEFS = config.ROOT / "briefs"

COMPONENTS = [
    {"name": "Research sources (Hacker News, Reddit, GitHub, Stack Exchange)", "status": "Working"},
    {"name": "Local model (Ollama)", "status": "Working"},
    {"name": "Gates and founder approval", "status": "Working"},
    {"name": "Guardrails", "status": "Working"},
    {"name": "Customer interviews (sending outreach)", "status": "STUBBED"},
    {"name": "Publishing pages and posts", "status": "STUBBED"},
    {"name": "Waitlist hosting (public URL)", "status": "STUBBED"},
    {"name": "Payment provider / checkout", "status": "MOCKED"},
    {"name": "Delivery emails", "status": "STUBBED"},
]


def _bg(fn, *args) -> None:
    def runner():
        try:
            fn(*args)
        except Exception as e:  # recorded in the run state by the orchestrator
            print(f"background error: {e}")
    threading.Thread(target=runner, daemon=True).start()


def _founder_only(token: str | None) -> None:
    """Gate decisions and approvals are the founder's alone. With FOUNDER_TOKEN set, prove it."""
    if config.FOUNDER_TOKEN and token != config.FOUNDER_TOKEN:
        raise HTTPException(403, "founder token required for decisions and approvals")


def _view(run: dict) -> dict:
    return {
        "run": {k: run[k] for k in ("id", "status", "phase", "created", "updated", "brief", "original_idea", "screening", "attempts")}
               | {"progress": run.get("progress"), "warnings": run.get("warnings", []),
                  "interview_notes": run["ctx"].get("interview_notes"), "researched": bool(run["ctx"].get("candidates"))},
        "error": run.get("error"),
        "phases": orchestrator.PHASES,
        "gates": run["gates"],
        "current_gate": orchestrator.current_gate(run) if run["status"] == "awaiting_founder" else None,
        "actions": run["pending_actions"],
        "steps": run["steps"],
        "outputs": run["outputs"],
        "log": decision_log.read(run_id=run["id"])[-200:],
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/status")
def status():
    s = llm.STATS
    return {"model": llm.model_status(), "components": COMPONENTS, "cost_usd": 0.0,
            "tokens": s.prompt_tokens + s.completion_tokens, "llm_calls": s.calls, "fallbacks": s.fallbacks}


@app.get("/api/samples")
def samples():
    out = []
    for p in sorted(BRIEFS.glob("*_founder.json")):
        out.append({"name": p.stem, "brief": json.loads(p.read_text(encoding="utf-8"))})
    return out


@app.get("/api/runs")
def runs():
    return orchestrator.list_runs()


@app.post("/api/runs")
def create(payload: dict = Body(...)):
    raw = payload.get("brief")
    if payload.get("sample"):
        p = BRIEFS / f"{Path(payload['sample']).name}.json"
        if not p.exists():
            raise HTTPException(404, "unknown sample")
        raw = json.loads(p.read_text(encoding="utf-8"))
    if not raw:
        raise HTTPException(400, "brief is required")
    run = orchestrator.create_run(raw)
    _bg(orchestrator.advance, run["id"])
    return {"id": run["id"]}


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    try:
        return _view(orchestrator.load(run_id))
    except KeyError:
        raise HTTPException(404, "run not found")


@app.post("/api/runs/{run_id}/advance")
def advance(run_id: str):
    run = orchestrator.load(run_id)
    if run["status"] not in ("ready", "monitoring"):
        raise HTTPException(409, f"run is {run['status']}")
    _bg(orchestrator.advance, run_id)
    return {"ok": True}


@app.post("/api/runs/{run_id}/decide")
def decide(run_id: str, payload: dict = Body(...), x_founder_token: str | None = Header(None)):
    """Called only by the founder's click in the dashboard."""
    _founder_only(x_founder_token)
    try:
        run = orchestrator.decide(run_id, payload.get("decision", ""), approval.FOUNDER, payload.get("note", ""))
    except (ValueError, approval.ApprovalRequired) as e:
        raise HTTPException(400, str(e))
    if run["status"] == "ready":
        _bg(orchestrator.advance, run_id)
    return {"status": run["status"], "phase": run["phase"]}


@app.post("/api/runs/{run_id}/actions/{action_id}")
def decide_action(run_id: str, action_id: str, payload: dict = Body(...), x_founder_token: str | None = Header(None)):
    _founder_only(x_founder_token)
    try:
        run = orchestrator.decide_action(run_id, action_id, bool(payload.get("approve")), approval.FOUNDER, payload.get("note", ""))
    except KeyError:
        raise HTTPException(404, "action not found")
    except (ValueError, approval.ApprovalRequired) as e:  # e.g. a broken promise: the item must be fixed, not approved
        raise HTTPException(400, str(e))
    return {"ok": True, "actions": run["pending_actions"]}


@app.get("/api/runs/{run_id}/outputs/{name}")
def output(run_id: str, name: str):
    path = orchestrator.run_dir(run_id) / "outputs" / Path(name).name
    if not path.exists():
        raise HTTPException(404, "not found")
    if path.suffix == ".html":
        return HTMLResponse(path.read_text(encoding="utf-8"),
                            headers={"Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'"})
    return PlainTextResponse(path.read_text(encoding="utf-8"))


@app.get("/api/runs/{run_id}/interview-notes")
def get_interview_notes(run_id: str):
    return {"notes": orchestrator.interview_notes(run_id)}


@app.post("/api/runs/{run_id}/interview-notes")
def add_interview_notes(run_id: str, payload: dict = Body(...), x_founder_token: str | None = Header(None)):
    """The founder pastes notes from real interviews; an agent separates commitments from compliments."""
    _founder_only(x_founder_token)
    try:
        run = orchestrator.save_interview_notes(run_id, str(payload.get("notes", "")), approval.FOUNDER)
    except KeyError:
        raise HTTPException(404, "run not found")
    except (ValueError, approval.ApprovalRequired) as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "output": "phase1_step5_interview-notes.md", "summary": run["ctx"]["interview_notes"]}


@app.post("/api/waitlist/{run_id}", response_class=HTMLResponse)
def waitlist(run_id: str, email: str = Form(...), consent: str = Form("")):
    try:
        n = orchestrator.add_waitlist_signup(run_id, email, consent == "yes")
    except (ValueError, KeyError) as e:
        raise HTTPException(400, str(e))
    return f"<p>Thanks, you're on the list. We'll email you once, when it's ready.</p><!-- {n} -->"


@app.post("/api/checkout/{run_id}", response_class=HTMLResponse)
def checkout(run_id: str):
    return ("<p><strong>MOCKED checkout.</strong> This prototype takes no payments. In production the buyer goes to the payment "
            "provider's hosted page; its webhook triggers delivery (see payments.py, webhooks.py, delivery.py).</p>")


@app.get("/api/log")
def log(run_id: str | None = None):
    return decision_log.read(run_id=run_id)[-500:]


@app.post("/api/ask")
def ask(payload: dict = Body(...)):
    """'Ask the team': any free-text request goes through the guardrails first."""
    # Five layers: (1) secrets are redacted before anything else sees the text, (2) rules on the request,
    # (3) the model's second opinion on the request, (4) rules on the draft, (5) the model's second opinion on the draft.
    # The assistant has no tools: whatever it writes is a draft, and it cannot publish, send, charge or change a gate.
    raw = str(payload.get("text", ""))[:2000]
    text = guardrails.redact_secrets(raw)
    run_id = payload.get("run_id") or None
    verdict = guardrails.screen_request(raw)
    if verdict.allowed:
        verdict = guardrails.screen_request_deep(text)
    if not verdict.allowed:
        decision_log.log("guardrails", "refuse_request", run_id=run_id, outcome="refused", detail=f"{verdict.category}: {text[:120]}",
                         model=(llm.model_status().get("roles") or {}).get("judge") or llm.model_status().get("model") if "model-judge" in verdict.matches else None)
        return {"allowed": False, "category": verdict.category, "reply": guardrails.refusal_message(verdict), "matches": verdict.matches}
    context = ""
    if run_id:
        try:
            context = "Founder brief: " + json.dumps(orchestrator.load(run_id)["brief"], ensure_ascii=False)
        except KeyError:
            pass
    res = llm.complete(load_prompt("assistant") + "\n\n" + GLOBAL_RULES, f"{context}\n\nRequest: {text}",
                       "The local model is not available right now, so nothing was drafted. The request passed the rule check; "
                       "the model's second check and the draft need the model. Try again once it has finished downloading.", max_tokens=700)
    scan = guardrails.scan_output(res.text)
    draft, claims = guardrails.scrub_action_claims(scan.text)
    removed = len(scan.violations) + claims
    check = guardrails.judge_output(draft) if res.model else guardrails.Verdict(True)
    if not check.allowed:
        decision_log.log("guardrails", "withhold_draft", run_id=run_id, model=res.model, cost=res.cost, outcome="refused",
                         detail=f"{check.category}: {text[:120]}")
        return {"allowed": False, "category": check.category, "reply": guardrails.refusal_message(check), "matches": check.matches}
    decision_log.log("assistant", "answer_request", run_id=run_id, model=res.model, cost=res.cost, outcome="answered",
                     detail=text[:120], guardrail_removals=removed or None)
    note = " (Some sentences were removed by the guardrails.)" if removed else ""
    return {"allowed": True, "reply": (draft or "Nothing could be drafted for this request.") + note, "model": res.model,
            "note": "Draft only. The assistant cannot publish, send, charge or change a gate. Nothing goes out without your approval."}


@app.exception_handler(Exception)
def errors(_, exc: Exception):
    return JSONResponse({"error": f"{type(exc).__name__}: {exc}"}, status_code=500)
