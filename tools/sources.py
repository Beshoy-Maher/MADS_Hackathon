"""Public evidence sources for the researcher agent.

Each source returns a list of Evidence items with a real URL, so every market
claim in the outputs can cite where it came from. All sources are free,
public and need no key: Hacker News (Algolia API), Reddit (public JSON),
GitHub search, and Stack Exchange.

If a source cannot be reached the researcher records that, uses the sources
that worked, and labels anything unsupported as ASSUMPTION.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import time
from dataclasses import asdict, dataclass, field
from urllib.parse import quote_plus

import httpx

import config

# Words that show someone has the problem or would pay for a fix.
PAIN_WORDS = ("struggl", "hard to", "how do i", "how to", "help", "looking for", "is there a", "any tool", "recommend",
              "frustrat", "confus", "stuck", "need", "wish", "pain", "problem", "can't", "cannot", "difficult",
              "advice", "best way", "alternative", "template", "checklist", "guide")
PAY_WORDS = ("pay", "paid", "price", "pricing", "buy", "bought", "purchase", "worth it", "subscription", "$", "cost",
             "course", "premium", "invest in")


@dataclass
class Evidence:
    source: str
    url: str
    title: str
    engagement: int = 0  # points, stars, upvotes or answers+score
    comments: int = 0
    created: str = ""
    snippet: str = ""
    query: str = ""
    community: str = ""  # who/where: subreddit, repo owner, HN author, SE site
    signals: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return asdict(self)


def _cache_get(key: str):
    path = config.DATA_DIR / "cache" / f"{key}.json"
    if path.exists() and time.time() - path.stat().st_mtime < 24 * 3600:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _cache_put(key: str, value) -> None:
    path = config.DATA_DIR / "cache" / f"{key}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _get_json(url: str, headers: dict | None = None):
    key = hashlib.sha1(url.encode()).hexdigest()[:20]
    cached = _cache_get(key)
    if cached is not None:
        return cached
    h = {"User-Agent": config.HTTP_USER_AGENT, "Accept": "application/json"}
    h.update(headers or {})
    r = httpx.get(url, headers=h, timeout=config.HTTP_TIMEOUT_SECONDS, follow_redirects=True)
    r.raise_for_status()
    data = r.json()
    _cache_put(key, data)
    return data


_PAIN_RX = re.compile(r"\b(" + "|".join(re.escape(w) for w in PAIN_WORDS) + r")", re.IGNORECASE)
_PAY_RX = re.compile(r"(\$\s?\d|\b(" + "|".join(re.escape(w) for w in PAY_WORDS if w != "$") + r")\b)", re.IGNORECASE)


def _signals(text: str) -> list[str]:
    out = []
    if _PAIN_RX.search(text or ""):
        out.append("pain")
    if _PAY_RX.search(text or ""):
        out.append("willingness_to_pay")
    return out


def hackernews(query: str, limit: int = 10) -> list[Evidence]:
    data = _get_json(f"https://hn.algolia.com/api/v1/search?query={quote_plus(query)}&tags=(story,ask_hn)&hitsPerPage={limit}")
    out = []
    for h in data.get("hits", []):
        title = h.get("title") or h.get("story_title") or ""
        if not title:
            continue
        text = f"{title} {h.get('story_text') or ''}"
        out.append(Evidence("hackernews", f"https://news.ycombinator.com/item?id={h.get('objectID')}", title,
                            int(h.get("points") or 0), int(h.get("num_comments") or 0), (h.get("created_at") or "")[:10],
                            (h.get("story_text") or "")[:240], query, "hn:" + str(h.get("author", "")), _signals(text)))
    return out


def reddit(query: str, limit: int = 10) -> list[Evidence]:
    path = f"/search.json?q={quote_plus(query)}&limit={limit}&sort=relevance&t=all"
    try:
        data = _get_json("https://www.reddit.com" + path)
    except httpx.HTTPError:
        data = _get_json("https://old.reddit.com" + path)  # sometimes less strict with scripts
    out = []
    for c in data.get("data", {}).get("children", []):
        d = c.get("data", {})
        title = d.get("title", "")
        text = f"{title} {d.get('selftext', '')}"
        created = time.strftime("%Y-%m-%d", time.gmtime(d.get("created_utc", 0))) if d.get("created_utc") else ""
        out.append(Evidence("reddit", "https://www.reddit.com" + d.get("permalink", ""), f"r/{d.get('subreddit', '')}: {title}",
                            int(d.get("score") or 0), int(d.get("num_comments") or 0), created,
                            (d.get("selftext") or "")[:240], query, "reddit:r/" + str(d.get("subreddit", "")), _signals(text)))
    return out


def github(query: str, limit: int = 8) -> list[Evidence]:
    headers = {"Accept": "application/vnd.github+json"}
    if config.GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {config.GITHUB_TOKEN}"
    out = []
    repos = _get_json(f"https://api.github.com/search/repositories?q={quote_plus(query)}&sort=stars&order=desc&per_page={limit}", headers)
    for r in repos.get("items", []):
        text = f"{r.get('full_name')} {r.get('description') or ''}"
        out.append(Evidence("github", r.get("html_url", ""), f"Repository {r.get('full_name')}: {(r.get('description') or '')[:120]}",
                            int(r.get("stargazers_count") or 0), int(r.get("open_issues_count") or 0), (r.get("created_at") or "")[:10],
                            (r.get("description") or "")[:240], query, "github:" + str((r.get("owner") or {}).get("login", "")),
                            # A repository is something that already exists. Its description is the author's pitch
                            # ("struggling with X?"), not a person describing a problem, so it never counts as a pain post.
                            ["existing_solution"] + [s for s in _signals(text) if s != "pain"]))
    try:
        issues = _get_json(f"https://api.github.com/search/issues?q={quote_plus(query)}+is:issue&per_page={limit}", headers)
    except httpx.HTTPError:
        issues = {}  # repositories alone are still useful evidence
    for i in issues.get("items", []):
        text = f"{i.get('title')} {(i.get('body') or '')[:400]}"
        reactions = int((i.get("reactions") or {}).get("total_count") or 0)
        out.append(Evidence("github", i.get("html_url", ""), f"Issue: {i.get('title', '')[:140]}", reactions,
                            int(i.get("comments") or 0), (i.get("created_at") or "")[:10], (i.get("body") or "")[:240], query,
                            "github:" + str((i.get("user") or {}).get("login", "")), _signals(text)))
    return out


def stackexchange(query: str, limit: int = 8, site: str = "stackoverflow") -> list[Evidence]:
    data = _get_json("https://api.stackexchange.com/2.3/search/advanced?order=desc&sort=votes"
                     f"&q={quote_plus(query)}&site={site}&pagesize={limit}")
    out = []
    for q in data.get("items", []):
        title = q.get("title", "")
        created = time.strftime("%Y-%m-%d", time.gmtime(q.get("creation_date", 0))) if q.get("creation_date") else ""
        out.append(Evidence("stackexchange", q.get("link", ""), title, int(q.get("score") or 0) + int(q.get("view_count", 0) // 1000),
                            int(q.get("answer_count") or 0), created, "", query,
                            "stackexchange:" + str((q.get("owner") or {}).get("user_id", "")), _signals(title) or ["pain"]))
    return out


SOURCES = {"hackernews": hackernews, "reddit": reddit, "github": github, "stackexchange": stackexchange}


def search(queries: list[str], sources: list[str] | None = None) -> tuple[list[Evidence], dict]:
    """Run every query on every source. Returns (evidence, report of which sources worked)."""
    sources = sources or config.RESEARCH_SOURCES
    found: dict[str, Evidence] = {}
    report = {s: {"ok": 0, "failed": 0, "error": ""} for s in sources}
    if not config.RESEARCH_ONLINE:
        for s in sources:
            report[s]["error"] = "online research disabled (RESEARCH_ONLINE=false)"
        return [], report
    def one_source(s: str) -> list[Evidence]:
        """All queries for one source, in order. A source that fails twice is left alone."""
        fn, items = SOURCES.get(s), []
        if not fn:
            return items
        for q in queries:
            if report[s]["failed"] >= 2:
                break
            try:
                items += fn(q)
                report[s]["ok"] += 1
            except Exception as e:
                report[s]["failed"] += 1
                report[s]["error"] = f"{type(e).__name__}: {str(e)[:120]}"
        return items

    # Sources are independent sites, so they are queried side by side: one slow or blocked site no longer holds up the rest.
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=max(1, len(sources))) as pool:
        results = list(pool.map(one_source, sources))
    for items in results:  # merged in source order, so the result does not depend on which site answered first
        for ev in items:
            if ev.url and ev.url not in found:
                found[ev.url] = ev
    return list(found.values()), report


def relevance(ev: Evidence, keywords: list[str]) -> float:
    """Share of the idea's keywords that appear in the item's title/snippet."""
    if not keywords:
        return 0.0
    t = f"{ev.title} {ev.snippet}".lower()
    hits = sum(1 for k in keywords if k.lower() in t)
    return hits / len(keywords)


def engagement_score(items: list[Evidence]) -> float:
    """0-100, log-scaled total engagement so one viral post can't dominate."""
    total = sum(max(0, e.engagement) + max(0, e.comments) for e in items)
    return min(100.0, 18 * math.log10(1 + total))
