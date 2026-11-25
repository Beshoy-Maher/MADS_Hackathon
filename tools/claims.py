"""Claim checker: every market claim must cite a source we actually fetched, or be labelled ASSUMPTION.

Small models invent statistics and citations ("over 100,000 jobs (source:
LinkedIn, 2023)"). This deterministic pass runs on research-type outputs:

* Links to URLs that are not in the run's evidence are removed. In research
  outputs the link text stays, marked unverified; in text a buyer or visitor
  reads (buyer_facing=True) the link becomes its plain anchor text and a bare
  URL is removed, with no marker. The footer counts the removed links either way.
* Sentences with a statistic or a citation phrase ("source:", "according
  to", "studies show", "%", "million"...) that do not contain an evidence URL
  are labelled "ASSUMPTION (unverified):".
"""
from __future__ import annotations

import re

LINK_RX = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
URL_RX = re.compile(r"https?://[^\s)\]]+")
CLAIM_RX = re.compile(
    r"(\d+(\.\d+)?\s?%|\b\d{1,3}(,\d{3})+\b|\b\d+(\.\d+)?\s?(million|billion|thousand|k|m|bn)\b|\b(over|more than|nearly|about|around|approximately)\s+\d{3,}"
    r"|\(source[:s]?|\bsource:|\baccording to\b|\bstudies (show|suggest)|\bresearch (shows|suggests)|\bsurveys? (show|found)|\breports? (show|that)"
    r"|\b\d{1,2}\s?[–-]\s?\d{1,2}\s+years?\b|\bstatistics\b|\bon average\b|\b(market|industry) (is worth|size of|is growing|grew)\b|\bCAGR\b"
    r"|\b(growing|rising|increasing|expanding|booming)\s+(fast|rapidly|quickly|steadily)\b|\b(high|huge|strong|growing|rising|massive)\s+demand\b"
    r"|\bin[- ]demand\b|\bmost (employers|companies|recruiters|people|students|analysts)\b)",
    re.IGNORECASE,
)
# Light mode, for product, pricing, launch and support texts: these may hold ordinary numbers (a price, a day count),
# so only citation phrases and market-trend statements are treated as claims.
LIGHT_RX = re.compile(
    r"(\(source[:s]?|\bsource:|\baccording to\b|\bstudies (show|suggest)|\bresearch (shows|suggests)|\bsurveys? (show|found)|\breports? (show|that)"
    r"|\bstatistics\b|\b(market|industry) (is worth|size of|is growing|grew)\b|\bCAGR\b|\b\d+(\.\d+)?\s?(million|billion)\b"
    r"|\b(is|are) (often|usually|typically|generally|commonly|widely) (costly|expensive|pricey|unaffordable|scarce|hard to (find|get|afford)|underpaid|overpriced)\b"
    r"|\b\d+(\.\d+)?\s?%\s+of\s+(people|companies|employers|recruiters|students|users|analysts|customers|developers|founders)\b"
    r"|\b(growing|rising|increasing|expanding|booming)\s+(fast|rapidly|quickly|steadily)\b|\b(is|are|has|have|shows?|sees?|with|there'?s)\s+(a\s+)?(high|huge|strong|growing|rising|massive)\s+demand\b"
    r"|\bin[- ]demand\b|\bmost (employers|companies|recruiters)\b)",
    re.IGNORECASE,
)
_BARE_URL = re.compile(r"(?<![(\[<\"'=])\bhttps?://[^\s)\]>\"']+")
MARKER = "(unverified link removed)"
_MARK = "\u2063UNVERIFIED\u2063"  # internal placeholder, replaced before the text leaves check()
_ORPHAN_SOURCE = re.compile(r"^\s*[*_>-]*\s*\**(source|sources|reference|references|further reading|see also)\**\s*:.*" + _MARK + ".*$",
                            re.IGNORECASE)


def _tidy_buyer_line(line: str) -> str:
    """A line a removed link was cut out of: no marker, no empty brackets, no doubled spaces or stray punctuation."""
    lead = re.match(r"^\s*", line).group(0)
    body = line[len(lead):].replace(" " + _MARK, "").replace(_MARK, "")
    body = re.sub(r"\(\s*(?:e\.g\.,?|see|at|via|like|from)?\s*[,;]?\s*\)", "", body, flags=re.IGNORECASE)
    body = re.sub(r"\b(?:at|via|see|here:)\s*([.,;:!?]|$)", r"\1", body, flags=re.IGNORECASE)
    body = re.sub(r" {2,}", " ", body)
    body = re.sub(r"\s+([.,;:!?)])", r"\1", body)
    body = re.sub(r"([(])\s+", r"\1", body)
    return lead + body.rstrip()


def strip_unverified(text: str, allowed_urls: set[str]) -> tuple[str, int]:
    """Buyer-facing text: a link to an unfetched URL becomes its anchor text, a bare unfetched URL goes. No marker."""
    out, report = check(text, allowed_urls, mode="none", buyer_facing=True)
    return out, report["removed_links"]


def check(text: str, allowed_urls: set[str], mode: str = "full", buyer_facing: bool = False) -> tuple[str, dict]:
    """mode="full" for research outputs; mode="light" for everything else (see LIGHT_RX); mode="none" removes links only.
    buyer_facing=True for text the buyer or a visitor reads: removed links leave no marker."""
    claim_rx = {"full": CLAIM_RX, "light": LIGHT_RX}.get(mode)
    removed_links = 0
    relabelled = 0

    def fix_link(m: re.Match) -> str:
        nonlocal removed_links
        if m.group(2).rstrip(".,") in allowed_urls:
            return m.group(0)
        removed_links += 1
        if m.group(1).strip().startswith(("http://", "https://", "www.")):
            return _MARK
        return f"{m.group(1)} {_MARK}"

    def fix_bare(m: re.Match) -> str:
        nonlocal removed_links
        url = m.group(0).rstrip(".,;:")
        if url in allowed_urls or "localhost" in url:
            return m.group(0)
        removed_links += 1
        return _MARK

    text = LINK_RX.sub(fix_link, text or "")
    text = _BARE_URL.sub(fix_bare, text)
    # A "Source: ..." line whose only link was invented is itself an invented citation: drop the whole line.
    text = "\n".join(l for l in text.splitlines() if not _ORPHAN_SOURCE.match(l))
    if buyer_facing:
        text = "\n".join(_tidy_buyer_line(l) if _MARK in l else l for l in text.splitlines())
    else:
        text = text.replace(_MARK, MARKER)
    if claim_rx is None:
        return text, {"relabelled": 0, "removed_links": removed_links}
    out_lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "|", "---", "Generated by", "Sources cited")):
            out_lines.append(line)
            continue
        parts = re.split(r"(?<=[.!?])\s+", line)
        new_parts = []
        for p in parts:
            urls = {u.rstrip(".,") for u in URL_RX.findall(p)}
            sourced = bool(urls & allowed_urls)
            if claim_rx.search(p) and not sourced and "ASSUMPTION" not in p:
                # Drop invented citations such as "(source: LinkedIn Job Trends, 2023)".
                p = re.sub(r"\s*\((source|sources)[^)]*\)", "", p, flags=re.IGNORECASE)
                lead = re.match(r"^(\s*(?:[-*]|\d+\.)\s+)?", p).group(0)
                p = f"{lead}ASSUMPTION (unverified): {p[len(lead):]}"
                relabelled += 1
            new_parts.append(p)
        out_lines.append(" ".join(new_parts))
    return "\n".join(out_lines), {"relabelled": relabelled, "removed_links": removed_links}


def footer_note(report: dict) -> str:
    if not report["relabelled"] and not report["removed_links"]:
        return "Claim check: every statistic or citation above links to fetched evidence."
    return (f"Claim check: {report['relabelled']} unsourced claim(s) labelled ASSUMPTION, "
            f"{report['removed_links']} link(s) not found in the fetched evidence removed.")
