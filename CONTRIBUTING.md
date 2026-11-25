# Contributing to Venture Builder

Thanks for helping. Venture Builder is MIT-licensed and runs on a free local model, so every contribution must keep working with `docker compose up` and no paid service.

## Set up

```bash
docker compose up -d --build          # app on http://localhost:8000, local model via Ollama
docker compose run --rm app pytest -q # tests need no model and no network
```

Without Docker: Python 3.12, `pip install -r requirements.txt`, then `pytest -q`. Settings are listed in `.env.example`; real keys go in an untracked `.env`.

## Rules every change keeps

- **Models only write text. Decisions are code.** Scores, gates, QA tests, prices, payments and approvals stay deterministic. Do not let a model decide a gate.
- **Nothing goes out without the founder.** Anything that would publish, send, spend, sign or refund goes through `approval.request_action` and stays STUBBED or MOCKED.
- **Gate thresholds are fixed before data is seen.** Change `gates.THRESHOLDS` only in its own pull request, with the reason, never to make a run pass.
- **Every market claim has a source URL or the label `ASSUMPTION`.** Agent text passes the claim checker (`tools/claims.py`) automatically; do not bypass it.
- **The system never** promises income, writes reviews or testimonials, invents sign-ups or numbers, creates urgency, poses as anyone, moves money, creates accounts or stores passwords or card numbers.
- **`outputs/` and `decision_log.json` come from running `scripts/run_demo.py`.** Never edit them by hand.

## Add an agent

1. Create `agents/<role>.py` with a class that extends `agents.base.Agent`, sets `role = "<role>"`, and returns `self.result(...)` from its step. The base class logs the action, scans the text with the guardrails and runs the claim checker.
2. Create `prompts/<role>.md` with the agent's instructions.
3. Call it from the right phase in `orchestrator.py`, and add a `_progress(...)` line so the dashboard shows it working.
4. Add a smoke test in `tests/` that runs with `LLM_PROVIDER=none`.

## Add an evidence source

1. Write a function in `tools/sources.py` that takes a query and returns a list of `Evidence` items, each with its URL.
2. Register it in `SOURCES`. A source that fails is reported under "Source coverage" and the run carries on with the others.
3. Add a test that mocks the HTTP call (tests never use the network).

## Add a guardrail test

- A trick prompt that got through: add it to `evals/trick_prompts.json` with its expected category, add the rule to `guardrails.py`, and run `python scripts/run_evals.py`.
- A normal request that was refused: add it to `requests_allowed` in the same file and fix the rule.
- **Never copy a prompt from `evals/heldout_prompts.json` into the rules or the judge prompts.** That set measures prompts the guardrails have not seen; `tests/test_guardrails.py` fails if one leaks. Measure it with `python scripts/run_evals.py --deep` and a running model, and commit `evals/results.md` whatever the result.

## Before opening a pull request

- `pytest -q` passes.
- `python scripts/check_submission.py` passes.
- If you changed an agent, prompt, gate or guardrail: rerun `scripts/run_demo.py` with a real model and commit the regenerated `outputs/` and `decision_log.json`.
- Every mocked or stubbed part you add is labelled `MOCKED` or `STUBBED` in the README table and in the app.
