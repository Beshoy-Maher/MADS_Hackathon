"""Originality guard: the product must not copy the sources we read, or take another product's name.

Deterministic code, no model. Two checks, run by the QA agent in Phase 3:

* Copied text: every run of COPY_MIN_WORDS or more consecutive words that the
  product shares with a fetched source (title or snippet) is reported with the
  source's link. Any such passage fails the check.
* Name clash: the product name is compared with the names of existing products
  found in the evidence (GitHub repositories, "Show HN" launches). A name that is
  the same, or nearly the same, fails the check. A well-known brand inside the
  name is only a warning, because "templates for Figma" is a fair, descriptive use.

Scope, stated plainly: only the text we fetched (titles and snippets of up to
240 characters) is compared, not the full pages behind the links.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from urllib.parse import urlparse

COPY_MIN_WORDS = 12          # a shared run of 12+ words is copying, not a common phrase
NAME_SIMILARITY = 0.85       # 0-1, SequenceMatcher ratio on normalised names
NAME_MIN_CHARS = 8           # very short names ("sql", "notes") are too generic to clash
BRANDS = ("apple", "google", "microsoft", "amazon", "meta", "facebook", "openai", "chatgpt", "notion", "canva", "coursera",
          "udemy", "linkedin", "leetcode", "hackerrank", "datacamp", "figma", "excel", "github", "youtube", "tiktok", "instagram")

_WORD = re.compile(r"[a-z0-9]+")


def _words(text: str) -> list[str]:
    return _WORD.findall(text.lower())


def _norm_name(name: str) -> str:
    return " ".join(_words(name.replace("-", " ").replace("_", " ")))


def existing_names(evidence: list[dict]) -> list[dict]:
    """Names of products that already exist, taken from the evidence: GitHub repositories and Show HN launches."""
    out = []
    for e in evidence:
        url = e.get("url", "")
        if e.get("source") == "github":
            parts = [p for p in urlparse(url).path.split("/") if p]
            if len(parts) == 2:  # github.com/<owner>/<repo>: a repository, not an issue
                out.append({"name": parts[1], "url": url})
        m = re.match(r"\s*Show HN:\s*([^:\-–—(]{3,60})", e.get("title", ""))
        if m:
            out.append({"name": m.group(1).strip(), "url": url})
    return out


def name_check(product_name: str, evidence: list[dict]) -> dict:
    mine = _norm_name(product_name)
    clashes = []
    for ex in existing_names(evidence):
        theirs = _norm_name(ex["name"])
        if len(theirs) < NAME_MIN_CHARS or len(mine) < NAME_MIN_CHARS:
            continue
        ratio = SequenceMatcher(None, mine, theirs).ratio()
        if ratio >= NAME_SIMILARITY:
            clashes.append({"name": ex["name"], "url": ex["url"], "similarity": round(ratio, 2)})
    brands = [b for b in BRANDS if re.search(rf"\b{b}\b", mine)]
    return {"product_name": product_name, "clashes": clashes, "brand_warnings": brands, "names_compared": len(existing_names(evidence))}


def copy_check(product_md: str, evidence: list[dict], min_words: int = COPY_MIN_WORDS) -> dict:
    mine = _words(product_md)
    shingles: dict[tuple, int] = {}
    for i in range(len(mine) - min_words + 1):
        shingles.setdefault(tuple(mine[i:i + min_words]), i)
    passages, compared = [], 0
    for e in evidence:
        theirs = _words(f"{e.get('title', '')} {e.get('snippet', '')}")
        if len(theirs) < min_words:
            continue
        compared += 1
        j = 0
        while j <= len(theirs) - min_words:
            start = shingles.get(tuple(theirs[j:j + min_words]))
            if start is None:
                j += 1
                continue
            n = min_words  # extend the match as far as it goes
            while j + n < len(theirs) and start + n < len(mine) and theirs[j + n] == mine[start + n]:
                n += 1
            passages.append({"url": e.get("url", ""), "words": n, "text": " ".join(theirs[j:j + n])[:200]})
            j += n
    return {"passages": passages, "sources_compared": compared, "min_words": min_words}


def check(product_md: str, product_name: str, evidence: list[dict]) -> dict:
    names = name_check(product_name, evidence)
    copies = copy_check(product_md, evidence)
    return {"passed": not names["clashes"] and not copies["passages"], "name": names, "copy": copies}


def report_lines(result: dict) -> list[str]:
    """Markdown section for the QA report."""
    n, c = result["name"], result["copy"]
    md = ["", "## Originality (code check, no model)", "",
          f"- Product name **{n['product_name']}** compared with {n['names_compared']} existing product name(s) found in the evidence: "
          + ("no clash." if not n["clashes"] else f"**{len(n['clashes'])} clash(es)**."),
          f"- Product text compared with {c['sources_compared']} fetched source(s) for runs of {c['min_words']}+ identical words: "
          + ("no copied passage." if not c["passages"] else f"**{len(c['passages'])} copied passage(s)**."),
          "- Scope: only the fetched titles and snippets are compared, not the full pages behind the links."]
    for x in n["clashes"]:
        md.append(f"- Name clash: [{x['name']}]({x['url']}) (similarity {x['similarity']}). Choose a different name.")
    for b in n["brand_warnings"]:
        md.append(f"- Warning: the name contains the brand \"{b}\". Use it only to describe compatibility (\"for {b.title()}\"), "
                  "never as if the product came from that brand.")
    for p in c["passages"]:
        md.append(f"- Copied from [{p['url']}]({p['url']}) ({p['words']} words): \"{p['text']}\". Rewrite it in your own words.")
    return md
