"""The command line accepts any brief: a JSON file, a text file or pasted text of any length.

No model and no network: the subprocess runs with LLM_PROVIDER=none and RESEARCH_ONLINE=false.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import cli
import orchestrator

ROOT = Path(__file__).resolve().parent.parent

LONG_BRIEF = ("Founder: Nour\nStarting idea: a practical checklist and code snippets kit that helps freelance web developers "
              "make client websites accessible (WCAG 2.2)\nSkills: frontend development, HTML and CSS, accessibility audits\n"
              "Budget: $60\nTime: 10 hours per week\nTarget market: freelance web developers who build sites for small businesses\n"
              + "More detail about the founder's background and goals. " * 10)


def _cli_run(brief: str, stdin: str, tmp_path: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ, LLM_PROVIDER="none", RESEARCH_ONLINE="false", DATA_DIR=str(tmp_path / "data"),
               DECISION_LOG_PATH=str(tmp_path / "decision_log.json"))
    return subprocess.run([sys.executable, str(ROOT / "cli.py"), "run", brief], input=stdin, capture_output=True, text=True,
                          timeout=300, env=env, cwd=str(ROOT))


def test_load_brief_returns_long_text_unchanged():
    text = ("Starting idea: flashcards for German verbs. " * 60)[:2000]
    assert len(text) == 2000
    assert cli._load_brief(text) == text


def test_load_brief_reads_json_file(tmp_path):
    p = tmp_path / "brief.json"
    p.write_text(json.dumps({"idea": "SQL interview practice pack", "budget": 30}), encoding="utf-8")
    assert cli._load_brief(str(p)) == {"idea": "SQL interview practice pack", "budget": 30}


def test_load_brief_reads_text_file(tmp_path):
    p = tmp_path / "brief.txt"
    p.write_text("Starting idea: a résumé template kit\nBudget: $20\n", encoding="utf-8")
    assert cli._load_brief(str(p)) == "Starting idea: a résumé template kit\nBudget: $20\n"


def test_cli_run_with_long_pasted_brief(tmp_path):
    assert len(LONG_BRIEF) >= 600
    p = _cli_run(LONG_BRIEF, "reject\nstop\n" * 20, tmp_path)
    out = p.stdout + p.stderr
    assert p.returncode == 0, out[-2000:]
    assert "Traceback" not in out and "File name too long" not in out
    assert "Run stopped" in out


def test_cli_end_of_input_keeps_the_run(tmp_path):
    p = _cli_run(LONG_BRIEF, "", tmp_path)
    out = p.stdout + p.stderr
    assert p.returncode == 0, out[-2000:]
    assert "Traceback" not in out
    assert "is saved" in out and "dashboard" in out
    states = list((tmp_path / "data" / "runs").glob("*/state.json"))
    assert len(states) == 1
    assert json.loads(states[0].read_text(encoding="utf-8"))["status"] == "awaiting_founder"


def test_paused_makes_an_interrupted_phase_startable_again():
    run = orchestrator.create_run("Starting idea: SQL interview practice pack for junior data analysts. Budget: $30")
    run["status"] = "running"
    run["progress"] = {"text": "searching", "since": "now"}
    orchestrator.save(run)
    assert cli._paused(run["id"]) == 0
    saved = orchestrator.load(run["id"])
    assert saved["status"] == "ready" and "progress" not in saved
