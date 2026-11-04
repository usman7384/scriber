import argparse
import re
from collections import Counter
from pathlib import Path

ROW = re.compile(r"^\| ([A-Z][A-Z]-\d+) \| ([^|]*) \|.*\| ([^|]*) \|$")
STATES = ("done", "in progress", "open")


def rows(checklist: str) -> list[tuple[str, str, str, str]]:
    section, found = "", []
    for line in checklist.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
        elif m := ROW.match(line.rstrip()):
            found.append((section, m[1], m[2].strip(), m[3].strip()))
    return found


def state(status: str) -> str:
    return next((s for s in STATES if status.startswith(s)), "open")


def report(found: list[tuple[str, str, str, str]]) -> str:
    total = Counter(state(s) for *_, s in found)
    lines = [
        "# Parity report",
        "",
        "Generated from `docs/reference/PARITY_CHECKLIST.md` by `scriber-parity-report`; a row is done only with a passing",
        "acceptance test and a recorded demo (D-030). Evidence paths are in each row's status.",
        "",
        f"**{total['done']} done, {total['in progress']} in progress, {total['open']} open, of {len(found)} rows.**",
        "",
        "| Area | done | in progress | open |",
        "|---|---|---|---|",
    ]
    for section in dict.fromkeys(s for s, *_ in found):
        c = Counter(state(st) for s, *_, st in found if s == section)
        lines.append(f"| {section} | {c['done']} | {c['in progress']} | {c['open']} |")
    for wanted in ("in progress", "open"):
        lines += ["", f"## {wanted.capitalize()}", "", "| Row | Capability | Status |", "|---|---|---|"]
        lines += [f"| {r} | {cap} | {st} |" for _, r, cap, st in found if state(st) == wanted]
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(prog="scriber-parity-report")
    p.add_argument("--checklist", type=Path, default=Path("docs/reference/PARITY_CHECKLIST.md"))
    p.add_argument("--out", type=Path, default=Path("docs/PARITY_REPORT.md"))
    args = p.parse_args()
    args.out.write_text(report(rows(args.checklist.read_text(encoding="utf-8"))), encoding="utf-8")


if __name__ == "__main__":
    main()
