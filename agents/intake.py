"""Turns a founder brief (JSON or free text) into the structured brief every agent uses.

Nothing is guessed. A field the founder did not give stays empty (numbers stay None) and is listed in
brief["missing"], which the dashboard, the CLI and the scorecard show. A number the model extracts is
only kept if that number is really in the founder's text.
"""
from __future__ import annotations

import re

import llm
from agents.base import load_prompt

FIELDS = ("founder_name", "idea", "skills", "budget_usd", "hours_per_week", "target_market", "values", "constraints")
# Shown to the founder when absent. Values and constraints are optional.
REQUIRED = ("founder_name", "idea", "skills", "budget_usd", "hours_per_week", "target_market")
LABELS = {"founder_name": "your name", "idea": "the idea", "skills": "your skills", "budget_usd": "budget (USD)",
          "hours_per_week": "hours per week", "target_market": "target market"}

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
          "eleven": 11, "twelve": 12, "fifteen": 15, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "hundred": 100}
_NUM = r"(\d[\d,]*(?:\.\d+)?|" + "|".join(_WORDS) + r")"
_USD = re.compile(rf"(?:\$\s?{_NUM}|{_NUM}\s?(?:usd|us dollars?|dollars?|bucks|دولار)\b)", re.IGNORECASE)
_OTHER_CURRENCY = re.compile(rf"{_NUM}\s?(egp|le|l\.e\.?|eur|euros?|gbp|pounds?|sar|aed|riyals?|dirhams?|جنيه|جنيها|ريال|درهم|يورو)(?![a-z])|([€£])\s?{_NUM}",
                             re.IGNORECASE)
_BUDGET_WORDS = re.compile(r"\b(budget|spend|afford|invest|savings?|to start|have about|have around|i have|got)\b|ميزانية|الميزانية", re.IGNORECASE)
_PRICE_WORDS = re.compile(r"\b(price|sell|charge|cost(s)? (them|buyers)|per month|a month|each|subscription|earn|make|revenue|income)\b", re.IGNORECASE)
_HOURS = re.compile(rf"{_NUM}\s*(?:-\s*\d+\s*)?(?:h|hrs?|hours?)\s*(?:/|a|per|each|every)?\s*(?:week|wk)(?:ly)?\b"
                    rf"|{_NUM}\s*(?:ساعات|ساعة|ساعه)\s*(?:في|فى|كل|بال|/)?\s*(?:ال)?(?:أسبوع|اسبوع|أسبوعيا|اسبوعيا|أسبوعياً)", re.IGNORECASE)
_HOURS_LABEL = re.compile(rf"(?:time|hours|availability|الوقت)\s*[:\-]\s*{_NUM}\s*(?:h|hrs?|hours?|ساعات|ساعة)?\s*(?:/|a|per)?\s*(?:week|wk|أسبوع|اسبوع)?",
                          re.IGNORECASE)
# English and Arabic labels of a "Field: value" brief.
_FIELD_LABELS = {
    "founder_name": ("founder name", "founder", "name", "my name is", "الاسم", "اسمي"),
    "idea": ("starting idea", "idea", "product", "الفكرة", "فكرتي", "المنتج"),
    "skills": ("skills", "المهارات", "مهاراتي"),
    "target_market": ("target market", "market", "audience", "customers", "السوق المستهدف", "السوق", "الجمهور", "العملاء"),
    "values": ("values", "القيم"),
    "constraints": ("constraints", "القيود"),
}


def _to_number(token: str) -> float | None:
    token = (token or "").lower().replace(",", "")
    if token in _WORDS:
        return float(_WORDS[token])
    try:
        return float(token)
    except ValueError:
        return None


def _first(m: re.Match) -> float | None:
    return next((n for n in (_to_number(g) for g in m.groups() if g) if n is not None), None)


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?؟])\s+|\n+", text) if s.strip()]


def find_budget(text: str) -> tuple[float | None, str]:
    """(budget in USD or None, note). A price the founder wants to charge is not a budget; other currencies are not converted."""
    usd, other = [], []
    for s in _sentences(text):
        budgetish, priceish = bool(_BUDGET_WORDS.search(s)), bool(_PRICE_WORDS.search(s))
        for m in _USD.finditer(s):
            usd.append((_first(m), budgetish, priceish))
        for m in _OTHER_CURRENCY.finditer(s):
            if budgetish or not priceish:
                other.append(" ".join(m.group(0).split()))
    labelled = [n for n, b, _ in usd if b and n is not None]
    if labelled:
        return labelled[0], ""
    plain = [n for n, _, p in usd if not p and n is not None]
    if len(plain) == 1 and not other:
        return plain[0], ""
    if other:
        return None, f"The brief gives a budget of {other[0]}. It was not converted to US dollars."
    return None, ""


def find_hours(text: str) -> float | None:
    m = _HOURS.search(text)
    if not m:
        m = _HOURS_LABEL.search(text)
        # "Time: 2 hours a day" is not a weekly figure, and turning it into one would be a guess.
        if m and re.match(r"[^\n]{0,12}\b(day|daily|month|monthly)\b|[^\n]{0,12}(يوم|شهر)", text[m.end():], re.IGNORECASE):
            m = None
    return _first(m) if m else None


def _numbers_in(text: str) -> set[float]:
    found = {_to_number(t) for t in re.findall(r"\d[\d,]*(?:\.\d+)?", text)}
    found |= {float(v) for w, v in _WORDS.items() if re.search(rf"\b{w}\b", text, re.IGNORECASE)}
    return {n for n in found if n is not None}


def _list(v) -> list[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        return [x.strip() for x in re.split(r"[,;،\n]", v) if x.strip()]
    return []


def fallback_parse(text: str) -> dict:
    """Rule-based reading of a brief. Used alone when no model is available, and as the check on the model's numbers."""
    text = text.translate(_ARABIC_DIGITS)

    def field(key: str) -> str:
        for label in _FIELD_LABELS[key]:
            m = re.search(rf"(?:^|\n)\s*[-*•]?\s*{label}\s*[:\-]\s*(.+)", text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""
    labelled = any(field(k) for k in _FIELD_LABELS)
    # Unlabelled text: the whole text is the founder's description of the idea (cut to size later).
    idea = field("idea") or ("" if labelled else " ".join(text.split()))
    name = field("founder_name")
    if not name:
        m = re.search(r"\b(?i:my name is|i am|i'm|this is)\s+(?!Not\b|Good\b|Sure\b|Based\b|Looking\b)([A-Z][a-z]+)\b(?!\s+(?:a|an|the)\b)", text) or \
            re.search(r"(?:اسمي|أنا|انا)\s+([\u0621-\u064A]{2,12})(?=\s*[،,.]|\s+و)", text)
        name = m.group(1) if m else ""
    budget, note = find_budget(text)
    out = {"founder_name": name, "idea": idea, "skills": _list(field("skills")), "budget_usd": budget,
           "hours_per_week": find_hours(text), "target_market": field("target_market"),
           "values": _list(field("values")), "constraints": field("constraints")}
    if note:
        out["budget_note"] = note
    return out


def _number(v) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"\d[\d,]*(?:\.\d+)?", str(v).translate(_ARABIC_DIGITS))
    return _to_number(m.group(0)) if m else None


def normalize(brief: dict) -> dict:
    out = {k: brief.get(k) for k in FIELDS}
    name = str(out.get("founder_name") or "").strip()
    out["founder_name"] = (name or "Founder")[:60]
    out["idea"] = str(out.get("idea") or "").strip()[:600]
    out["skills"] = _list(out.get("skills"))
    out["values"] = _list(out.get("values"))
    for k in ("budget_usd", "hours_per_week"):
        out[k] = _number(out.get(k))  # None when the founder did not say; never a default
    for k in ("target_market", "constraints"):  # a model sometimes answers with a list where a sentence is expected
        v = out.get(k)
        out[k] = ("; ".join(_list(v)) if isinstance(v, list) else str(v or "")).strip()[:300]
    for k in ("waitlist_target", "waitlist_window_days", "slug", "budget_note"):
        if brief.get(k):
            out[k] = brief[k]
    missing = [k for k in REQUIRED if out[k] in (None, "", [])]
    if not name:
        missing.insert(0, "founder_name")
    out["missing"] = list(dict.fromkeys(missing))
    return out


def missing_note(brief: dict) -> str:
    """One sentence for the founder about what the brief did not say. Empty when nothing is missing."""
    missing = [LABELS[k] for k in brief.get("missing", []) if k in LABELS]
    parts = []
    if missing:
        parts.append("Not given in the brief: " + ", ".join(missing) + ". Nothing was assumed in their place"
                     + ("; founder fit counts a missing budget or missing hours as 0 until you add them" if
                        {"budget_usd", "hours_per_week"} & set(brief.get("missing", [])) else "") + ".")
    if brief.get("budget_note"):
        parts.append(brief["budget_note"])
    return " ".join(parts)


def parse(raw: dict | str) -> tuple[dict, str | None]:
    """Returns (brief, model used or None)."""
    if isinstance(raw, dict) and raw.get("idea"):
        return normalize(raw), None
    text = raw if isinstance(raw, str) else str(raw)
    fb = fallback_parse(text)
    data, res = llm.complete_json(load_prompt("intake"),
                                  "Founder brief text:\n" + text[:3000] + "\n\nExtract JSON with keys: " + ", ".join(FIELDS) +
                                  ". skills and values are lists of strings; budget_usd and hours_per_week are numbers or null. "
                                  "Use the founder's own words (keep the founder's language). A field the text does not state: "
                                  "empty string, [] or null. Never fill a gap with a typical value.",
                                  {k: fb.get(k) for k in FIELDS}, max_tokens=500)
    if not isinstance(data, dict):
        data = {}
    merged = dict(fb)
    for k in ("founder_name", "idea", "skills", "target_market", "values", "constraints"):
        v = data.get(k)
        if v not in (None, "", [], 0) and not (isinstance(v, str) and v.strip().lower() in ("unknown", "n/a", "none", "null", "not specified", "not stated")):
            merged[k] = v
    # Numbers: the rule-based reading wins. The model's number is used only when the rules found none and the
    # number really appears in the founder's text (a model likes to fill a gap with a plausible figure).
    stated = _numbers_in(text.translate(_ARABIC_DIGITS))
    if merged.get("hours_per_week") is None:
        n = _number(data.get("hours_per_week"))
        if n and n in stated and re.search(r"week|wk|أسبوع|اسبوع", text, re.IGNORECASE):
            merged["hours_per_week"] = n
    if merged.get("budget_usd") is None and not merged.get("budget_note"):
        n = _number(data.get("budget_usd"))
        if n and n in stated and re.search(r"\$|usd|dollar|دولار", text, re.IGNORECASE):
            merged["budget_usd"] = n
    if not str(merged.get("idea") or "").strip():
        merged["idea"] = " ".join(text.split())
    return normalize(merged), res.model
