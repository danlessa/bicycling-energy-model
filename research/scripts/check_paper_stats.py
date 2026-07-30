#!/usr/bin/env python3
"""Cross-check the paper's marked statistics against the gate battery.

Every published statistic in the article carries an inline marker:

    **5.6%**<!--@ id=pool35.f3.med scope=out-of-sample gate=3c -->

The marker is an HTML comment, so it is invisible in every renderer and costs
the reader nothing. What it buys:

  1. CHECKABILITY. This script verifies that each marked value actually appears
     in the gate section it names. The audit that found four un-gated numbers in
     section 3.2.2 was done by hand; this makes it a command.
  2. SCOPE, INLINE. `scope=` distinguishes calibration / in-sample /
     out-of-sample at the point of use. That is the distinction the last review
     said the framing blurs, and the one a summariser most often loses — a
     machine reader that keeps the marker cannot promote a calibration figure to
     a headline by accident.
  3. A REWRITE-SURVIVABLE CONTRACT. The human draft is written on top of the
     pre-draft; carrying the ids across is what lets this check keep working
     against prose nobody has seen yet.

Exits non-zero on any mismatch. Run: python3 research/scripts/check_paper_stats.py
"""

from __future__ import annotations

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
PAPER = os.path.join(REPO, "research", "article", "paper1-closed-form.md")
GATES = os.path.join(REPO, "src", "harness", "bootstrap_ci.py")

# The marker itself. The VALUE is read backwards from the comment — the last
# number appearing before it — because a forward regex happily matches a stray
# digit earlier in the line (a subscript in \varepsilon_2, a bracketed CI bound)
# and silently checks the wrong number. Reading backwards from a fixed anchor
# has one answer.
MARKER = re.compile(
    r"<!--@\s*id=(?P<id>[\w.]+)\s+scope=(?P<scope>[\w-]+)\s+gate=(?P<gate>[\w.]+)\s*-->"
)
NUM_BEFORE = re.compile(r"(-?\d+(?:\.\d+)?)(?!.*\d)", re.S)
SCOPES = {"calibration", "in-sample", "out-of-sample", "external", "derived"}


def gate_sections(src: str) -> dict[str, str]:
    """Split bootstrap_ci.py into its numbered sections."""
    marks = list(re.finditer(r"^# -{4,} ?([0-9][a-z0-9]*)\. ", src, re.M))
    out: dict[str, str] = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(src)
        out[m.group(1)] = src[m.start():end]
    return out


def main() -> int:
    paper = open(PAPER, encoding="utf-8").read()
    sections = gate_sections(open(GATES, encoding="utf-8").read())

    marks = list(MARKER.finditer(paper))
    if not marks:
        print("no @-markers found — nothing to check")
        return 0

    bad = 0
    seen: set[str] = set()
    for m in marks:
        sid, scope, gate = m["id"], m["scope"], m["gate"]
        before = paper[max(0, m.start() - 60):m.start()]
        nm = NUM_BEFORE.search(before)
        val = nm.group(1) if nm else "?"
        problems = []
        if sid in seen:
            problems.append("duplicate id")
        seen.add(sid)
        if scope not in SCOPES:
            problems.append(f"unknown scope (expected one of {sorted(SCOPES)})")
        if gate not in sections:
            problems.append(f"no gate section '{gate}' in bootstrap_ci.py")
        elif val not in sections[gate]:
            problems.append(f"value {val} not asserted anywhere in gate section {gate}")
        status = "OK" if not problems else "FAIL: " + "; ".join(problems)
        print(f"  {sid:<28} {val:>8}  {scope:<14} gate {gate:<4} {status}")
        if problems:
            bad += 1

    print(f"\n{len(marks)} marked statistics, {bad} failing")
    if bad:
        print("PAPER-STATS CHECK FAILED", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
