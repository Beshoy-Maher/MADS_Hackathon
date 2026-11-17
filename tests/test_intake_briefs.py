"""Messy founder briefs through intake, create_run and Phase 1.

What must hold: nothing is guessed (a field the founder did not give is listed as missing and shown to them),
an excluded product hidden anywhere in the text is refused, a borderline idea pauses at the scope check,
and Phase 1 still runs to its gate on every brief that is allowed. No model, no network (see conftest).
"""
import json

import llm
import orchestrator
from agents import intake

ARABIC = ("اسمي ليلى، معلمة لغة عربية من القاهرة. أريد أن أبيع قوالب جاهزة لخطط الدروس لمعلمي اللغة العربية "
          "الذين يدرّسون الأطفال عبر الإنترنت. عندي ٤٠ دولار للبداية وأستطيع العمل ٥ ساعات في الأسبوع.")

ONE_PARAGRAPH = ("hi so im karim, backend dev for like 6 yrs, and honestly every time i start a side project i waste a whole weekend "
                 "wiring up the same fastapi + postgres + auth boilerplate, so i was thinking of selling a starter kit with docs for "
                 "indie devs who want to ship faster, i can put in maybe ten hours a week after work and i have about $60 to spend "
                 "on a domain and stuff, i care about no lock-in and clear docs")

NO_BUDGET_NO_HOURS = """Founder: Nour
Starting idea: Notion templates that help university students plan group projects
Skills: Notion, project management
Target market: undergraduate students in Egypt who do group coursework"""

HIDDEN_EXCLUDED = """Founder: Tarek
Starting idea: a pack of Canva templates for small restaurant menus
Skills: graphic design, Canva
Budget: $25
Time: 5 hours per week
Notes: the menus are the main thing. Also every buyer should get access to my private channel with daily crypto trading signals as a bonus, that is what will really make it sell.
Target market: small restaurant owners"""

BORDERLINE_FINANCE = """Founder: Hana
Starting idea: a Google Sheets budgeting template for freelancers with irregular income
Skills: Excel, Google Sheets
Budget: $15
Time: 4 hours per week
Target market: freelance designers and writers"""

OTHER_CURRENCY = """Name: Youssef
Idea: a printable-free, fully digital revision checklist pack for Egyptian high-school maths students
Skills: maths tutoring
Budget: 1500 EGP
Time: 2 hours a day
Market: thanaweya amma students"""

PRICE_NOT_BUDGET = ("I'm Dina. I want to make a short video course on Figma auto-layout for junior designers and sell it for $19. "
                    "I'm good at Figma and teaching. Not sure yet how much time I can give it.")

SHOUTY_BULLETS = """* NAME - Omar
* IDEA - regex cheat sheets + practice drills for support engineers who grep logs all day!!!
* SKILLS - regex; bash; log analysis
* BUDGET - 25 usd
* time: ~8hrs/wk
* AUDIENCE - support engineers & SREs"""

BACKGROUND_ONLY = """Founder: Mona
Starting idea: a shift-swap spreadsheet template for hospital ward teams
Skills: scheduling, Google Sheets
Constraints: I work as a nurse full time, so evenings only
Budget: $20
Time: 6 hours per week
Target market: ward managers who build staff rotas"""

MESSY_JSON = {"idea": "  A Chrome extension that turns long docs into flashcards for language learners  ", "founder_name": "",
              "skills": "JavaScript; language teaching", "budget_usd": "50$", "hours_per_week": "weekends", "target_market": None}

ALL_TEXT = [ARABIC, ONE_PARAGRAPH, NO_BUDGET_NO_HOURS, HIDDEN_EXCLUDED, BORDERLINE_FINANCE, OTHER_CURRENCY, PRICE_NOT_BUDGET,
            SHOUTY_BULLETS, BACKGROUND_ONLY]


def _phase1(raw):
    run = orchestrator.create_run(raw)
    return orchestrator.advance(run["id"])


def test_arabic_brief_keeps_its_numbers_and_language():
    run = _phase1(ARABIC)
    b = run["brief"]
    assert b["budget_usd"] == 40 and b["hours_per_week"] == 5 and b["founder_name"] == "ليلى"
    assert "خطط الدروس" in b["idea"]
    assert run["screening"]["allowed"] and orchestrator.current_gate(run)["gate"] == "evidence_gate"


def test_single_paragraph_brief_reads_number_words_and_budget():
    run = _phase1(ONE_PARAGRAPH)
    b = run["brief"]
    assert b["hours_per_week"] == 10 and b["budget_usd"] == 60
    assert "starter kit" in b["idea"]
    assert "skills" in b["missing"]            # not labelled, and no model to read them: shown as missing, not invented
    assert len(run["steps"]) == 4


def test_missing_budget_and_hours_are_shown_not_guessed():
    run = _phase1(NO_BUDGET_NO_HOURS)
    b = run["brief"]
    assert b["budget_usd"] is None and b["hours_per_week"] is None
    assert {"budget_usd", "hours_per_week"} <= set(b["missing"])
    assert any("budget (USD)" in w and "hours per week" in w and "Nothing was assumed" in w for w in run["warnings"])
    out = orchestrator.run_dir(run["id"]) / "outputs"
    card = (out / "phase1_step2_scorecard.md").read_text()
    assert "hours per week not given in the brief" in card and "budget not given in the brief" in card
    assert "counts as 0" in card and "None" not in card
    assert orchestrator.current_gate(run)["gate"] == "evidence_gate"


def test_excluded_product_hidden_in_the_middle_is_refused():
    run = _phase1(HIDDEN_EXCLUDED)
    assert not run["screening"]["allowed"] and run["screening"]["category"] == "excluded_product:financial"
    g = orchestrator.current_gate(run)
    assert g["recommendation"] == "stop" and g["allowed"] == ["stop"] and not run["steps"]


def test_borderline_finance_idea_pauses_at_the_scope_check():
    run = _phase1(BORDERLINE_FINANCE)
    assert run["screening"]["allowed"] and run["screening"]["clarify"]
    assert orchestrator.current_gate(run)["gate"] == "scope_gate" and not run["steps"]
    assert run["brief"]["budget_usd"] == 15 and run["brief"]["hours_per_week"] == 4


def test_other_currency_and_hours_per_day_are_not_converted():
    run = _phase1(OTHER_CURRENCY)
    b = run["brief"]
    assert b["budget_usd"] is None and b["hours_per_week"] is None
    assert "1500 EGP" in b["budget_note"]
    assert any("1500 EGP" in w and "not converted" in w for w in run["warnings"])


def test_a_selling_price_is_not_read_as_the_budget():
    run = _phase1(PRICE_NOT_BUDGET)
    b = run["brief"]
    assert b["budget_usd"] is None and b["hours_per_week"] is None and b["founder_name"] == "Dina"
    assert {"budget_usd", "hours_per_week"} <= set(b["missing"])


def test_shouty_bullets_with_odd_labels():
    run = _phase1(SHOUTY_BULLETS)
    b = run["brief"]
    assert b["founder_name"] == "Omar" and b["budget_usd"] == 25 and b["hours_per_week"] == 8
    assert b["skills"] == ["regex", "bash", "log analysis"] and "support engineers" in b["target_market"]
    assert b["idea"].startswith("regex cheat sheets") and b["missing"] == []


def test_founder_background_in_an_excluded_field_is_not_a_refusal():
    run = _phase1(BACKGROUND_ONLY)
    assert run["screening"]["allowed"]
    assert run["brief"]["budget_usd"] == 20 and run["brief"]["hours_per_week"] == 6


def test_messy_json_brief():
    run = _phase1(MESSY_JSON)
    b = run["brief"]
    assert b["idea"].startswith("A Chrome extension") and b["skills"] == ["JavaScript", "language teaching"]
    assert b["budget_usd"] == 50 and b["hours_per_week"] is None and b["founder_name"] == "Founder"
    assert set(b["missing"]) == {"founder_name", "hours_per_week", "target_market"}
    assert orchestrator.current_gate(run)["gate"] == "evidence_gate"


def test_every_allowed_brief_reaches_a_gate_with_valid_state():
    for raw in ALL_TEXT + [MESSY_JSON]:
        run = _phase1(raw)
        assert run["status"] == "awaiting_founder" and not run.get("error"), raw
        assert run["brief"]["idea"] and isinstance(run["brief"]["missing"], list)
        json.dumps(run)  # state stays serialisable


def test_numbers_a_model_makes_up_are_dropped(monkeypatch):
    """A model that fills the gaps with plausible figures: none of them reaches the brief."""
    def guessing_model(system, user, fallback, *, max_tokens=1200):
        data = {"founder_name": "Nour", "idea": "Notion templates that help university students plan group projects",
                "skills": ["Notion", "project management"], "budget_usd": 100, "hours_per_week": 10,
                "target_market": "undergraduate students in Egypt", "values": [], "constraints": "unknown"}
        return data, llm.LLMResult(text=json.dumps(data), model="fake-model")
    monkeypatch.setattr(llm, "complete_json", guessing_model)
    brief, model = intake.parse(NO_BUDGET_NO_HOURS)
    assert model == "fake-model"
    assert brief["budget_usd"] is None and brief["hours_per_week"] is None and brief["constraints"] == ""
    assert {"budget_usd", "hours_per_week"} <= set(brief["missing"])


def test_numbers_a_model_reads_from_the_text_are_kept(monkeypatch):
    text = "I'm Sara. Selling Anki decks for medical school exams vocabulary. I can do 7h weekly and my budget is 35 dollars."
    def reading_model(system, user, fallback, *, max_tokens=1200):
        data = {"founder_name": "Sara", "idea": "Anki decks for medical school exams vocabulary", "skills": [],
                "budget_usd": 35, "hours_per_week": 7, "target_market": "", "values": [], "constraints": ""}
        return data, llm.LLMResult(text=json.dumps(data), model="fake-model")
    monkeypatch.setattr(llm, "complete_json", reading_model)
    brief, _ = intake.parse(text)
    assert brief["budget_usd"] == 35 and brief["hours_per_week"] == 7
