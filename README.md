# Venture Builder by The Overfitters

An open-source team of AI agents that takes a founder's brief toward a validated, sellable **digital** product, through six gated phases: Discover, Validate, Build, Commercial setup, Launch, Operate and learn. It runs on a free local open-weight model, cites a public source for every market claim (or labels it `ASSUMPTION`), and says **"don't launch this"** when the evidence is weak. The founder approves every gate, and nothing is published, sent, spent or refunded without a click. That rule is enforced in code. Before every gate a **critic agent on a different model family debates the phase's outputs with the agents that wrote them**, and the founder sees what was conceded and what is still open.

Measured, not claimed: more than 380 tests that run with no model or network; guardrails refuse 37 of 40 trick prompts they were never tuned on (rules alone: 2 of 40) and wrongly refuse 0 of 62 normal requests ([`evals/results.md`](evals/results.md)); Phase 1 takes about 70 seconds on a 4-core laptop CPU; $0.00 per run.

The committed demo run, produced by `scripts/run_demo.py` with the local model, shows the three outcomes that matter:

- **Promising idea, GO:** an SQL interview workbook passes the evidence gate on 24 relevant sources, 23 independent voices and 5 pain posts ([gate](outputs/phase1_gate_decision.md)), then runs through all six phases to a [MOCKED sale-to-cash test](outputs/payment_test_log.md). The demand gate recommended repeat because no real visitor has seen the page; the demo founder overrode it to show the later phases, and the override is recorded ([gate](outputs/phase2_gate_decision.md)).
- **Weak idea, STOP:** a paid daily-quotes email for developers fails on founder fit and total score, and no alternative passes, so the system says "do not launch this" ([gate](outputs/phase1_gate_decision_weak-idea.md)).
- **Excluded idea, refused:** a crypto-signals channel is refused before any agent runs ([gate](outputs/phase1_gate_decision_excluded-idea.md)).

## Quickstart

```bash
docker compose up
```

Then open **http://localhost:8000**. Pick a sample founder (or paste any brief) and click **Run Phase 1**. After each phase, read the gate's recommendation and click **Go / Repeat / Pivot / Stop**. Launch items wait in the **Approval queue** for Approve / Reject.

- The first start downloads the models once, smallest first: `qwen3:4b-instruct-2507-q4_K_M` (2.5 GB, the app is fully usable as soon as it is there), then the writer `qwen3:30b-a3b-instruct-2507-q4_K_M` (18 GB) and the critic `gpt-oss:20b` (14 GB). Until a model is there its steps use the 4B model, and the dashboard and decision log say which model did what. Before any model is ready the agents use a labelled deterministic fallback.
- Small laptop (under 32 GB RAM): use the 4B model for every role, for example with a `.env` holding `LLM_MODEL`, `LLM_CRITIC_MODEL` set to `qwen3:4b-instruct-2507-q4_K_M` (see `.env.example`).
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
| 3 Gate | Automated MVP tests (11 checks, one of them: the verifier left no error open); gate needs all to pass | **Working** |
| 4 Commercial | Price from sourced comparables (rule-based), draft terms / privacy / refund policy | **Working** |
| 5 Launch | Store page and launch posts (drafts in the founder's voice) | **Working** |
| 5 Launch | Publishing store page and posts | **STUBBED** (approval-gated, saved to outbox) |
| 5 Launch | Checkout and payment provider | **MOCKED** (no real payments of any kind) |
| 5 Launch | Automatic delivery, idempotent webhooks, refunds revoke access, reconciliation | **Working** (against the MOCKED provider) |
| 5 Launch | Delivery emails | **STUBBED** (recorded, not sent) |
| 6 Operate | Support kit, metrics (real vs. MOCKED kept apart), persevere-or-pivot memo | **Working** |
| All | Guardrails (requests, briefs, every output), secret redaction, decision log, founder approval | **Working** |
| All | Scope check: an idea close to an excluded category (money, health, legal) waits for the founder's confirmation | **Working** |
| All | Debate before each gate: a critic (devil's advocate, different model family) challenges the phase's outputs, the authors concede with a correction or defend with a fetched source; shown to the founder, never changes the gate | **Working** |
| All | Claim check on every agent's text: unsourced statistics labelled `ASSUMPTION`, links not in fetched evidence removed | **Working** |

## Architecture

An **orchestrator** (`orchestrator.py`) runs the six phases in order. Each phase is a few role-named agents (`agents/<role>.py`, prompts in `prompts/`) that call a local model through `llm.py` and public evidence sources through `tools/sources.py`. After every phase a **gate** (`gates.py`) compares the results with thresholds fixed in code before the data arrives and recommends go, repeat, pivot or stop; the run then pauses until the founder decides. Anything outbound goes through `approval.py`, which refuses to execute without the founder's approval. Before the gate, a **critic** (`agents/critic.py`) on a different model family debates the phase's main outputs with the agents that wrote them; code keeps only objections that quote the document and keeps unsourced defences open, and the result is shown to the founder without changing the recommendation. `guardrails.py` screens briefs, requests and every generated text, and every agent action is appended to `decision_log.json`. Full design: [ARCHITECTURE.md](ARCHITECTURE.md).

## Models and free resources

- **Models:** open-weight models served locally by **Ollama**, downloaded automatically by `docker compose up`. One model per kind of work:

  | Role | Model | Licence | Download | Used for |
  |---|---|---|---|---|
  | Writer | `qwen3:30b-a3b-instruct-2507-q4_K_M` (Qwen3-30B-A3B-Instruct-2507, MoE, 3.3B active) | Apache-2.0 | 18 GB | research, analysis, product, every text the founder reads, the authors' side of the debate |
  | Fast | `qwen3:4b-instruct-2507-q4_K_M` (Qwen3-4B-Instruct-2507) | Apache-2.0 | 2.5 GB | intake (brief to fields) |
  | Judge | `qwen3:4b-instruct-2507-q4_K_M` | Apache-2.0 | (same) | the two safety judges, temperature 0 |
  | Critic | `gpt-oss:20b` (OpenAI gpt-oss-20b) | Apache-2.0 | 14 GB | devil's advocate in the debate before each gate |

  The critic is deliberately a different model family from the writer, so it does not share the writer's blind spots. A model that is missing or cannot be loaded (for example, not enough memory) hands over to the next one in `LLM_FALLBACK_MODELS` (`qwen3:4b-instruct-2507-q4_K_M`, `qwen3:4b-instruct`, `qwen3:4b`, `qwen3:1.7b`), and the decision log records the model that really answered. Every model is set in `.env` (`LLM_MODEL`, `LLM_FAST_MODEL`, `LLM_JUDGE_MODEL`, `LLM_CRITIC_MODEL`). The committed demo run in `outputs/` and `decision_log.json` was produced with `qwen3:4b-instruct-2507-q4_K_M` for every role, before the debate step was added.
- **Hardware:** everything runs on a CPU. With an NVIDIA GPU, add `docker-compose.gpu.yml`; the models use GPU memory first, then system RAM.
- **No paid service is required.** Optionally, point `LLM_PROVIDER=openai_compatible` and `LLM_BASE_URL` at any free-tier OpenAI-compatible endpoint serving an open-weight model.
- **Without any model** (`LLM_PROVIDER=none`), every agent falls back to deterministic templates; such steps are logged with `"model": null` and labelled in the outputs.
- **Evidence sources:** free public APIs with no keys: Hacker News (Algolia), Reddit public JSON, GitHub search, Stack Exchange. An optional free `GITHUB_TOKEN` in `.env` raises GitHub's search rate limit. Each run reports per source what worked under "Source coverage": in the committed demo run Reddit refused the requests (HTTP 403) from our network, so its evidence comes from the other three.
- **Decisions don't depend on the model:** scores, gates, QA tests, pricing and payments are deterministic code.

## Cost per run

**About $0.00 per run** (local model, ~23k tokens for all three demo founders in our demo run: 28 model calls, including the verifier's reviews and one module revision; research APIs are free). The dashboard header shows the running cost, and every decision-log entry records `"cost": 0`.

## Demo video

Demo video (3 minutes): link coming soon.

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

These limits are code (`guardrails.py`, `approval.py`, `gates.py`). The rule layer is tested by `tests/` on 255 cases in `evals/trick_prompts.json`; prompts the rules have never seen are in `evals/heldout_prompts.json` and are measured together with the model's second opinion by `python scripts/run_evals.py --deep` (results: `evals/results.md`).

## How the project stays alive after the hackathon

- **Maintainers:** The Overfitters team maintains the repository; contributions are reviewed through pull requests.
- **Roadmap:** real payment-provider adapter in test mode, hosted landing pages with founder approval, more evidence sources, and Arabic-first outputs. See the roadmap in [ARCHITECTURE.md](ARCHITECTURE.md#roadmap).
- **Community:** MIT-licensed; new agents, evidence sources and guardrail tests are easy to add (one file each), as described in [CONTRIBUTING.md](CONTRIBUTING.md). Trick prompts from users become new tests, and held-out prompts are kept apart from the rules by a test.
- **Funding:** the software stays free and fully featured. Possible support: university and incubator partnerships, open-source grants, and optional paid hosting or setup help for founders who don't want to self-host. Core features are never paywalled.
