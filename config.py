"""Settings, read from environment variables (see .env.example).

Everything has a safe default so the app runs with zero configuration.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _env(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value if value not in (None, "") else default


# Local open-weight model served by Ollama (started by docker compose).
LLM_PROVIDER = _env("LLM_PROVIDER", "ollama")  # "ollama" | "openai_compatible" | "none"
LLM_BASE_URL = _env("LLM_BASE_URL", "http://localhost:11434")
# One model per kind of work. All are open-weight (Apache-2.0) and run locally through Ollama.
# Default: Qwen3-4B-Instruct-2507 for every role, so `docker compose up` runs on any laptop (2.5 GB download).
# Optional larger models for a machine with 32+ GB RAM or a GPU: see models-large.env.
# Writer: research, analysis and every text the founder reads.
LLM_MODEL = _env("LLM_MODEL", "qwen3:4b-instruct-2507-q4_K_M")
# Fast: intake (brief to fields).
LLM_FAST_MODEL = _env("LLM_FAST_MODEL", "qwen3:4b-instruct-2507-q4_K_M")
# Judge: the two safety judges (yes/no, temperature 0).
LLM_JUDGE_MODEL = _env("LLM_JUDGE_MODEL", "qwen3:4b-instruct-2507-q4_K_M")
# Critic: the devil's advocate in the debate before each gate (models-large.env: gpt-oss-20b, a different model family).
LLM_CRITIC_MODEL = _env("LLM_CRITIC_MODEL", "qwen3:4b-instruct-2507-q4_K_M")
# Tried in order when a role's model is not downloaded or cannot be loaded (for example not enough memory).
LLM_FALLBACK_MODELS = [m.strip() for m in _env("LLM_FALLBACK_MODELS",
                       "qwen3:4b-instruct-2507-q4_K_M,qwen3:4b-instruct,qwen3:4b,qwen3:1.7b").split(",") if m.strip()]
LLM_API_KEY = _env("LLM_API_KEY", "")  # only for a free-tier OpenAI-compatible endpoint
LLM_TIMEOUT_SECONDS = float(_env("LLM_TIMEOUT_SECONDS", "300"))
LLM_TEMPERATURE = float(_env("LLM_TEMPERATURE", "0.3"))
# Price per 1M tokens of the model in USD. 0 for a local model.
LLM_COST_PER_MTOK = float(_env("LLM_COST_PER_MTOK", "0"))

# Debate before each gate: a critic challenges the phase's outputs, the authors answer, the critic gives a verdict.
# It informs the founder; it never changes a gate's recommendation.
DEBATE = _env("DEBATE", "true").lower() == "true"

# Public evidence sources used by the researcher.
RESEARCH_ONLINE = _env("RESEARCH_ONLINE", "true").lower() == "true"
RESEARCH_SOURCES = [s.strip() for s in _env("RESEARCH_SOURCES", "hackernews,reddit,github,stackexchange").split(",") if s.strip()]
GITHUB_TOKEN = _env("GITHUB_TOKEN", "")  # optional, raises GitHub search rate limits
HTTP_TIMEOUT_SECONDS = float(_env("HTTP_TIMEOUT_SECONDS", "8"))
HTTP_USER_AGENT = _env("HTTP_USER_AGENT", "venture-builder-research/0.1 (open-source research agent)")

# Where runs, caches and the decision log live.
DATA_DIR = Path(_env("DATA_DIR", str(ROOT / "data")))
OUTPUTS_DIR = Path(_env("OUTPUTS_DIR", str(ROOT / "outputs")))
DECISION_LOG_PATH = Path(_env("DECISION_LOG_PATH", str(DATA_DIR / "decision_log.json")))
PROMPTS_DIR = ROOT / "prompts"

# Optional: when set, gate decisions and approvals need header X-Founder-Token (for shared/hosted deployments).
FOUNDER_TOKEN = _env("FOUNDER_TOKEN", "")

APP_HOST = _env("APP_HOST", "0.0.0.0")
APP_PORT = int(_env("APP_PORT", "8000"))
