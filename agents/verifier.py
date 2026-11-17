"""Phase 3: the verifier reviews each module the builder writes.

Two checks per module:

1. The model lists factual errors (wrong statements, code that would not run,
   invented facts). Every error must quote the wrong text; an error whose
   quote is not in the module is dropped, so the reviewer cannot invent one.
2. SQL code blocks are executed in an in-memory SQLite database. Tables and
   columns are inferred from the example. Only errors that do not depend on
   the inferred schema are reported (syntax errors, misused aggregates). If
   the schema cannot be inferred, the statement is skipped silently.

If a module has errors the builder revises it once, and the verifier reviews
the revision. Errors that are still open after that fail a QA test.
"""
from __future__ import annotations

import re
import sqlite3

import decision_log
import llm
from agents.base import Agent

MAX_ERRORS = 5
_SQL_BLOCK = re.compile(r"```[ \t]*(?:sql|sqlite|postgresql|postgres|mysql)[^\n]*\n(.*?)```", re.DOTALL | re.IGNORECASE)
_RUNNABLE = re.compile(r"^\s*(select|with|create\s+(temp(orary)?\s+)?(table|view|index)|insert|update|delete|drop\s+(table|view|index)|alter\s+table)\b",
                       re.IGNORECASE)
# Statements with a visible gap ("...", "<table>", "[columns]") are sketches, not code to run.
_SKETCH = re.compile(r"\.\.\.|…|<[a-z_ ]+>|\[[a-z_ ,.]+\]", re.IGNORECASE)
_REPORTABLE = ("syntax error", "incomplete input", "misuse of aggregate", "misuse of window function",
               "aggregate functions are not allowed", "do not have the same number of result columns",
               "unrecognized token")
_ALIAS_STOP = {"where", "on", "join", "left", "right", "inner", "outer", "full", "cross", "natural", "group", "order", "limit",
               "having", "union", "using", "set", "values", "select", "as", "window", "except", "intersect", "returning"}
_FROM = re.compile(r"\b(?:from|join|update|into)\s+\"?([A-Za-z_]\w*)\"?(?:\s+(?:as\s+)?([A-Za-z_]\w*))?", re.IGNORECASE)
_DENIED = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA}


_ANY_FENCE = re.compile(r"```.*?```", re.DOTALL)
_BARE_SQL = re.compile(r"^(?:SELECT|WITH)\b[^;`]{10,600};", re.MULTILINE)


def sql_blocks(markdown: str) -> list[str]:
    """Fenced SQL blocks, plus statements written as plain lines (a query the model forgot to fence is still code)."""
    text = markdown or ""
    blocks = [b.strip() for b in _SQL_BLOCK.findall(text) if b.strip()]
    return blocks + [m.group(0) for m in _BARE_SQL.finditer(_ANY_FENCE.sub("", text))]


_CHECKBOX = re.compile(r"^\s*[-*]\s*\[([^\]]*)\]")
_SPLIT_NUMBER = re.compile(r"\|\s*(\d+ \d+)\s*(?=\|)")


def format_errors(markdown: str) -> list[str]:
    """Slips a reader would trip over, found without a model: a broken checklist box, a number split in two in a table."""
    out = []
    for line in _ANY_FENCE.sub("", markdown or "").splitlines():
        m = _CHECKBOX.match(line)
        if m and m.group(1) not in (" ", "x", "X"):
            out.append(f"Broken checklist box, write '- [ ]': `{line.strip()[:80]}`")
        m = _SPLIT_NUMBER.search(line) if line.lstrip().startswith("|") else None
        if m:
            out.append(f"A number in a table looks split in two ('{m.group(1)}'): `{line.strip()[:80]}`")
    return out[:MAX_ERRORS]


def _statements(block: str) -> list[str]:
    text = re.sub(r"--[^\n]*", "", block)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return [s.strip() for s in text.split(";") if s.strip()]


def _connect() -> sqlite3.Connection:
    """In-memory only: nothing the example says can open a file, and a runaway query is cut off."""
    con = sqlite3.connect(":memory:")
    con.set_authorizer(lambda action, *_: sqlite3.SQLITE_DENY if action in _DENIED else sqlite3.SQLITE_OK)
    budget = {"left": 2000}

    def tick() -> int:
        budget["left"] -= 1
        return 1 if budget["left"] < 0 else 0
    con.set_progress_handler(tick, 1000)
    return con


def _add_column(con: sqlite3.Connection, table: str, column: str) -> bool:
    try:
        con.execute(f'ALTER TABLE "{table}" ADD COLUMN "{column}"')
        return True
    except sqlite3.Error:
        return False


def _run(con: sqlite3.Connection, stmt: str, inferred: set[str]) -> str | None:
    """Execute one statement, inferring missing tables and columns. Returns a reportable error or None."""
    aliases: dict[str, str] = {}
    order: list[str] = []
    for table, alias in _FROM.findall(stmt):
        order.append(table.lower())
        if alias and alias.lower() not in _ALIAS_STOP:
            aliases[alias.lower()] = table.lower()
    seen: set[str] = set()
    for _ in range(80):
        try:
            con.execute(stmt).fetchmany(5)
            return None
        except sqlite3.Error as e:
            msg = str(e)
        if msg in seen:
            return None  # inference is not getting anywhere: not our call to make
        seen.add(msg)
        low = msg.lower()
        if any(k in low for k in _REPORTABLE):
            return msg
        m = re.match(r"no such table: (\S+)$", msg)
        if m:
            name = m.group(1)
            if not re.fullmatch(r"[A-Za-z_]\w*", name):
                return None
            try:
                con.execute(f'CREATE TABLE "{name}" ("id")')
            except sqlite3.Error:
                return None
            inferred.add(name.lower())
            continue
        m = re.match(r"no such column: (?:\"?([A-Za-z_]\w*)\"?\.)?\"?([A-Za-z_]\w*)\"?$", msg) or \
            re.match(r"table (\S+) has no column named (\S+)$", msg)
        if m:
            qualifier, column = (m.group(1) or "").lower(), m.group(2)
            if qualifier:
                target = aliases.get(qualifier, qualifier)
            else:
                target = next((t for t in order if t in inferred), "")
            if target not in inferred or not _add_column(con, target, column):
                return None  # the column belongs to something we did not infer (a CTE, a subquery, a table the example defined)
            continue
        return None  # unknown function, ambiguous name, dialect feature: cannot be judged without the real database
    return None


def check_sql(markdown: str) -> dict:
    """Run a module's SQL blocks. Returns {"blocks": n, "executed": n, "errors": [str]}."""
    blocks = sql_blocks(markdown)
    report = {"blocks": len(blocks), "executed": 0, "errors": []}
    if not blocks:
        return report
    con, inferred = _connect(), set()
    try:
        for block in blocks:
            for stmt in _statements(block):
                if not _RUNNABLE.match(stmt) or _SKETCH.search(stmt):
                    continue
                report["executed"] += 1
                err = _run(con, stmt, inferred)
                if err:
                    first = " ".join(stmt.split())[:90]
                    report["errors"].append(f"SQL does not run (SQLite: {err}): `{first}`")
    finally:
        con.close()
    report["errors"] = report["errors"][:MAX_ERRORS]
    return report


def _norm(text: str) -> str:
    return re.sub(r"[\s`*_\"'“”‘’]+", " ", (text or "").lower()).strip()


class Verifier(Agent):
    role = "verifier"

    def model_errors(self, module: dict, body: str) -> tuple[list[str], str | None, float]:
        """Errors the model found, each grounded in a quote from the module. Returns (errors, model or None, cost)."""
        task = (f"Product for: {self.brief.get('target_market', '')}\nModule: {module.get('title', '')}\n\nMODULE TEXT:\n{body[:4500]}\n\n"
                "List the factual errors in MODULE TEXT. Check these four things in order:\n"
                "1. Each numbered step: is the instruction technically correct? Would a beginner who follows it literally succeed?\n"
                "2. The worked example: does the code do what the text says, and is the shown result exactly what the code returns for the shown data?\n"
                "3. Each item under 'Common mistakes': is it really a mistake? If the thing is optional, allowed or correct, the item is an error.\n"
                "4. Invented facts: made-up tools, people, statistics, sources or web addresses.\n"
                "Not errors: style, tone, length, missing topics, simplifications, opinions, things you would have written differently.\n"
                "For each error copy the wrong words exactly from MODULE TEXT into \"quote\" (5-20 words) and say in \"problem\" what "
                f"is wrong and what is correct. At most {MAX_ERRORS}. If you are not sure something is wrong, leave it out.\n"
                'JSON: {"errors": [{"quote": "...", "problem": "..."}]}. No errors: {"errors": []}.')
        data, res = llm.complete_json(self.system(), task + "\n\nAnswer with one JSON object only.", {"errors": []}, max_tokens=350)
        self._track(res)
        if not res.model:
            return [], None, res.cost
        text, out = _norm(body), []
        for e in data.get("errors") if isinstance(data.get("errors"), list) else []:
            if not isinstance(e, dict):
                continue
            quote, problem = str(e.get("quote", "")).strip(), " ".join(str(e.get("problem", "")).split())
            # The quote must really be in the module. This is what stops the reviewer from inventing an error.
            if len(_norm(quote)) < 8 or _norm(quote) not in text or not problem:
                continue
            out.append(f"\"{quote[:160]}\": {problem[:240]}")
        return out[:MAX_ERRORS], res.model, res.cost

    def review(self, index: int, module: dict, body: str, pass_no: int = 1) -> dict:
        errors, model, cost = self.model_errors(module, body)
        sql = check_sql(body)
        sql["errors"] = (sql["errors"] + format_errors(body))[:MAX_ERRORS]  # both are found by code, not by the model
        review = {"module": index, "title": module.get("title", ""), "pass": pass_no, "errors": errors, "sql_errors": sql["errors"],
                  "sql_blocks": sql["blocks"], "sql_executed": sql["executed"], "model": model}
        found = len(errors) + len(sql["errors"])
        how = "model review" if model else "no model available: SQL check only"
        decision_log.log("verifier", "review_module", run_id=self.run["id"], model=model, cost=cost,
                         step="phase3_step2_product.md", outcome="errors" if found else "clean",
                         detail=f"module {index}, pass {pass_no} ({how}): {found} error(s); "
                                f"{sql['executed']} SQL statement(s) executed in SQLite" + ("; " + " | ".join((errors + sql['errors'])[:3]) if found else ""))
        return review


def all_errors(review: dict) -> list[str]:
    return list(review.get("errors", [])) + list(review.get("sql_errors", []))


def last_passes(reviews: list[dict]) -> list[dict]:
    """The final review of each module (the one that counts for QA)."""
    last: dict[int, dict] = {}
    for r in reviews:
        if r["module"] not in last or r["pass"] >= last[r["module"]]["pass"]:
            last[r["module"]] = r
    return [last[k] for k in sorted(last)]
