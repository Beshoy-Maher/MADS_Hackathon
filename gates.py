"""Gates between phases.

Every phase ends with a gate. A gate is one of three kinds:
  * evidence  - numbers measured against thresholds fixed BEFORE the data comes in
  * tests     - automated checks must pass
  * founder   - the founder must explicitly approve

The gate produces a recommendation (go / repeat / pivot / stop) with reasons.
The founder then makes the final call. Thresholds live in THRESHOLDS so they
are visible, versioned and can't be quietly moved after seeing the results.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

GO, REPEAT, PIVOT, STOP = "go", "repeat", "pivot", "stop"
OUTCOMES = (GO, REPEAT, PIVOT, STOP)
MAX_ATTEMPTS = 2  # after this, "repeat" is no longer offered: decide.

# Pre-registered thresholds. Changing them is a code change, visible in git.
THRESHOLDS = {
    "evidence": {
        "min_relevant_sources": 5,      # distinct URLs that are actually about the idea
        "min_independent_voices": 4,    # different people/communities (authors, subreddits, repo owners)
        "min_pain_signals": 2,          # posts where people describe the problem
        "min_demand_score": 40,         # 0-100
        "min_founder_fit": 50,          # 0-100
        "min_total_score": 50,          # 0-100
    },
    "demand": {
        "default_waitlist_target": 100,  # sign-ups
        "default_window_days": 14,
        "pivot_below_share": 0.5,        # under 50% of target: pivot or stop, never "almost there"
    },
    "build": {"min_pass_rate": 1.0},     # every MVP test must pass
    "launch": {"payment_tests_must_pass": True},
    "operate": {
        "min_real_buyers_for_decision": 10,
        "min_refund_rate_to_worry": 0.15,
        "review_after_days": 14,
    },
}


@dataclass
class Check:
    name: str
    passed: bool
    value: object
    threshold: object
    note: str = ""


@dataclass
class GateResult:
    phase: int
    gate: str
    kind: str  # evidence | tests | founder
    recommendation: str
    reasons: list[str]
    checks: list[Check] = field(default_factory=list)
    pivot_to: str | None = None
    allowed: tuple = OUTCOMES

    def as_dict(self) -> dict:
        d = asdict(self)
        d["allowed"] = list(self.allowed)
        return d


def _allowed(attempt: int) -> tuple:
    return OUTCOMES if attempt < MAX_ATTEMPTS else (GO, PIVOT, STOP)


# ------------------------------------------------------------- scope gate
def scope_gate(screening: dict) -> GateResult:
    """Before Phase 1, for an idea close to an excluded category (money, health, legal).

    The system does not guess. It names what it saw and the founder decides: GO confirms that the
    product is a tool, template or teaching material that gives no advice; PIVOT rewords the idea
    (type it in the note); STOP ends the run.
    """
    return GateResult(1, "scope_gate", "founder", PIVOT,
                      [screening.get("reason", ""), screening.get("safe_alternative", ""),
                       "GO = I confirm it gives no financial, health or legal advice. PIVOT = I will reword the idea (use the note). STOP = end here.",
                       "Whatever you choose, the system will not write financial, health or legal advice."],
                      [Check("clearly_outside_excluded_categories", False, ", ".join(screening.get("matches", [])) or "unclear",
                             "founder confirmation")],
                      allowed=(GO, PIVOT, STOP))


# ------------------------------------------------------------- phase 1 gate
def evidence_gate(candidates: list[dict], attempt: int = 1, sources_ok: bool = True) -> GateResult:
    """candidates[0] is the founder's (sharpened) idea; the rest are alternatives.

    Each candidate has: title, relevant_sources, voices, pain, demand_score,
    founder_fit, total, excluded (bool).
    """
    t = THRESHOLDS["evidence"]
    main = candidates[0]

    def checks_for(c: dict) -> list[Check]:
        return [
            Check("relevant_sources", c["relevant_sources"] >= t["min_relevant_sources"], c["relevant_sources"], t["min_relevant_sources"]),
            Check("independent_voices", c["voices"] >= t["min_independent_voices"], c["voices"], t["min_independent_voices"]),
            Check("pain_signals", c["pain"] >= t["min_pain_signals"], c["pain"], t["min_pain_signals"]),
            Check("demand_score", c["demand_score"] >= t["min_demand_score"], round(c["demand_score"], 1), t["min_demand_score"]),
            Check("founder_fit", c["founder_fit"] >= t["min_founder_fit"], round(c["founder_fit"], 1), t["min_founder_fit"]),
            Check("total_score", c["total"] >= t["min_total_score"], round(c["total"], 1), t["min_total_score"]),
            Check("allowed_product", not c.get("excluded"), "excluded" if c.get("excluded") else "ok", "not excluded"),
        ]

    main_checks = checks_for(main)
    failed = [c.name for c in main_checks if not c.passed]
    allowed = _allowed(attempt)
    if main.get("excluded"):
        return GateResult(1, "evidence_gate", "evidence", STOP, ["The product is in an excluded category."], main_checks, allowed=(STOP,))
    if not failed:
        reasons = [f"'{main['title']}' meets every pre-set evidence threshold."]
        if main.get("platforms", 2) < 2:
            reasons.append("All of this evidence comes from one platform. It passes the thresholds, but treat it as weaker than it "
                           "looks: confirm it in the customer interviews (step 4) before spending money.")
        return GateResult(1, "evidence_gate", "evidence", GO, reasons, main_checks, allowed=allowed)
    passing_alts = [c for c in candidates[1:] if not c.get("excluded") and all(ch.passed for ch in checks_for(c))]
    if passing_alts:
        best = max(passing_alts, key=lambda c: c["total"])
        return GateResult(1, "evidence_gate", "evidence", PIVOT,
                          [f"The starting idea fails: {', '.join(failed)}.",
                           f"Alternative '{best['title']}' passes every threshold (total {best['total']:.0f})."],
                          main_checks, pivot_to=best["title"], allowed=allowed)
    too_little = all(c["relevant_sources"] < t["min_relevant_sources"] for c in candidates if not c.get("excluded"))
    no_fit = all(c["founder_fit"] < t["min_founder_fit"] for c in candidates if not c.get("excluded"))
    if too_little and no_fit:
        # More searching cannot fix founder fit: it depends on the founder's skills, hours and budget, not on evidence.
        return GateResult(1, "evidence_gate", "evidence", STOP,
                          ["Too little public discussion was found, and founder fit fails for every candidate.",
                           "A broader search could not change founder fit, which comes from the founder's skills, hours and budget.",
                           "Recommendation: do not launch this. Spending time and money on it is not supported by the evidence."],
                          main_checks, allowed=allowed)
    if too_little and REPEAT in allowed:
        return GateResult(1, "evidence_gate", "evidence", REPEAT,
                          ["Too little public discussion was found for any candidate to judge demand either way.",
                           "Absence of evidence is not evidence of absence: repeat with broader search terms, and talk to "
                           "5 real customers (interview guide in step 4) before deciding."], main_checks, allowed=allowed)
    if too_little:
        return GateResult(1, "evidence_gate", "evidence", STOP,
                          [f"After {attempt} searches there is still no public evidence that people have this problem.",
                           "Recommendation: do not build yet. Run the customer interviews first; restart Discover only if they show "
                           "real commitments (time, money, introductions)."], main_checks, allowed=allowed)
    if not sources_ok and REPEAT in allowed:
        return GateResult(1, "evidence_gate", "evidence", REPEAT,
                          ["Some research sources could not be reached, so the evidence is incomplete. Repeat the search before deciding."],
                          main_checks, allowed=allowed)
    reasons = [f"The starting idea fails: {', '.join(failed)}.",
               "No alternative passes the thresholds either.",
               "Recommendation: do not launch this. Spending time and money on it is not supported by the evidence."]
    return GateResult(1, "evidence_gate", "evidence", STOP, reasons, main_checks, allowed=allowed)


# ------------------------------------------------------------- phase 2 gate
def demand_gate(signups: int | None, target: int, days_elapsed: int | None, window_days: int,
                attempt: int = 1, canvas_ok: bool = True) -> GateResult:
    """Waitlist test. signups=None means no real traffic yet (test not run)."""
    allowed = _allowed(attempt)
    checks = [Check("lean_canvas_complete", canvas_ok, "complete" if canvas_ok else "incomplete", "complete")]
    if signups is None:
        checks.append(Check("waitlist_signups", False, "not measured yet (needs real visitors)", f">= {target} in {window_days} days"))
        rec = REPEAT if REPEAT in allowed else STOP
        return GateResult(2, "demand_gate", "evidence", rec,
                          ["The landing-page test has not run on real visitors, so demand is not proven yet.",
                           f"Pre-set target: {target} sign-ups in {window_days} days. Publish the page (with your approval), "
                           "collect real sign-ups, then re-run this gate.",
                           "The system will not invent sign-ups to pass this gate."], checks, allowed=allowed)
    share = signups / max(1, target)
    checks.append(Check("waitlist_signups", signups >= target, signups, f">= {target} in {window_days} days"))
    if signups >= target:
        return GateResult(2, "demand_gate", "evidence", GO, [f"{signups} real sign-ups vs target {target}."], checks, allowed=allowed)
    window_over = days_elapsed is not None and days_elapsed >= window_days
    if not window_over and REPEAT in allowed:
        return GateResult(2, "demand_gate", "evidence", REPEAT,
                          [f"{signups}/{target} sign-ups after {days_elapsed} of {window_days} days. Keep the test running."], checks, allowed=allowed)
    if share < THRESHOLDS["demand"]["pivot_below_share"]:
        return GateResult(2, "demand_gate", "evidence", STOP if attempt >= MAX_ATTEMPTS else PIVOT,
                          [f"Only {signups} of {target} sign-ups ({share:.0%}) in the full window. The target was missed.",
                           "Recommendation: pivot back to Discover (different audience or problem) or stop. The result is not spun."],
                          checks, allowed=allowed)
    return GateResult(2, "demand_gate", "evidence", REPEAT if REPEAT in allowed else PIVOT,
                      [f"{signups} of {target} sign-ups ({share:.0%}): partial signal. Repeat with a sharper message or narrower audience."],
                      checks, allowed=allowed)


# ------------------------------------------------------------- phase 3 gate
def build_gate(test_results: list[dict], attempt: int = 1) -> GateResult:
    passed = sum(1 for r in test_results if r["passed"])
    total = len(test_results)
    rate = passed / total if total else 0
    checks = [Check(r["name"], r["passed"], r.get("value"), r.get("threshold"), r.get("note", "")) for r in test_results]
    allowed = _allowed(attempt)
    if total and rate >= THRESHOLDS["build"]["min_pass_rate"]:
        return GateResult(3, "build_gate", "tests", GO, [f"All {total} MVP tests pass."], checks, allowed=allowed)
    failing = [r["name"] for r in test_results if not r["passed"]]
    return GateResult(3, "build_gate", "tests", REPEAT if REPEAT in allowed else STOP,
                      [f"{passed}/{total} tests pass. Failing: {', '.join(failing)}. Rebuild before going on."], checks, allowed=allowed)


# ------------------------------------------------------------- phase 4 gate
def commercial_gate(price_ok: bool, policies_ok: bool, guardrail_violations: int, attempt: int = 1) -> GateResult:
    checks = [Check("price_set_with_rationale", price_ok, price_ok, True),
              Check("terms_privacy_refund_drafted", policies_ok, policies_ok, True),
              Check("no_guardrail_violations_left", guardrail_violations == 0, guardrail_violations, 0)]
    allowed = _allowed(attempt)
    if all(c.passed for c in checks):
        return GateResult(4, "commercial_gate", "founder", GO,
                          ["Price and draft policies are ready for your review. They are drafts, not legal advice: "
                           "have them checked before real sales."], checks, allowed=allowed)
    return GateResult(4, "commercial_gate", "founder", REPEAT if REPEAT in allowed else STOP,
                      ["Commercial setup is incomplete."], checks, allowed=allowed)


# ------------------------------------------------------------- phase 5 gate
def launch_gate(payment_tests: list[dict], publish_actions: list[dict], attempt: int = 1) -> GateResult:
    tests_ok = bool(payment_tests) and all(t["passed"] for t in payment_tests)
    approved = [a for a in publish_actions if a["status"] == "approved"]
    pending = [a for a in publish_actions if a["status"] == "pending"]
    checks = [Check("sale_to_cash_tests_pass", tests_ok, f"{sum(t['passed'] for t in payment_tests)}/{len(payment_tests)}", "all"),
              Check("launch_items_reviewed_by_founder", not pending, f"{len(approved)} approved, {len(pending)} pending", "0 pending")]
    allowed = _allowed(attempt)
    if tests_ok and not pending:
        return GateResult(5, "launch_gate", "founder", GO, ["Delivery flow passes its tests and every launch item was reviewed by you."],
                          checks, allowed=allowed)
    reasons = []
    if not tests_ok:
        reasons.append("The sale-to-delivery tests do not all pass.")
    if pending:
        reasons.append(f"{len(pending)} launch item(s) still wait for your Approve/Reject.")
    return GateResult(5, "launch_gate", "founder", REPEAT if REPEAT in allowed else STOP, reasons, checks, allowed=allowed)


# ------------------------------------------------------------- phase 6 gate
def operate_gate(real_buyers: int, refund_rate: float | None, waitlist: int | None, attempt: int = 1) -> GateResult:
    t = THRESHOLDS["operate"]
    checks = [Check("enough_real_buyers_to_judge", real_buyers >= t["min_real_buyers_for_decision"], real_buyers, t["min_real_buyers_for_decision"]),
              Check("refund_rate_ok", refund_rate is None or refund_rate < t["min_refund_rate_to_worry"],
                    "n/a" if refund_rate is None else f"{refund_rate:.0%}", f"< {t['min_refund_rate_to_worry']:.0%}")]
    allowed = _allowed(attempt)
    if real_buyers < t["min_real_buyers_for_decision"]:
        return GateResult(6, "operate_gate", "evidence", REPEAT if REPEAT in allowed else STOP,
                          [f"Only {real_buyers} real buyers so far: too little data to persevere or pivot with confidence.",
                           f"Keep operating and review again after {t['review_after_days']} days. Numbers from MOCKED test orders are excluded."],
                          checks, allowed=allowed)
    if refund_rate is not None and refund_rate >= t["min_refund_rate_to_worry"]:
        return GateResult(6, "operate_gate", "evidence", PIVOT, [f"Refund rate {refund_rate:.0%} is too high: the product misses the need."], checks, allowed=allowed)
    return GateResult(6, "operate_gate", "evidence", GO, ["Real buyers and a healthy refund rate: persevere."], checks, allowed=allowed)


def validate_decision(decision: str, gate: dict) -> str:
    decision = (decision or "").strip().lower()
    if decision not in gate.get("allowed", OUTCOMES):
        raise ValueError(f"decision must be one of {gate.get('allowed')}")
    return decision
