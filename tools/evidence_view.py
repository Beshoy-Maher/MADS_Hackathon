"""How evidence is shown to the founder (display only: nothing here changes a score or a gate).

* Evidence is split into "People describing the problem" (Hacker News, Reddit and Stack Exchange posts, GitHub
  issues) and "Existing solutions" (GitHub repositories), each item with its date.
* A statement the model wrote (the sharpened problem, the ideal-customer line) is labelled ASSUMPTION unless a
  fetched item supports it. A place name in it ("in Egypt") needs a fetched item that names that place, or the
  statement is an ASSUMPTION whatever else supports it.
"""
from __future__ import annotations

import re

from tools.text import keywords

PROBLEM_SOURCES = ("hackernews", "reddit", "stackexchange")

# Place names (with demonyms) a statement can claim. A claim with one of these needs a fetched source naming it.
LOCATIONS = {
    "Egypt": ("egypt", "egyptian", "cairo", "alexandria", "giza"),
    "MENA": ("mena", "middle east", "north africa"),
    "the Gulf": ("gulf", "gcc", "khaleej"),
    "Saudi Arabia": ("saudi", "ksa", "riyadh", "jeddah"),
    "the UAE": ("uae", "emirates", "emirati", "dubai", "abu dhabi"),
    "Qatar": ("qatar", "qatari", "doha"),
    "Kuwait": ("kuwait",), "Bahrain": ("bahrain",), "Oman": ("oman", "omani", "muscat"),
    "Jordan": ("jordan", "jordanian", "amman"), "Lebanon": ("lebanon", "lebanese", "beirut"),
    "Morocco": ("morocco", "moroccan"), "Tunisia": ("tunisia", "tunisian"), "Algeria": ("algeria", "algerian"),
    "the Arab world": ("arab world", "arab region", "arab countries"),
    "Africa": ("africa", "african"), "Nigeria": ("nigeria", "nigerian", "lagos"), "Kenya": ("kenya", "kenyan", "nairobi"),
    "India": ("india", "indian"), "Pakistan": ("pakistan", "pakistani"), "Turkey": ("turkey", "turkish"),
    "Europe": ("europe", "european"), "the UK": ("united kingdom", "britain", "british"),
    "Latin America": ("latin america", "latam"), "Brazil": ("brazil", "brazilian"),
}


def is_problem_post(item: dict) -> bool:
    return item.get("source") in PROBLEM_SOURCES or (item.get("source") == "github" and str(item.get("title", "")).startswith("Issue"))


def split_evidence(items: list[dict]) -> tuple[list[dict], list[dict]]:
    """(people describing the problem, existing solutions). Order is kept; the lists are new, the items untouched."""
    problem = [e for e in items if is_problem_post(e)]
    existing = [e for e in items if not is_problem_post(e)]
    return problem, existing


def item_line(e: dict) -> str:
    when = e.get("created") or "date unknown"
    return (f"- [{e['title'][:110]}]({e['url']}) ({e['source']}, {when}, {e.get('engagement', 0)} pts/stars, "
            f"{e.get('comments', 0)} comments)")


def evidence_sections(items: list[dict], limit: int = 6, heading: str = "") -> list[str]:
    problem, existing = split_evidence(items)
    out = []
    for title, group in (("People describing the problem", problem), ("Existing solutions", existing)):
        out += [f"{heading}{title} ({len(group)}):" if heading else f"{title} ({len(group)}):"]
        out += [item_line(e) for e in group[:limit]] or ["- Nothing of this kind was found."]
        out.append("")
    return out


def _has(text: str, variant: str) -> bool:
    return re.search(rf"\b{re.escape(variant)}\b", text) is not None


def locations_in(text: str) -> list[str]:
    t = (text or "").lower()
    return [name for name, variants in LOCATIONS.items() if any(_has(t, v) for v in variants)]


def _item_text(e: dict) -> str:
    return f"{e.get('title', '')} {e.get('snippet', '')}".lower()


def support(statement: str, items: list[dict], min_matches: int = 3) -> tuple[dict | None, str]:
    """(the fetched item that supports the statement, or None; why not). A statement is supported when it cites a
    fetched URL, or a problem post with a pain signal shares at least `min_matches` of its key words. Every place it
    names must also be named by a fetched item."""
    for loc in locations_in(statement):
        if not any(any(_has(_item_text(e), v) for v in LOCATIONS[loc]) for e in items):
            return None, f"no fetched source mentions {loc}"
    by_url = {e["url"]: e for e in items}
    for url in re.findall(r"https?://[^\s)\]>\"']+", statement or ""):
        if url.rstrip(".,") in by_url:
            return by_url[url.rstrip(".,")], ""
    kw = [k for k in keywords(statement, 10) if not locations_in(k)]
    best, best_n = None, 0
    for e in items:
        if not is_problem_post(e) or "pain" not in e.get("signals", []):
            continue
        n = sum(1 for k in kw if k in _item_text(e))
        if n > best_n:
            best, best_n = e, n
    if best is not None and best_n >= min_matches:
        return best, ""
    return None, "no fetched post describes this"


def labelled(statement: str, items: list[dict]) -> str:
    """The statement as shown: with the post that supports it, or labelled ASSUMPTION with the reason."""
    s = (statement or "").strip()
    if not s:
        return "ASSUMPTION: not stated"
    if "ASSUMPTION" in s:
        return s
    item, why = support(s, items)
    if item is None:
        return f"ASSUMPTION ({why}): {s}"
    if item["url"] in s:
        return s
    return f"{s} (supported by [{item['title'][:80]}]({item['url']}))"
