"""Code checks on sales copy, launch posts, growth advice and the memo (tools/honesty.py)."""
from tools import honesty

BRIEF = {"skills": ["SQL", "data analysis", "mentoring junior analysts"],
         "constraints": "Works full time as a data analyst; can work evenings only.",
         "target_market": "Junior data analysts preparing for SQL interviews"}


def test_counts_the_product_cannot_back_are_removed():
    t, n = honesty.strip_counts("Contains 15 SQL interview questions inspired by common patterns.")
    assert "15" not in t and "SQL interview questions" in t and n == 1
    t, _ = honesty.strip_counts("Download the workbook (PDF, 45 pages)")
    assert t == "Download the workbook"
    t, _ = honesty.strip_counts("A 120-page guide with twenty worked examples")
    assert "120" not in t and "twenty" not in t and "worked examples" in t


def test_prices_refund_days_and_plain_text_are_kept():
    s = "One-time purchase at $11.99 with a 14-day refund."
    assert honesty.strip_counts(s) == (s, 0)
    s = "Step-by-step solutions for junior analysts."
    assert honesty.strip_counts(s) == (s, 0)


def test_experience_the_brief_does_not_state_is_removed():
    post = ("I made a workbook for junior analysts. It includes real SQL questions I've seen in actual interviews. "
            "What would you add?")
    t, n = honesty.strip_experience(post, BRIEF)
    assert "actual interviews" not in t and "What would you add?" in t and n == 1
    assert honesty.unbacked_experience("Written by a data analyst who's been through the job hunt.", BRIEF)


def test_experience_the_brief_states_is_kept():
    assert not honesty.unbacked_experience("I've been mentoring junior analysts for a while.", BRIEF)
    designer = {"skills": ["UX design", "5 years of freelance UX work"]}
    assert not honesty.unbacked_experience("In my experience, after 5 years of freelance UX work, case studies matter.", designer)


def test_covert_promotion_and_fake_urgency_are_dropped():
    plan = "\n".join([
        "- Engage with threads on Hacker News, subtly mentioning the workbook as a tool you use.",
        "- Post a brief update about your journey as a junior analyst in Egypt.",
        "- Offer a limited-time free file to people who share the link with 2 peers.",
        "- Ask the people interviewed in phase 1 whether they want to be notified.",
    ])
    t, n = honesty.drop_covert_lines(plan)
    assert n == 3 and t == "- Ask the people interviewed in phase 1 whether they want to be notified."


def test_honest_growth_advice_is_kept():
    plan = "- Share the landing page personally in Hacker News, following its rules.\n- One honest post per channel; no paid ads."
    assert honesty.drop_covert_lines(plan) == (plan, 0)


def test_cut_off_sentence_is_dropped():
    s = "There is no verified evidence of demand. The recommendation to repeat is consistent with the"
    assert honesty.complete_sentences(s) == "There is no verified evidence of demand."
    assert honesty.complete_sentences("Keep operating.") == "Keep operating."


def test_naming_the_target_market_does_not_back_an_experience_claim():
    brief = dict(BRIEF, target_market="Junior and aspiring data analysts preparing for SQL interviews")
    assert honesty.unbacked_experience("I've seen aspiring data analysts preparing for interviews fail.", brief)


# The agents, fed the text the local model actually wrote in the 4e86fde demo run.
import json

import orchestrator
from tests.test_pipeline import STRONG


def _fake(monkeypatch, text):
    import llm
    monkeypatch.setattr(llm, "complete", lambda *a, **k: llm.LLMResult(text=text, model="fake-model"))


def test_store_page_states_no_count_format_or_invented_experience(monkeypatch):
    from agents.copywriter import Copywriter
    _fake(monkeypatch, json.dumps({
        "headline": "SQL Interview Prep Workbook",
        "subheadline": "A practical workbook with real SQL interview questions, written by a data analyst who's been through the job hunt.",
        "bullets": ["Contains 15 SQL interview questions inspired by common patterns.", "Each question includes a worked answer."],
        "who_for": "Junior data analysts", "cta": "Download the workbook (PDF, 45 pages)"}))
    run = orchestrator.create_run(STRONG)
    res = Copywriter(run).store_page({"title": "SQL workbook"}, {}, {"price_usd": 11.99, "refund_window_text": "14-day refund."}, "p.md")
    for bad in ("15 SQL", "45 pages", "PDF", "been through the job hunt"):
        assert bad not in res.content
    assert "Buy and download" in res.content and "$11.99" in res.content and res.data["claims_removed_by_code"] >= 2


def test_launch_post_keeps_no_invented_experience_or_cut_off_sentence(monkeypatch):
    from agents.copywriter import Copywriter
    _fake(monkeypatch, "Show HN: a SQL workbook for junior analysts. It includes real SQL questions I've seen in actual "
                       "interviews, with worked answers. Is the reasoning clear for beginners? I would also like to")
    run = orchestrator.create_run(STRONG)
    res = Copywriter(run).launch_posts({"title": "SQL workbook"}, {"hackernews": 3}, 11.99)
    assert "actual interviews" not in res.content and "I would also like to" not in res.content
    assert "Is the reasoning clear for beginners?" in res.content


def test_demand_plan_drops_covert_promotion(monkeypatch):
    from agents.analyst import Analyst
    _fake(monkeypatch, "- Comment on Hacker News threads, subtly mentioning the workbook.\n"
                       "- Offer a limited-time free file for sharing the link with 2 peers.\n"
                       "- Share the landing page once on Hacker News, following its rules.")
    run = orchestrator.create_run(STRONG)
    res = Analyst(run).demand_plan({"title": "SQL workbook"}, {"hackernews": 3}, {"count": None})
    assert "subtly" not in res.content and "limited-time" not in res.content
    assert "Share the landing page once on Hacker News" in res.content


def test_canvas_lists_no_channel_outside_the_evidence(monkeypatch):
    from agents.strategist import Strategist
    _fake(monkeypatch, json.dumps({"channels": ["Reddit communities (e.g., r/UXDesign, r/DesignStudents)", "Founder's own network"]}))
    run = orchestrator.create_run(STRONG)
    res = Strategist(run).run_step({"title": "SQL workbook"}, {"communities": {"hackernews": 3, "github": 5}}, {})
    assert "r/UXDesign" not in res.content and "Founder's own network" in res.content
