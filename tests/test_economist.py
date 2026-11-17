"""Economist (Phase 4, step 4): how many sales a price needs. Arithmetic only, no forecast, nothing guessed."""
import json

import guardrails
import orchestrator
import payments
from agents import intake
from agents.economist import REFUND_RATE, economics, net_per_sale, sales_needed
from conftest import ROOT

STRONG = json.loads((ROOT / "briefs" / "strong_founder.json").read_text())


def test_net_per_sale_matches_the_mocked_provider_fee():
    # $19: 0.9 x 19 - (2.9% x 19 + $0.30) = 17.10 - 0.85 = 16.25
    assert payments.fee_for(19) == 0.85
    assert net_per_sale(19) == 16.25
    assert net_per_sale(19, refund_rate=0) == round(19 - payments.fee_for(19), 2)


def test_sales_needed_rounds_up_and_handles_missing_numbers():
    assert sales_needed(40, 16.25) == 3
    assert sales_needed(32.5, 16.25) == 2
    assert sales_needed(0, 16.25) == 0
    assert sales_needed(None, 16.25) is None
    assert sales_needed(40, 0) is None


def test_time_line_only_with_an_hourly_rate():
    e = economics(19, budget=40, hours_per_week=8, hourly_rate=None, target=100)
    assert e["sales_to_cover_budget"] == 3
    assert e["monthly_time_value_usd"] is None and e["sales_per_month_for_time"] is None
    e = economics(19, budget=40, hours_per_week=8, hourly_rate=10, target=100)
    assert e["monthly_time_value_usd"] == round(8 * 52 / 12 * 10, 2)
    assert e["sales_per_month_for_time"] == 22  # 346.67 / 16.25 = 21.3 -> 22
    assert not e["flags"]


def test_flags_when_even_every_signup_buying_is_not_enough():
    e = economics(9.99, budget=2000, hours_per_week=20, hourly_rate=25, target=100)
    assert len(e["flags"]) == 2
    assert any("budget" in f for f in e["flags"]) and any("time" in f for f in e["flags"])


def test_flags_a_price_that_keeps_nothing():
    e = economics(0.3, budget=None, hours_per_week=None, hourly_rate=None, target=100)
    assert e["net_per_sale_usd"] <= 0 and e["flags"]
    assert e["sales_to_cover_budget"] is None


def test_hourly_rate_is_optional_and_never_guessed():
    assert intake.normalize({"idea": "x", "founder_name": "A"})["hourly_rate_usd"] is None
    assert intake.normalize({"idea": "x", "founder_name": "A", "hourly_rate_usd": "12"})["hourly_rate_usd"] == 12
    assert "hourly_rate_usd" not in intake.REQUIRED


def test_phase4_writes_unit_economics_and_the_gate_is_unchanged():
    run = orchestrator.create_run(dict(STRONG, hourly_rate_usd=1000))
    decisions = [{"decision": "accept", "default_action": "approve"},
                 {"decision": "go", "default_action": "approve", "note": "founder override for test"}] + \
                [{"decision": "accept", "default_action": "approve"}] * 2
    run = orchestrator.run_to_gate_with(run["id"], decisions)
    step = [s for s in run["steps"] if s["phase"] == 4 and s["step"] == 4]
    assert step and step[0]["agent"] == "economist" and step[0]["model"] is None
    text = (orchestrator.run_dir(run["id"]) / "outputs" / "phase4_step4_unit-economics.md").read_text(encoding="utf-8")
    assert "Kept per sale" in text and "ASSUMPTION" in text and "not a forecast" in text
    assert not guardrails.scan_output(text).violations
    g = [g for g in run["gates"] if g["phase"] == 4][-1]
    # $1000/h makes the time line exceed the target: a warning reason, but the recommendation is still the code's.
    assert any(r.startswith("Unit economics warning") for r in g["reasons"])
    assert g["recommendation"] == "go"
    assert run["ctx"]["economics"]["refund_rate"] == REFUND_RATE
