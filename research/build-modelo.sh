#!/usr/bin/env bash
# Build the published article pages — https://simujaules.pedalhidrografi.co/modelo/ —
# from the working-paper markdown in this directory:
#
#   article-draft.pt-BR.md  →  modelo/index.html  + modelo/artigo.pdf   (canonical, pt-BR)
#   article-draft.md        →  modelo/en.html     + modelo/paper.pdf    (English)
#   figs/*.svg              →  modelo/figs/
#
# Output goes into the *simujaules* repo's modelo/ directory (committed there as
# static output; its deploy.sh ships it). Math is rendered to MathML at build
# time — the pages are self-contained, no JS, no CDN. Each page carries Google
# Scholar Highwire citation_* meta tags, schema.org ScholarlyArticle JSON-LD,
# hreflang alternates, and a citation_pdf_url; the PDFs are printed from the
# HTML by headless Chrome.
#
# Design: Distill-style (transformer-circuits.pub as the reference) — serif
# body on a ~44rem measure, sans headings, a small-caps byline grid under the
# title, hairline rules, sans tables/captions, and a TOC that docks to the
# left margin on wide screens. The markdown's own H1 is stripped at build time
# and replaced by the injected title block (also keeps the TOC clean).
#
# Requires: pandoc (tested 3.1) and Google Chrome.
# Usage: ./build-modelo.sh [output-dir]     default: ../../simujaules/modelo
set -euo pipefail
cd "$(dirname "$0")"

OUT="${1:-../../simujaules/modelo}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE="https://simujaules.pedalhidrografi.co/modelo"

TITLE_PT="Energia de Rotas de Bicicleta em Forma Fechada: Duas Correções, um Offset de Recuperação na Descida que se Transfere entre Ciclistas, e um Dual Energia↔Tempo"
TITLE_EN="Bicycle Route Energy in Closed Form: Two Corrections, a Descent-Recovery Offset That Transfers Across Riders, and an Energy↔Time Dual"
DESC_PT="Uma lei em forma fechada para a energia (kJ) de pedalar uma rota, validada contra ~1.400 pedaladas com medidor de potência — working paper do Pedal Hidrográfico."
DESC_EN="A closed-form law for the energy (kJ) of cycling a route, validated against ~1,400 power-meter rides — a Pedal Hidrográfico working paper."

mkdir -p "$OUT/figs"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ---------------------------------------------------------------- shared CSS
cat > "$TMP/style.html" <<'EOF'
<style>
:root {
  color-scheme: light dark;
  --bg: #ffffff; --fg: #1b1b1b; --muted: #616161; --faint: #9a9a9a;
  --hair: rgba(0,0,0,.14); --hair2: rgba(0,0,0,.07);
  --note-bg: #f7f7f4; --note-bd: #e9e9e3; --code-bg: #f4f4f0;
  --underline: rgba(0,0,0,.3);
  --sans: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
  --serif: Georgia, "Iowan Old Style", "Times New Roman", serif;
  --mono: ui-monospace, "SF Mono", SFMono-Regular, Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) { :root {
  --bg: #171614; --fg: #e7e3db; --muted: #a8a399; --faint: #7c776e;
  --hair: rgba(255,255,255,.17); --hair2: rgba(255,255,255,.08);
  --note-bg: #1f1e1b; --note-bd: #2d2b26; --code-bg: #242320;
  --underline: rgba(255,255,255,.35);
}}
html { -webkit-text-size-adjust: 100%; scroll-behavior: smooth; }
body { margin: 0 auto; max-width: 44rem; padding: 0 1.4rem 5rem;
  background: var(--bg); color: var(--fg);
  font: 1.06rem/1.72 var(--serif); overflow-wrap: break-word; }

/* ---- banner + front matter (Distill-style) ---- */
.d-banner { display: flex; justify-content: space-between; flex-wrap: wrap; gap: .4rem 1.5rem;
  padding: .75rem 0; border-bottom: 1px solid var(--hair2);
  font: .74rem var(--sans); letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }
.d-banner a { color: inherit; border-bottom: none; }
.d-banner a:hover { color: var(--fg); }
h1.d-title { font: 700 2.1rem/1.22 var(--sans); letter-spacing: -.015em; margin: 2.6rem 0 1.4rem; }
.d-byline { display: grid; grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
  gap: 1rem 2rem; padding: 1.05rem 0 1.15rem; margin: 0 0 1.8rem;
  border-top: 1px solid var(--hair); border-bottom: 1px solid var(--hair);
  font: .92rem/1.5 var(--sans); }
.d-byline .label { display: block; font-size: .68rem; letter-spacing: .13em;
  text-transform: uppercase; color: var(--faint); margin-bottom: .2rem; }

/* ---- headings ---- */
h2 { font: 600 1.42rem/1.3 var(--sans); letter-spacing: -.01em;
  margin: 3rem 0 1rem; padding-bottom: .4rem; border-bottom: 1px solid var(--hair2); }
h3 { font: 600 1.1rem/1.35 var(--sans); margin: 2.2rem 0 .7rem; }

/* ---- links: quiet, Distill-style hairline underline ---- */
a { color: inherit; text-decoration: none; border-bottom: 1px solid var(--underline); }
a:hover { border-bottom-color: currentColor; }

/* ---- notes / quotes ---- */
blockquote { margin: 1.7rem 0; padding: 1rem 1.3rem; background: var(--note-bg);
  border: 1px solid var(--note-bd); border-radius: 10px;
  font: .93rem/1.65 var(--sans); }
blockquote p { margin: .4rem 0; }

/* ---- code + math ---- */
code { font: .82em var(--mono); background: var(--code-bg);
  padding: .12em .32em; border-radius: 4px; }
pre { overflow-x: auto; padding: .95rem 1.15rem; background: var(--code-bg);
  border-radius: 10px; font-size: .85rem; line-height: 1.55; }
pre code { background: none; padding: 0; font-size: 1em; }
math { font-size: 1.06em; }
math[display="block"] { display: block; margin: 1.1rem 0; overflow-x: auto; }

/* ---- tables: sans, horizontal hairlines only ---- */
table { display: block; max-width: 100%; overflow-x: auto; border-collapse: collapse;
  font: .84rem/1.5 var(--sans); margin: 1.5rem 0; }
th, td { padding: .38rem .75rem; border-bottom: 1px solid var(--hair2);
  text-align: left; white-space: nowrap; }
thead th { border-bottom: 1px solid var(--hair); font-weight: 600; }
table a { border-bottom: none; }

/* ---- figures + captions ---- */
img { max-width: 100%; height: auto; display: block; margin: 2rem auto .8rem; }
p:has(> img:only-child) { margin: 0; }
p:has(> img:only-child) + p:has(> em:only-child) { margin: 0 auto 2rem;
  max-width: 38rem; font: .88rem/1.55 var(--sans); color: var(--muted); }

/* ---- TOC: boxed in-flow; docks to the left margin on wide screens ---- */
#TOC { margin: 2rem 0; padding: 1.1rem 1.4rem; border: 1px solid var(--hair2);
  border-radius: 10px; font: .9rem/1.55 var(--sans); }
#TOC h2, #toc-title { font: 600 .72rem var(--sans); letter-spacing: .13em;
  text-transform: uppercase; color: var(--faint);
  margin: 0 0 .55rem; padding: 0; border: none; }
#TOC ul { list-style: none; margin: 0; padding-left: 0; }
#TOC ul ul { padding-left: 1rem; }
#TOC li { margin: .18rem 0; }
#TOC a { border-bottom: none; color: var(--muted); }
#TOC a:hover { color: var(--fg); }
@media (min-width: 1420px) {
  #TOC { position: fixed; top: 3.4rem; left: max(1.2rem, calc(50vw - 22rem - 17rem));
    width: 14rem; max-height: calc(100vh - 6.5rem); overflow-y: auto;
    border: none; border-radius: 0; padding: 0 .4rem 0 0; font-size: .8rem; }
}

hr { border: none; border-top: 1px solid var(--hair); margin: 2.6rem 0; }
footer.modelo { margin-top: 3.5rem; padding-top: 1.2rem; border-top: 1px solid var(--hair);
  font: .85rem/1.6 var(--sans); color: var(--muted); }

@media print {
  body { max-width: none; font-size: 10pt; }
  .d-banner { display: none; }
  #TOC { position: static; width: auto; max-height: none; border: 1px solid var(--hair2);
    border-radius: 10px; padding: 1rem 1.3rem; }
  a { border-bottom: none; color: inherit; }
}
</style>
EOF

# ---------------------------------------------------------------- pt-BR head
cat > "$TMP/head.pt.html" <<EOF
<meta name="description" content="$DESC_PT">
<meta name="citation_title" content="$TITLE_PT">
<meta name="citation_author" content="Lessa Bernardineli, Danilo">
<meta name="citation_publication_date" content="2026/07">
<meta name="citation_language" content="pt">
<meta name="citation_technical_report_institution" content="Pedal Hidrográfico">
<meta name="citation_pdf_url" content="$BASE/artigo.pdf">
<link rel="canonical" href="$BASE/">
<link rel="alternate" hreflang="pt-BR" href="$BASE/">
<link rel="alternate" hreflang="en" href="$BASE/en.html">
<link rel="alternate" hreflang="x-default" href="$BASE/">
<link rel="icon" href="/favicon.ico">
<meta property="og:type" content="article">
<meta property="og:title" content="$TITLE_PT">
<meta property="og:description" content="$DESC_PT">
<meta property="og:url" content="$BASE/">
<meta property="og:locale" content="pt_BR">
<script type="application/ld+json">
{ "@context": "https://schema.org", "@type": "ScholarlyArticle",
  "headline": "$TITLE_PT",
  "author": { "@type": "Person", "name": "Danilo Lessa Bernardineli" },
  "publisher": { "@type": "Organization", "name": "Pedal Hidrográfico", "url": "https://pedalhidrografi.co" },
  "datePublished": "2026-07-09", "inLanguage": "pt-BR",
  "url": "$BASE/",
  "sameAs": "https://github.com/danlessa/bicycling-energy-model",
  "license": "https://creativecommons.org/licenses/by/4.0/",
  "encoding": { "@type": "MediaObject", "contentUrl": "$BASE/artigo.pdf", "encodingFormat": "application/pdf" } }
</script>
EOF

# ---------------------------------------------------------------- EN head
cat > "$TMP/head.en.html" <<EOF
<meta name="description" content="$DESC_EN">
<meta name="citation_title" content="$TITLE_EN">
<meta name="citation_author" content="Lessa Bernardineli, Danilo">
<meta name="citation_publication_date" content="2026/07">
<meta name="citation_language" content="en">
<meta name="citation_technical_report_institution" content="Pedal Hidrográfico">
<meta name="citation_pdf_url" content="$BASE/paper.pdf">
<link rel="canonical" href="$BASE/en.html">
<link rel="alternate" hreflang="pt-BR" href="$BASE/">
<link rel="alternate" hreflang="en" href="$BASE/en.html">
<link rel="alternate" hreflang="x-default" href="$BASE/">
<link rel="icon" href="/favicon.ico">
<meta property="og:type" content="article">
<meta property="og:title" content="$TITLE_EN">
<meta property="og:description" content="$DESC_EN">
<meta property="og:url" content="$BASE/en.html">
<meta property="og:locale" content="en">
<script type="application/ld+json">
{ "@context": "https://schema.org", "@type": "ScholarlyArticle",
  "headline": "$TITLE_EN",
  "author": { "@type": "Person", "name": "Danilo Lessa Bernardineli" },
  "publisher": { "@type": "Organization", "name": "Pedal Hidrográfico", "url": "https://pedalhidrografi.co" },
  "datePublished": "2026-07-09", "inLanguage": "en",
  "url": "$BASE/en.html",
  "sameAs": "https://github.com/danlessa/bicycling-energy-model",
  "license": "https://creativecommons.org/licenses/by/4.0/",
  "encoding": { "@type": "MediaObject", "contentUrl": "$BASE/paper.pdf", "encodingFormat": "application/pdf" } }
</script>
EOF

# ------------------------------------------- banner + title block + footers
cat > "$TMP/front.pt.html" <<EOF
<div class="d-banner"><span><a href="https://simujaules.pedalhidrografi.co/">Simujaules</a> · Pesquisa do Pedal Hidrográfico</span>
<span><a href="en.html" hreflang="en">English</a> · <a href="artigo.pdf">PDF</a></span></div>
<h1 class="d-title">$TITLE_PT</h1>
<div class="d-byline">
  <div><span class="label">Autor</span> Danilo Lessa Bernardineli</div>
  <div><span class="label">Afiliação</span> <a href="https://pedalhidrografi.co">Pedal Hidrográfico</a>, São Paulo</div>
  <div><span class="label">Publicado</span> 9 de julho de 2026 · v1.0</div>
  <div><span class="label">Recursos</span> <a href="artigo.pdf">PDF</a> · <a href="https://github.com/danlessa/bicycling-energy-model">Código e dados</a></div>
</div>
EOF
cat > "$TMP/front.en.html" <<EOF
<div class="d-banner"><span><a href="https://simujaules.pedalhidrografi.co/">Simujaules</a> · Pedal Hidrográfico Research</span>
<span><a href="./" hreflang="pt-BR">Português</a> · <a href="paper.pdf">PDF</a></span></div>
<h1 class="d-title">$TITLE_EN</h1>
<div class="d-byline">
  <div><span class="label">Author</span> Danilo Lessa Bernardineli</div>
  <div><span class="label">Affiliation</span> <a href="https://pedalhidrografi.co">Pedal Hidrográfico</a>, São Paulo</div>
  <div><span class="label">Published</span> July 9, 2026 · v1.0</div>
  <div><span class="label">Resources</span> <a href="paper.pdf">PDF</a> · <a href="https://github.com/danlessa/bicycling-energy-model">Code &amp; data</a></div>
</div>
EOF
cat > "$TMP/foot.pt.html" <<'EOF'
<footer class="modelo"><p>© 2026 Danilo Lessa Bernardineli — texto sob licença
<a href="https://creativecommons.org/licenses/by/4.0/deed.pt-br">CC BY 4.0</a>.
Gerado de <a href="https://github.com/danlessa/bicycling-energy-model"><code>article-draft.pt-BR.md</code></a>
por <code>research/build-modelo.sh</code>; a proveniência das análises está no
<a href="https://github.com/danlessa/bicycling-energy-model/blob/main/research/MODEL_COMPARISON_JOURNAL.md">journal do repositório</a>.
Parte da pesquisa do <a href="https://pedalhidrografi.co">Pedal Hidrográfico</a> — <em>seguir as águas</em>.</p></footer>
EOF
cat > "$TMP/foot.en.html" <<'EOF'
<footer class="modelo"><p>© 2026 Danilo Lessa Bernardineli — text licensed
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.
Generated from <a href="https://github.com/danlessa/bicycling-energy-model"><code>article-draft.md</code></a>
by <code>research/build-modelo.sh</code>; analysis provenance lives in the
<a href="https://github.com/danlessa/bicycling-energy-model/blob/main/research/MODEL_COMPARISON_JOURNAL.md">repository journal</a>.
Part of the <a href="https://pedalhidrografi.co">Pedal Hidrográfico</a> research — <em>seguir as águas</em>.</p></footer>
EOF

# ---------------------------------------------------------------- build HTML
build () { # $1 src.md  $2 out.html  $3 lang  $4 pagetitle  $5 toc-title  $6 front  $7 foot
  # Strip the markdown's own first H1 — the injected title block replaces it
  # (and keeps it out of the TOC). BSD-awk-safe (macOS sed lacks GNU's 0,/re/).
  awk '!d && /^# / { d=1; next } { print }' "$1" > "$TMP/src.md"
  # -implicit_figures: keep images as plain <p><img></p> so the following
  # *Figure N…* emphasis paragraph is the single styled caption (no duplicate
  # figcaption from the alt text).
  pandoc "$TMP/src.md" -f markdown-implicit_figures -t html5 --standalone --mathml \
    --toc --toc-depth=2 -V toc-title="$5" \
    -M pagetitle="$4" -M lang="$3" -M document-css=false \
    --include-in-header="$TMP/style.html" --include-in-header="$TMP/$6" \
    --include-before-body="$TMP/front.$7.html" --include-after-body="$TMP/foot.$7.html" \
    -o "$OUT/$2"
  echo ">> built $2 ($(du -h "$OUT/$2" | cut -f1 | tr -d ' '))"
}
build article-draft.pt-BR.md index.html pt-BR "$TITLE_PT" "Sumário"  head.pt.html pt
build article-draft.md       en.html    en    "$TITLE_EN" "Contents" head.en.html en

# ---------------------------------------------------------------- figs + PDF
cp figs/fig*.svg "$OUT/figs/"
echo ">> copied $(ls "$OUT"/figs/*.svg | wc -l | tr -d ' ') figures"

pdf () { # $1 in.html  $2 out.pdf
  "$CHROME" --headless --disable-gpu --no-pdf-header-footer \
    --print-to-pdf="$OUT/$2" "file://$(cd "$OUT" && pwd)/$1" 2>/dev/null
  echo ">> printed $2 ($(du -h "$OUT/$2" | cut -f1 | tr -d ' '))"
}
pdf index.html artigo.pdf
pdf en.html    paper.pdf

echo ">> done → $OUT"
