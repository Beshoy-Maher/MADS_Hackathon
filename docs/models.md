# Models

Every model is open-weight (Apache-2.0) and runs locally through Ollama. Each kind of work has its own setting.

| Role | Default (`docker compose up`) | `models-large.env` | Used for |
|---|---|---|---|
| Writer | `qwen3:4b-instruct-2507-q4_K_M` | `qwen3:30b-a3b-instruct-2507-q4_K_M` (Qwen3-30B-A3B-Instruct-2507, MoE, 3.3B active, 18 GB) | research, analysis, product, every text the founder reads, the authors' side of the debate |
| Fast | `qwen3:4b-instruct-2507-q4_K_M` | same | intake (brief to fields) |
| Judge | `qwen3:4b-instruct-2507-q4_K_M` | same | the two safety judges, temperature 0 |
| Critic | `qwen3:4b-instruct-2507-q4_K_M` | `gpt-oss:20b` (OpenAI gpt-oss-20b, 14 GB) | devil's advocate in the debate before each gate |

All are Apache-2.0. With `models-large.env` the critic is a different model family from the writer, so it does not share the writer's blind spots. A model that is missing or cannot be loaded (for example, not enough memory) hands over to the next one in `LLM_FALLBACK_MODELS`, and the decision log records the model that really answered. Each role's model can also be set on its own in `.env` (`LLM_MODEL`, `LLM_FAST_MODEL`, `LLM_JUDGE_MODEL`, `LLM_CRITIC_MODEL`).

Run the larger set with `docker compose --env-file models-large.env up` (32+ GB RAM, about 34 GB download), and add `-f docker-compose.yml -f docker-compose.gpu.yml` on a machine with an NVIDIA GPU and the NVIDIA Container Toolkit. `gpt-oss:20b` reasons before it answers; it runs at medium reasoning effort, and an answer left empty by long reasoning is asked once more with a larger budget.

## Cost per run

`decision_log.json` counts agent actions, not calls, so it has 70 entries with a model: the product is one entry for several calls, while each debate transcript (10) and each applied debate correction (8) is an entry that names its model without a new call.
