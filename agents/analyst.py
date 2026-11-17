"""Analyst: pre-registers the smoke test (Phase 2) and reads the numbers (Phase 6)."""


def validation_plan(brief):
    plan = {"visitors_target": 300, "signup_rate_go": 0.10, "signup_rate_stop": 0.03,
            "interviews": 5, "real_signups_collected": 0}
    md = f"""# Phase 2 Step 3: Validation plan (pre-registered)

Decided before any traffic arrives, so the result can't be argued afterwards.

| Item | Value |
|---|---|
| Visitors to send to the landing page | {plan['visitors_target']} |
| GO if waitlist sign-up rate is at least | {int(plan['signup_rate_go']*100)}% (ASSUMPTION: common smoke-test benchmark) |
| STOP if sign-up rate is below | {int(plan['signup_rate_stop']*100)}% (ASSUMPTION) |
| Problem interviews with target users | {plan['interviews']} |
| Real sign-ups collected so far | {plan['real_signups_collected']} (STUBBED: the system never simulates sign-ups) |

## Interview questions (Mom Test style: past behaviour, not opinions)
1. When did you last have to deal with {brief['problem']}? Walk me through it.
2. What did you use? What did it cost you in time or money?
3. What did you try that didn't work?
4. Who else on your team deals with this?
5. If you could change one thing about it, what would it be?
"""
    return plan, md


def metrics(recon, visitors=None):
    paid = recon["paid"]
    refunds = 1 if recon["refunded"] else 0
    return {"data_source": "MOCKED", "orders": recon["orders"], "paid": paid,
            "refund_rate": round(refunds / paid, 2) if paid else 0.0,
            "conversion": None if visitors is None else round(paid / visitors, 3),
            "gross": recon["gross"], "fees": recon["fees"], "payout": recon["payout"]}
