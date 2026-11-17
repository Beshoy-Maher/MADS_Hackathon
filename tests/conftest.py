import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config  # noqa: E402
import llm  # noqa: E402
from tools import evidence  # noqa: E402


def fake_ledger(n_recent=8, n_old=0, stars=500):
    items = []
    for i in range(n_recent):
        items.append({"kind": "voice", "title": f"Please add a changelog {i}", "url": f"https://github.com/o/r/issues/{i}",
                      "engagement": 40, "text": "", "age_days": 100, "source": "github_issues", "query": "changelog"})
    for i in range(n_old):
        items.append({"kind": "voice", "title": f"changelog question {i}", "url": f"https://github.com/o/old/issues/{i}",
                      "engagement": 5, "text": "", "age_days": 2000, "source": "github_issues", "query": "changelog"})
    for i in range(4):
        items.append({"kind": "competitor", "title": f"o/tool{i}", "url": f"https://github.com/o/tool{i}",
                      "stars": stars, "text": "changelog tool", "age_days": 10, "source": "github_repos", "query": "changelog"})
    return {"items": items, "totals": {"github_issues:changelog": 100}, "errors": [], "queries": ["changelog"]}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DECISION_LOG", tmp_path / "decision_log.json")
    monkeypatch.setattr(config, "LLM_PROVIDER", "none")
    llm.reset()
    yield


@pytest.fixture
def strong_evidence(monkeypatch):
    monkeypatch.setattr(evidence, "search", lambda qs: fake_ledger())


@pytest.fixture
def weak_evidence(monkeypatch):
    monkeypatch.setattr(evidence, "search", lambda qs: fake_ledger(n_recent=1, n_old=1))
