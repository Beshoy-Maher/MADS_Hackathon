"""Settings, read once from environment variables. Every value has a safe default."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _env(name, default):
    return os.environ.get(name, default)


LLM_PROVIDER = _env("LLM_PROVIDER", "ollama")          # ollama | none
LLM_BASE_URL = _env("LLM_BASE_URL", "http://localhost:11434")
LLM_MODEL = _env("LLM_MODEL", "qwen3:4b")              # small open-weight model
LLM_TIMEOUT = float(_env("LLM_TIMEOUT_SECONDS", "120"))
LLM_COST_PER_MTOK = float(_env("LLM_COST_PER_MTOK", "0"))  # 0 for a local model

RESEARCH_ONLINE = _env("RESEARCH_ONLINE", "true").lower() == "true"
GITHUB_TOKEN = _env("GITHUB_TOKEN", "")
HTTP_TIMEOUT = float(_env("HTTP_TIMEOUT_SECONDS", "15"))

DATA_DIR = Path(_env("DATA_DIR", str(ROOT / "data")))
DECISION_LOG = Path(_env("DECISION_LOG", str(DATA_DIR / "decision_log.json")))
APP_PORT = int(_env("APP_PORT", "8000"))
FOUNDER_TOKEN = _env("FOUNDER_TOKEN", "")
PAYMENT_MODE = _env("PAYMENT_MODE", "mock")            # only "mock" is implemented
