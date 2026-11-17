"""Run the demo founders through the real pipeline and export the results.

    python scripts/run_demo.py            (or: docker compose run --rm app python scripts/run_demo.py)

* strong_founder: a promising idea, driven through all six phases.
* weak_founder:   a weak idea; the evidence gate recommends STOP.
* excluded_founder: a crypto-signals idea; refused by the guardrails.

The founder's choices at each gate are read from briefs/demo_decisions.json
(the demo stands in for a founder clicking the buttons). Outputs are copied
to outputs/ and the run's decision log to decision_log.json. Nothing here is
written by hand.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
DEMO_DATA = ROOT / "data" / "demo"
os.environ.setdefault("DATA_DIR", str(DEMO_DATA))
os.environ["DECISION_LOG_PATH"] = str(DEMO_DATA / "decision_log.json")

import config  # noqa: E402
import llm  # noqa: E402
import orchestrator  # noqa: E402

RUNS = [("weak_founder", "_weak-idea"), ("excluded_founder", "_excluded-idea"), ("strong_founder", "")]


def main() -> int:
    if DEMO_DATA.exists():
        shutil.rmtree(DEMO_DATA)
    DEMO_DATA.mkdir(parents=True)
    status = llm.model_status(force=True)
    print(f"Model: {status['model']} via {status['provider']}: {status['detail']}")
    decisions = json.loads((ROOT / "briefs" / "demo_decisions.json").read_text())
    final_dir = ROOT / "outputs"
    out_dir = DEMO_DATA / "outputs_export"  # build here; replace outputs/ only when every run finished
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []
    for name, suffix in RUNS:
        brief = json.loads((ROOT / "briefs" / f"{name}.json").read_text())
        run = orchestrator.create_run(brief, slug=brief.get("slug"))
        run = orchestrator.run_to_gate_with(run["id"], decisions.get(name, [{"decision": "accept", "default_action": "reject"}]))
        src = orchestrator.run_dir(run["id"]) / "outputs"
        for f in sorted(src.iterdir()):
            if suffix and f.name == "payment_test_log.md":
                continue
            target = f.stem + suffix + f.suffix
            shutil.copy(f, out_dir / target)
        gates = [(g["phase"], g["recommendation"], g.get("founder_decision")) for g in run["gates"]]
        summary.append((name, run["status"], gates))
        print(f"{name}: status={run['status']} gates={gates}")
    if status["ready"] and llm.STATS.fallbacks and "--allow-fallback" not in sys.argv:
        print(f"ABORT: the model was ready but {llm.STATS.fallbacks} call(s) fell back (model crashed or timed out). "
              "outputs/ left unchanged. " + " | ".join(llm.STATS.errors[:5]))
        return 2
    if final_dir.exists():
        for f in final_dir.iterdir():
            if f.is_file():
                f.unlink()
    final_dir.mkdir(exist_ok=True)
    for f in out_dir.iterdir():
        shutil.copy(f, final_dir / f.name)
    shutil.copy(config.DECISION_LOG_PATH, ROOT / "decision_log.json")
    s = llm.STATS
    print(f"LLM calls: {s.calls}, fallbacks: {s.fallbacks}, tokens: {s.prompt_tokens + s.completion_tokens}, cost: $0.00")
    (DEMO_DATA / "stats.json").write_text(json.dumps({"calls": s.calls, "fallbacks": s.fallbacks, "prompt_tokens": s.prompt_tokens,
                                                      "completion_tokens": s.completion_tokens, "model": status["model"],
                                                      "model_ready": status["ready"], "summary": summary}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
