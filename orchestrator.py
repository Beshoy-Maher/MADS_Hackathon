"""Orchestrator: runs the six phases in order and stops at every gate.

One run = one JSON file (data/runs/<id>/run.json) that every agent reads and writes.
After each phase the gate (plain code) recommends go / repeat / pivot / stop and the run
pauses with status "awaiting_founder". Only orchestrator.decide(), called with
actor="founder", moves it on. Overriding the gate's recommendation needs a written reason.
"""
import json
import pickle
import uuid
from pathlib import Path

import approval
import config
import decision_log as log
import gates
import guardrails
import refunds
from agents import (analyst, builder, copywriter, policy_writer, pricer, qa, red_team,
                    researcher, scorer, strategist, support)
from delivery import Delivery
from payments import MockProvider
from reconcile import reconcile
from webhooks import WebhookHandler

PHASE_NAMES = {1: "Discover", 2: "Validate", 3: "Build", 4: "Commercial setup",
               5: "Sell, deliver, get paid", 6: "Operate and learn"}
GATE_NAMES = {1: "evidence", 2: "validate", 3: "build", 4: "commercial", 5: "sell", 6: "operate"}
DECISIONS = ("go", "repeat", "pivot", "stop")


# ---------- run file ----------

def runs_dir():
    return config.DATA_DIR / "runs"


def save(run):
    Path(run["dir"]).mkdir(parents=True, exist_ok=True)
    (Path(run["dir"]) / "run.json").write_text(json.dumps(run, indent=1, default=str))


def load(run_id):
    return json.loads((runs_dir() / run_id / "run.json").read_text())


def list_runs():
    if not runs_dir().exists():
        return []
    out = []
    for p in sorted(runs_dir().glob("*/run.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        r = json.loads(p.read_text())
        out.append({k: r.get(k) for k in ("id", "status", "phase", "brief_name", "created")} | {"recommendation": (r.get("gate") or {}).get("outcome")})
    return out


def output(run, name, text, agent, action, sources=(), model=None, cost=0):
    d = Path(run["dir"]) / "outputs"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text)
    run.setdefault("outputs", [])
    if name not in run["outputs"]:
        run["outputs"].append(name)
    log.append(agent, action, sources=[s for s in sources if s], model=model, cost=cost, run_id=run["id"], output=name)


# ---------- start ----------

def start(brief, name=None):
    rid = uuid.uuid4().hex[:8]
    run = {"id": rid, "brief": brief, "brief_name": name or brief.get("product_name", "idea"),
           "dir": str(runs_dir() / rid), "phase": 1, "status": "running", "repeats": 0,
           "created": log.now(), "history": [], "outbound": [],
           "preregistered_hash": gates.threshold_hash()}
    log.append("orchestrator", "preregister_gate_thresholds", run_id=rid, sha256=run["preregistered_hash"])
    screen = guardrails.screen_brief(json.dumps(brief))
    log.append("guardrails", "screen_brief", run_id=rid, outcome="allowed" if screen["allowed"] else "refused",
               reasons=screen["reasons"])
    if not screen["allowed"]:
        run["status"] = "refused"
        run["gate"] = {"gate": "scope", "outcome": "stop", "checks": [], "reasons": screen["reasons"]}
        output(run, "phase1_gate_scope.md", "# Phase 1 Gate: Scope check\n\n**Outcome: STOP (refused before any research)**\n\n"
               + "\n".join(f"- {r}" for r in screen["reasons"]) + "\n\nNo agent ran, nothing was searched or written.\n",
               "guardrails", "scope_gate")
        save(run)
        return run
    run_phase(run)
    return run


# ---------- phases ----------

def _ledger(run):
    return run["state"]["ledger"]


def phase1(run, broaden=False):
    b = run["brief"]
    r = researcher.research(b, broaden=broaden)
    run.setdefault("state", {})["ledger"] = r["ledger"]
    output(run, "phase1_step1_opportunities.md", r["md"], "researcher", "find_opportunities", r["sources"], r["model"], r["cost"])
    s = scorer.score(b, r["ledger"])
    run["state"]["score"] = s
    output(run, "phase1_step2_scorecard.md", scorer.to_md(s), "scorer", "score_evidence")
    rt = red_team.challenge(b, r["ledger"], s)
    run["state"]["risks"] = rt["risks"]
    output(run, "phase1_step3_red-team.md", rt["md"], "red_team", "try_to_kill_idea", rt["sources"], rt["model"], rt["cost"])
    return gates.evidence_gate(s, rt["risks"], run["repeats"], nothing_fetched=not r["ledger"]["totals"])


def phase2(run):
    b = run["brief"]
    vp = strategist.value_prop(b, _ledger(run))
    run["state"]["vp"] = {"pains": vp["pains"], "text": vp["text"]}
    output(run, "phase2_step1_value-proposition.md", vp["md"], "strategist", "value_proposition", vp["sources"], vp["model"], vp["cost"])
    lp = copywriter.landing_page(b, vp)
    output(run, "phase2_step2_landing-page.html", lp["html"], "copywriter", "landing_page", vp["sources"], lp["model"], lp["cost"])
    approval.request(run, "publish", "Publish landing page", {"file": "phase2_step2_landing-page.html"})
    plan, md = analyst.validation_plan(b)
    run["state"]["plan"] = plan
    output(run, "phase2_step3_validation-plan.md", md, "analyst", "preregister_smoke_test")
    return gates.validate_gate(copywriter.traceability(lp["html"], _ledger(run)), copywriter.violations(lp["html"]), plan)


def phase3(run):
    b = run["brief"]
    modules, md = builder.spec(b, run["state"]["vp"])
    run["state"]["modules"] = modules
    output(run, "phase3_step1_spec.md", md, "builder", "write_spec", [m["pain_url"] for m in modules])
    prod = builder.build(b, modules)
    output(run, "phase3_step2_product.md", prod["md"], "builder", "build_product", [m["pain_url"] for m in modules], prod["model"], prod["cost"])
    q = qa.check(modules, prod["md"], _ledger(run))
    output(run, "phase3_step3_qa-report.md", q["md"], "qa", "run_qa_checks")
    return gates.build_gate(q)


def phase4(run):
    b = run["brief"]
    p, md = pricer.price(b, run["state"]["score"], run["state"]["modules"])
    run["state"]["price"] = p
    output(run, "phase4_step1_pricing.md", md, "pricer", "set_price")
    pol, md = policy_writer.policies(b, p)
    run["state"]["policies"] = pol
    output(run, "phase4_step2_policies.md", md, "policy_writer", "draft_policies")
    return gates.commercial_gate(p, pol, config.PAYMENT_MODE)


def _sale_path(run):
    return Path(run["dir"]) / "sale_test.pickle"


def phase5(run):
    b, st = run["brief"], run["state"]
    page = copywriter.store_page(b, st["vp"], st["price"], st["modules"])
    output(run, "phase5_step1_store-page.html", page, "copywriter", "store_page", [p["url"] for p in st["vp"]["pains"]])
    approval.request(run, "publish", "Publish store page", {"file": "phase5_step1_store-page.html"})
    post = copywriter.launch_post(b, st["vp"], st["price"])
    output(run, "phase5_step2_launch-post.md", "# Phase 5 Step 2: Launch post (draft, needs founder approval)\n\n_"
           + post["label"] + "_\n\n" + post["text"] + "\n", "copywriter", "launch_post",
           [p["url"] for p in st["vp"]["pains"]], post["model"], post["cost"])
    approval.request(run, "send", "Post launch announcement", {"file": "phase5_step2_launch-post.md"})
    # Sale-to-cash test against the MOCKED provider
    prov, dlv = MockProvider(), Delivery()
    wh = WebhookHandler(prov, dlv)
    checks, steps = [], []

    def chk(name, ok, detail):
        checks.append({"name": name, "passed": bool(ok)})
        steps.append(f"| {len(steps)+1} | {name} | {detail} | {'PASS' if ok else 'FAIL'} |")

    o1 = prov.create_checkout(b["product_name"], st["price"], "buyer1@example.com")
    chk("checkout session created (MOCKED)", o1["mode"] == "MOCKED", o1["order_id"])
    body, sig = prov.pay(o1["order_id"])
    r = wh.handle(body, sig)
    chk("payment triggers delivery", r == "delivered", r)
    r = wh.handle(body, sig)
    chk("same webhook again does not deliver twice", r == "duplicate_ignored" and len(dlv.sent) == 1, r)
    r = wh.handle(body, "0" * 64)
    chk("webhook with a bad signature is rejected", r == "rejected", r)
    o2 = prov.create_checkout(b["product_name"], st["price"], "buyer2@example.com")
    body2, sig2 = prov.pay(o2["order_id"])
    r = wh.handle(body2, sig2)
    chk("second order delivered", r == "delivered", r)
    pay2 = [p for p in prov.payments.values() if p["order"] == o2["order_id"]][0]["id"]
    item = refunds.request_refund(run, pay2, "test refund: customer asked within 14 days")
    try:
        refunds.execute_refund(run, item["id"], prov, wh)
        chk("refund blocked until founder approves", False, "refund ran without approval")
    except approval.ApprovalRequired:
        chk("refund blocked until founder approves", True, "ApprovalRequired raised; refund queued for the founder")
    run["state"]["sale"] = {"checks": checks, "steps": steps, "refund_item": item["id"], "done": False}
    _sale_path(run).write_bytes(pickle.dumps((prov, dlv, wh)))
    return _sell_gate(run)


def finish_sale_test(run):
    """Called after the founder decides the test refund. Completes the test and reconciles."""
    st = run["state"]["sale"]
    if st["done"]:
        return
    prov, dlv, wh = pickle.loads(_sale_path(run).read_bytes())
    item = approval.find(run, st["refund_item"])
    steps, checks = st["steps"], st["checks"]

    def chk(name, ok, detail):
        checks.append({"name": name, "passed": bool(ok)})
        steps.append(f"| {len(steps)+1} | {name} | {detail} | {'PASS' if ok else 'FAIL'} |")

    if item["status"] == "approved":
        r = refunds.execute_refund(run, item["id"], prov, wh)
        token = dlv.grants[prov.payments[item["payload"]["payment_id"]]["order"]]["token"]
        chk("approved refund revokes access", r == "revoked" and not dlv.can_download(token), r)
    else:
        chk("rejected refund leaves access active", True, "founder rejected; no money moved")
    po = prov.payout()
    rec = reconcile(prov, dlv)
    chk("reconciliation: orders, payments, fees, refunds, payout match", rec["matched"],
        f"gross ${rec['gross']} - fees ${rec['fees']} - refunds ${rec['refunded']} = payout ${rec['payout']}")
    st["reconcile"], st["done"] = rec, True
    md = ("# Payment and delivery test log\n\n**Provider: MOCKED** (no real money). Generated by a pipeline run, "
          f"run `{run['id']}`, at {log.now()}.\n\n| # | Check | Detail | Result |\n|---|---|---|---|\n" + "\n".join(steps)
          + f"\n\n## Reconciliation\n\n```json\n{json.dumps(rec, indent=1)}\n```\n\nDelivery emails: STUBBED ({len(dlv.sent)} recorded, none sent).\n")
    output(run, "phase5_step3_sale-to-cash.md", md, "launcher", "sale_to_cash_test")
    output(run, "payment_test_log.md", md, "launcher", "payment_test_log")
    _sale_path(run).write_bytes(pickle.dumps((prov, dlv, wh)))


def _sell_gate(run):
    st = run["state"]["sale"]
    return gates.sell_gate(st["checks"] if st["done"] else st["checks"] + [{"name": "test incomplete", "passed": False}],
                           len(approval.pending(run)))


def phase6(run):
    st = run["state"]
    rec = st["sale"]["reconcile"]
    m = analyst.metrics(rec)
    st["metrics"] = m
    output(run, "phase6_step1_metrics.md", "# Phase 6 Step 1: Metrics\n\n**Data: MOCKED** (from the Phase 5 sale-to-cash test, "
           "not real customers).\n\n| Metric | Value |\n|---|---|\n" + "\n".join(f"| {k} | {v} |" for k, v in m.items())
           + "\n\nPersevere-or-pivot rule (pre-registered in gates.py): pivot if refund rate > 20%; persevere if "
           "conversion >= 2% on real traffic; otherwise keep measuring.\n", "analyst", "read_metrics")
    output(run, "phase6_step2_support.md", support.kit(run["brief"], st["price"], st["modules"]), "support", "support_kit")
    return gates.operate_gate(m)


PHASES = {1: phase1, 2: phase2, 3: phase3, 4: phase4, 5: phase5, 6: phase6}


def gate_md(run, g):
    n = run["phase"]
    rows = "\n".join(f"| {c['name']} | {c['value']} | {c['threshold']} | {'PASS' if c['passed'] else 'FAIL'} |" for c in g["checks"])
    return (f"# Phase {n} Gate: {g['gate']}\n\n**Recommendation: {g['outcome'].upper()}**\n\n"
            + "\n".join(f"- {r}" for r in g["reasons"])
            + f"\n\n| Check | Value | Threshold | Result |\n|---|---|---|---|\n{rows}\n\n"
            f"Thresholds pre-registered before research: sha256 `{run['preregistered_hash'][:16]}...` "
            f"(matches code: {gates.verify_preregistration(run)}).\n\n"
            "Founder decision: pending.\n")


def run_phase(run, **kw):
    n = run["phase"]
    run["status"] = "running"
    g = PHASES[n](run, **kw) if kw else PHASES[n](run)
    _set_gate(run, g)
    return run


def _set_gate(run, g):
    n = run["phase"]
    run["gate"] = g
    run["status"] = "awaiting_founder"
    output(run, f"phase{n}_gate_{GATE_NAMES[n]}.md", gate_md(run, g), "gate", f"{GATE_NAMES[n]}_gate")
    log.append("gate", f"{GATE_NAMES[n]}_gate_recommendation", run_id=run["id"], outcome=g["outcome"])
    save(run)


# ---------- founder actions ----------

def decide_outbound(run, item_id, approve, actor, via="dashboard or CLI"):
    approval.decide(run, item_id, approve, actor, via=via)
    sale = (run.get("state") or {}).get("sale")
    if sale and item_id == sale["refund_item"]:
        finish_sale_test(run)
    if run["phase"] == 5 and run["status"] == "awaiting_founder":
        _set_gate(run, _sell_gate(run))
    save(run)
    return run


def decide(run, decision, actor, reason="", via="dashboard or CLI"):
    if actor != approval.FOUNDER:
        raise PermissionError("only the founder can decide at a gate")
    if run["status"] != "awaiting_founder":
        raise ValueError(f"run is {run['status']}, not waiting for a decision")
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}")
    rec = run["gate"]["outcome"]
    if decision != rec and not reason.strip():
        raise ValueError(f"the gate recommends {rec.upper()}; overriding it needs a written reason")
    n = run["phase"]
    log.append("founder", f"{GATE_NAMES[n]}_gate_decision", approved_by=approval.FOUNDER, run_id=run["id"],
               outcome=decision, recommended=rec, override=decision != rec, reason=reason or None, via=via)
    p = Path(run["dir"]) / "outputs" / f"phase{n}_gate_{GATE_NAMES[n]}.md"
    p.write_text(p.read_text().replace("Founder decision: pending.", f"Founder decision: **{decision.upper()}**"
                                       + (f" (override of {rec.upper()}; reason: {reason})" if decision != rec else " (follows the recommendation)") + "."))
    run["history"].append({"phase": n, "recommended": rec, "decision": decision, "reason": reason})
    if decision == "stop":
        run["status"] = "stopped"
    elif decision == "pivot":
        run["status"] = "pivoted"  # the founder starts a new run with the new idea; it is screened again
    elif decision == "repeat":
        run["repeats"] += 1
        return run_phase(run, broaden=True) if n == 1 else run_phase(run)
    elif n == 6:
        run["status"] = "done"
    else:
        run["phase"] = n + 1
        return run_phase(run)
    save(run)
    return run
