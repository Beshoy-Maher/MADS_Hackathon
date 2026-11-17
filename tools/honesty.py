"""Code checks on model-written text that buyers or the founder act on.

Each function is deterministic and only removes text, so it cannot add a claim:
- counts the product cannot back (pages, number of questions, modules) are dropped from sales copy;
- experience the founder brief does not state is dropped (the system never speaks for the founder);
- covert promotion and fake urgency are dropped from growth advice;
- a sentence cut off by the token limit is dropped.
"""
from __future__ import annotations

import re

_NUM = r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|fifteen|twenty|thirty|forty|fifty|hundred)"
_NOUNS = (r"questions?|exercises?|examples?|problems?|queries|pages?|templates?|worksheets?|challenges?|modules?|chapters?|"
          r"lessons?|units?|videos?|layouts?|screens?|files?|case studies|case study|prompts?|drills?|answers?")
# "15 SQL interview questions" -> "SQL interview questions": the number goes, the noun stays.
COUNT = re.compile(rf"\b{_NUM}\+?\s+((?:[A-Za-z][\w-]*\s+){{0,3}}?)({_NOUNS})\b", re.IGNORECASE)
# "a 45-page workbook", "a 40-question workbook" -> "a workbook".
PAGE_ADJ = re.compile(rf"\b{_NUM}[- ](?:page|question|exercise|example|problem|module|lesson|chapter|template|worksheet)\b\s*", re.IGNORECASE)
# "(PDF, 45 pages)" or "(45 pages)": the whole parenthetical goes.
PAREN_COUNT = re.compile(rf"\s*\([^()]*\b(?:{_NUM}\s+pages?|pdf)\b[^()]*\)", re.IGNORECASE)
# "PDF workbook" -> "workbook"; a bare "PDF" becomes "file", so no sentence loses its noun ("It's a with ...").
PDF_ADJ = re.compile(r"\b(?:downloadable\s+)?PDF\s+(?=(?:workbook|guide|book|ebook|file|download|version|pack|document|template|format)s?\b)",
                     re.IGNORECASE)
PDF_WORD = re.compile(r"\b(?:downloadable\s+)?PDF\b", re.IGNORECASE)

EXPERIENCE = re.compile(r"\b(i(?:'|’)?ve (?:seen|been|faced|hired|interviewed|used|met|helped|worked)|i have (?:seen|been|faced|hired|interviewed)|"
                        r"who(?:'|’)?s been|who has been|been through|in my (?:own )?(?:experience|career|years|interviews)|"
                        r"from (?:my|personal) experience|i (?:hired|interviewed|failed|struggled)|when i was (?:a|an|looking|job)|"
                        r"actual interviews|real interviews i|i(?:'|’)?ve (?:encountered|run into|come across|dealt with|gone through|faced)|"
                        r"i (?:encountered|ran into|came across|went through|wish (?:something|this|i had|there was))|"
                        r"when i (?:was starting|started|first started|began)|starting out|"
                        r"(?:struggles?|problems?|challenges?|pain) you (?:faced|had|went through)|you(?:'|’)?ve (?:faced|been through)|"
                        r"when you were (?:a|an|starting|junior|new))\b", re.IGNORECASE)

COVERT = re.compile(r"\b(subtl\w*|covert\w*|disguis\w*|without (?:saying|disclosing|mentioning|revealing)|pretend\w*|"
                    r"limited[- ]time|for a limited|only \w+ (?:spots?|copies|seats?) (?:left|available)|hurry|act now|"
                    r"before it(?:'|’)?s gone|countdown|scarcity|in exchange for (?:sharing|referr\w*|inviting)|"
                    rf"(?:share|send) (?:the link |it )?(?:with|to) {_NUM} (?:peers?|friends?|people|colleagues)|"
                    r"(?:comment|repl|respond|answer|engag)\w*\b[^.\n]{0,80}\b(?:link\w*|mention\w*|plug\w*|promot\w*|drop\w*)\b[^.\n]{0,40}\b(?:waitlist|workbook|product|page|pack|template)|"
                    r"your (?:own )?(?:journey|story) as an?|as if you (?:were|are)|astroturf\w*|sock ?puppet\w*)\b",
                    re.IGNORECASE)

GROUP_PLACE = re.compile(r"\b(facebook|linkedin|discord|slack|telegram|whatsapp|twitter|instagram|tiktok|behance|dribbble|"
                         r"quora|medium|youtube|product hunt|indie hackers)\b(?:\s+\w+){0,3}?\s+(groups?|communit\w*|servers?|channels?|"
                         r"forums?|pages?)\b", re.IGNORECASE)
# Advice to stop or pause selling: only the gate (code) can recommend that.
PAUSE = re.compile(r"\b(?:pause|halt|stop|suspend|freeze|shut down|pull)\w*\s+(?:the |all |your |any )?(?:launch\w*|sales?|selling|store|product)\b",
                   re.IGNORECASE)
_DANGLING = re.compile(r"^(?:since then|despite this|however|still|yet|but|nevertheless|that said|even so|because of this|"
                       r"as a result|in addition|also|moreover|furthermore|therefore|thus|so|and),?\s+", re.IGNORECASE)

_END = re.compile(r"[.!?…)\"'”’»]\s*$")
_SENT = re.compile(r"(?<=[.!?])\s+")


def strip_counts(text: str) -> tuple[str, int]:
    """Remove counts and formats the copy states but code cannot check. Returns (text, how many were removed)."""
    n = 0
    def drop(rx, repl, s):
        nonlocal n
        s2, k = rx.subn(repl, s)
        n += k
        return s2
    t = drop(PAREN_COUNT, "", text or "")
    t = drop(PAGE_ADJ, "", t)
    t = drop(COUNT, lambda m: m.group(1) + m.group(2), t)
    t = drop(PDF_ADJ, "", t)
    t = drop(PDF_WORD, "file", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    if t[:1].islower() and (text or "")[:1].isupper():
        t = t[0].upper() + t[1:]
    return t, n


def _brief_text(brief: dict) -> str:
    # Only what the brief says about the founder: not the idea or the target market.
    parts = [str(brief.get(k, "")) for k in ("constraints", "notes", "experience")]
    parts += [str(s) for s in brief.get("skills") or []]
    return " ".join(parts).lower()


def unbacked_experience(sentence: str, brief: dict) -> bool:
    """True when a sentence claims experience for the founder that the brief does not state."""
    if not EXPERIENCE.search(sentence):
        return False
    def grams(text: str) -> set[str]:
        w = re.findall(r"[a-z]{4,}", text.lower())
        return {" ".join(w[i:i + 3]) for i in range(len(w) - 2)}
    # Backed only if the sentence repeats a stated fact, e.g. "5 years of freelance UX work".
    return not (grams(sentence) & grams(_brief_text(brief)))


def strip_experience(text: str, brief: dict) -> tuple[str, int]:
    sents = _SENT.split((text or "").strip())
    keep = [s for s in sents if not unbacked_experience(s, brief)]
    return " ".join(keep).strip(), len(sents) - len(keep)


def drop_covert_lines(text: str) -> tuple[str, int]:
    lines = (text or "").splitlines()
    keep = [l for l in lines if not COVERT.search(l)]
    return "\n".join(keep), len(lines) - len(keep)


def unresearched_places(text: str, found: set[str]) -> bool:
    """True when a line names a group or community on a platform the research did not find."""
    return any(m.group(1).lower() not in " ".join(found).lower() for m in GROUP_PLACE.finditer(text or ""))


def fix_punctuation(text: str) -> str:
    """'evidence., meaning' -> 'evidence, meaning'; 'data..' -> 'data.'"""
    t = re.sub(r"\.\s*([,;:])", r"\1", text or "")
    return re.sub(r"(?<!\.)\.\.(?!\.)", ".", t)


def clean_memo(text: str, recommendation: str) -> str:
    """The memo's reasoning: no dangling opener, no broken punctuation, no advice that contradicts the gate, no cut-off end."""
    t = fix_punctuation(text)
    sents = [s for s in _SENT.split(t.strip()) if s]
    if recommendation.lower() != "stop":
        sents = [s for s in sents if not PAUSE.search(s)]
    t = " ".join(sents)
    t = _DANGLING.sub("", t)
    t = t[:1].upper() + t[1:]
    return complete_sentences(t)


def complete_sentences(text: str) -> str:
    """Drop a trailing fragment the token limit cut off ('...is consistent with the')."""
    t = (text or "").rstrip()
    if not t or _END.search(t):
        return t
    cut = max(t.rfind(". "), t.rfind("! "), t.rfind("? "), t.rfind(".\n"))
    return t[:cut + 1].rstrip() if cut > 0 else t
