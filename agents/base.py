"""Shared helper for every agent: the model writes, guardrails clean, code decides.

`write()` asks the small local model for prose. If no model is reachable it uses the
agent's deterministic template and labels the text TEMPLATE. Either way the text goes
through guardrails.clean() before anyone sees it.
"""
from pathlib import Path

import config
import guardrails
import llm

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"


def prompt(role):
    return (PROMPTS / f"{role}.md").read_text()


def write(role, task, template, max_tokens=500):
    text, usage = llm.generate(prompt(role), task, max_tokens=max_tokens)
    if text:
        model, cost, label = config.LLM_MODEL, usage["cost"], f"Written by {config.LLM_MODEL} (local model)."
    else:
        text, model, cost, label = template, None, 0, "TEMPLATE: no model reachable, deterministic text."
    clean, removed = guardrails.clean(text)
    return {"text": clean, "model": model, "cost": cost, "label": label, "removed": removed}


def keywords_in(text, keywords):
    t = (text or "").lower()
    return [k for k in keywords if k.lower() in t]
