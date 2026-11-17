from datetime import date

from agents.scorer import recency_weight, score_candidate

BRIEF = {"skills": ["SQL"], "hours_per_week": 8, "budget_usd": 50}


def _ev(url, signals, engagement=100, created="2026-01-01", community=None):
    return {"source": "hackernews", "url": url, "title": "sql interview pain", "engagement": engagement, "comments": 10,
            "created": created, "snippet": "", "query": "", "community": community or url, "signals": signals}


def test_repositories_are_not_counted_as_voices():
    talk = [_ev("https://a", ["pain"]), _ev("https://b", ["pain"])]
    repo = _ev("https://github.com/x/y", ["existing_solution"], engagement=50000, community="github:x")
    with_repo = score_candidate(BRIEF, {"title": "sql", "evidence": talk + [repo]}, 1.0)
    without = score_candidate(BRIEF, {"title": "sql", "evidence": talk}, 1.0)
    assert with_repo["voices"] == without["voices"] == 2


def test_old_posts_count_for_less():
    today = date(2026, 11, 17)
    assert recency_weight("2026-05-01", today) == 1.0
    assert recency_weight("2022-05-01", today) == 0.5
    assert recency_weight("2015-05-01", today) == 0.25
    assert recency_weight("", today) == 0.5
