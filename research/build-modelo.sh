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
:root { color-scheme: light dark; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0 auto; max-width: 46rem; padding: 1.5rem 1.2rem 4rem;
  font: 1rem/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  color: #1a1a1a; background: #fffefc; overflow-wrap: break-word; }
h1 { font-size: 1.55rem; line-height: 1.25; margin: 1.2rem 0 .8rem; }
h2 { font-size: 1.25rem; margin: 2.2rem 0 .6rem; }
h3 { font-size: 1.05rem; margin: 1.8rem 0 .5rem; }
a { color: #0b6bcb; }
img { max-width: 100%; height: auto; }
figure { margin: 1.4rem 0; } figcaption, em:has(> img) { font-size: .92rem; }
blockquote { margin: 1.2rem 0; padding: .6rem 1rem; border-left: 4px solid #d0a54a;
  background: rgba(208,165,74,.09); font-size: .95rem; }
code { font: .88em ui-monospace, SFMono-Regular, Menlo, monospace;
  background: rgba(120,120,120,.12); padding: .1em .28em; border-radius: 4px; }
pre { overflow-x: auto; padding: .8rem 1rem; background: rgba(120,120,120,.1);
  border-radius: 8px; } pre code { background: none; padding: 0; }
table { display: block; max-width: 100%; overflow-x: auto; border-collapse: collapse;
  font-size: .92rem; margin: 1.2rem 0; }
th, td { padding: .3rem .6rem; border-bottom: 1px solid rgba(120,120,120,.35);
  text-align: left; white-space: nowrap; }
thead th { border-bottom: 2px solid rgba(120,120,120,.6); }
math { font-size: 1.05em; }
#TOC { margin: 1.6rem 0; padding: .8rem 1.2rem; border: 1px solid rgba(120,120,120,.3);
  border-radius: 10px; font-size: .93rem; }
#TOC ul { margin: .2rem 0; padding-left: 1.1rem; list-style: none; }
#TOC > ul { padding-left: 0; }
.lang-nav { display: flex; gap: 1rem; justify-content: space-between;
  font-size: .9rem; padding: .5rem 0 1rem; border-bottom: 1px solid rgba(120,120,120,.3); }
footer.modelo { margin-top: 3rem; padding-top: 1rem; font-size: .88rem;
  border-top: 1px solid rgba(120,120,120,.3); }
@media (prefers-color-scheme: dark) {
  body { color: #e6e2da; background: #14130f; }
  a { color: #6fb3f2; }
}
@media print {
  body { max-width: none; font-size: 10.5pt; }
  .lang-nav { display: none; }
  a { color: inherit; text-decoration: none; }
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

# ------------------------------------------------------------ nav + footers
cat > "$TMP/nav.pt.html" <<'EOF'
<nav class="lang-nav"><span><a href="https://simujaules.pedalhidrografi.co/">← Simujaules</a></span>
<span><a href="en.html" hreflang="en">English version</a> · <a href="artigo.pdf">PDF</a></span></nav>
EOF
cat > "$TMP/nav.en.html" <<'EOF'
<nav class="lang-nav"><span><a href="https://simujaules.pedalhidrografi.co/">← Simujaules</a></span>
<span><a href="./" hreflang="pt-BR">Versão em português</a> · <a href="paper.pdf">PDF</a></span></nav>
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
build () { # $1 src.md  $2 out.html  $3 lang  $4 pagetitle  $5 toc-title  $6 head  $7 nav  $8 foot
  pandoc "$1" -f markdown -t html5 --standalone --mathml \
    --toc --toc-depth=2 -V toc-title="$5" \
    -M pagetitle="$4" -M lang="$3" -M document-css=false \
    --include-in-header="$TMP/style.html" --include-in-header="$TMP/$6" \
    --include-before-body="$TMP/$7" --include-after-body="$TMP/$8" \
    -o "$OUT/$2"
  echo ">> built $2 ($(du -h "$OUT/$2" | cut -f1 | tr -d ' '))"
}
build article-draft.pt-BR.md index.html pt-BR "$TITLE_PT" "Sumário"  head.pt.html nav.pt.html foot.pt.html
build article-draft.md       en.html    en    "$TITLE_EN" "Contents" head.en.html nav.en.html foot.en.html

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
