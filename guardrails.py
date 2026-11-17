"""Safety rules, written as general patterns (not a list of known test prompts).

Two jobs:
1. screen_brief(): refuse ideas outside scope (physical goods, finance/investment/crypto,
   health or legal advice) and requests to deceive (fake reviews, fake urgency,
   impersonation, income promises, handling money or passwords ourselves).
2. clean(): scan every text an agent writes and remove sentences that break the rules,
   so a model (or a template) can never ship a fake testimonial or an income promise.
"""
import re
import unicodedata

# category -> patterns. Matching is on a normalised, lower-case copy of the text.
EXCLUDED_PRODUCTS = {
    "finance_investment_crypto": [
        r"\bcrypto\w*", r"\bbitcoin\b", r"\bethereum\b", r"\btoken sale\b", r"\bnft\w*",
        r"\btrading (signal|bot|strateg)\w*", r"\bforex\b", r"\bstock (pick|tip|signal)\w*",
        r"\binvest(ment|ing)? (advice|tips|signals|portfolio)\b", r"\bday ?trad\w+",
        r"\bloan\w*\b", r"\bcredit (repair|score fix)\w*", r"\bget rich\b",
    ],
    "health_advice": [
        r"\bdiagnos\w+", r"\bsymptom checker\b", r"\bsupplement\w*", r"\bdiet plan\w*",
        r"\btreat(ment|ing)? (for|of)\b", r"\bcure\w*\b", r"\bmedical advice\b",
        r"\bmental health (advice|therapy)\b", r"\bdosage\b", r"\bweight loss\b",
    ],
    "legal_advice": [
        r"\blegal advice\b", r"\blawsuit\w*", r"\bimmigration (advice|case)\w*",
        r"\bcontract review service\b", r"\bact as (my|a) lawyer\b", r"\bsue\b",
    ],
    "physical_goods": [
        r"\bship(ping)? (physical|boxes|products)\b", r"\bdropship\w*", r"\bmanufactur\w+",
        r"\bwarehouse\b", r"\bprint(ed)? (mugs|t-?shirts|merch)\b", r"\bphysical (product|goods)\b",
    ],
}

DECEPTION = {
    "fake_social_proof": [
        r"\b(fake|invent|fabricat\w*|made[- ]up|generate) (\w+ ){0,3}(reviews?|testimonials?|ratings?|sign-?ups?|users?|customers?)\b",
        r"\b\d[\d,]* (happy|satisfied) (customers|users)\b",
        r"\bas seen (on|in)\b",
    ],
    "fake_urgency": [
        r"\bcountdown\b", r"\bonly \d+ (left|spots?|copies)\b", r"\bexpires? in \d+",
        r"\blast chance\b", r"\bprice goes up (in|at|tonight|tomorrow)\b",
    ],
    "income_promise": [
        r"\bguarantee\w* (income|revenue|profit|results|success|sales)\b",
        r"\b(earn|make) \$?\d[\d,]*\+? (a|per|every) (day|week|month)\b",
        r"\bpassive income\b", r"\bget rich\b", r"\brisk[- ]free (income|profit)\b",
    ],
    "impersonation": [
        r"\b(pretend|pose|posing|act) (to be|as) (the founder|a customer|a real customer|\w+ (inc|corp|official))\b",
        r"\bsign (it|this|posts?) as (the founder|a customer)\b", r"\bon behalf of (apple|google|microsoft|amazon|stripe)\b",
    ],
    "money_or_credentials": [
        r"\b(store|save|collect|keep) (\w+ ){0,2}(passwords?|card numbers?|cvv|credit cards?)\b",
        r"\b(move|transfer|hold|withdraw) (the )?(money|funds|payouts?)\b",
        r"\bauto-?refund\w*\b", r"\bcreate (accounts?|an account) for\b",
    ],
    "rule_override": [
        r"\b(ignore|disregard|bypass|skip|override) (\w+ ){0,3}(rules?|instructions|guardrails|approval|gates?)\b",
        r"\bwithout (founder )?(approval|asking)\b", r"\bauto-?approve\b",
    ],
}


# Rules applied to every text an agent writes (the brief-only rules are left out).
OUTPUT_RULES = {k: DECEPTION[k] for k in ("fake_social_proof", "fake_urgency", "income_promise", "impersonation")}


def normalise(text):
    t = unicodedata.normalize("NFKC", text or "").lower()
    t = re.sub(r"[​-‏⁠]", "", t)        # zero-width characters
    t = re.sub(r"(?<=\w)[\.\-_*](?=\w\b)", "", t)       # c.r.y.p.t.o style splitting
    return re.sub(r"\s+", " ", t)


def _hits(text, table):
    t = normalise(text)
    found = []
    for cat, pats in table.items():
        for p in pats:
            m = re.search(p, t)
            if m:
                found.append({"category": cat, "match": m.group(0)})
                break
    return found


def screen_brief(text):
    """Return {"allowed": bool, "reasons": [...]} for a founder's brief."""
    excluded = _hits(text, EXCLUDED_PRODUCTS)
    deceptive = _hits(text, DECEPTION)
    reasons = [f"excluded product: {h['category']} ('{h['match']}')" for h in excluded]
    reasons += [f"refused request: {h['category']} ('{h['match']}')" for h in deceptive]
    return {"allowed": not reasons, "reasons": reasons}


def clean(text):
    """Remove every sentence that breaks a rule. Returns (clean_text, removed_list)."""
    removed = []
    kept_lines = []
    for line in (text or "").split("\n"):
        parts = re.split(r"(?<=[.!?])\s+", line)
        keep = []
        for s in parts:
            hits = _hits(s, OUTPUT_RULES)
            if hits:
                removed.append({"sentence": s.strip(), "category": hits[0]["category"]})
            else:
                keep.append(s)
        kept_lines.append(" ".join(keep))
    return "\n".join(kept_lines), removed
