# Architecture

## Overview

Venture Gates is one orchestrator (`orchestrator.py`), eleven small agents (`agents/`), six deterministic gates (`gates.py`), an approval lock (`approval.py`), guardrails (`guardrails.py`) and a MOCKED sale-to-cash stack (`payments.py`, `webhooks.py`, `delivery.py`, `refunds.py`, `reconcile.py`). The design rule is **the model writes, code decides**: a small open-weight model (`qwen3:4b` via Ollama) only drafts prose, and every number, gate, price and payment step is plain code. If the model is missing, the same pipeline runs with deterministic text labelled `TEMPLATE`. The app uses only the Python standard library.

```
 Founder brief (JSON) ──> guardrails.screen_brief ──refused──> phase1_gate_scope.md (STOP)
        │
        ▼
 orchestrator.start ── logs SHA-256 of gates.THRESHOLDS (pre-registration) ──┐
        │                                                                   │
        ▼                                                                   │
 ┌── Phase N agents ──> outputs/phaseN_stepM_*.md  + decision_log.json      │
 │        │                                                                 │
 │        ▼                                                                 │
 │   gates.<gate>(numbers) ──> recommendation + checks ─ hash still equal? ◄┘
 │        │
 │        ▼
 │   status = awaiting_founder   (nothing moves until the founder decides)
 │        │
 │   founder: go ──> Phase N+1 │ repeat ──> Phase N again │ pivot / stop ──> run ends
 └────────┘           (override of the recommendation needs a written reason)

 Outbound (publish / post / refund) ──> approval.request ──> founder approve/reject
                                          └─ approve ──> STUBBED outbox (or MOCKED refund)
```

## Phases

### Phase 1: Discover
- **Agents:** `researcher`, `scorer`, `red_team`.
- **Tools:** `tools/evidence.py`: GitHub repository search (competitors), GitHub issue search with the keyword in the title (pain voices), Hacker News Algolia search (pain voices). Free and keyless.
- **Method:** search each founder keyword (on REPEAT, also the broader keywords). Keep each item's URL, age and engagement. The scorer computes, with fixed formulas: `demand = 6 x recent voices + 2 x older voices + min(20, engagement/10)`, `fit = 40 if the founder is a target user + 10 per matching skill (max 30) + 3 x hours/week (max 30)`, `competition_level = 20 x log10(top stars + 1)`. Voices count only if they contain a keyword; "recent" means under 3 years old. The red team asks fixed kill questions: a free open-source tool with 20,000+ stars, all pain older than 3 years, under 3 founder hours a week (critical), plus non-blocking concerns.
- **Output:** `phase1_step1_opportunities.md`, `phase1_step2_scorecard.md`, `phase1_step3_red-team.md`, `phase1_gate_evidence.md`.

### Phase 2: Validate
- **Agents:** `strategist`, `copywriter`, `analyst`.
- **Method:** the strategist picks the 3 most-engaged recent pain voices and writes the value proposition and a short lean canvas. The copywriter builds a landing page in which every pain bullet links its source. The analyst pre-registers the smoke test: 300 visitors, GO at 10% or more sign-ups, STOP below 3% (benchmarks labelled `ASSUMPTION`), and 5 Mom Test interviews. Real sign-ups are never simulated.
- **Output:** `phase2_step1_value-proposition.md`, `phase2_step2_landing-page.html`, `phase2_step3_validation-plan.md`, `phase2_gate_validate.md`. Publishing the page is queued for founder approval.

### Phase 3: Build
- **Agents:** `builder`, `qa`.
- **Method:** the spec has one module per evidenced pain plus a quick start. Each module needs a checklist (5 or more items), a template and the link to its pain. The builder writes the product as a Markdown toolkit (the model adds tips when available). QA checks every spec item, every source link against the evidence ledger, and the guardrails.
- **Output:** `phase3_step1_spec.md`, `phase3_step2_product.md`, `phase3_step3_qa-report.md`, `phase3_gate_build.md`.

### Phase 4: Commercial setup
- **Agents:** `pricer`, `policy_writer`.
- **Method:** price = $9 + $4 per evidenced module, minus $4 if a popular free alternative exists (1,000+ stars), clamped to $5-$49 (rule labelled `ASSUMPTION`). Terms, a 14-day refund policy and a privacy note (no card numbers or passwords stored) are drafted for founder review.
- **Output:** `phase4_step1_pricing.md`, `phase4_step2_policies.md`, `phase4_gate_commercial.md`.

### Phase 5: Sell, deliver, get paid
- **Agents:** `copywriter`, `launcher` (the sale-to-cash test in `orchestrator.phase5`).
- **Method:** store page and launch post drafts go to the approval queue. The sale-to-cash test runs against the MOCKED provider (see Sale to cash), and the test refund waits for the founder.
- **Output:** `phase5_step1_store-page.html`, `phase5_step2_launch-post.md`, `phase5_step3_sale-to-cash.md`, `payment_test_log.md`, `phase5_gate_sell.md`.

### Phase 6: Operate and learn
- **Agents:** `analyst`, `support`.
- **Method:** metrics (orders, refund rate, conversion, gross, fees, payout) from the reconciled ledger, marked `MOCKED`. A support FAQ comes from the policies and the product. The persevere-or-pivot rule is pre-registered in `gates.THRESHOLDS["operate"]`.
- **Output:** `phase6_step1_metrics.md`, `phase6_step2_support.md`, `phase6_gate_operate.md`.

## Gates

All thresholds live in `gates.THRESHOLDS`. Their SHA-256 is logged when a run starts, before research, and each gate report says whether the code still matches it.

| Gate | Checks | GO | REPEAT | PIVOT | STOP |
|---|---|---|---|---|---|
| 1 Evidence | sources >= 10, recent voices >= 5, demand >= 40, fit >= 50, critical risks = 0 | all pass | some signal; or every source failed (network) | demand exists but a critical risk or low fit | **recent voices < 3 or demand < 25**, or still short after 2 repeats |
| 2 Validate | 100% of landing-page claims link a fetched source; 0 rule violations; smoke-test target >= 200 visitors | all pass | otherwise | n/a | founder |
| 3 Build | 100% of QA checks pass | all pass | otherwise | n/a | founder |
| 4 Commercial | price $5-$49; refund window >= 14 days; no card storage; payment mode `mock` | all pass | otherwise | n/a | founder |
| 5 Sell | all sale-to-cash checks pass; 0 outbound items still pending | all pass | otherwise | n/a | founder |
| 6 Operate | real customer data; refund rate <= 20%; conversion >= 2% | all pass on real data | **any MOCKED data**, or below target | refund rate > 20% | founder |

**When it recommends STOP:** at the evidence gate, when fewer than 3 recent people describe the pain or demand is under 25, the gate says "do not build this". It also stops after 2 repeats that still fall short, rather than searching until it finds a yes. In the demo, the weak idea (a pet-mood colour palette app) found 0 voices and got STOP (`outputs/phase1_gate_evidence_weak-idea.md`).

**Founder control:** `orchestrator.decide` accepts only `actor="founder"`, only while the run is `awaiting_founder`, and refuses a decision that differs from the recommendation unless there is a written reason. The decision, the recommendation, the override flag and the reason all go into `decision_log.json`.

## Sale to cash

```
checkout (MOCKED, hosted) ──pay──> signed event payment.succeeded ──> webhooks.handle
   verify HMAC signature ──bad──> rejected
   event id seen before? ──yes──> duplicate_ignored        (idempotency)
   delivery.grant(order) ──> one access token per order     (second grant returns the first)
refund: refunds.request_refund ──> approval queue ──founder approves──> provider.refund
   signed event payment.refunded ──> webhooks.handle ──> delivery.revoke (download stops working)
reconcile: orders = payments = deliveries; payout = gross - fees - refunds
```

- **Payment triggers delivery:** `webhooks.WebhookHandler.handle` grants access only on a verified `payment.succeeded` event.
- **A refund revokes access:** `payment.refunded` calls `delivery.revoke`. The refund itself runs only after the founder approves it (`refunds.execute_refund` raises `ApprovalRequired` otherwise).
- **Idempotency:** event ids are stored, and `delivery.grant` is keyed by order id, so a retried webhook never delivers twice.
- **Reconciliation:** `reconcile.reconcile` matches orders, payments, deliveries, fees (2.9% + $0.30, `ASSUMPTION`), refunds and payouts, and lists every mismatch. The demo run passed 8/8 checks (`outputs/payment_test_log.md`).

## Data flow

1. The brief (JSON) is screened by `guardrails.screen_brief`. A refused brief stops here and no agent runs.
2. `orchestrator.start` creates `data/runs/<id>/run.json` and logs the threshold hash.
3. Each agent reads from `run["state"]` (evidence ledger, score, pains, modules, price) and writes a file to `data/runs/<id>/outputs/`, plus one entry in the decision log (`agent`, `action`, `sources`, `model`, `cost`, `approved_by`).
4. Every text an agent writes goes through `guardrails.clean`, which removes fake social proof, urgency, income promises and impersonation.
5. Outbound items live in `run["outbound"]`. An approved publish or send is written to `data/runs/<id>/outbox.jsonl` (STUBBED).
6. `scripts/run_demo.py` runs three briefs end to end and copies their files into `outputs/` and the log into `decision_log.json`.

## Built vs. stubbed

| Part | Status |
|---|---|
| Orchestrator, gates, pre-registration hash, founder decisions with override reasons | Built |
| Evidence search (GitHub repos and issues, Hacker News) | Built |
| Agents (11) with model drafting and `TEMPLATE` fallback | Built |
| Guardrails: brief screening and output cleaning, 33 eval prompts | Built |
| Approval lock for publish, send and refund | Built |
| Publishing pages, posting, sending email | **STUBBED** (local outbox file) |
| Waitlist form and real sign-up collection | **STUBBED** |
| Payment provider and checkout | **MOCKED** |
| Delivery, idempotent webhooks, refunds, reconciliation | Built (against the MOCKED provider) |
| Phase 6 metrics | Built, on **MOCKED** data |
| Dashboard (`app.py`, `static/index.html`) and CLI (`cli.py`) | Built |

## Roadmap

1. A Stripe test-mode adapter behind the same `payments.py` interface (keys only in `.env`).
2. A real waitlist endpoint with consent, feeding sign-up counts into the Phase 2 gate.
3. More evidence sources (Reddit, Stack Exchange) with the same "failed means listed, never guessed" rule.
4. Interview-notes analysis that turns founder notes into evidence items.
5. Arabic output templates.
