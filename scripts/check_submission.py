"""Pre-push self-check against the repository conventions in CLAUDE.md.

    python scripts/check_submission.py      (exit code 0 = all good)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README_HEADINGS = ["## Quickstart", "## What works and what is mocked", "## Architecture", "## Models and free resources",
                   "## Cost per run", "## Demo video", "## What our system will NOT do", "## How the project stays alive after the hackathon"]
ARCH_HEADINGS = ["## Overview", "## Phases", "## Gates", "## Sale to cash", "## Data flow", "## Built vs. stubbed", "## Roadmap"]
OUT_NAME = re.compile(r"^(phase\d+_step\d+_[A-Za-z0-9-]+(_[A-Za-z0-9-]+)?|phase\d+_gate_[A-Za-z0-9-]+(_[A-Za-z0-9-]+)?|payment_test_log)\.(md|json|csv|txt|html)$")
SECRET = re.compile(r"(sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{30,}|sk_live_[A-Za-z0-9]+|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----)")

problems: list[str] = []
ok: list[str] = []


def check(cond: bool, msg: str) -> None:
    (ok if cond else problems).append(msg)


def headings(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return [line.strip() for line in text.splitlines() if re.match(r"^## ", line)]


def main() -> int:
    branch = subprocess.run(["git", "-C", str(ROOT), "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
    check(branch == "main", f"on default branch main (current: {branch or 'unknown'})")

    for f in ["README.md", "LICENSE", "docker-compose.yml", "decision_log.json", "ARCHITECTURE.md", ".env.example", "CLAUDE.md"]:
        check((ROOT / f).exists(), f"{f} exists")
    for d in ["outputs", "tests", "prompts"]:
        check((ROOT / d).is_dir() and any((ROOT / d).iterdir()), f"{d}/ exists and is not empty")

    if (ROOT / "README.md").exists():
        h = headings(ROOT / "README.md")
        check(h == README_HEADINGS, f"README ## headings exactly match, in order (found: {h})")
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        qs = text.split("## Quickstart", 1)[-1].split("\n## ", 1)[0]
        check(re.search(r"```bash\s*\ndocker compose up\s*\n```", qs) is not None, "Quickstart has a bash block with exactly `docker compose up`")
        cost = text.split("## Cost per run", 1)[-1].split("\n## ", 1)[0]
        check("$" in cost and re.search(r"\$\d", cost) is not None, "Cost per run has a $ figure")
        table = text.split("## What works and what is mocked", 1)[-1].split("\n## ", 1)[0]
        check("|" in table and ("MOCKED" in table or "STUBBED" in table) and "Working" in table, "status table has Working and MOCKED/STUBBED")
        demo = text.split("## Demo video", 1)[-1].split("\n## ", 1)[0]
        if not re.search(r"https?://(www\.)?(youtube\.com|youtu\.be|vimeo\.com|loom\.com|drive\.google\.com)", demo):
            print("WARN  Demo video section has no YouTube/Vimeo/Loom/Drive link yet")

    if (ROOT / "ARCHITECTURE.md").exists():
        h = headings(ROOT / "ARCHITECTURE.md")
        check([x for x in h if x in ARCH_HEADINGS] == ARCH_HEADINGS, "ARCHITECTURE.md has all 7 sections in order")
        text = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")
        check("```mermaid" in text, "ARCHITECTURE.md has a Mermaid diagram")
        phases = text.split("## Phases", 1)[-1].split("\n## ", 1)[0]
        check(len(re.findall(r"^### ", phases, re.MULTILINE)) >= 6, "## Phases has one ### per phase (6)")
        check("STOP" in text or "stop" in text, "Gates section covers STOP")

    lic = (ROOT / "LICENSE").read_text(encoding="utf-8") if (ROOT / "LICENSE").exists() else ""
    check("Permission is hereby granted, free of charge" in lic and "WITHOUT WARRANTY OF ANY KIND" in lic, "LICENSE is full MIT text")

    try:
        entries = json.loads((ROOT / "decision_log.json").read_text(encoding="utf-8"))
        sys.path.insert(0, str(ROOT))
        import decision_log
        errs = decision_log.validate(entries)
        check(isinstance(entries, list) and entries and not errs, f"decision_log.json valid ({len(entries)} entries) {errs[:3]}")
        check(any(e.get("approved_by") == "founder" for e in entries), "decision log contains founder approvals")
    except Exception as e:
        check(False, f"decision_log.json parses ({e})")

    outs = [p for p in (ROOT / "outputs").iterdir() if p.is_file()] if (ROOT / "outputs").exists() else []
    bad = [p.name for p in outs if not OUT_NAME.match(p.name)]
    check(not bad, f"outputs/ names follow phase<N>_step<M>_<name> / phase<N>_gate_<name> ({bad})")
    check(any("_gate_" in p.name for p in outs), "outputs/ has a gate decision")
    check(any("_gate_" in p.name and "STOP" in p.read_text(encoding="utf-8") for p in outs), "outputs/ shows a STOP recommendation")
    check((ROOT / "outputs" / "payment_test_log.md").exists(), "outputs/payment_test_log.md exists")
    # outputs/ must come from the code as it is now: no code change committed after the last demo run.
    def last_commit(*paths: str) -> int:
        r = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%ct", "--", *paths], capture_output=True, text=True)
        return int(r.stdout.strip() or 0)
    code_paths = ["agents", "orchestrator.py", "gates.py", "guardrails.py", "prompts", "tools", "llm.py", "approval.py",
                  "payments.py", "delivery.py", "refunds.py", "webhooks.py", "reconcile.py", "decision_log.py"]
    out_t, code_t = last_commit("outputs", "decision_log.json"), last_commit(*code_paths)
    dirty = subprocess.run(["git", "-C", str(ROOT), "status", "--porcelain", "--", *code_paths],
                           capture_output=True, text=True).stdout.strip()
    check(out_t >= code_t and not dirty, "outputs/ and decision_log.json are not older than the code (rerun scripts/run_demo.py after code changes)")
    expected = {"phase4_step4_unit-economics.md", "phase4_step5_debate.md"} if (ROOT / "agents" / "economist.py").exists() else set()
    missing = sorted(n for n in expected if not any(p.name.startswith(n.rsplit(".", 1)[0].rsplit("_", 1)[0]) for p in outs))
    check(not missing, f"outputs/ has every step the code writes ({missing})")
    big = [p.name for p in outs if p.stat().st_size > 200_000]
    check(not big, f"output files are small ({big})")

    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True).stdout.split()
    check(".env" not in tracked, ".env is not committed")
    leaks = []
    for f in tracked:
        p = ROOT / f
        if p.is_file() and p.stat().st_size < 2_000_000:
            try:
                if SECRET.search(p.read_text(encoding="utf-8", errors="ignore")):
                    leaks.append(f)
            except Exception:
                pass
    check(not leaks, f"no secrets in tracked files ({leaks})")
    check(not any(f.startswith("docs/") and Path(f).name in ("CLAUDE.md", "AGENTS.md") for f in tracked), "CLAUDE.md is not in docs/")
    binaries = [f for f in tracked if f.lower().endswith((".png", ".jpg", ".pdf", ".zip", ".mp4", ".pptx"))]
    check(not binaries, f"no binary files tracked ({binaries})")

    r = subprocess.run([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")], capture_output=True, text=True, cwd=ROOT)
    last = (r.stdout.strip().splitlines() or ["no output"])[-1]
    check(r.returncode == 0, f"tests pass ({last})")

    for m in ok:
        print("OK   ", m)
    for m in problems:
        print("FAIL ", m)
    print(f"\n{len(ok)} ok, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
