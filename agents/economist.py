"""Phase 4, step 4: unit economics. How many sales does this price need before it is worth it?

Plain arithmetic, no model. From the Phase 4 price, the payment fee (the same fee model as payments.py),
an assumed refund rate, the founder's budget and hours, it works out:

- what the founder keeps per sale, on average, after fees and refunds;
- how many sales cover the budget;
- how many sales a month would pay for the founder's weekly hours, only if the founder gave an hourly rate;
- whether those numbers are more than the demand test's sign-up target (Phase 2): if even every sign-up
  buying would not be enough, the founder is told before launch.

It never forecasts sales or income: it says how many sales would be needed, never how many will happen.
A number the brief does not give stays "not given"; nothing is guessed.
"""
from __future__ import annotations

import math

import payments
from agents.base import Agent, StepResult, DETERMINISTIC, footer

REFUND_RATE = 0.10        # ASSUMPTION: share of buyers who ask for a refund
WEEKS_PER_MONTH = 52 / 12


def net_per_sale(price: float, refund_rate: float = REFUND_RATE) -> float:
    """Average amount kept per sale. A refunded sale returns the full price and the fee is not returned
    (as in payments.py), so: (1 - refund_rate) x price - fee."""
    return round((1 - refund_rate) * price - payments.fee_for(price), 2)


def sales_needed(amount: float | None, net: float) -> int | None:
    if amount is None or net <= 0:
        return None
    return math.ceil(amount / net) if amount > 0 else 0


def economics(price: float, budget: float | None, hours_per_week: float | None, hourly_rate: float | None,
              target: int, refund_rate: float = REFUND_RATE) -> dict:
    fee = payments.fee_for(price)
    net = net_per_sale(price, refund_rate)
    monthly_time = (round(hours_per_week * WEEKS_PER_MONTH * hourly_rate, 2)
                    if hours_per_week is not None and hourly_rate is not None else None)
    budget_sales = sales_needed(budget, net)
    time_sales = sales_needed(monthly_time, net)
    flags = []
    if net <= 0:
        flags.append(f"After fees and refunds this price keeps nothing per sale (${net:.2f}). Raise the price or "
                     "repeat Phase 4.")
    if budget_sales is not None and budget_sales > target:
        flags.append(f"Covering the budget needs {budget_sales} sales, more than the demand test's target of {target} "
                     "sign-ups: even if every sign-up bought, the budget would not be covered.")
    if time_sales is not None and time_sales > target:
        flags.append(f"Paying for your time needs {time_sales} sales a month, more than the demand test's target of "
                     f"{target} sign-ups: even if every sign-up bought, one month of your time would not be paid for.")
    return {"price_usd": price, "fee_usd": fee, "refund_rate": refund_rate, "net_per_sale_usd": net,
            "budget_usd": budget, "sales_to_cover_budget": budget_sales,
            "hours_per_week": hours_per_week, "hourly_rate_usd": hourly_rate, "monthly_time_value_usd": monthly_time,
            "sales_per_month_for_time": time_sales, "demand_target": target, "flags": flags}


def _given(v, fmt: str) -> str:
    return fmt.format(v) if v is not None else "not given in the brief"


class Economist(Agent):
    role = "economist"

    def run_step(self, pricing: dict, demand_target: int) -> StepResult:
        e = economics(float(pricing["price_usd"]), self.brief.get("budget_usd"), self.brief.get("hours_per_week"),
                      self.brief.get("hourly_rate_usd"), int(demand_target))
        p = e["price_usd"]
        md = [f"# Phase 4, step 4: Unit economics at ${p:.2f}", "",
              "How many sales this price needs before it is worth it. Plain arithmetic, no model. "
              "It is not a forecast: it says how many sales would be needed, never how many will happen.", "",
              "## Per sale", "| | Amount |", "|---|---|",
              f"| Price (Phase 4) | ${p:.2f} |",
              f"| Payment fee, {payments.FEE_PERCENT * 100:.1f}% + ${payments.FEE_FIXED:.2f} (ASSUMPTION: same fee model "
              f"as the MOCKED provider) | -${e['fee_usd']:.2f} |",
              f"| Refunds: {int(REFUND_RATE * 100)} in 100 buyers ask for one (ASSUMPTION), the fee is not returned | "
              f"-${p * REFUND_RATE:.2f} on average |",
              f"| **Kept per sale, on average** | **${e['net_per_sale_usd']:.2f}** |", "",
              "## Sales needed", "| Goal | Input | Sales needed |", "|---|---|---|",
              f"| Cover your budget | {_given(e['budget_usd'], '${:g}')} | "
              f"{_given(e['sales_to_cover_budget'], '{} sales')} |"]
        if e["hourly_rate_usd"] is None:
            md.append("| Pay for your time | hourly rate not given in the brief (optional field `hourly_rate_usd`) | "
                      "not worked out |")
        else:
            md.append(f"| Pay for your time | {_given(e['hours_per_week'], '{:g} h/week')} x "
                      f"${e['hourly_rate_usd']:g}/h = {_given(e['monthly_time_value_usd'], '${:,.2f}')} a month | "
                      f"{_given(e['sales_per_month_for_time'], '{} sales a month')} |")
        md += ["", "## Compared with the demand test",
               f"- Demand test target (Phase 2, set before any data): **{e['demand_target']} sign-ups**."]
        md += [f"- **Warning:** {f}" for f in e["flags"]] or \
              ["- The sales needed above are within the sign-up target. That is not a forecast: sign-ups are not sales."]
        md += ["", "## What this does not do",
               "- No sales or income forecast, no projections, no 'you will sell' numbers.",
               "- The fee and the refund rate are assumptions until real orders exist; Phase 6 reports the real ones.",
               "- To change the price, choose Repeat at the Phase 4 gate: pricing recomputes it and this step reruns.",
               footer(DETERMINISTIC)]
        return self.result("unit-economics", "unit_economics", "\n".join(md), data=e)
