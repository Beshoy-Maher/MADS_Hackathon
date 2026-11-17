# Research basis

Venture Builder's main design choices follow published findings on multi-agent LLM systems, LLM judges and startup evaluation. The table maps each choice to the paper it follows and the file that implements it. We did not reproduce these papers' experiments; the numbers below are the papers' own.

| Design choice | Finding it follows | Where it is built |
|---|---|---|
| One agent per role, each producing a named document that the next step reads | MetaGPT: agents that follow standard procedures and exchange structured documents make fewer errors than free chat ([arXiv 2308.00352](https://arxiv.org/abs/2308.00352)) | [`agents/`](../agents), [`orchestrator.py`](../orchestrator.py), `outputs/phase<N>_step<M>_*` |
| A reviewer role checks the builder's work before the build gate | ChatDev: a chain of roles with a dedicated reviewer and tester ([arXiv 2307.07924](https://arxiv.org/abs/2307.07924)) | [`agents/qa.py`](../agents/qa.py) (12 deterministic tests), [`agents/critic.py`](../agents/critic.py) |
| A critic debates each phase's outputs with their authors before the gate | Multi-agent debate reduces factual errors compared with a single model answering alone (Du et al., [arXiv 2305.14325](https://arxiv.org/abs/2305.14325)) | [`agents/critic.py`](../agents/critic.py), `outputs/phase*_debate.md` |
| Gates, scores, tests and prices are code, not a model's opinion; the debate informs the founder but never changes a gate's recommendation | LLM judges show position, length and self-preference biases (Zheng et al., [arXiv 2306.05685](https://arxiv.org/abs/2306.05685)); LLM code judges are swayed by comments and claims of correctness ([arXiv 2505.16222](https://arxiv.org/abs/2505.16222)) | [`gates.py`](../gates.py) (`THRESHOLDS`) |
| With `models-large.env`, the critic is a different model family from the writer | Self-preference bias: a model rates its own outputs higher (Zheng et al., above) | [`config.py`](../config.py) (`LLM_CRITIC_MODEL`), [`docs/models.md`](models.md) |
| The debate has a fixed shape (objections, answers, verdict) with at most 4 objections, and "repeat" is offered at most twice per phase | DIALECTIC, a multi-agent startup evaluator: quality fell after more than 2 refinement rounds, so it uses an explicit stop rule ([arXiv 2603.12274](https://arxiv.org/abs/2603.12274)) | [`agents/critic.py`](../agents/critic.py) (`MAX_OBJECTIONS`), [ARCHITECTURE.md](../ARCHITECTURE.md#gates) |
| Thresholds are fixed before the data arrives, and the system recommends STOP when public evidence is weak | SSFF: GPT-4o alone predicted success for most startups (21% precision on a 50-startup set), while quantitative signals did better ([arXiv 2405.19456](https://arxiv.org/abs/2405.19456)) | [`gates.py`](../gates.py), `outputs/phase1_gate_decision_weak-idea.md` |
| Customers are never simulated; the founder runs real interviews and only real sign-ups count at the demand gate | Synthetic Founders: LLM personas amplify "polite lies" and cannot replace real interviews ([arXiv 2509.02605](https://arxiv.org/abs/2509.02605)) | [`agents/interviewer.py`](../agents/interviewer.py), `gates.demand_gate` |
| A verification step before each gate (verifier, claim checker, QA tests) | Why Do Multi-Agent LLM Systems Fail? (MAST): about 21% of failures are weak verification, and adding a high-level verification step raised ChatDev's success by 15.6 points ([arXiv 2503.13657](https://arxiv.org/abs/2503.13657)) | [`tools/claims.py`](../tools/claims.py), [`agents/qa.py`](../agents/qa.py) |

## What we do not do yet

- **Open assumptions are not counted at the gate.** MAST finds that agents proceeding on unchecked assumptions cause about 12% of multi-agent failures. Our outputs label unsourced claims `ASSUMPTION`, but the gate decision files do not yet show how many remain unconfirmed.
- **Debate quality is not measured.** We report what each debate fixed, defended or left open, but we have no evaluation of whether the critic's objections were correct.
- **No pro and con teams.** DIALECTIC argues each idea from both sides and ranks the arguments; our critic argues only against.
- **No failure-mode tagging.** The decision log records every action, but it is not labelled with MAST's failure categories.
