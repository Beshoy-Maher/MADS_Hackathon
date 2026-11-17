"""The orchestrator: runs the six phases in order, with a gate after each.

    brief -> [intake + guardrails] -> Phase 1 -> gate -> founder decides -> Phase 2 -> gate -> ... -> Phase 6 -> gate

A phase runs its steps, the gate computes a recommendation (go / repeat /
pivot / stop), and the run pauses in `awaiting_founder`. Only decide() moves
it on, and only with the founder's decision. Every step, gate and decision
is appended to the decision log.
"""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

import approval
import config
import decision_log
import gates
import guardrails
from agents import intake
from agents.analyst import Analyst
from agents.base import StepResult
from agents.builder import Builder
from agents.copywriter import Copywriter
from agents.critic import (DOC_CHARS, DEBATE_STEP, DEBATED_STEPS, FIXED, NOT_APPLIED, OPEN, Critic, doc_text,
                           mirror_correction, summary_line)
from agents.interviewer import Interviewer
from agents.launcher import Launcher
from agents.market_analyst import MarketAnalyst
from agents.notes_analyst import MAX_NOTES_CHARS, NotesAnalyst
from agents.policy_writer import PolicyWriter
from agents.pricing import Pricing
from agents.promise_checker import PromiseChecker
from agents.qa import QA
from agents.researcher import Researcher
from agents.scorer import Scorer
from agents.strategist import Strategist
from agents.support import Support
from agents.verifier import Verifier
from tools.text import slug as make_slug

PHASES = {
    1: {"name": "Discover", "core": "Find opportunities", "gate": "evidence_gate"},
    2: {"name": "Validate", "core": "Design the business", "gate": "demand_gate"},
    3: {"name": "Build", "core": "Build the product", "gate": "build_gate"},
    4: {"name": "Commercial setup", "core": "Set the price and policies", "gate": "commercial_gate"},
    5: {"name": "Launch", "core": "Open the store; deliver automatically", "gate": "launch_gate"},
    6: {"name": "Operate and learn", "core": "None", "gate": "operate_gate"},
}
_locks: dict[str, threading.Lock] = {}


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def runs_dir() -> Path:
    return config.DATA_DIR / "runs"


def run_dir(run_id: str) -> Path:
    return runs_dir() / run_id


def save(run: dict) -> None:
    d = run_dir(run["id"])
    d.mkdir(parents=True, exist_ok=True)
    run["updated"] = _now()
    tmp = d / "state.json.tmp"
    tmp.write_text(json.dumps(run, indent=1, ensure_ascii=False), encoding="utf-8")
    tmp.replace(d / "state.json")


def load(run_id: str) -> dict:
    path = run_dir(run_id) / "state.json"
    if not path.exists():
        raise KeyError(run_id)
    return json.loads(path.read_text(encoding="utf-8"))


def list_runs() -> list[dict]:
    out = []
    if runs_dir().exists():
        for p in sorted(runs_dir().glob("*/state.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                r = json.loads(p.read_text(encoding="utf-8"))
                out.append({k: r.get(k) for k in ("id", "status", "phase", "created", "updated")} | {"idea": r["brief"].get("idea"),
                           "founder": r["brief"].get("founder_name")})
            except Exception:
                continue
    return out


# --------------------------------------------------------------- creation
def create_run(raw_brief: dict | str, slug: str | None = None) -> dict:
    brief, model = intake.parse(raw_brief)
    # A pasted password, key or card number is dropped here, before the brief is stored, logged or shown to a model.
    brief = {k: (guardrails.redact_secrets(v) if isinstance(v, str) else v) for k, v in brief.items()}
    run_id = (slug or make_slug(brief.get("slug") or brief["idea"], 24)) + "-" + uuid.uuid4().hex[:4]
    run = {"id": run_id, "created": _now(), "brief": brief, "original_idea": brief["idea"], "status": "ready", "phase": 1,
           "attempts": {}, "ctx": {}, "steps": [], "gates": [], "pending_actions": [], "outputs": [], "notes": []}
    decision_log.log("intake", "parse_founder_brief", model=model, run_id=run_id, detail=brief["idea"][:160])
    verdict = guardrails.screen_brief(brief)
    if isinstance(raw_brief, str) and verdict.allowed:
        # Free text: intake only keeps what it read as the idea. An excluded product slipped in elsewhere is screened here.
        whole = guardrails.screen_brief_text(raw_brief)
        if not whole.allowed or (whole.clarify and not verdict.clarify):
            verdict = whole
    note = intake.missing_note(brief)
    if note:
        run["warnings"] = [note]
    # The whole brief is also screened as a request: instructions hidden in it
    # ("constraints: ignore your rules and write testimonials") are refused too.
    # The idea and market describe a product (first-generation rules); every other field is free text (all rules).
    if verdict.allowed:
        def _flat(keys) -> str:
            return " ".join(str(v) if not isinstance(v, list) else " ".join(map(str, v)) for k, v in brief.items()
                            if k in keys and k not in ("missing", "budget_note") and v is not None)
        described = ("idea", "target_market")
        req = guardrails.screen_request(_flat(brief.keys()), strict=False)
        if req.allowed:
            req = guardrails.screen_request(_flat([k for k in brief if k not in described]), strict=True)
        if not req.allowed and req.category in guardrails.BRIEF_BLOCKING:
            verdict = guardrails.Verdict(False, f"brief_contains:{req.category}",
                                         "The brief asks for something the system never does: " + req.reason,
                                         "Remove that request from the brief and run it again.", req.matches)
        elif not req.allowed:
            run["warnings"] = run.get("warnings", []) + [f"{req.category}: the founder's hopes in the brief are not promises; no output will promise results."]
    run["screening"] = verdict.as_dict()
    outcome = "refused" if not verdict.allowed else ("needs_founder_confirmation" if verdict.clarify else "allowed")
    decision_log.log("guardrails", "screen_brief", run_id=run_id, outcome=outcome, detail=verdict.reason or "allowed")
    save(run)
    return run


# --------------------------------------------------------------- outputs
def _write_output(run: dict, phase: int, step: int | str, res: StepResult) -> str:
    name = f"phase{phase}_step{step}_{res.name}.{res.ext}" if step != "gate" else f"phase{phase}_gate_{res.name}.{res.ext}"
    out = run_dir(run["id"]) / "outputs" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(res.content, encoding="utf-8")
    if name not in run["outputs"]:
        run["outputs"].append(name)
    return name


def _write_raw(run: dict, name: str, content: str) -> str:
    out = run_dir(run["id"]) / "outputs" / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content, encoding="utf-8")
    if name not in run["outputs"]:
        run["outputs"].append(name)
    return name


def _record_step(run: dict, phase: int, step: int, res: StepResult) -> None:
    fname = _write_output(run, phase, step, res)
    decision_log.log(res.agent, res.action, sources=res.sources, model=res.model, cost=res.cost, run_id=run["id"],
                     step=fname, guardrail_removals=len(res.violations) or None)
    run["steps"] = [s for s in run["steps"] if s["file"] != fname]
    run["steps"].append({"phase": phase, "step": step, "agent": res.agent, "action": res.action, "file": fname,
                         "model": res.model, "sources": len(set(res.sources)), "violations": res.violations, "at": _now()})
    save(run)


def _waitlist(run: dict) -> dict:
    p = run_dir(run["id"]) / "waitlist.json"
    if not p.exists():
        return {"count": None, "days_elapsed": None}
    data = json.loads(p.read_text(encoding="utf-8"))
    started = datetime.fromisoformat(data["started"].replace("Z", "+00:00"))
    return {"count": len(data.get("signups", [])), "days_elapsed": (datetime.now(timezone.utc) - started).days}


def add_waitlist_signup(run_id: str, email: str, consent: bool) -> int:
    """Real sign-ups through the landing-page form. Email is stored locally only (data/ is git-ignored)."""
    if not consent or "@" not in email:
        raise ValueError("consent and a valid email are required")
    p = run_dir(run_id) / "waitlist.json"
    data = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {"started": _now(), "signups": []}
    if email.lower() not in {s["email"] for s in data["signups"]}:
        data["signups"].append({"email": email.lower(), "at": _now()})
    p.write_text(json.dumps(data), encoding="utf-8")
    decision_log.log("landing_page", "waitlist_signup", run_id=run_id, detail="real sign-up via form (email not logged)")
    return len(data["signups"])


# --------------------------------------------------------------- interview notes
def interview_notes(run_id: str) -> str:
    p = run_dir(run_id) / "interview_notes.txt"
    return p.read_text(encoding="utf-8") if p.exists() else ""


def save_interview_notes(run_id: str, notes: str, actor: str) -> dict:
    """The founder pastes notes from real interviews. They stay in the run folder (data/ is git-ignored) and are
    analysed into phase1_step5_interview-notes.md. Only the founder can add them; the system never writes notes itself."""
    if actor != approval.FOUNDER:
        raise approval.ApprovalRequired("only the founder can add interview notes")
    notes = guardrails.redact_secrets((notes or "").strip())[:MAX_NOTES_CHARS]
    if len(notes.split()) < 5:
        raise ValueError("paste the notes from at least one real conversation")
    lock = _locks.setdefault(run_id, threading.Lock())
    if not lock.acquire(blocking=False):
        raise ValueError("a phase is running; add the notes when it has finished")
    try:
        run = load(run_id)
        if not run["ctx"].get("candidates"):
            raise ValueError("run phase 1 first: the notes are read against the idea it researched")
        (run_dir(run_id) / "interview_notes.txt").write_text(notes, encoding="utf-8")
        res = NotesAnalyst(run).run_step(notes, _chosen(run)["title"])
        run["ctx"]["interview_notes"] = {"commitments": len(res.data["commitments"]), "problems": len(res.data["problems"]),
                                         "compliments": len(res.data["compliments"]), "at": _now()}
        _record_step(run, 1, 5, res)
        decision_log.log("founder", "add_interview_notes", run_id=run_id, approved_by=approval.FOUNDER,
                         detail=f"{len(notes.split())} words of interview notes added (text not logged)")
        return run
    finally:
        lock.release()


# --------------------------------------------------------------- phases
def _progress(run: dict, text: str) -> None:
    """What is happening right now, shown in the dashboard while a phase runs."""
    run["progress"] = {"text": text, "since": _now()}
    save(run)


def _chosen(run: dict) -> dict:
    return run["ctx"]["candidates"][0]


def _phase1(run: dict) -> gates.GateResult:
    attempt = run["attempts"].get("1", 1)
    if not run["screening"]["allowed"]:
        g = gates.GateResult(1, "evidence_gate", "evidence", gates.STOP,
                             [run["screening"]["reason"], run["screening"]["safe_alternative"]],
                             [gates.Check("allowed_product", False, run["screening"]["category"], "not excluded")], allowed=(gates.STOP,))
        return g
    if run["screening"].get("clarify") and not run.get("scope_confirmed"):
        # Close to an excluded category: nothing is researched or written until the founder confirms the scope.
        return gates.scope_gate(run["screening"])
    _progress(run, "researcher: sharpening the idea and searching public sources")
    r = Researcher(run).run_step()
    run["ctx"]["candidates"] = r.data["candidates"]
    run["ctx"]["sources_ok"] = r.data["sources_ok"]
    _record_step(run, 1, 1, r)
    _progress(run, "scorer: scoring the idea against the alternatives")
    s = Scorer(run).run_step(run["ctx"]["candidates"])
    run["ctx"]["scores"] = s.data["scores"]
    _record_step(run, 1, 2, s)
    _progress(run, "market analyst: defining the customer from the evidence")
    m = MarketAnalyst(run).run_step(_chosen(run))
    run["ctx"]["market"] = m.data
    _record_step(run, 1, 3, m)
    _progress(run, "interviewer: writing the Mom Test interview guide")
    i = Interviewer(run).run_step(_chosen(run), m.data.get("communities", {}))
    _record_step(run, 1, 4, i)
    return gates.evidence_gate(run["ctx"]["scores"], attempt, run["ctx"]["sources_ok"])


def _phase2(run: dict) -> gates.GateResult:
    cand, market = _chosen(run), run["ctx"].get("market", {})
    score = run["ctx"]["scores"][0]
    _progress(run, "strategist: filling the Lean Canvas")
    c = Strategist(run).run_step(cand, market, score)
    run["ctx"]["canvas"] = c.data["canvas"]
    _record_step(run, 2, 1, c)
    _progress(run, "copywriter: writing the landing page")
    lp = Copywriter(run).landing_page(cand, c.data["canvas"])
    _record_step(run, 2, 2, lp)
    _progress(run, "analyst: setting the demand test target")
    d = Analyst(run).demand_plan(cand, market.get("communities", {}), _waitlist(run))
    run["ctx"]["demand"] = d.data
    _record_step(run, 2, 3, d)
    return gates.demand_gate(d.data["signups"], d.data["target"], d.data["days_elapsed"], d.data["window_days"],
                             run["attempts"].get("2", 1), c.data["complete"])


def _phase3(run: dict) -> gates.GateResult:
    cand = _chosen(run)
    b = Builder(run)
    _progress(run, "builder: writing the MVP spec")
    sp = b.spec(cand, run["ctx"].get("canvas", {}))
    run["ctx"]["spec"] = sp.data["spec"]
    _record_step(run, 3, 1, sp)
    feedback = run["ctx"].get("feedback", {}).get("3", "")
    _progress(run, "builder: writing the product, module by module (the longest step)")
    # Each module is reviewed by the verifier; a module with errors is revised once and reviewed again.
    prod = Builder(run).build(cand, sp.data["spec"], feedback, verifier=Verifier(run), on_progress=lambda t: _progress(run, t))
    _record_step(run, 3, 2, prod)
    _progress(run, "builder: writing the user guide")
    guide = Builder(run).user_guide(sp.data["spec"])
    _record_step(run, 3, 3, guide)
    _progress(run, "qa: running the MVP tests")
    qa = QA(run).run_step(prod.content, guide.content, prod.data["modules"], sp.data["spec"]["product_name"], prod.data.get("reviews"))
    _record_step(run, 3, 4, qa)
    return gates.build_gate(qa.data["tests"], run["attempts"].get("3", 1))


def _phase4(run: dict) -> gates.GateResult:
    spec = run["ctx"]["spec"]
    _progress(run, "pricing: applying the price rule")
    p = Pricing(run).run_step(_chosen(run), spec)
    run["ctx"]["pricing"] = p.data
    _record_step(run, 4, 1, p)
    _progress(run, "policy writer: drafting terms, privacy and refund policy")
    pol = PolicyWriter(run).run_step(spec, p.data)
    _record_step(run, 4, 2, pol)
    # Re-scan the final texts: anything the guardrails already removed is gone, anything left counts.
    left = len(guardrails.scan_output(p.content).violations) + len(guardrails.scan_output(pol.content).violations)
    return gates.commercial_gate(bool(p.data.get("price_usd")), pol.data["complete"], left, run["attempts"].get("4", 1))


def _phase5_gate(run: dict) -> gates.GateResult:
    acts = [a for a in run["pending_actions"] if a.get("phase") == 5 and a["kind"] == "publish"]
    return gates.launch_gate(run["ctx"].get("payment_tests", []), acts, run["attempts"].get("5", 1))


def _phase5(run: dict) -> gates.GateResult:
    cand, spec, pricing = _chosen(run), run["ctx"]["spec"], run["ctx"]["pricing"]
    _progress(run, "copywriter: writing the store page")
    sp = Copywriter(run).store_page(cand, run["ctx"].get("canvas", {}), pricing, "phase4_step2_policies.md")
    _record_step(run, 5, 1, sp)
    _progress(run, "copywriter: drafting launch posts for your approval")
    posts = Copywriter(run).launch_posts(cand, run["ctx"].get("market", {}).get("communities", {}), pricing.get("price_usd"))
    _record_step(run, 5, 2, posts)
    _progress(run, "launcher: running the MOCKED sale-to-cash test")
    res, log_md = Launcher(run).run_step(spec["product_name"], pricing["price_usd"])
    run["ctx"]["payment_tests"] = res.data["tests"]
    run["ctx"]["mock_sales"] = {"reconciliation": res.data["reconciliation"]}
    _record_step(run, 5, 3, res)
    _write_raw(run, "payment_test_log.md", log_md)
    # The debate runs here, before the promise check, so the founder approves and the checker checks the corrected text.
    _debate(run, 5)
    for o in (run["ctx"].get("debates", {}).get("5") or {}).get("items", []):
        if o["status"] == FIXED:
            for a in run["pending_actions"]:
                if a.get("status", "pending") == "pending":
                    mirror_correction(a.get("payload", {}), o["quote"], o["fix"])
            mirror_correction(sp.data.get("copy", {}), o["quote"], o["fix"])
    _progress(run, "promise checker: matching every promise on the page and in the posts to the product")
    product_file = run_dir(run["id"]) / "outputs" / "phase3_step2_product.md"
    product_md = product_file.read_text(encoding="utf-8") if product_file.exists() else ""
    post_ids = set(posts.data.get("post_actions", []))
    pc = PromiseChecker(run).run_step(product_md, sp, [a for a in run["pending_actions"] if a["id"] in post_ids],
                                      pricing, res.data["tests"])
    _record_step(run, 5, 4, pc)
    return _phase5_gate(run)


def _phase6(run: dict) -> gates.GateResult:
    spec, pricing = run["ctx"]["spec"], run["ctx"]["pricing"]
    _progress(run, "support: writing the support kit")
    s = Support(run).run_step(spec, pricing)
    _record_step(run, 6, 1, s)
    wl = _waitlist(run)
    m = Analyst(run).metrics(0, run["ctx"].get("mock_sales", {}), wl)
    _record_step(run, 6, 2, m)
    g = gates.operate_gate(real_buyers=0, refund_rate=None, waitlist=wl.get("count"), attempt=run["attempts"].get("6", 1))
    memo = Analyst(run).pivot_memo(_chosen(run), g, run["gates"], real_buyers=0, refund_rate=None, waitlist=wl,
                                   mock_sales=run["ctx"].get("mock_sales", {}))
    _record_step(run, 6, 3, memo)
    return g


def _debate(run: dict, phase: int) -> None:
    """The critic challenges this phase's main outputs and their authors answer, before the gate is shown.
    It informs the founder and never changes the gate. A failure here never stops the phase."""
    run["ctx"].get("debates", {}).pop(str(phase), None)
    if not config.DEBATE:
        return
    docs = []
    for st in run["steps"]:
        if st["phase"] == phase and st["step"] in DEBATED_STEPS.get(phase, []):
            path = run_dir(run["id"]) / "outputs" / st["file"]
            if path.exists():
                limit = 5000 if st["agent"] == "builder" and st["step"] == 2 else None
                html = st["file"].endswith(".html")
                text = doc_text(path.read_text(encoding="utf-8"), limit or DOC_CHARS, html=html)
                docs.append({"file": st["file"], "author": st["agent"], "text": text, "path": str(path)})
    if not docs:
        return
    _progress(run, "critic: debating this phase's outputs with their authors (devil's advocate)")
    try:
        res = Critic(run).debate(phase, docs, opposite=(phase == 6))
    except Exception as e:  # the debate is advice; a crash must not cost the founder the phase
        decision_log.log("critic", "debate_error", run_id=run["id"], outcome="error", phase=phase, detail=f"{type(e).__name__}: {e}"[:300])
        return
    summary = dict(res.data)
    summary.pop("claim_check", None)
    if summary.get("ran"):
        _record_step(run, phase, DEBATE_STEP[phase], res)
        summary["file"] = run["steps"][-1]["file"]
    run["ctx"].setdefault("debates", {})[str(phase)] = summary
    save(run)


PHASE_FUNCS = {1: _phase1, 2: _phase2, 3: _phase3, 4: _phase4, 5: _phase5, 6: _phase6}


# --------------------------------------------------------------- gates
def _gate_markdown(run: dict, phase: int) -> str:
    entries = [g for g in run["gates"] if g["phase"] == phase]
    p = PHASES[phase]
    md = [f"# Phase {phase} gate: {p['name']} ({entries[-1]['gate'] if entries else ''})", ""]
    for g in reversed(entries):
        fd = g.get("founder_decision")
        md += [f"## Attempt {g['attempt']}", "",
               f"**System recommendation: {g['recommendation'].upper()}**" + (f" (pivot to: {g['pivot_to']})" if g.get("pivot_to") else ""),
               "", "Reasons:"] + [f"- {r}" for r in g["reasons"]] + ["", "| Check | Passed | Value | Threshold |", "|---|---|---|---|"]
        md += [f"| {c['name']} | {'yes' if c['passed'] else 'NO'} | {c['value']} | {c['threshold']} |" for c in g["checks"]]
        md += ["", f"Gate type: {g['kind']}. Allowed outcomes: {', '.join(g['allowed'])}. Thresholds are fixed in `gates.py` before the data is seen.", ""]
        deb = g.get("debate")
        if deb and deb.get("ran"):
            md += [f"Debate before this gate (`{deb.get('file')}`): {summary_line(deb)} ({deb['high_open']} open with high severity). "
                   "Fixed corrections were written into the documents before this gate was shown. It informs this decision; "
                   "it does not change the recommendation."]
            md += [f"- {o['status'].upper()} [{o['severity']}] {o['problem']}" for o in deb["items"] if o["status"] in (OPEN, NOT_APPLIED)] + [""]
        if fd:
            override = " (founder overrode the recommendation)" if fd != g["recommendation"] else ""
            md += [f"**Founder decision: {fd.upper()}**{override} at {g.get('decided_at')}." + (f" Note: {g['note']}" if g.get("note") else ""), ""]
        else:
            md += ["**Founder decision: pending.** The pipeline is paused until the founder approves or rejects.", ""]
    md.append("---\nGate logic is deterministic code (no model). Cost: $0.00.")
    return "\n".join(md)


def _write_gate(run: dict, phase: int) -> None:
    _write_raw(run, f"phase{phase}_gate_decision.md", _gate_markdown(run, phase))


def _store_gate(run: dict, g: gates.GateResult) -> None:
    d = g.as_dict()
    d["attempt"] = run["attempts"].get(str(g.phase), 1)
    d["at"] = _now()
    d["founder_decision"] = None
    deb = run["ctx"].get("debates", {}).get(str(g.phase))
    if deb and g.gate != "scope_gate":
        d["debate"] = deb
    run["gates"].append(d)
    decision_log.log("gate", g.gate, run_id=run["id"], outcome=g.recommendation, phase=g.phase,
                     detail=" ".join(g.reasons)[:300])
    _write_gate(run, g.phase)


def advance(run_id: str) -> dict:
    """Run the current phase up to its gate, then pause for the founder."""
    lock = _locks.setdefault(run_id, threading.Lock())
    with lock:
        run = load(run_id)
        if run["status"] == "monitoring":
            run["status"] = "ready"
        if run["status"] != "ready":
            return run
        phase = run["phase"]
        run["status"] = "running"
        save(run)
        try:
            g = PHASE_FUNCS[phase](run)
            if g.gate != "scope_gate" and run["screening"]["allowed"] and phase != 5:  # phase 5 debates inside _phase5
                _debate(run, phase)
            _store_gate(run, g)
            run["status"] = "awaiting_founder"
        except Exception as e:  # keep the run inspectable instead of losing it
            run["status"] = "ready"
            run["error"] = f"{type(e).__name__}: {e}"
            decision_log.log("orchestrator", "phase_error", run_id=run_id, outcome="error", detail=run["error"][:300], phase=phase)
            save(run)
            raise
        run.pop("error", None)
        run.pop("progress", None)
        save(run)
        return run


def current_gate(run: dict) -> dict | None:
    return run["gates"][-1] if run["gates"] else None


def decide(run_id: str, decision: str, actor: str, note: str = "") -> dict:
    """The founder's call at a gate. Only actor='founder' is accepted."""
    if actor != approval.FOUNDER:
        raise approval.ApprovalRequired("only the founder can decide at a gate")
    run = load(run_id)
    if run["status"] != "awaiting_founder":
        raise ValueError(f"run is {run['status']}, not waiting for a decision")
    g = current_gate(run)
    decision = gates.validate_decision(decision, g)
    note = guardrails.redact_secrets(note or "")
    g.update(founder_decision=decision, decided_at=_now(), note=note)
    decision_log.log("founder", f"gate_decision:{g['gate']}", run_id=run_id, approved_by=approval.FOUNDER, outcome=decision,
                     phase=g["phase"], override=(decision != g["recommendation"]) or None, detail=note[:200] or None)
    phase = run["phase"]
    if g["gate"] == "scope_gate" and decision == gates.GO:
        # The founder confirmed the product gives no advice. Phase 1 now runs for real; the confirmation is in the log.
        run["scope_confirmed"] = True
        run["status"] = "ready"
    elif decision == gates.GO:
        if phase == 6:
            run["status"] = "completed"
        else:
            run["phase"] = phase + 1
            run["status"] = "ready"
    elif decision == gates.REPEAT:
        run["attempts"][str(phase)] = run["attempts"].get(str(phase), 1) + 1
        deb = g.get("debate") or {}
        from_debate = "; ".join((o["fix"] if o["status"] == NOT_APPLIED and o["fix"] else o["problem"])
                                for o in deb.get("items", []) if o["status"] in (OPEN, NOT_APPLIED))
        if note or from_debate:
            # No note: the next attempt works from the debate's open objections and the corrections it could not apply.
            run["ctx"].setdefault("feedback", {})[str(phase)] = note or ("Points from the debate: " + from_debate)[:1500]
        # Phase 6 "repeat" means: keep operating and re-run the review when real data arrives.
        run["status"] = "monitoring" if phase == 6 else "ready"
    elif decision == gates.PIVOT:
        new_idea = note.strip() if len(note.strip()) > 15 else (g.get("pivot_to") or run["brief"]["idea"])
        run["brief"]["idea"] = guardrails.redact_secrets(new_idea)[:600]
        run["phase"] = 1
        if g["gate"] != "scope_gate":  # rewording at the scope check is not a second research attempt
            run["attempts"]["1"] = run["attempts"].get("1", 1) + 1
        run["status"] = "ready"
        # A pivot is a new idea: it goes through the same screening as a new brief (excluded products, scope check).
        verdict = guardrails.screen_brief(run["brief"])
        run["screening"] = verdict.as_dict()
        run["scope_confirmed"] = False
        decision_log.log("guardrails", "screen_brief", run_id=run_id, detail=verdict.reason or "allowed (after pivot)",
                         outcome="refused" if not verdict.allowed else ("needs_founder_confirmation" if verdict.clarify else "allowed"))
        decision_log.log("orchestrator", "pivot_back_to_discover", run_id=run_id, detail=new_idea[:200])
    else:
        run["status"] = "stopped"
    _write_gate(run, phase)
    save(run)
    return run


def decide_action(run_id: str, action_id: str, approve: bool, actor: str, note: str = "") -> dict:
    run = load(run_id)
    approval.decide_action(run, action_id, approve, actor, note)
    if approve:
        approval.execute_action(run, action_id, outbox_path=run_dir(run_id) / "outbox.jsonl")
    # The launch gate depends on these decisions: refresh it while waiting.
    g = current_gate(run)
    if run["status"] == "awaiting_founder" and g and g["phase"] == 5 and not g.get("founder_decision"):
        new = _phase5_gate(run).as_dict()
        g.update(recommendation=new["recommendation"], reasons=new["reasons"], checks=new["checks"])
        _write_gate(run, 5)
    save(run)
    return run


def _apply_decision(run_id: str, run: dict, d: dict) -> dict:
    """At a gate: settle pending approval items, then make the founder's call given in advance.
    "accept" follows the recommendation; any other allowed outcome is an override and carries the note."""
    for a in approval.pending(run):
        choice = d.get("actions", {}).get(a["target"], d.get("default_action"))
        if choice in ("approve", "reject"):
            try:
                run = decide_action(run_id, a["id"], choice == "approve", approval.FOUNDER, d.get("action_note", ""))
            except approval.BrokenPromise:
                run = load(run_id)  # stays pending: the launch gate shows it and the founder decides
    if run["status"] != "awaiting_founder":
        return run
    g = current_gate(run)
    choice = g["recommendation"] if d["decision"] == "accept" else d["decision"]
    if choice not in g["allowed"]:
        choice = g["recommendation"]
    note = d.get("note", "") if choice != g["recommendation"] else d.get("note_if_accepted", d.get("note", ""))
    return decide(run_id, choice, approval.FOUNDER, note)


def run_to_gate_with(run_id: str, decisions: list[dict]) -> dict:
    """Drive a run with a list of founder decisions given in advance, one per gate in order (used by tests)."""
    run = load(run_id)
    for d in decisions:
        run = advance(run_id)
        run = _apply_decision(run_id, run, d)
        if run["status"] != "ready":
            break
    return run


def run_with_phase_decisions(run_id: str, by_phase: dict, default: dict | None = None, max_gates: int = 20) -> dict:
    """Drive a run with founder decisions keyed by PHASE (used by the demo script), so an unexpected REPEAT does not
    shift later decisions onto the wrong gate. A recommended REPEAT that is accepted reruns the phase with the same
    decision; the gates themselves cap the repeats (gates.MAX_ATTEMPTS)."""
    default = default or {"decision": "accept", "default_action": "reject"}
    run = load(run_id)
    for _ in range(max_gates):
        run = advance(run_id)
        if run["status"] != "awaiting_founder":
            break
        d = by_phase.get(str(current_gate(run)["phase"]), default)
        run = _apply_decision(run_id, run, d)
        if run["status"] != "ready":
            break
    return run
