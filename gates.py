"""The six gates. Plain code, no model.

The thresholds below are PRE-REGISTERED: when a run starts, the orchestrator writes the
SHA-256 of this table into the decision log *before* any evidence is fetched. If anyone
(or any model) changes a threshold after seeing the data, the hash in the run no longer
matches `threshold_hash()`, and `verify_preregistration()` reports it.

Each gate returns a recommendation: go | repeat | pivot | stop. The founder makes the
final call (see orchestrator.decide), and an override of the recommendation needs a
written reason, which is logged.
"""
import hashlib
import json

THRESHOLDS = {
    "evidence": {"min_sources": 10, "min_recent_voices": 5, "min_demand": 40, "min_fit": 50,
                 "stop_below_recent_voices": 3, "stop_below_demand": 25, "max_repeats": 2},
    "validate": {"min_traceability": 1.0, "max_rule_violations": 0, "min_smoke_visitors": 200},
    "build": {"min_qa_pass_rate": 1.0},
    "commercial": {"min_price": 5, "max_price": 49, "min_refund_days": 14},
    "sell": {"payment_checks_must_pass": True, "max_pending_approvals": 0},
    "operate": {"max_refund_rate": 0.2, "min_conversion": 0.02},
}


def threshold_hash():
    return hashlib.sha256(json.dumps(THRESHOLDS, sort_keys=True).encode()).hexdigest()


def verify_preregistration(run):
    return run.get("preregistered_hash") == threshold_hash()


def _check(name, value, threshold, passed):
    return {"name": name, "value": value, "threshold": threshold, "passed": bool(passed)}


def _result(gate, outcome, checks, reasons):
    return {"gate": gate, "outcome": outcome, "checks": checks, "reasons": reasons}


def evidence_gate(score, risks, repeats=0, nothing_fetched=False):
    t = THRESHOLDS["evidence"]
    checks = [
        _check("distinct source URLs", score["sources"], f">= {t['min_sources']}", score["sources"] >= t["min_sources"]),
        _check("recent pain voices (< 3 years)", score["recent_voices"], f">= {t['min_recent_voices']}", score["recent_voices"] >= t["min_recent_voices"]),
        _check("demand score", score["demand"], f">= {t['min_demand']}", score["demand"] >= t["min_demand"]),
        _check("founder fit", score["fit"], f">= {t['min_fit']}", score["fit"] >= t["min_fit"]),
        _check("critical risks from red team", len(risks), "== 0", len(risks) == 0),
    ]
    if nothing_fetched:
        return _result("evidence", "repeat", checks, ["Every evidence source failed (network), so there is nothing to judge. Retry; nothing is assumed."])
    if all(c["passed"] for c in checks):
        return _result("evidence", "go", checks, ["Every pre-registered threshold is met."])
    if score["recent_voices"] < t["stop_below_recent_voices"] or score["demand"] < t["stop_below_demand"]:
        return _result("evidence", "stop", checks, [
            f"Weak evidence: {score['recent_voices']} recent pain voices and demand {score['demand']} "
            f"(STOP below {t['stop_below_recent_voices']} voices or demand {t['stop_below_demand']}).",
            "Recommendation: do not build this. Keep the time and money."])
    if repeats >= t["max_repeats"]:
        return _result("evidence", "stop", checks, [f"Still short after {repeats} repeats: stop rather than keep searching for a yes."])
    if risks or score["fit"] < t["min_fit"]:
        why = [r["risk"] for r in risks] or [f"founder fit {score['fit']} < {t['min_fit']}"]
        return _result("evidence", "pivot", checks, ["Demand exists but: " + "; ".join(why)])
    return _result("evidence", "repeat", checks, ["Some signal, not enough yet: broaden the search or interview users."])


def validate_gate(traceability, violations, plan):
    t = THRESHOLDS["validate"]
    checks = [
        _check("landing-page claims traced to a source URL", round(traceability, 2), f">= {t['min_traceability']}", traceability >= t["min_traceability"]),
        _check("rule violations left in landing page", violations, f"<= {t['max_rule_violations']}", violations <= t["max_rule_violations"]),
        _check("smoke-test visitors target set", plan.get("visitors_target", 0), f">= {t['min_smoke_visitors']}", plan.get("visitors_target", 0) >= t["min_smoke_visitors"]),
    ]
    ok = all(c["passed"] for c in checks)
    return _result("validate", "go" if ok else "repeat", checks,
                   ["Message matches evidence; smoke test is pre-registered. Real sign-ups are not collected yet (STUBBED)."] if ok
                   else ["Fix the failed checks and run the phase again."])


def build_gate(qa):
    t = THRESHOLDS["build"]
    rate = qa["passed"] / max(1, qa["total"])
    checks = [_check("QA checks passed", f"{qa['passed']}/{qa['total']}", f"rate >= {t['min_qa_pass_rate']}", rate >= t["min_qa_pass_rate"])]
    ok = checks[0]["passed"]
    return _result("build", "go" if ok else "repeat", checks, ["Every spec item is in the product." if ok else "Some QA checks failed."])


def commercial_gate(price, policies, payment_mode):
    t = THRESHOLDS["commercial"]
    checks = [
        _check("price in band (USD)", price, f"{t['min_price']}-{t['max_price']}", t["min_price"] <= price <= t["max_price"]),
        _check("refund window (days)", policies.get("refund_days", 0), f">= {t['min_refund_days']}", policies.get("refund_days", 0) >= t["min_refund_days"]),
        _check("privacy: no card numbers or passwords stored", policies.get("stores_cards", True) is False, "True", policies.get("stores_cards", True) is False),
        _check("payment mode", payment_mode, "mock", payment_mode == "mock"),
    ]
    ok = all(c["passed"] for c in checks)
    return _result("commercial", "go" if ok else "repeat", checks, ["Commercial setup is complete." if ok else "Fix the failed checks."])


def sell_gate(payment_checks, pending):
    t = THRESHOLDS["sell"]
    passed = sum(1 for c in payment_checks if c["passed"])
    checks = [
        _check("sale-to-cash test checks passed", f"{passed}/{len(payment_checks)}", "all", passed == len(payment_checks)),
        _check("outbound items waiting for founder", pending, f"<= {t['max_pending_approvals']}", pending <= t["max_pending_approvals"]),
    ]
    ok = all(c["passed"] for c in checks)
    reason = "Sale to cash works end to end (MOCKED provider)." if ok else (
        "Founder still has to approve or reject outbound items." if pending else "A payment check failed.")
    return _result("sell", "go" if ok else "repeat", checks, [reason])


def operate_gate(metrics):
    t = THRESHOLDS["operate"]
    real = metrics.get("data_source") == "real"
    checks = [
        _check("metrics come from real customers", metrics.get("data_source"), "real", real),
        _check("refund rate", metrics.get("refund_rate"), f"<= {t['max_refund_rate']}", metrics.get("refund_rate", 1) <= t["max_refund_rate"]),
        _check("visitor-to-buyer conversion", metrics.get("conversion"), f">= {t['min_conversion']}", (metrics.get("conversion") or 0) >= t["min_conversion"]),
    ]
    if not real:
        return _result("operate", "repeat", checks, ["Only MOCKED test data so far. Persevere-or-pivot needs real sales: collect them, then rerun this phase."])
    if metrics["refund_rate"] > t["max_refund_rate"]:
        return _result("operate", "pivot", checks, ["Too many refunds: the product does not deliver what the page promises."])
    ok = all(c["passed"] for c in checks)
    return _result("operate", "go" if ok else "repeat", checks, ["Persevere." if ok else "Below target: improve and measure again."])
