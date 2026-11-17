# Venture Builder by The Overfitters

An open-source team of AI agents that takes a founder's brief toward a validated, sellable **digital** product through six gated phases: Discover, Validate, Build, Commercial setup, Launch, Operate and learn. Models only write text; every decision is code (scores, gates, build tests, prices, approvals). Every market claim cites a fetched source or is labelled `ASSUMPTION`, the system says **"don't launch this"** when the evidence is weak, and nothing is published, sent, spent or refunded without the founder's click, enforced in [`approval.py`](approval.py). Before each gate a critic agent challenges the phase's documents: mistakes the authors concede are corrected in the documents, and what stays open is shown to the founder.

Measured, not claimed: more than 440 tests that run with no model or network; guardrails refuse 37 of 40 trick prompts they were never tuned on (rules alone: 2 of 40) and wrongly refuse 0 of 62 normal requests ([`evals/results.md`](evals/results.md)); Phase 1, including its debate, took 33 seconds on an NVIDIA RTX 4080 in the committed demo run; $0.00 per run.

The committed demo run (`scripts/run_demo.py`, local open-weight models, see [Models and free resources](#models-and-free-resources)) shows the three outcomes that matter:

- **Promising idea, GO:** an SQL interview workbook passes the evidence gate on 25 relevant sources, 25 independent voices and 7 pain posts ([gate](outputs/phase1_gate_decision.md)), passes 12 of 12 build tests ([report](outputs/phase3_step4_qa-report.md)) and reaches a [MOCKED sale-to-cash test](outputs/payment_test_log.md). The demand gate recommended repeat because no real visitor has seen the page; the demo founder overrode it to show the later phases, and the override is recorded ([gate](outputs/phase2_gate_decision.md)).
- **Weak idea, STOP:** a paid daily-quotes email for developers fails on founder fit and total score, and no alternative passes, so the system says "do not launch this" ([gate](outputs/phase1_gate_decision_weak-idea.md)).
- **Excluded idea, refused:** a crypto-signals channel is refused before any agent runs ([gate](outputs/phase1_gate_decision_excluded-idea.md)).

Where each claim can be checked:

| Claim | Evidence |
|---|---|
| The system recommends STOP on weak evidence | [`outputs/phase1_gate_decision_weak-idea.md`](outputs/phase1_gate_decision_weak-idea.md), thresholds in [`gates.py`](gates.py) (`THRESHOLDS`) |
| Nothing is published, sent, spent or refunded without the founder | [`approval.py`](approval.py) (`request_action`, `execute_action`), [`tests/test_approval.py`](tests/test_approval.py) |
| Guardrail results, including the prompts that get through | [`evals/results.md`](evals/results.md), cases in [`evals/`](evals/) |
| Every market claim has a source or the label `ASSUMPTION` | [`outputs/phase1_step1_opportunities.md`](outputs/phase1_step1_opportunities.md), [`outputs/phase1_step3_market.md`](outputs/phase1_step3_market.md), checker in [`tools/claims.py`](tools/claims.py) |
| The product passes 12 deterministic build tests, originality included | [`outputs/phase3_step4_qa-report.md`](outputs/phase3_step4_qa-report.md), tests in [`agents/qa.py`](agents/qa.py), [`tools/originality.py`](tools/originality.py) |
| Every promise on the store page and in the posts is matched to the product: 10 checked, 8 kept, 0 broken, 2 for the founder to confirm | [`outputs/phase5_step4_promise-check.md`](outputs/phase5_step4_promise-check.md), [`agents/promise_checker.py`](agents/promise_checker.py) |
| Before the six gates the critic raised 9 objections: 7 corrected in the documents, 1 conceded but not applied (its quote appears twice), 1 open. Example: the Phase 6 memo claimed sign-ups and clicks that did not exist, and was corrected | [`outputs/phase6_step4_debate.md`](outputs/phase6_step4_debate.md), [`agents/critic.py`](agents/critic.py), [`tests/test_debate.py`](tests/test_debate.py) |
| Payment triggers delivery, refunds revoke access, books reconcile (MOCKED provider) | [`outputs/payment_test_log.md`](outputs/payment_test_log.md), [`tests/test_payments.py`](tests/test_payments.py) |
| Every agent action is logged with sources, model, cost and approver | [`decision_log.json`](decision_log.json) |

## Quickstart

```bash
docker compose up
```

Then open **http://localhost:8000**. Pick a sample founder (or paste any brief) and click **Run Phase 1**. After each phase, read the gate's recommendation and click **Go / Repeat / Pivot / Stop**. Launch items wait in the **Approval queue** for Approve / Reject.

- The first start downloads the model (`qwen3:4b-instruct-2507-q4_K_M`, about 2.5 GB) once. Until it is ready the dashboard says so and the agents use a labelled deterministic fallback, so the app works right away.
- Larger models (32+ GB RAM or a GPU, about 34 GB download): `docker compose --env-file models-large.env up` runs a 30B writer and a different-family critic (see [Models and free resources](#models-and-free-resources)).
- On a slow laptop, use a smaller model: `LLM_MODEL=qwen3:1.7b docker compose up`.
- NVIDIA GPU (optional, needs the NVIDIA Container Toolkit): `docker compose -f docker-compose.yml -f docker-compose.gpu.yml up`.
- Command line instead of the dashboard: `docker compose run --rm app python cli.py run briefs/strong_founder.json`.
- Regenerate `outputs/` and `decision_log.json`: `docker compose run --rm app python scripts/run_demo.py`.
- Tests: `docker compose run --rm app pytest -q`.

## What works and what is mocked

| Phase | Step | Status |
|---|---|---|
| 1 Discover | Find opportunities: sharpen idea, alternatives, public evidence (Hacker News, Reddit, GitHub, Stack Exchange) | **Working** |
| 1 Discover | Score idea vs. alternatives (fixed formulas + model skill-fit) | **Working** |
| 1 Discover | Define the market (ICP, current solutions, sourced or `ASSUMPTION`) | **Working** |
| 1 Discover | Mom Test interview guide and outreach draft | **Working** |
| 1 Discover | Sending outreach / running interviews | **STUBBED** (founder sends; answers are never simulated) |
| 1 Discover | Interview notes pasted by the founder: commitments vs. compliments, quoting only the notes | **Working** |
| 1 Gate | Evidence gate with pre-set thresholds, recommends STOP on weak evidence | **Working** |
| 2 Validate | Lean Canvas | **Working** |
| 2 Validate | Landing page with consent-based waitlist form | **Working** |
| 2 Validate | Publishing the landing page to a public URL | **STUBBED** (approval-gated, saved to outbox) |
| 2 Gate | Demand gate (pre-registered sign-up target, counts only real sign-ups) | **Working** |
| 3 Build | MVP spec, product content, user guide; verifier reviews each module (facts, SQL run in SQLite), one revision | **Working** |
| 3 Build | Originality guard: no passage copied from the sources read, no name taken from an existing product (code, compares fetched snippets) | **Working** |
| 3 Gate | Automated MVP tests (12 checks, among them: the verifier left no error open, the product is original); gate needs all to pass | **Working** |
| 4 Commercial | Price from sourced comparables (rule-based), draft terms / privacy / refund policy | **Working** |
| 5 Launch | Store page and launch posts (drafts in the founder's voice) | **Working** |
| 5 Launch | Promise checker: every promise on the store page and in the posts matched to the product, price, refund policy and delivery test; a broken promise cannot be approved | **Working** |
| 5 Launch | Publishing store page and posts | **STUBBED** (approval-gated, saved to outbox) |
| 5 Launch | Checkout and payment provider | **MOCKED** (no real payments of any kind) |
| 5 Launch | Automatic delivery, idempotent webhooks, refunds revoke access, reconciliation | **Working** (against the MOCKED provider) |
| 5 Launch | Delivery emails | **STUBBED** (recorded, not sent) |
| 6 Operate | Support kit, metrics (real vs. MOCKED kept apart), persevere-or-pivot memo | **Working** |
| All | Guardrails (requests, briefs, every output), secret redaction, decision log, founder approval | **Working** |
| All | Scope check: an idea close to an excluded category (money, health, legal) waits for the founder's confirmation | **Working** |
| All | Debate before each gate: a critic (devil's advocate) challenges the phase's outputs, the authors concede with a correction or defend with a fetched source; shown to the founder, never changes the gate | **Working** |
| All | Claim check on every agent's text: unsourced statistics labelled `ASSUMPTION`, links not in fetched evidence removed | **Working** |

## Architecture

An **orchestrator** ([`orchestrator.py`](orchestrator.py)) runs the six phases in order; each phase is a few role-named agents (`agents/<role>.py`, prompts in `prompts/`) that call local models through `llm.py` and free public evidence APIs through `tools/sources.py`. After every phase a **gate** ([`gates.py`](gates.py)) compares the results with thresholds fixed in code before the data arrives, recommends go, repeat, pivot or stop, and the run pauses until the founder decides. Before the gate, a **critic** ([`agents/critic.py`](agents/critic.py)) debates the phase's main documents with their authors; code keeps only objections that quote the document, and writes a conceded correction into it only when the quote is found once and the guardrails and claim checker accept the new text. Anything outbound goes through [`approval.py`](approval.py), which refuses to execute without the founder's approval, and [`guardrails.py`](guardrails.py) screens briefs, requests and every generated text. Every agent action is appended to [`decision_log.json`](decision_log.json). Full design, diagrams and the sale-to-cash flow: [ARCHITECTURE.md](ARCHITECTURE.md).

## Models and free resources

- **Default model:** `qwen3:4b-instruct-2507-q4_K_M` (Qwen3-4B-Instruct-2507, Apache-2.0, open weights) for every role, served locally by **Ollama** and downloaded automatically by `docker compose up` (2.5 GB). If that tag is unavailable the downloader falls back to `qwen3:4b-instruct`, `qwen3:4b`, then `qwen3:1.7b`.
- **Committed demo run:** `qwen3:30b-a3b-instruct-2507-q4_K_M` for writing, `gpt-oss:20b` as the critic and `qwen3:4b-instruct-2507-q4_K_M` for intake and the safety judges, on an NVIDIA GPU (RTX 4080), via the optional [`models-large.env`](models-large.env). All Apache-2.0. Roles, fallbacks and settings: [docs/models.md](docs/models.md).
- **No paid service is required.** Optionally, point `LLM_PROVIDER=openai_compatible` and `LLM_BASE_URL` at any free-tier OpenAI-compatible endpoint serving an open-weight model.
- **Without any model** (`LLM_PROVIDER=none`), every agent falls back to deterministic templates; such steps are logged with `"model": null` and labelled in the outputs.
- **Evidence sources:** free public APIs with no keys: Hacker News (Algolia), Reddit public JSON, GitHub search, Stack Exchange. An optional free `GITHUB_TOKEN` in `.env` raises GitHub's search rate limit. Each run reports per source what worked under "Source coverage": in the committed demo run Reddit refused the requests (HTTP 403) from our network, so its evidence comes from the other three.
- **Decisions don't depend on the model:** scores, gates, build tests, pricing and payments are deterministic code.

## Cost per run

**About $0.00 per run** (local models; ~59k tokens and 40 model calls for all three demo founders in the committed run, including the verifier's reviews, the debate before each gate and the promise check; research APIs are free). `decision_log.json` counts agent actions, not calls, so it has 51 entries with a model: the builder's product is one entry for several calls, and each applied debate correction is an entry that names the model that wrote it without a new call. The dashboard header shows the running cost, and every decision-log entry records `"cost": 0`.

## Demo video

Demo video: https://drive.google.com/file/d/1_flIP4f2UaXU5lvi1eR81f5lqV7ubHwC/view?usp=sharing

## What our system will NOT do

- Promise income, earnings or success, in any text it writes.
- Write reviews, testimonials, ratings or customer quotes, or invent sign-ups, users or sales numbers.
- Use countdown timers, fake scarcity or pressure tactics.
- Pose as the founder, a customer or another brand. Drafts are for the founder to send as themselves.
- Publish, send, spend, sign or refund anything without the founder's explicit approval.
- Hold, move or refund money by itself, create accounts, or store passwords or card numbers.
- Build physical goods, financial / investment / crypto products, or health or legal advice products.
- Put core features behind a paywall.
- Let a model's opinion move a gate: the debate before each gate informs the founder; the recommendation comes from fixed thresholds in code.
- Spin weak evidence: a missed target is reported as missed, with a pivot or stop recommendation.
- Move a gate's threshold after seeing the data, or pretend a gate passed.

These limits are code (`guardrails.py`, `approval.py`, `gates.py`). The rule layer is tested by `tests/` on 255 cases in `evals/trick_prompts.json`; 40 prompts the rules have never seen are in `evals/heldout_prompts.json` and are measured together with the model's second opinion by `python scripts/run_evals.py --deep` ([`evals/results.md`](evals/results.md), including the 3 that get through).

## How the project stays alive after the hackathon

- **Maintainers:** The Overfitters team maintains the repository; contributions are reviewed through pull requests.
- **Roadmap:** real payment-provider adapter in test mode, hosted landing pages with founder approval, more evidence sources, and Arabic-first outputs. See the roadmap in [ARCHITECTURE.md](ARCHITECTURE.md#roadmap).
- **Community:** MIT-licensed; new agents, evidence sources and guardrail tests are easy to add (one file each), as described in [CONTRIBUTING.md](CONTRIBUTING.md). Trick prompts from users become new tests; a test keeps held-out prompts from being copied into the rules or the judge prompts.
- **Funding:** the software stays free and fully featured. Possible support: university and incubator partnerships, open-source grants, and optional paid hosting or setup help for founders who don't want to self-host. Core features are never paywalled.
