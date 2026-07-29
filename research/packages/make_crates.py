#!/usr/bin/env python3
"""make_crates.py — build per-entry evidence packages (RO-Crates) for every
journal entry (research objects pattern; supersedes make_entry22_crate.py).

For each `## <date> — Entry N: <title>` in MODEL_COMPARISON_JOURNAL.md this
writes research/packages/entryNN/ holding ONLY aggregates and hashes:
  ro-crate-metadata.json   RO-Crate (Workflow-Run Process Run profile where
                           the entry has a harness run)
  ro-crate-preview.html    human-readable page (RO-Crate convention)
  bootstrap_ci_report.txt  (entry 22 only) captured stdout of the gated run
  claim.ttl                (entry 22 only, hand-written — not regenerated)

The entry→artifact registry below follows data/results/README.md (file →
producer → journal entry). Gitignored per-ride CSVs and raw tracks are described
hash-only / by reference — never copied into a crate.

Deterministic by construction: no wall-clock timestamps (dates come from the
journal headers; versioning from git). Entry 22 re-executes bootstrap_ci.py
and aborts everything if any published-median gate fails.

Usage: python3 research/packages/make_crates.py
"""

import hashlib
import html
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
RESULTS = os.path.join(REPO, "data", "results")
JOURNAL = os.path.join(REPO, "research", "journal", "MODEL_COMPARISON_JOURNAL.md")
CLAIMS_TTL = os.path.join(REPO, "research", "notes", "claims.ttl")

DOI = "https://doi.org/10.5281/zenodo.21282165"
GITHUB = "https://github.com/danlessa/bicycling-energy-model"
JOURNAL_URL = f"{GITHUB}/blob/main/research/journal/MODEL_COMPARISON_JOURNAL.md"
CLAIMS_URL = f"{GITHUB}/blob/main/research/notes/claims.ttl"
PROFILE = "https://w3id.org/ro/wfrun/process/0.5"

HEADER_RE = re.compile(r"^## (?P<date>[0-9-]+) — Entry (?P<n>\d+): (?P<title>.+)$",
                       re.M)

# data/results/README.md mapping: output CSV → producer. Regeneration commands
# for the hash-only result entities.
PRODUCER = {
    "model_comparison.csv": "python3 src/harness/compare.py",
    "censo_comparison.csv": "python3 src/harness/censo_compare.py",
    "eps_hypothesis.csv": "python3 src/harness/eps_hypothesis.py",
    "eps_sp.csv": "python3 src/harness/eps_sp_test.py",
    "ppaz_comparison.csv": "python3 src/harness/ppaz_compare.py",
    "time_comparison.csv": "python3 src/harness/time_compare.py",
    "jaam_comparison.csv": "python3 src/harness/jaam_compare.py",
    "cda_estimate.csv": "python3 src/harness/cda_estimate.py",
    "param_fit.csv": "python3 src/harness/param_fit.py",
    "danlessa_comparison.csv": "python3 src/harness/danlessa_compare.py",
    "regime_comparison.csv": "python3 src/harness/regime_compare.py",
    "igc_resolution_test.csv": "python3 src/harness/igc_resolution_test.py",
    "goal_calibration.csv": "python3 src/harness/goal_calibration.py",
    "scale_trio.csv": "python3 src/harness/scale_trio.py",
    "e26_portal_profiles.csv": "python3 src/harness/e26_portal_profiles.py",
    "e26_grid.csv": "node ../simujaules/docs/grid-e26.mjs",
    "e26_grid_cal.csv": "E26_BUNDLE=cal node ../simujaules/docs/grid-e26.mjs",
    "e26_detour.csv": "python3 src/harness/e26_detour.py",
    "param_sweep.csv": "python3 src/harness/param_sweep.py",
    "param_sweep_canon.csv": "SWEEP_CANON=1 python3 src/harness/param_sweep.py",
    "longoes_frozen.csv": "python3 src/harness/longoes_frozen.py",
    "perride_invert.csv": "python3 src/harness/perride_invert.py",
    "scurve_deficit.csv": "python3 src/harness/scurve_deficit.py",
    "e35_residual.csv": "python3 src/harness/e35_residual.py",
    "e36_eps0.csv": "python3 src/harness/e36_eps0.py",
    "e38_tau.csv": "python3 src/harness/e38_tau.py",
    "e39_tau_reg.csv": "python3 src/harness/e39_tau_reg.py",
    "e40_roller.csv": "python3 src/harness/e40_roller.py",
    "e42_lump.csv": "python3 src/harness/e42_lump.py",
    "skc_comparison.csv": "python3 src/harness/skc_compare.py",
    "skc_invert.csv": "python3 src/harness/skc_invert.py",
    "skc_descent_occupancy.csv": "python3 src/harness/skc_invert.py",
    "skc_eps_vs_pedal.csv": "python3 src/harness/skc_eps_vs_pedal.py",
    "e44_scurve_cells.csv": "python3 src/harness/e44_scurve.py",
    "e44_scurve_fits.csv": "python3 src/harness/e44_scurve.py",
    "e41_dem_route.csv": "python3 src/harness/e41_dem_route.py",
}

# entry → (instrument harness scripts, result CSVs, uses private tracks,
# related committed docs). Follows data/results/README.md; entries without a
# harness run (derivations, reviews, external analyses) get claim-only crates.
ENTRIES = {
    1: (["src/harness/compare.py"], ["model_comparison.csv"], True, []),
    2: (["src/harness/compare.py"], ["model_comparison.csv"], True, []),
    3: (["src/harness/compare.py"], ["model_comparison.csv"], True, []),
    4: (["src/harness/compare.py"], ["model_comparison.csv"], True, []),
    5: (["src/harness/compare.py"], ["model_comparison.csv"], True, []),
    6: (["src/harness/build_model_inputs.py"], [], True,
        ["research/notes/dem-elevation-comparison.md"]),
    7: (["src/harness/compare.py"], ["model_comparison.csv"], True, []),
    8: (["src/harness/eps_hypothesis.py"], ["eps_hypothesis.csv"], True,
        ["research/notes/original_notes.md"]),
    9: (["src/harness/censo_compare.py"], ["censo_comparison.csv"], True, []),
    10: (["src/harness/eps_sp_test.py"], ["eps_sp.csv"], True, []),
    11: ([], [], False, ["research/notes/VERIFICATION_NOTES.md"]),
    12: (["src/harness/ppaz_compare.py"], ["ppaz_comparison.csv"], True, []),
    13: (["src/harness/time_compare.py"], ["time_comparison.csv"], True, []),
    14: (["src/harness/jaam_compare.py"], ["jaam_comparison.csv"], True, []),
    15: (["src/harness/cda_estimate.py", "src/harness/param_fit.py"],
         ["cda_estimate.csv", "param_fit.csv"], True, []),
    16: (["src/harness/danlessa_compare.py"], ["danlessa_comparison.csv"], True, []),
    17: (["src/harness/regime_compare.py"], ["regime_comparison.csv"], True, []),
    18: (["src/harness/regime_compare.py"], ["regime_comparison.csv"], True, []),
    19: (["src/harness/igc_resolution_test.py"], ["igc_resolution_test.csv"], True, []),
    20: (["src/harness/goal_calibration.py"], ["goal_calibration.csv"], True, []),
    21: (["src/harness/scale_trio.py"], ["scale_trio.csv"], True, []),
    22: (["src/harness/bootstrap_ci.py"], [], False, []),
    23: ([], [], False, []),
    24: ([], [], False, ["research/notes/ascent-error-literature.md"]),
    25: ([], [], False, []),
    26: (["src/harness/e26_pairs.py", "src/harness/e26_portal_profiles.py", "src/harness/e26_detour.py"],
         ["e26_portal_profiles.csv", "e26_grid.csv", "e26_grid_cal.csv", "e26_detour.csv"],
         True, []),
    27: (["src/harness/bootstrap_ci.py"],
         ["model_comparison.csv", "censo_comparison.csv", "eps_sp.csv",
          "igc_resolution_test.csv"], False, []),
    28: (["src/harness/bootstrap_ci.py"], [], False, []),
    29: (["src/harness/param_sweep.py"], ["param_sweep.csv"], True, []),
    30: (["src/harness/param_sweep.py"], ["param_sweep_canon.csv"], True, []),
    31: (["src/harness/longoes_frozen.py"], ["longoes_frozen.csv"], True, []),
    32: (["src/harness/bootstrap_ci.py"],
         ["ppaz_comparison.csv", "jaam_comparison.csv", "danlessa_comparison.csv",
          "longoes_frozen.csv", "time_comparison.csv"], False, []),
    33: (["src/harness/perride_invert.py"], ["perride_invert.csv"], True, []),
    34: (["src/harness/scurve_deficit.py"], ["scurve_deficit.csv"], True,
         ["research/notes/original_notes.md"]),
    35: (["src/harness/e35_residual.py"], ["e35_residual.csv"], True, []),
    36: (["src/harness/e36_eps0.py"], ["e36_eps0.csv"], True, []),
    37: ([], [], False, ["research/notes/original_notes.md"]),
    38: (["src/harness/e38_tau.py"], ["e38_tau.csv"], True, []),
    39: (["src/harness/e39_tau_reg.py"], ["e39_tau_reg.csv"], True, []),
    40: (["src/harness/e40_roller.py"], ["e40_roller.csv"], True, []),
    41: (["src/harness/e41_dem_route.py"], ["e41_dem_route.csv"], True,
         ["research/article/paper2-dem-deployment.md"]),
    42: (["src/harness/e42_lump.py"], ["e42_lump.csv"], True, []),
    43: (["src/harness/skc_compare.py", "src/harness/skc_invert.py",
         "src/harness/skc_eps_vs_pedal.py"],
        ["skc_comparison.csv", "skc_invert.csv", "skc_descent_occupancy.csv",
         "skc_eps_vs_pedal.csv"], True, []),
    44: (["src/harness/e44_scurve.py"],
         ["e44_scurve_cells.csv", "e44_scurve_fits.csv"], True, []),
}

# entry 22 reads the per-ride CSVs the other harnesses wrote
ENTRY22_INPUTS = ["model_comparison.csv", "censo_comparison.csv",
                  "ppaz_comparison.csv", "jaam_comparison.csv",
                  "time_comparison.csv"]


def load_claim_texts():
    """Entry number → the entry's (first) assertion text from claims.ttl.
    The graph is the canonical claim source; the journal title is the
    fallback for any entry the graph doesn't cover yet."""
    src = open(CLAIMS_TTL, encoding="utf-8").read()
    texts = {}
    for m in re.finditer(r"^:assert(\d+)[ab]? a schema:Claim ;(.*?)(?=\n\n|\Z)",
                         src, re.M | re.S):
        n = int(m.group(1))
        t = re.search(r'schema:text "([^"]*)"', m.group(2))
        if t and n not in texts:
            texts[n] = t.group(1)
    return texts


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_entity(name):
    """Hash-only contextual entity for a gitignored per-ride CSV."""
    path = os.path.join(RESULTS, name)
    if not os.path.exists(path):
        return None
    return {
        "@id": f"#data/results/{name}",
        "@type": "File",
        "name": f"data/results/{name}",
        "description": (f"Per-ride CSV — gitignored (rows carry ride names/dates "
                        f"tied to private activities); described hash-only, never "
                        f"distributed. Regenerates via `{PRODUCER[name]}`."),
        "sha256": sha256(path),
        "contentSize": str(os.path.getsize(path)),
        "encodingFormat": "text/csv",
    }


TRACKS_ENTITY = {
    "@id": "#ride-recordings",
    "@type": "Dataset",
    "name": "Raw ride recordings (NOT distributed)",
    "description": ("FIT tracks (GPS + power) and source spreadsheets — excluded "
                    "from version control and from this crate: location and "
                    "private-activity data. Coordinate-stripped aggregates "
                    "available on request."),
    "conditionsOfAccess": "Available on request from the author, coordinates stripped.",
}


def build_crate(n, date, title, commit, claim_text, report_text=None):
    instruments, outputs, tracks, docs = ENTRIES[n]
    crate_dir = os.path.join(HERE, f"entry{n:02d}")
    os.makedirs(crate_dir, exist_ok=True)
    has_run = bool(instruments)
    entry22 = n == 22

    parts = []
    graph = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
            "about": {"@id": "./"},
        },
    ]
    root = {
        "@id": "./",
        "@type": "Dataset",
        "name": f"Entry {n:02d} evidence package — {title}",
        "description": (f"Evidence package for journal Entry {n} "
                        f"({date}): aggregates, hashes and provenance only — "
                        f"the prose remains authoritative in the journal. "
                        f"Regenerate all packages: "
                        f"`python3 research/packages/make_crates.py`."),
        "author": {"@id": "#danilo"},
        "dateCreated": date,
        "isPartOf": {"@id": DOI},
        "url": f"{GITHUB}/tree/main/research/packages/entry{n:02d}",
        "hasPart": parts,
        "mentions": [{"@id": "#claim"}],
        "subjectOf": {"@id": JOURNAL_URL},
    }
    if has_run:
        root["conformsTo"] = {"@id": PROFILE}
    graph.append(root)

    graph.append({
        "@id": "#danilo",
        "@type": "Person",
        "name": "Danilo Lessa Bernardineli",
        "email": "danilo.lessa@gmail.com",
    })
    graph.append({
        "@id": JOURNAL_URL,
        "@type": "CreativeWork",
        "name": "Model comparison journal",
        "encodingFormat": "text/markdown",
    })

    claim = {
        "@id": "#claim",
        "@type": "Claim",
        "name": f"Entry {n}: {title}",
        "text": claim_text,
        "appearance": [{"@id": JOURNAL_URL}],
        "subjectOf": {"@id": CLAIMS_URL},
    }
    graph.append({
        "@id": CLAIMS_URL,
        "@type": "Dataset",
        "name": "Claims–questions–evidence graph (Entries 1–24)",
        "encodingFormat": "text/turtle",
    })
    if entry22:
        claim["subjectOf"] = [{"@id": "claim.ttl"}, {"@id": CLAIMS_URL}]
        parts.append({"@id": "claim.ttl"})
        graph.append({
            "@id": "claim.ttl",
            "@type": ["File", "Dataset"],
            "name": "Entry 22 claim slice (claims–questions–evidence graph; schema.org Claim + CiTO typed links)",
            "encodingFormat": "text/turtle",
            "about": {"@id": "#claim"},
        })
    graph.append(claim)

    if has_run:
        objects, results = [], []
        if entry22:
            for name in ENTRY22_INPUTS:
                ent = csv_entity(name)
                if ent:
                    objects.append({"@id": ent["@id"]})
                    graph.append(ent)
            parts.append({"@id": "bootstrap_ci_report.txt"})
            results.append({"@id": "bootstrap_ci_report.txt"})
        else:
            if tracks:
                objects.append({"@id": "#ride-recordings"})
                graph.append(dict(TRACKS_ENTITY))
            for name in outputs:
                ent = csv_entity(name)
                if ent:
                    results.append({"@id": ent["@id"]})
                    graph.append(ent)

        action = {
            "@id": "#run",
            "@type": "CreateAction",
            "name": f"Entry {n} harness run",
            "description": ("Re-executable from the repository and the private "
                            "inputs; see the journal entry for protocol, "
                            "endpoints and verdicts."),
            "endTime": date,
            "actionStatus": {"@id": "http://schema.org/CompletedActionStatus"},
            "agent": {"@id": "#danilo"},
            "instrument": [{"@id": f"#{p}"} for p in instruments],
        }
        if objects:
            action["object"] = objects
        if results:
            action["result"] = results
        graph.append(action)
        root["mentions"].append({"@id": "#run"})

        for p in instruments:
            graph.append({
                "@id": f"#{p}",
                "@type": ["File", "SoftwareApplication", "SoftwareSourceCode"],
                "name": p,
                "url": f"{GITHUB}/blob/{commit}/{p}",
                "sha256": sha256(os.path.join(REPO, p)),
                "version": commit,
                "programmingLanguage": "Python",
            })

    if entry22 and report_text is not None:
        with open(os.path.join(crate_dir, "bootstrap_ci_report.txt"), "w",
                  encoding="utf-8") as fh:
            fh.write(report_text)
        graph.append({
            "@id": "bootstrap_ci_report.txt",
            "@type": "File",
            "name": "bootstrap_ci.py report (aggregates only)",
            "description": ("Captured stdout: medians, bootstrap CIs, sign tests "
                            "and gate status per corpus. Aggregate statistics "
                            "only — no ride-level data."),
            "encodingFormat": "text/plain",
            "sha256": sha256(os.path.join(crate_dir, "bootstrap_ci_report.txt")),
        })

    for doc in docs:
        graph.append({
            "@id": f"{GITHUB}/blob/main/{doc}",
            "@type": "CreativeWork",
            "name": doc,
            "encodingFormat": "text/markdown",
        })
        root.setdefault("citation", []).append({"@id": f"{GITHUB}/blob/main/{doc}"})

    graph.append({
        "@id": "ro-crate-preview.html",
        "@type": ["File", "CreativeWork"],
        "name": "Pré-visualização humana do pacote (convenção RO-Crate)",
        "encodingFormat": "text/html",
        "about": {"@id": "./"},
    })
    graph.append({
        "@id": DOI,
        "@type": "Dataset",
        "name": "bicycling-energy-model — research package",
        "url": GITHUB,
    })

    metadata = {
        "@context": [
            "https://w3id.org/ro/crate/1.1/context",
            {"sha256": "https://w3id.org/ro/terms/workflow-run#sha256"},
        ],
        "@graph": graph,
    }
    with open(os.path.join(crate_dir, "ro-crate-metadata.json"), "w",
              encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    with open(os.path.join(crate_dir, "ro-crate-preview.html"), "w",
              encoding="utf-8") as fh:
        fh.write(render_preview(n, date, title, graph, commit, report_text))
    return crate_dir


CSS = """
:root {
  --paper:#f6f9f8; --ink:#1d2b30; --muted:#5b7076; --accent:#16717f;
  --panel:#ecf1f0; --line:#d4dedd;
}
@media (prefers-color-scheme: dark) {
  :root { --paper:#131a1c; --ink:#d9e4e2; --muted:#8fa5a9; --accent:#56b4c2;
          --panel:#1b2427; --line:#2c383b; }
}
:root[data-theme="dark"] { --paper:#131a1c; --ink:#d9e4e2; --muted:#8fa5a9;
  --accent:#56b4c2; --panel:#1b2427; --line:#2c383b; }
:root[data-theme="light"] { --paper:#f6f9f8; --ink:#1d2b30; --muted:#5b7076;
  --accent:#16717f; --panel:#ecf1f0; --line:#d4dedd; }
* { box-sizing:border-box; }
body { margin:0; background:var(--paper); color:var(--ink);
  font:16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
main { max-width:72ch; margin:0 auto; padding:2.5rem 1.25rem 4rem;
  display:flex; flex-direction:column; gap:2rem; }
h1, h2 { font-family:Palatino, "Palatino Linotype", Georgia, serif;
  line-height:1.25; text-wrap:balance; margin:0; }
h1 { font-size:1.6rem; }
h2 { font-size:1.15rem; margin-bottom:.6rem; }
.eyebrow { text-transform:uppercase; letter-spacing:.09em; font-size:.72rem;
  color:var(--accent); margin-bottom:.4rem; }
.badges { display:flex; flex-wrap:wrap; gap:.5rem; margin-top:.9rem;
  font-size:.78rem; }
.badges span { border:1px solid var(--line); border-radius:2px;
  padding:.1rem .5rem; color:var(--muted); }
blockquote { margin:0; padding:1rem 1.25rem; background:var(--panel);
  border-left:3px solid var(--accent); font-size:1.02rem; }
blockquote footer { margin-top:.6rem; font-size:.8rem; color:var(--muted); }
p { margin:.4rem 0; }
.muted { color:var(--muted); font-size:.88rem; }
table { border-collapse:collapse; width:100%; font-size:.85rem; }
th, td { text-align:left; padding:.45rem .6rem;
  border-bottom:1px solid var(--line); vertical-align:top; }
th { text-transform:uppercase; letter-spacing:.07em; font-size:.7rem;
  color:var(--muted); font-weight:600; }
.num { font-variant-numeric:tabular-nums; white-space:nowrap; }
.tablewrap { overflow-x:auto; }
code, pre { font-family:ui-monospace, "SF Mono", Menlo, monospace; }
code { font-size:.92em; }
.hash { color:var(--muted); }
pre { background:var(--panel); border:1px solid var(--line); padding:1rem;
  overflow-x:auto; font-size:.72rem; line-height:1.5; margin:0;
  font-variant-numeric:tabular-nums; }
a { color:var(--accent); }
a:focus-visible { outline:2px solid var(--accent); outline-offset:2px; }
ul { margin:.4rem 0; padding-left:1.2rem; }
"""


def render_preview(n, date, title, graph, commit, report_text):
    """ro-crate-preview.html — human-readable face of a crate (PT labels,
    both color themes, no external assets). Deterministic like the metadata."""
    by_id = {ent["@id"]: ent for ent in graph}
    e = html.escape
    instruments, outputs, tracks, docs = ENTRIES[n]
    has_run = bool(instruments)

    file_rows = "\n".join(
        f"<tr><td><code>{e(ent['name'])}</code></td>"
        f"<td class='num'>{int(ent['contentSize']):,} B</td>"
        f"<td><code class='hash'>{e(ent['sha256'][:16])}…</code></td>"
        f"<td>{e(ent['description'].split('Regenerates via')[-1].strip('` .'))}</td></tr>"
        for ent in graph
        if ent.get("sha256") and ent.get("encodingFormat") == "text/csv")

    sections = [f"""<header>
  <div class="eyebrow">Pacote de evidência · RO-Crate{' (Process Run)' if has_run else ''}</div>
  <h1>Entrada {n:02d} — {e(title)}</h1>
  <div class="badges">
    <span>{e(date)}</span>
    <span>commit {e(commit[:12])}</span>
    <span>{'com execução de harness' if has_run else 'somente afirmação'}</span>
  </div>
</header>

<section>
  <h2>A afirmação</h2>
  <blockquote>
    {e(by_id["#claim"]["text"])}
    <footer>Conforme registrado no
    <a href="{JOURNAL_URL}">diário de comparação de modelos</a> e no grafo de
    afirmações (<a href="{CLAIMS_URL}">claims.ttl</a>) — a prosa da entrada
    permanece a fonte autoritativa.</footer>
  </blockquote>
</section>"""]

    if has_run:
        instr = ", ".join(
            f"<code>{e(p)}</code> (sha256 <code class='hash'>"
            f"{e(by_id['#' + p]['sha256'][:16])}…</code>, "
            f"<a href=\"{e(by_id['#' + p]['url'])}\">fonte no commit</a>)"
            for p in instruments)
        tracks_note = ("<p class='muted'>Insumos primários: gravações de pedaladas "
                       "privadas (FIT com GPS e potência) — fora do repositório e "
                       "deste pacote; agregados sem coordenadas disponíveis sob "
                       "pedido.</p>" if tracks and n != 22 else "")
        sections.append(f"""<section>
  <h2>Como foi produzida</h2>
  <p>Instrumento(s): {instr}.</p>
  {tracks_note}
  <p class="muted">Reconstruir os pacotes:
  <code>python3 research/packages/make_crates.py</code>.</p>
</section>""")

    if file_rows:
        sections.append(f"""<section>
  <h2>Arquivos de resultado (apenas hash — dados privados)</h2>
  <p class="muted">CSVs por pedalada ficam fora do repositório (nomes e datas de
  atividades privadas). Os hashes permitem a um verificador com acesso
  consentido confirmar que recebeu os mesmos arquivos.</p>
  <div class="tablewrap"><table>
    <tr><th>arquivo</th><th>tamanho</th><th>sha256</th><th>regenera via</th></tr>
    {file_rows}
  </table></div>
</section>""")

    if report_text is not None and n == 22:
        sections.append(f"""<section>
  <h2>Relatório (somente agregados)</h2>
  <pre>{e(report_text)}</pre>
</section>""")

    doc_items = "".join(
        f"<li>Documento relacionado: <a href=\"{GITHUB}/blob/main/{e(d)}\">{e(d)}</a></li>"
        for d in docs)
    sections.append(f"""<section>
  <h2>Contexto</h2>
  <ul>
    <li>Diário (entrada {n}): <a href="{JOURNAL_URL}">MODEL_COMPARISON_JOURNAL.md</a></li>
    <li>Grafo de afirmações: <a href="{CLAIMS_URL}">claims.ttl</a></li>
    {doc_items}
    <li>Pacote de pesquisa: <a href="{DOI}">{DOI}</a></li>
    <li>Metadados legíveis por máquina: <code>ro-crate-metadata.json</code></li>
  </ul>
</section>""")

    body = "\n\n".join(sections)
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Entrada {n:02d} — pacote de evidência</title>
<style>{CSS}</style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def main():
    # entry 22's gated run first — any gate failure aborts the whole build
    run = subprocess.run([sys.executable, os.path.join(REPO, "src", "harness", "bootstrap_ci.py")],
                         capture_output=True, text=True)
    if run.returncode != 0:
        sys.stderr.write(run.stdout + run.stderr)
        sys.stderr.write("\nbootstrap_ci.py failed its gates — NO crates built\n")
        sys.exit(run.returncode)

    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                            capture_output=True, text=True).stdout.strip()

    entries = [(int(m["n"]), m["date"], m["title"].strip())
               for m in HEADER_RE.finditer(open(JOURNAL, encoding="utf-8").read())]
    entries.sort()
    missing = sorted(set(ENTRIES) ^ {n for n, _, _ in entries})
    if missing:
        sys.exit(f"journal entries and ENTRIES registry disagree on: {missing}")

    claim_texts = load_claim_texts()
    for n, date, title in entries:
        build_crate(n, date, title, commit, claim_texts.get(n, title),
                    report_text=run.stdout if n == 22 else None)
    print(f"{len(entries)} crates built under research/packages/ "
          f"(commit {commit[:12]}, all gates passed)")


if __name__ == "__main__":
    main()
