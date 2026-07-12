// /modelo/ page interactions — vanilla JS, progressive enhancement (the page
// reads fine with JS off). Injected inline by build-modelo.sh.
//
//  1. Citations [Author 2026] → links to the reference entry, with a
//     Distill-style hover card carrying the full reference.
//  2. §-cross-references → anchor links, hover card shows the section title
//     and its opening lines. "journal Entry N" → link to the repo journal.
//  3. Sortable tables (numeric-aware, pt-BR decimal commas handled).
//  4. Figures: click for a lossless SVG lightbox (Esc/click to close).
//  5. Scrollspy: active-section highlighting in the TOC (subsections expand
//     for the active section) + a right-edge minimap rail with proportional
//     section segments, reading progress, hover labels, click-to-jump.
//  6. Hover anchors (#) on headings.
(function () {
  'use strict';
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var canHover = window.matchMedia('(hover: hover)').matches;
  var JOURNAL_URL = 'https://github.com/danlessa/bicycling-energy-model/blob/main/research/MODEL_COMPARISON_JOURNAL.md';

  /* ---------------- 1+2. reference map, section map, text-node linking */
  var refMap = {};                       // "Martin et al. 1998" -> <li>
  var refsHeading = $$('h2').filter(function (h) { return /^refer/i.test(h.id || ''); })[0];
  if (refsHeading) {
    var el = refsHeading.nextElementSibling;
    while (el && el.tagName !== 'UL') el = el.nextElementSibling;
    if (el) $$('li', el).forEach(function (li, i) {
      var m = li.textContent.match(/^\s*\[([^\]]+)\]/);
      if (m) { if (!li.id) li.id = 'ref-' + (i + 1); refMap[m[1].trim()] = li; }
    });
  }
  var secMap = {};                       // "8.9" -> heading element
  $$('h2[id], h3[id]').forEach(function (h) {
    var m = h.textContent.match(/^(\d+(?:\.\d+)?)[.\s]/);
    if (m) secMap[m[1]] = h;
  });

  var SKIP = { A: 1, PRE: 1, CODE: 1, SCRIPT: 1, STYLE: 1, MATH: 1, FIGURE: 1, NAV: 1, H1: 1 };
  function skippable(node) {
    for (var p = node.parentNode; p && p !== document.body; p = p.parentNode) {
      if (SKIP[p.tagName] || p.id === 'TOC' || p.id === 'hovercard' ||
          (p.classList && (p.classList.contains('d-byline') || p.classList.contains('d-banner')))) return true;
      if (refsHeading && p.tagName === 'UL' && p.previousElementSibling === refsHeading) return true;
    }
    return false;
  }

  var LINK_RE = /\[([^\[\]]{2,90})\]|§\s?(\d+(?:\.\d+)?)|((?:journal Entry|Entry|[Ee]ntradas?)\s+(\d+))/g;
  function linkTextNode(node) {
    var text = node.nodeValue, m, last = 0, frag = null;
    LINK_RE.lastIndex = 0;
    while ((m = LINK_RE.exec(text)) !== null) {
      var rep = null;
      if (m[1] !== undefined) {                       // [citation; citation]
        var parts = m[1].split(';').map(function (s) { return s.trim(); });
        if (parts.some(function (p) { return refMap[p]; })) {
          rep = document.createDocumentFragment();
          rep.appendChild(document.createTextNode('['));
          parts.forEach(function (p, i) {
            if (i) rep.appendChild(document.createTextNode('; '));
            if (refMap[p]) {
              var a = document.createElement('a');
              a.className = 'cite'; a.href = '#' + refMap[p].id; a.textContent = p;
              rep.appendChild(a);
            } else rep.appendChild(document.createTextNode(p));
          });
          rep.appendChild(document.createTextNode(']'));
        }
      } else if (m[2] !== undefined && secMap[m[2]]) { // §8.9
        rep = document.createElement('a');
        rep.className = 'secref'; rep.href = '#' + secMap[m[2]].id; rep.textContent = m[0];
      } else if (m[4] !== undefined && m[3].match(/Entry|ntrada/)) { // journal entries
        rep = document.createElement('a');
        rep.className = 'entryref'; rep.href = JOURNAL_URL;
        rep.target = '_blank'; rep.rel = 'noopener'; rep.textContent = m[0];
      }
      if (rep) {
        frag = frag || document.createDocumentFragment();
        frag.appendChild(document.createTextNode(text.slice(last, m.index)));
        frag.appendChild(rep);
        last = m.index + m[0].length;
      }
    }
    if (frag) {
      frag.appendChild(document.createTextNode(text.slice(last)));
      node.parentNode.replaceChild(frag, node);
    }
  }
  var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null);
  var nodes = [];
  while (walker.nextNode()) {
    var n = walker.currentNode;
    if (n.nodeValue.length > 3 && /[\[§]|Entry|ntrada/.test(n.nodeValue) && !skippable(n)) nodes.push(n);
  }
  nodes.forEach(linkTextNode);

  /* ---------------- hover card */
  var card = document.createElement('div');
  card.id = 'hovercard';
  document.body.appendChild(card);
  var hideT = null;
  function showCard(target, kicker, html) {
    clearTimeout(hideT);
    card.innerHTML = '<span class="hc-kicker">' + kicker + '</span>' + html;
    card.style.display = 'block';
    var r = target.getBoundingClientRect();
    var top = r.top + window.scrollY - card.offsetHeight - 10;
    if (top < window.scrollY + 8) top = r.bottom + window.scrollY + 10;
    var left = Math.min(Math.max(10, r.left + window.scrollX - 40),
      window.scrollX + document.documentElement.clientWidth - card.offsetWidth - 10);
    card.style.top = top + 'px'; card.style.left = left + 'px';
  }
  function hideCardSoon() { hideT = setTimeout(function () { card.style.display = 'none'; }, 220); }
  card.addEventListener('mouseenter', function () { clearTimeout(hideT); });
  card.addEventListener('mouseleave', hideCardSoon);
  function sectionPreview(h) {
    var out = '', el = h.nextElementSibling, chars = 0;
    while (el && chars < 220 && !/^H[1-3]$/.test(el.tagName)) {
      if (el.tagName === 'P') { out += el.textContent + ' '; chars = out.length; }
      el = el.nextElementSibling;
    }
    out = out.trim();
    if (out.length > 220) out = out.slice(0, 220).replace(/\s\S*$/, '') + ' …';
    return out;
  }
  if (canHover) {
    $$('a.cite').forEach(function (a) {
      a.addEventListener('mouseenter', function () {
        var li = refMap[a.textContent.trim()];
        if (li) showCard(a, a.textContent, li.innerHTML);
      });
      a.addEventListener('mouseleave', hideCardSoon);
    });
    $$('a.secref').forEach(function (a) {
      a.addEventListener('mouseenter', function () {
        var h = document.getElementById(a.getAttribute('href').slice(1));
        if (h) showCard(a, a.textContent,
          '<strong>' + h.textContent + '</strong><br>' + sectionPreview(h));
      });
      a.addEventListener('mouseleave', hideCardSoon);
    });
  }

  /* ---------------- 3. sortable tables */
  $$('table').forEach(function (t) {
    var thead = t.tHead, tbody = t.tBodies[0];
    if (!thead || !tbody || tbody.rows.length < 3) return;
    t.classList.add('sortable');
    var original = $$('tr', tbody);
    function cellVal(row, i) {
      var c = row.cells[i]; if (!c) return null;
      var m = c.textContent.replace(/−/g, '-').match(/-?\d+(?:[.,]\d+)?/);
      return m ? parseFloat(m[0].replace(',', '.')) : null;
    }
    $$('th', thead).forEach(function (th, i) {
      th.tabIndex = 0;
      function sort() {
        var dir = th.dataset.dir === 'asc' ? 'desc' : 'asc';
        $$('th', thead).forEach(function (o) { delete o.dataset.dir; o.removeAttribute('aria-sort'); });
        th.dataset.dir = dir;
        th.setAttribute('aria-sort', dir === 'asc' ? 'ascending' : 'descending');
        var rows = $$('tr', tbody);
        rows.sort(function (a, b) {
          var x = cellVal(a, i), y = cellVal(b, i);
          if (x === null && y === null) return 0;
          if (x === null) return 1;
          if (y === null) return -1;
          return dir === 'asc' ? x - y : y - x;
        });
        rows.forEach(function (r) { tbody.appendChild(r); });
      }
      th.addEventListener('click', sort);
      th.addEventListener('keydown', function (e) { if (e.key === 'Enter') sort(); });
      th.title = 'Ordenar / sort';
    });
  });

  /* ---------------- 4. figures: lightbox, point tooltips, legend toggles */
  var lb = document.createElement('div');
  lb.id = 'lightbox';
  document.body.appendChild(lb);
  function closeLb() { lb.classList.remove('open'); lb.innerHTML = ''; }
  $$('figure.fig').forEach(function (fig) {
    fig.addEventListener('click', function (e) {
      if (e.target.closest('.lg') || e.target.closest('[data-tip]')) return;
      var svg = $('svg', fig);
      if (!svg) return;
      lb.innerHTML = '';
      lb.appendChild(svg.cloneNode(true));
      lb.classList.add('open');
    });
  });
  lb.addEventListener('click', function (e) {
    if (e.target.closest('.lg') || e.target.closest('[data-tip]')) return;
    closeLb();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeLb(); });

  // data-tip tooltips (delegated, so they also work inside the lightbox clone)
  var figtip = document.createElement('div');
  figtip.id = 'figtip';
  document.body.appendChild(figtip);
  document.addEventListener('mouseover', function (e) {
    var t = e.target.closest && e.target.closest('[data-tip]');
    if (t) { figtip.textContent = t.getAttribute('data-tip'); figtip.style.display = 'block'; }
    else figtip.style.display = 'none';
  });
  document.addEventListener('mousemove', function (e) {
    if (figtip.style.display !== 'block') return;
    var x = e.clientX + 14, y = e.clientY + 14;
    if (x + figtip.offsetWidth > document.documentElement.clientWidth - 8)
      x = e.clientX - figtip.offsetWidth - 10;
    if (y + figtip.offsetHeight > document.documentElement.clientHeight - 8)
      y = e.clientY - figtip.offsetHeight - 10;
    figtip.style.left = x + 'px'; figtip.style.top = y + 'px';
  }, { passive: true });

  // legend series toggling (delegated; works in figures and in the lightbox)
  document.addEventListener('click', function (e) {
    var lg = e.target.closest && e.target.closest('.lg[data-series]');
    if (!lg) return;
    var svg = lg.closest('svg');
    var off = lg.classList.toggle('off');
    $$('.' + lg.dataset.series, svg).forEach(function (el) {
      el.classList.toggle('soff', off);
    });
  });

  /* ---------------- 5. scrollspy + minimap */
  var headings = $$('h2[id], h3[id]').filter(function (h) {
    return h.id !== 'toc-title' && !h.closest('#TOC');
  });
  var tocLinks = {};
  $$('#TOC a[href^="#"]').forEach(function (a) { tocLinks[a.getAttribute('href').slice(1)] = a; });

  var mm = document.createElement('div');
  mm.id = 'minimap';
  mm.setAttribute('aria-hidden', 'true');
  var h2s = headings.filter(function (h) { return h.tagName === 'H2'; });
  var segs = [];
  h2s.forEach(function (h, i) {
    var seg = document.createElement('a');
    seg.className = 'seg'; seg.href = '#' + h.id;
    seg.dataset.label = h.textContent.trim();
    var top = h.offsetTop;
    var next = h2s[i + 1] ? h2s[i + 1].offsetTop : document.body.scrollHeight;
    seg.style.flexGrow = Math.max(1, next - top);
    mm.appendChild(seg);
    segs.push({ el: seg, top: top });
  });
  if (segs.length) document.body.appendChild(mm);

  var ticking = false;
  function spy() {
    ticking = false;
    var y = window.scrollY + 130;
    var cur = null;
    for (var i = 0; i < headings.length; i++) {
      if (headings[i].offsetTop <= y) cur = headings[i]; else break;
    }
    $$('#TOC a.active').forEach(function (a) { a.classList.remove('active'); });
    $$('#TOC li.open').forEach(function (li) { li.classList.remove('open'); });
    if (cur) {
      var link = tocLinks[cur.id];
      if (link) {
        link.classList.add('active');
        for (var li = link.closest('li'); li; li = li.parentElement.closest('li')) {
          li.classList.add('open');
          var pl = $('a', li); // section-level link stays highlighted too
          if (pl && pl !== link) pl.classList.add('active');
        }
      }
    }
    var curH2 = null;
    for (var j = 0; j < h2s.length; j++) { if (h2s[j].offsetTop <= y) curH2 = j; else break; }
    segs.forEach(function (s, k) {
      s.el.classList.toggle('active', k === curH2);
      s.el.classList.toggle('done', curH2 !== null && k < curH2);
    });
  }
  window.addEventListener('scroll', function () {
    if (!ticking) { ticking = true; requestAnimationFrame(spy); }
  }, { passive: true });
  spy();

  /* ---------------- 6. heading anchors */
  headings.forEach(function (h) {
    var a = document.createElement('a');
    a.className = 'hanchor'; a.href = '#' + h.id; a.textContent = '#';
    a.setAttribute('aria-label', 'link');
    h.appendChild(a);
  });
})();
