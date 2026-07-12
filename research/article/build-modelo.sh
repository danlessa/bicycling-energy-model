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
# Interactivity (modelo-assets/, all inlined, vanilla JS, no-JS degrades
# gracefully): code-span pseudo-math rendered as real math (math.lua),
# citation links with Distill-style hover cards, §-cross-reference links with
# section-preview cards, sortable tables, inline-SVG figures with hoverable
# points + a lossless lightbox, TOC scrollspy (3 levels), and a right-edge
# minimap rail with reading progress.
#
# Requires: pandoc (tested 3.1) and Google Chrome.
# Usage: ./build-modelo.sh [output-dir]     default: ../../simujaules/modelo
set -euo pipefail
cd "$(dirname "$0")"

OUT="${1:-../../../simujaules/modelo}"
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
BASE="https://simujaules.pedalhidrografi.co/modelo"

# DOI — the Zenodo deposit's reserved DOI (env MODELO_DOI overrides). It
# drives the citation_doi meta tag, the DOI byline entry, and the Plaudit
# open-endorsement widget (https://plaudit.pub — ORCID-signed public
# endorsements; its embed resolves the work via citation_doi). NB: while the
# Zenodo deposit stays a DRAFT the DOI is reserved but does not resolve at
# doi.org yet — it goes live when the deposit is published. The Plaudit embed
# is the page's one external script — a hosted service by design, deliberately
# excepted from the self-contained rule. Set empty to omit all of it.
DOI="${MODELO_DOI:-10.5281/zenodo.21282165}"
DOI_META=""; DOI_ITEM=""; PLAUDIT_PT=""; PLAUDIT_EN=""
if [[ -n "$DOI" ]]; then
  DOI_META="<meta name=\"citation_doi\" content=\"$DOI\">"
  DOI_ITEM="<div><span class=\"label\">DOI</span> <a href=\"https://doi.org/$DOI\">$DOI</a></div>"
  PLAUDIT_PT='<div class="plaudit-box"><span class="label">Endossos abertos (ORCID · Plaudit)</span><script src="https://plaudit.pub/embed/endorsements.js" crossorigin="anonymous" async></script></div>'
  PLAUDIT_EN='<div class="plaudit-box"><span class="label">Open endorsements (ORCID · Plaudit)</span><script src="https://plaudit.pub/embed/endorsements.js" crossorigin="anonymous" async></script></div>'
fi

TITLE_PT="Energia de Rotas de Bicicleta em Forma Fechada: Duas Correções, um Offset de Recuperação na Descida que se Transfere entre Ciclistas, e um Dual Energia↔Tempo"
TITLE_EN="Bicycle Route Energy in Closed Form: Two Corrections, a Descent-Recovery Offset That Transfers Across Riders, and an Energy↔Time Dual"
DESC_PT="Uma lei em forma fechada para a energia (kJ) de pedalar uma rota, validada contra ~1.400 pedaladas com medidor de potência — working paper do Pedal Hidrográfico."
DESC_EN="A closed-form law for the energy (kJ) of cycling a route, validated against ~1,400 power-meter rides — a Pedal Hidrográfico working paper."

mkdir -p "$OUT/figs"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# ------------------------------------------------- style + script (assets)
# CSS and JS live in modelo-assets/ (style.css, app.js); the math/SVG pandoc
# filter is modelo-assets/math.lua. All are inlined into the pages.
{ printf '<style>\n'; cat modelo-assets/style.css; printf '</style>\n'; } > "$TMP/style.html"
{ printf '<script>\n'; cat modelo-assets/app.js; printf '</script>\n'; } > "$TMP/app.html"

# ---------------------------------------------------------------- pt-BR head
cat > "$TMP/head.pt.html" <<EOF
<meta name="description" content="$DESC_PT">
<meta name="citation_title" content="$TITLE_PT">
<meta name="citation_author" content="Lessa Bernardineli, Danilo">
<meta name="citation_publication_date" content="2026/07">
<meta name="citation_language" content="pt">
<meta name="citation_technical_report_institution" content="Pedal Hidrográfico">
<meta name="citation_pdf_url" content="$BASE/artigo.pdf">
$DOI_META
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
$DOI_META
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
  $DOI_ITEM
</div>
$PLAUDIT_PT
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
  $DOI_ITEM
</div>
$PLAUDIT_EN
EOF
cat > "$TMP/foot.pt.html" <<'EOF'
<footer class="modelo"><p>© 2026 Danilo Lessa Bernardineli — texto sob licença
<a href="https://creativecommons.org/licenses/by/4.0/deed.pt-br">CC BY 4.0</a>.
Gerado de <a href="https://github.com/danlessa/bicycling-energy-model"><code>article-draft.pt-BR.md</code></a>
por <code>research/article/build-modelo.sh</code>; a proveniência das análises está no
<a href="https://github.com/danlessa/bicycling-energy-model/blob/main/research/notes/MODEL_COMPARISON_JOURNAL.md">journal do repositório</a>.
Parte da pesquisa do <a href="https://pedalhidrografi.co">Pedal Hidrográfico</a> — <em>seguir as águas</em>.</p></footer>
EOF
cat > "$TMP/foot.en.html" <<'EOF'
<footer class="modelo"><p>© 2026 Danilo Lessa Bernardineli — text licensed
<a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.
Generated from <a href="https://github.com/danlessa/bicycling-energy-model"><code>article-draft.md</code></a>
by <code>research/article/build-modelo.sh</code>; analysis provenance lives in the
<a href="https://github.com/danlessa/bicycling-energy-model/blob/main/research/notes/MODEL_COMPARISON_JOURNAL.md">repository journal</a>.
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
    --lua-filter=modelo-assets/math.lua \
    --toc --toc-depth=3 -V toc-title="$5" \
    -M pagetitle="$4" -M lang="$3" -M document-css=false \
    --include-in-header="$TMP/style.html" --include-in-header="$TMP/$6" \
    --include-before-body="$TMP/front.$7.html" \
    --include-after-body="$TMP/foot.$7.html" --include-after-body="$TMP/app.html" \
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
