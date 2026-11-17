"""Evidence search on free public APIs (no keys needed).

- GitHub repository search  -> existing solutions (competition)
- GitHub issue search       -> people describing the pain in their own words (demand voices)
- Hacker News (Algolia)     -> discussions (demand voices)

Every item keeps its URL. A source that cannot be reached is recorded as an error,
never replaced by invented data.
"""
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import config

UA = {"User-Agent": "venture-gates-research/1.0", "Accept": "application/json"}


def _get(url):
    headers = dict(UA)
    if "api.github.com" in url and config.GITHUB_TOKEN:
        headers["Authorization"] = "Bearer " + config.GITHUB_TOKEN
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=config.HTTP_TIMEOUT) as r:
        return json.load(r)


def _age_days(iso):
    try:
        t = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - t).days
    except Exception:
        return None


def github_repos(query):
    url = "https://api.github.com/search/repositories?" + urllib.parse.urlencode(
        {"q": query, "sort": "stars", "order": "desc", "per_page": 10})
    data = _get(url)
    items = [{"kind": "competitor", "title": r["full_name"], "url": r["html_url"],
              "stars": r.get("stargazers_count", 0), "text": (r.get("description") or "")[:200],
              "age_days": _age_days(r.get("pushed_at", ""))} for r in data.get("items", [])]
    return items, data.get("total_count", 0), url


def github_issues(query):
    url = "https://api.github.com/search/issues?" + urllib.parse.urlencode(
        {"q": f"\"{query}\" in:title is:issue", "sort": "reactions", "order": "desc", "per_page": 15})
    data = _get(url)
    items = [{"kind": "voice", "title": i["title"][:160], "url": i["html_url"],
              "engagement": i.get("comments", 0) + (i.get("reactions") or {}).get("total_count", 0),
              "text": (i.get("body") or "")[:240].replace("\n", " "),
              "age_days": _age_days(i.get("created_at", ""))} for i in data.get("items", [])]
    return items, data.get("total_count", 0), url


def hackernews(query):
    url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(
        {"query": query, "tags": "(story,ask_hn)", "hitsPerPage": 10})
    data = _get(url)
    items = [{"kind": "voice", "title": (h.get("title") or "")[:160],
              "url": f"https://news.ycombinator.com/item?id={h['objectID']}",
              "engagement": (h.get("points") or 0) + (h.get("num_comments") or 0), "text": "",
              "age_days": _age_days(h.get("created_at", ""))} for h in data.get("hits", [])]
    return items, data.get("nbHits", 0), url


SOURCES = {"github_repos": github_repos, "github_issues": github_issues, "hackernews": hackernews}


def search(queries):
    """Run every source for every query. Returns a ledger dict."""
    ledger = {"items": [], "totals": {}, "errors": [], "queries": list(queries)}
    if not config.RESEARCH_ONLINE:
        ledger["errors"].append("RESEARCH_ONLINE=false: no evidence fetched")
        return ledger
    seen = set()
    for q in queries:
        for name, fn in SOURCES.items():
            try:
                items, total, url = fn(q)
            except Exception as e:  # network refusal, rate limit, timeout
                ledger["errors"].append(f"{name} '{q}': {type(e).__name__}: {str(e)[:80]}")
                continue
            ledger["totals"][f"{name}:{q}"] = total
            for it in items:
                if it["url"] not in seen:
                    seen.add(it["url"])
                    it["source"] = name
                    it["query"] = q
                    ledger["items"].append(it)
    return ledger
