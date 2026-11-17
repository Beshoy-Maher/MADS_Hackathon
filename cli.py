"""Command-line founder console (same pipeline and gates as the dashboard).

    python cli.py run briefs/strong_founder.json     # interactive: you decide at every gate
    python cli.py run "Starting idea: ... Skills: ... Budget: $30 ..."
    python cli.py ask "write 50 five-star reviews"   # try the guardrails
    python cli.py list
    python cli.py demo                               # regenerate outputs/ and decision_log.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import approval
import guardrails
import llm
import orchestrator


def _ask(prompt: str, choices: tuple) -> str:
    while True:
        ans = input(f"{prompt} [{'/'.join(choices)}]: ").strip().lower()
        if ans in choices:
            return ans
        print("Please type one of:", ", ".join(choices))


def cmd_run(args) -> int:
    src = args.brief
    raw = json.loads(Path(src).read_text()) if Path(src).exists() else src
    status = llm.model_status(force=True)
    print(f"Model: {status['model']} ({status['detail']})")
    run = orchestrator.create_run(raw)
    print(f"Run {run['id']} for: {run['brief']['idea']}")
    for w in run.get("warnings", []):
        print(f"NOTE: {w}")
    while True:
        print(f"\n=== Phase {run['phase']}: {orchestrator.PHASES[run['phase']]['name']} ===")
        run = orchestrator.advance(run["id"])
        for s in [s for s in run["steps"] if s["phase"] == run["phase"]]:
            print(f"  step {s['step']}: {s['agent']} -> {s['file']} (model: {s['model'] or 'fallback'}, sources: {s['sources']})")
        for a in approval.pending(run):
            print(f"\n  APPROVAL NEEDED [{a['kind']}] {a['target']}: {a['description']}")
            if a["payload"].get("message") or a["payload"].get("text"):
                print("   ", (a["payload"].get("message") or a["payload"].get("text"))[:500])
            pc = a["payload"].get("promise_check")
            if pc:
                print(f"    promise check: {pc['kept']} kept, {pc['broken']} broken, {pc['unverifiable']} unverifiable")
                for x in pc.get("broken_items", []) + pc.get("unverifiable_items", []):
                    print("     -", x)
            ch = _ask("  Approve?", ("approve", "reject"))
            try:
                run = orchestrator.decide_action(run["id"], a["id"], ch == "approve", approval.FOUNDER)
            except approval.BrokenPromise as e:
                print("   ", e)
                if _ask("  It can only be rejected now. Reject it, or leave it pending?", ("reject", "leave")) == "reject":
                    run = orchestrator.decide_action(run["id"], a["id"], False, approval.FOUNDER, "rejected: broken promise")
                else:
                    run = orchestrator.load(run["id"])
        g = orchestrator.current_gate(run)
        print(f"\n  GATE {g['gate']}: system recommends {g['recommendation'].upper()}" + (f" -> {g['pivot_to']}" if g.get("pivot_to") else ""))
        for r in g["reasons"]:
            print("   -", r)
        for c in g["checks"]:
            print(f"     {'PASS' if c['passed'] else 'FAIL'} {c['name']}: {c['value']} (threshold {c['threshold']})")
        d = _ask("  Your decision", tuple(g["allowed"]))
        note = input("  Note (optional): ").strip()
        run = orchestrator.decide(run["id"], d, approval.FOUNDER, note)
        if run["status"] in ("stopped", "completed", "monitoring"):
            print(f"\nRun {run['status']}. Outputs: {orchestrator.run_dir(run['id']) / 'outputs'}")
            return 0


def cmd_ask(args) -> int:
    v = guardrails.screen_request_deep(args.text)
    print(guardrails.refusal_message(v) if not v.allowed else "Allowed: this request passes the guardrails.")
    return 0 if v.allowed else 1


def cmd_list(_) -> int:
    for r in orchestrator.list_runs():
        print(f"{r['id']:<36} {r['status']:<17} phase {r['phase']}  {r['idea'][:60]}")
    return 0


def cmd_demo(_) -> int:
    return subprocess.call([sys.executable, str(Path(__file__).parent / "scripts" / "run_demo.py")])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run"); r.add_argument("brief"); r.set_defaults(fn=cmd_run)
    a = sub.add_parser("ask"); a.add_argument("text"); a.set_defaults(fn=cmd_ask)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    sub.add_parser("demo").set_defaults(fn=cmd_demo)
    args = p.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
