"""Regenerates outputs/ and decision_log.json from a real pipeline run.

Three demo briefs (fictional founders): a strong idea, a weak idea, an excluded idea.
The founder's clicks are scripted in briefs/demo_decisions.json and logged with
via="scripted demo founder", so the log shows exactly what was decided and by whom.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import config  # noqa: E402

TMP = ROOT / "data" / "demo"
shutil.rmtree(TMP, ignore_errors=True)
config.DATA_DIR = TMP
config.DECISION_LOG = TMP / "decision_log.json"

import llm  # noqa: E402
import orchestrator as orch  # noqa: E402

VIA = "scripted demo founder (briefs/demo_decisions.json)"


def play(brief_file, script):
    run = orch.start(json.load(open(ROOT / "briefs" / brief_file)), name=brief_file)
    for step in script:
        if run["status"] != "awaiting_founder":
            break
        if step.get("approve_all_outbound"):
            for it in list(run["outbound"]):
                if it["status"] == "pending":
                    run = orch.decide_outbound(run, it["id"], True, "founder", via=VIA)
            continue
        if step["decision"] == "wait":
            break
        run = orch.decide(run, step["decision"], "founder", step.get("reason", ""), via=VIA)
    return run


def main():
    decisions = json.load(open(ROOT / "briefs" / "demo_decisions.json"))
    out = ROOT / "outputs"
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir()
    summary = {"model_available": llm.available(), "model": config.LLM_MODEL if llm.available() else None, "runs": []}
    for brief_file, suffix in (("strong_idea.json", ""), ("weak_idea.json", "_weak-idea"), ("excluded_idea.json", "_excluded-idea")):
        run = play(brief_file, decisions[brief_file])
        for f in run.get("outputs", []):
            stem, ext = f.rsplit(".", 1)
            name = f if (suffix == "" or f == "payment_test_log.md") else f"{stem}{suffix}.{ext}"
            shutil.copy(Path(run["dir"]) / "outputs" / f, out / name)
        summary["runs"].append({"brief": brief_file, "run_id": run["id"], "final_status": run["status"],
                                "last_phase": run["phase"], "history": run["history"],
                                "last_recommendation": (run.get("gate") or {}).get("outcome"),
                                "outbound": [{k: i[k] for k in ("kind", "title", "status")} for i in run["outbound"]]})
    shutil.copy(config.DECISION_LOG, ROOT / "decision_log.json")
    entries = json.load(open(ROOT / "decision_log.json"))
    summary["decision_log_entries"] = len(entries)
    summary["entries_with_model"] = sum(1 for e in entries if e["model"])
    summary["total_cost_usd"] = round(sum(e["cost"] for e in entries), 4)
    (out / "demo_run_summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
