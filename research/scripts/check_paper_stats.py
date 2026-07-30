#!/usr/bin/env python3
"""Cross-check the papers' claim annotations against the gate battery.

Every published statistic carries an invisible anchor at the number:

    reads **5.6% [5.2, 6.2]**<!--@c-pool34.f3d.med-->

and is described in a SIDECAR, <paper>.meta.ttl, in the project's existing RDF
vocabulary (schema:Claim, CiTO, PROV-O, Dublin Core) so paper claims COMPOSE with
research/notes/claims.ttl and research/data-graph.ttl instead of forming a
parallel vocabulary. The sidecar keeps the metadata out of prose that humans are
about to rewrite, inherits the repo's rule that every .ttl is rdflib-validated,
and survives the draft moving to a format where an HTML comment would not. A claim can cite the output that evidences it
(cito:citesAsEvidence dg:o_ppaz) and the journal assertion it descends from
(prov:wasDerivedFrom claims:assert12), which is the article-claim -> entry
traceability direction the journal deliverable (J.3) otherwise lacks.

WHAT THIS CHECKS
  1. every anchor has a claim and every claim has an anchor;
  2. pc:value is actually asserted in the gate section named by pc:gateSection —
     the audit that found four un-gated numbers in paper 1, as a command;
  3. dcterms:type is drawn from a closed vocabulary, so scope (calibration /
     in-sample / out-of-sample / external) is explicit AT THE POINT OF USE. That
     is the distinction reviewers said the framing blurs and the first thing a
     summariser loses;
  4. `planned` claims are reported, never failed — a scaffold honestly declaring
     what it does not yet have is correct, but a planned claim that never
     acquires a value is a promise the paper did not keep, so they stay visible.

Requires rdflib (the repo's usual TTL dependency). Exits non-zero on failure.
Run: python3 research/scripts/check_paper_stats.py
"""

from __future__ import annotations

import os
import re
import sys

import rdflib
from rdflib import Namespace, RDF
from rdflib.namespace import DCTERMS

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
ARTICLES = ["paper1-closed-form.md", "paper2-dem-deployment.md", "paper3-edge-cost.md"]
GATES = os.path.join(REPO, "src", "harness", "bootstrap_ci.py")

SCHEMA = Namespace("http://schema.org/")
PC = Namespace("https://danlessa.github.io/bicycling-energy-model/paper-claims#")
SCOPES = {"calibration", "in-sample", "out-of-sample", "external", "derived", "planned"}


def gate_sections(src: str) -> dict[str, str]:
    marks = list(re.finditer(r"^# -{4,} ?([0-9][a-z0-9]*)\. ", src, re.M))
    out: dict[str, str] = {}
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(src)
        out[m.group(1)] = src[m.start():end]
    return out


def check(path: str, sections: dict[str, str]) -> tuple[int, int, int]:
    text = open(path, encoding="utf-8").read()
    sidecar = path[:-3] + ".meta.ttl"
    if not os.path.exists(sidecar):
        return 0, 0, 0
    graph = rdflib.Graph()
    graph.parse(sidecar, format="turtle")

    anchors = set(re.findall(r"<!--@c-([\w.]+)-->", text))
    claims = {str(s).split("#c-")[-1]: s for s in graph.subjects(RDF.type, SCHEMA.Claim)}

    bad = planned = 0
    print(f"\n{os.path.basename(path)} — {len(claims)} claims, {len(anchors)} anchors")

    for cid in sorted(claims):
        node = claims[cid]
        scope = str(graph.value(node, DCTERMS.type) or "")
        val = graph.value(node, PC.value)
        gate = graph.value(node, PC.gateSection)
        problems = []

        if scope == "planned":
            planned += 1
            print(f"  {cid:<32} {'—':>9}  planned        (no value yet)")
            continue

        if scope not in SCOPES:
            problems.append(f"scope '{scope}' not in {sorted(SCOPES)}")
        if cid not in anchors:
            problems.append("no anchor in the prose")
        if val is None:
            problems.append("no pc:value")
        elif gate is None:
            problems.append("no pc:gateSection")
        else:
            g = str(gate)
            if g not in sections:
                problems.append(f"gate section '{g}' does not exist")
            elif str(val) not in sections[g]:
                problems.append(f"value {val} not asserted in gate section {g}")

        status = "OK" if not problems else "FAIL: " + "; ".join(problems)
        print(f"  {cid:<32} {str(val):>9}  {scope:<14} {status}")
        if problems:
            bad += 1

    for orphan in sorted(anchors - set(claims)):
        print(f"  {orphan:<32} {'—':>9}  ANCHOR WITH NO CLAIM")
        bad += 1

    return len(claims), bad, planned


def main() -> int:
    sections = gate_sections(open(GATES, encoding="utf-8").read())
    total = bad = planned = 0
    for name in ARTICLES:
        p = os.path.join(REPO, "research", "article", name)
        if not os.path.exists(p):
            continue
        t, b, pl = check(p, sections)
        total += t
        bad += b
        planned += pl

    print(f"\n{total} claims across {len(ARTICLES)} papers · {planned} planned · {bad} failing")
    if bad:
        print("PAPER-CLAIMS CHECK FAILED", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
