"""Researcher: collects public evidence for the idea (Phase 1, step 1).

Method: search each founder keyword on GitHub repositories (existing solutions),
GitHub issues and Hacker News (people describing the pain). On REPEAT it broadens the
search with the audience and problem words. Nothing is invented: a failed source is
listed as an error.
"""
from agents.base import write
from tools import evidence


def queries(brief, broaden=False):
    qs = list(brief["keywords"])
    if broaden:
        qs += [w for w in brief.get("broader_keywords", [])]
    return qs


def research(brief, broaden=False):
    ledger = evidence.search(queries(brief, broaden))
    voices = [i for i in ledger["items"] if i["kind"] == "voice"]
    comps = [i for i in ledger["items"] if i["kind"] == "competitor"]
    top = sorted(voices, key=lambda v: -v["engagement"])[:8]
    template = (f"Idea: {brief['idea']}\nAudience: {brief['audience']}\n"
                f"Found {len(voices)} pain voices and {len(comps)} existing solutions "
                f"across {len(ledger['queries'])} search terms.")
    summary = write("researcher", f"Summarise the opportunity in 3 sentences for: {brief['idea']}. "
                    f"Evidence titles: {[v['title'] for v in top]}. Do not add numbers that are not in the titles.", template)
    lines = [f"# Phase 1 Step 1: Opportunities and evidence\n", f"_{summary['label']}_\n", summary["text"], "",
             "## Search terms", ", ".join(ledger["queries"]), "", "## Pain voices (most engaged first)"]
    for v in sorted(voices, key=lambda v: -v["engagement"])[:15]:
        age = f"{v['age_days']} days old" if v["age_days"] is not None else "age unknown"
        lines.append(f"- [{v['title']}]({v['url']}) ({v['source']}, engagement {v['engagement']}, {age})")
    lines += ["", "## Existing solutions (competition)"]
    for c in sorted(comps, key=lambda c: -c["stars"])[:10]:
        lines.append(f"- [{c['title']}]({c['url']}) ({c['stars']} stars): {c['text']}")
    lines += ["", "## Sources that failed (not replaced by guesses)"] + [f"- {e}" for e in ledger["errors"]] if ledger["errors"] else []
    return {"ledger": ledger, "md": "\n".join(lines), "model": summary["model"], "cost": summary["cost"],
            "sources": [i["url"] for i in ledger["items"]]}
