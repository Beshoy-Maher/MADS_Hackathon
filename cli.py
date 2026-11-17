"""Command line: the same pipeline and the same founder controls as the dashboard.

  python cli.py start briefs/strong_idea.json
  python cli.py status <run_id>
  python cli.py decide <run_id> go|repeat|pivot|stop [--reason "..."]
  python cli.py approve <run_id> <item_id>     |  python cli.py reject <run_id> <item_id>

Every decision is made as the founder at this terminal; it asks for confirmation first.
"""
import argparse
import json

import orchestrator as orch


def show(run):
    print(f"run {run['id']}  phase {run['phase']} ({orch.PHASE_NAMES.get(run['phase'])})  status {run['status']}")
    g = run.get("gate") or {}
    if g:
        print(f"gate {g['gate']}: recommends {g['outcome'].upper()}")
        for r in g["reasons"]:
            print("  -", r)
        for c in g["checks"]:
            print(f"  [{'PASS' if c['passed'] else 'FAIL'}] {c['name']}: {c['value']} (needs {c['threshold']})")
    for it in run.get("outbound", []):
        print(f"  outbound {it['id']} {it['kind']:8} {it['status']:9} {it['title']}")


def confirm(msg):
    return input(f"{msg} Type 'yes' to confirm: ").strip().lower() == "yes"


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start"); s.add_argument("brief")
    s = sub.add_parser("status"); s.add_argument("run_id")
    s = sub.add_parser("decide"); s.add_argument("run_id"); s.add_argument("decision", choices=orch.DECISIONS); s.add_argument("--reason", default="")
    for name in ("approve", "reject"):
        s = sub.add_parser(name); s.add_argument("run_id"); s.add_argument("item_id")
    a = ap.parse_args(argv)
    if a.cmd == "start":
        run = orch.start(json.load(open(a.brief)))
    elif a.cmd == "status":
        run = orch.load(a.run_id)
    elif a.cmd == "decide":
        run = orch.load(a.run_id)
        if not confirm(f"Founder decision {a.decision.upper()} at the {run['gate']['gate']} gate?"):
            return print("Cancelled. Nothing changed.")
        run = orch.decide(run, a.decision, "founder", a.reason, via="CLI")
    else:
        run = orch.load(a.run_id)
        if not confirm(f"{a.cmd.capitalize()} outbound item {a.item_id}?"):
            return print("Cancelled. Nothing changed.")
        run = orch.decide_outbound(run, a.item_id, a.cmd == "approve", "founder", via="CLI")
    show(run)


if __name__ == "__main__":
    main()
