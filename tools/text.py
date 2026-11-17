"""Small text helpers (keyword extraction, slugs, Markdown to HTML)."""
from __future__ import annotations

import html
import re

STOPWORDS = set("""a an the and or but for to of in on at by with from into about over under as is are was were be been being
this that these those it its i me my we our you your they their them he she his her who whom which what when where why how
can could should would will shall may might must do does did done have has had having not no yes so very just also than then
there here all any each every some such more most less few many much own same other only both either neither via per
want wants like help helps make makes build builds sell sells selling product products digital simple easy small new
people person someone users user customers customer idea ideas business online based using use way ways get gets
who need needs thing things lot lots one two three first next etc e.g ie""".split())


FORMAT_WORDS = set("""workbook workbooks practice template templates guide guides course courses toolkit toolkits pack packs
paid daily weekly email emails newsletter newsletters ebook ebooks book worked answers set sets kit kits bundle library
collection series app tool tools platform website channel program plan plans checklist checklists starter ready
made ready-made premium free sell""".split())


_MONEY = re.compile(r"\$\s?\d[\d.,\-–]*\d|\$\s?\d")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def money_tokens(text: str) -> list[str]:
    return [m.group(0) for m in _MONEY.finditer(text or "")]


def wrong_money(text: str, allowed: list[float]) -> list[str]:
    """Dollar amounts in a text that are none of the amounts the code computed (a model garbles or invents prices)."""
    ok = set()
    for a in allowed:
        ok |= {f"${a:.2f}", f"${a:g}", f"${int(a)}" if float(a) == int(a) else f"${a:.2f}"}
    return [t for t in money_tokens(text) if t.replace(" ", "").rstrip(".,") not in ok]


def drop_sentences_with(text: str, needles: list[str]) -> str:
    """Remove the sentences that contain any of the given strings."""
    if not needles:
        return text
    lines = []
    for line in (text or "").splitlines():
        parts = re.split(r"(?<=[.!?])\s+", line)
        kept = [p for p in parts if not any(n in p for n in needles)]
        if kept or not line.strip():
            lines.append(" ".join(kept))
    return "\n".join(lines)


def strip_invented_contacts(text: str, known: str = "") -> str:
    """Email addresses that are not in the founder's brief are invented: replace them with a neutral phrase."""
    return _EMAIL.sub(lambda m: m.group(0) if m.group(0).lower() in (known or "").lower() else "the address on your receipt", text or "")


def topic_keywords(text: str, n: int = 3) -> list[str]:
    """Keywords about the problem/topic, without format words like 'workbook' or 'newsletter'."""
    return [w for w in keywords(text, 30) if w not in FORMAT_WORDS][:n]


def short_market(text: str, n: int = 6) -> str:
    words = (text or "").replace(",", " ").split()
    return " ".join(words[:n]).rstrip(".,;") or "its users"


def keywords(text: str, n: int = 6) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z+#\-]{1,}", (text or "").lower())
    seen, out = set(), []
    for w in words:
        w = w.strip("-")
        if len(w) < 3 or w in STOPWORDS or w in seen:
            continue
        seen.add(w)
        out.append(w)
    return out[:n]


def short_query(text: str, n: int = 3) -> str:
    return " ".join(keywords(text, n))


def slug(text: str, n: int = 40) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s[:n].strip("-") or "item"


def md_to_html(md: str, title: str = "") -> str:
    """Tiny Markdown subset to HTML (headings, bullets, bold, links, paragraphs)."""
    out, in_list = [], False
    for raw in (md or "").splitlines():
        line = html.escape(raw.rstrip())
        line = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", line)
        line = re.sub(r"\[(.+?)\]\((https?://[^\s)]+)\)", r'<a href="\2">\1</a>', line)
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            if in_list:
                out.append("</ul>"); in_list = False
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{m.group(2)}</h{lvl}>")
        elif re.match(r"^\s*[-*]\s+", line):
            if not in_list:
                out.append("<ul>"); in_list = True
            out.append("<li>" + re.sub(r"^\s*[-*]\s+", "", line) + "</li>")
        elif line.strip():
            if in_list:
                out.append("</ul>"); in_list = False
            out.append(f"<p>{line}</p>")
    if in_list:
        out.append("</ul>")
    body = "\n".join(out)
    return body if not title else f"<h1>{html.escape(title)}</h1>\n{body}"
