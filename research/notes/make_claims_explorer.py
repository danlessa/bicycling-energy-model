#!/usr/bin/env python3
"""make_claims_explorer.py — build the interactive claims-graph explorer.

Reads research/notes/claims.ttl (the claims–questions–evidence graph, all 24
journal entries, widely-used vocabularies only) and writes
research/notes/claims-explorer.html: a self-contained, no-dependency page
(vanilla JS + canvas force layout) for browsing the graph — questions, claims,
hypotheses, evidence nodes, runs, plans and artifacts, with the CiTO/PROV/
schema.org relations between them. PT labels, light+dark themes, no CDN.

Deterministic: same claims.ttl → byte-identical HTML (layout is seeded
client-side).

Needs rdflib (the repo's sanctioned RDF validation tool).
Usage: python3 research/notes/make_claims_explorer.py
"""

import json
import os
import re

import rdflib
from rdflib.namespace import RDF

HERE = os.path.dirname(os.path.abspath(__file__))
TTL = os.path.join(HERE, "claims.ttl")
OUT = os.path.join(HERE, "claims-explorer.html")

SCHEMA = rdflib.Namespace("http://schema.org/")
CITO = rdflib.Namespace("http://purl.org/spar/cito/")
PROV = rdflib.Namespace("http://www.w3.org/ns/prov#")
PPLAN = rdflib.Namespace("http://purl.org/net/p-plan#")
DCT = rdflib.Namespace("http://purl.org/dc/terms/")
RDFS = rdflib.RDFS
BASE = "https://danlessa.github.io/bicycling-energy-model/claims#"

# predicate → edge group (drawn style) — everything else is ignored
EDGE_GROUPS = {
    CITO.supports: "sup",
    CITO.disputes: "dis",
    CITO.corrects: "meta",
    CITO.updates: "meta",
    CITO.qualifies: "meta",
    CITO.extends: "meta",
    CITO.citesAsEvidence: "cites",
    SCHEMA.about: "about",
    PROV.used: "prov",
    PROV.generated: "prov",
    PROV.wasGeneratedBy: "prov",
    PPLAN.correspondsToStep: "prov",
    DCT.isPartOf: "ref",
    DCT.source: "ref",
}


def local(term):
    s = str(term)
    return s[len(BASE):] if s.startswith(BASE) else s.rsplit("/", 1)[-1]


def main():
    g = rdflib.Graph()
    g.parse(TTL)

    nodes, links = {}, []

    def kind_of(s):
        types = set(g.objects(s, RDF.type))
        if SCHEMA.Question in types:
            return "question"
        if PPLAN.Plan in types:
            return "plan"
        if PROV.Activity in types:
            return "run"
        if SCHEMA.Claim in types:
            dt = {str(o) for o in g.objects(s, DCT.type)}
            if "hypothesis" in dt:
                return "hypothesis"
            if re.search(r"_ev\d+$", local(s)):
                return "evidence"
            return "claim"
        if types:
            return "artifact"
        return None

    def add_node(s):
        lid = local(s)
        if lid in nodes:
            return lid
        kind = kind_of(s)
        if kind is None:
            return None
        text = (g.value(s, SCHEMA.text) or g.value(s, SCHEMA.name)
                or g.value(s, RDFS.comment) or "")
        desc = g.value(s, DCT.description) or ""
        m = re.match(r"(?:assert|q|run|plan|hyp|h|entry)(\d+)", lid)
        nodes[lid] = {
            "id": lid, "kind": kind,
            "text": str(text), "desc": str(desc),
            "entry": int(m.group(1)) if m else None,
        }
        return lid

    for s, p, o in g:
        grp = EDGE_GROUPS.get(p)
        if grp is None or isinstance(o, rdflib.Literal):
            continue
        sid, oid = add_node(s), add_node(o)
        if sid and oid:
            links.append({"s": sid, "t": oid, "p": local(p), "g": grp})

    links.sort(key=lambda e: (e["s"], e["t"], e["p"]))
    data = {"nodes": sorted(nodes.values(), key=lambda n: n["id"]),
            "links": links}
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"))

    html = TEMPLATE.replace("__DATA__", payload)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(html)
    print(f"claims-explorer.html: {len(nodes)} nodes, {len(links)} edges")


TEMPLATE = r"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Grafo de afirmações — bicycling-energy-model</title>
<style>
:root {
  --paper:#f6f9f8; --ink:#1d2b30; --muted:#5b7076; --panel:#ecf1f0;
  --line:#d4dedd; --accent:#16717f;
  --c-claim:#4a4fd0; --c-question:#c05a12; --c-process:#159a7e;
  --c-artifact:#b52e84;
}
@media (prefers-color-scheme: dark) {
  :root { --paper:#131a1c; --ink:#d9e4e2; --muted:#8fa5a9; --panel:#1b2427;
    --line:#2c383b; --accent:#56b4c2;
    --c-claim:#6a6fe2; --c-question:#d0691f; --c-process:#18ab8c;
    --c-artifact:#c9459c; }
}
:root[data-theme="dark"] { --paper:#131a1c; --ink:#d9e4e2; --muted:#8fa5a9;
  --panel:#1b2427; --line:#2c383b; --accent:#56b4c2;
  --c-claim:#6a6fe2; --c-question:#d0691f; --c-process:#18ab8c;
  --c-artifact:#c9459c; }
:root[data-theme="light"] { --paper:#f6f9f8; --ink:#1d2b30; --muted:#5b7076;
  --panel:#ecf1f0; --line:#d4dedd; --accent:#16717f;
  --c-claim:#4a4fd0; --c-question:#c05a12; --c-process:#159a7e;
  --c-artifact:#b52e84; }
* { box-sizing:border-box; }
body { margin:0; background:var(--paper); color:var(--ink);
  font:14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  height:100vh; display:flex; flex-direction:column; overflow:hidden; }
header { padding:.7rem 1rem .5rem; border-bottom:1px solid var(--line);
  display:flex; flex-wrap:wrap; gap:.6rem 1.2rem; align-items:baseline; }
header h1 { font:600 1.05rem/1.3 Palatino, "Palatino Linotype", Georgia, serif;
  margin:0; }
header .hint { color:var(--muted); font-size:.75rem; }
#controls { display:flex; flex-wrap:wrap; gap:.4rem .9rem; align-items:center;
  padding:.45rem 1rem; border-bottom:1px solid var(--line); font-size:.78rem; }
#controls label { display:inline-flex; align-items:center; gap:.3rem;
  cursor:pointer; user-select:none; }
#controls input[type=search] { background:var(--panel); color:var(--ink);
  border:1px solid var(--line); border-radius:3px; padding:.25rem .5rem;
  font-size:.8rem; width:14rem; }
#controls input[type=search]:focus-visible,
#controls input[type=checkbox]:focus-visible { outline:2px solid var(--accent);
  outline-offset:1px; }
.sw { display:inline-block; width:.72rem; height:.72rem; border-radius:50%; }
#wrap { flex:1; display:flex; min-height:0; }
#graph { flex:1; min-width:0; position:relative; }
#canvas { position:absolute; inset:0; width:100%; height:100%; cursor:grab; }
#side { width:21rem; max-width:40vw; border-left:1px solid var(--line);
  padding:1rem; overflow-y:auto; display:none; background:var(--panel); }
#side.open { display:block; }
#side h2 { margin:0 0 .2rem; font-size:.95rem;
  font-family:Palatino, Georgia, serif; overflow-wrap:anywhere; }
#side .kind { text-transform:uppercase; letter-spacing:.08em; font-size:.68rem;
  color:var(--accent); }
#side p { font-size:.82rem; margin:.5rem 0; }
#side .desc { color:var(--muted); font-style:italic; }
#side h3 { font-size:.72rem; text-transform:uppercase; letter-spacing:.07em;
  color:var(--muted); margin:1rem 0 .3rem; }
#side li { font-size:.78rem; margin:.15rem 0; overflow-wrap:anywhere; }
#side ul { margin:0; padding-left:1.1rem; }
#side a, #side button.nav { color:var(--accent); background:none; border:none;
  padding:0; font:inherit; cursor:pointer; text-decoration:underline; }
#side .close { float:right; background:none; border:1px solid var(--line);
  border-radius:3px; color:var(--muted); cursor:pointer; font-size:.75rem; }
#tip { position:fixed; pointer-events:none; background:var(--panel);
  border:1px solid var(--line); color:var(--ink); border-radius:4px;
  padding:.4rem .55rem; font-size:.75rem; max-width:22rem; display:none;
  z-index:5; box-shadow:0 2px 8px rgba(0,0,0,.15); }
#tip .id { font-weight:600; }
#tip .t { color:var(--muted); }
kbd { background:var(--panel); border:1px solid var(--line); border-radius:3px;
  padding:0 .25rem; font-size:.7rem; }
</style>
</head>
<body>
<header>
  <h1>Grafo de afirmações — perguntas, evidências e vereditos (Entradas 1–24)</h1>
  <span class="hint">arraste os nós · roda = zoom · clique = detalhes ·
  fundo = mover</span>
</header>
<div id="controls">
  <input id="q" type="search" placeholder="buscar (ex.: assert13, ε, FABDEM)"
    aria-label="Buscar nós">
  <span id="modeSwitch">
    <label><input type="radio" name="mode" value="layers" checked> camadas</label>
    <label><input type="radio" name="mode" value="force"> força</label>
  </span>
  <span id="legend"></span>
  <span class="hint" id="edgeLegend"></span>
</div>
<div id="wrap">
  <div id="graph"><canvas id="canvas" aria-label="Grafo de afirmações"></canvas></div>
  <aside id="side" aria-live="polite"></aside>
</div>
<div id="tip" role="tooltip"></div>
<script>
"use strict";
const DATA = __DATA__;

/* ── model ── */
const KINDS = {
  question:  {c:"--c-question", pt:"pergunta",  shape:"ring",     r:11},
  claim:     {c:"--c-claim",    pt:"afirmação", shape:"circle",   r:12},
  hypothesis:{c:"--c-claim",    pt:"hipótese",  shape:"diamond",  r:11},
  evidence:  {c:"--c-claim",    pt:"evidência", shape:"dot",      r:6},
  run:       {c:"--c-process",  pt:"execução",  shape:"triangle", r:9},
  plan:      {c:"--c-process",  pt:"protocolo", shape:"square",   r:9},
  artifact:  {c:"--c-artifact", pt:"artefato",  shape:"rect",     r:8},
};
const EDGE_PT = {sup:"sustenta", dis:"contesta", meta:"cita (corrige/atualiza/qualifica/estende)",
  cites:"cita como evidência", about:"sobre", prov:"proveniência", ref:"referência"};

/* deterministic PRNG so the initial layout is stable */
let seed = 42;
function rand(){ seed=(seed+0x6D2B79F5)|0; let t=Math.imul(seed^seed>>>15,1|seed);
  t=t+Math.imul(t^t>>>7,61|t)^t; return ((t^t>>>14)>>>0)/4294967296; }

const nodes = DATA.nodes.map(n => ({...n,
  x:(rand()-0.5)*900, y:(rand()-0.5)*700, vx:0, vy:0}));
const byId = Object.fromEntries(nodes.map(n=>[n.id,n]));
const links = DATA.links.map(l => ({...l, a:byId[l.s], b:byId[l.t]}));
nodes.forEach(n => { n.deg = 0; });
links.forEach(l => { l.a.deg++; l.b.deg++; });

/* ── layered layout (default): columns = journal entries, lanes = node kind ── */
const COL = 150;
const LANES = {question:-300, hypothesis:-210, claim:-120, evidence:-20,
  run:70, plan:150};
const LANE_PT = [["perguntas",-300],["hipóteses",-210],["afirmações",-120],
  ["evidências",-20],["execuções",70],["protocolos",150],["artefatos",300]];
function layeredLayout(){
  const groups = {};
  for(const n of nodes){
    if(n.entry==null || !(n.kind in LANES)) continue;
    (groups[n.entry+"|"+n.kind] = groups[n.entry+"|"+n.kind]||[]).push(n);
  }
  for(const key in groups){
    const [e] = key.split("|");
    const arr = groups[key].sort((a,b)=>a.id<b.id?-1:1);
    arr.forEach((n,i)=>{
      n.x = (e-12.5)*COL + (i%2 ? 26 : 0);
      n.y = LANES[n.kind] + i*34 - (arr.length-1)*17;
      n.vx=n.vy=0;
    });
  }
  const rest = nodes.filter(n=>n.entry==null || !(n.kind in LANES));
  for(const n of rest){
    const nb=[];
    for(const l of links){
      if(l.a===n && l.b.entry!=null) nb.push((l.b.entry-12.5)*COL);
      if(l.b===n && l.a.entry!=null) nb.push((l.a.entry-12.5)*COL);
    }
    n._cx = nb.length ? nb.reduce((s,v)=>s+v,0)/nb.length : 0;
  }
  rest.sort((a,b)=>a._cx-b._cx || (a.id<b.id?-1:1));
  rest.forEach((n,i)=>{
    n.x = (rest.length>1 ? (i/(rest.length-1)-0.5) : 0) * 23.5*COL;
    n.y = 260 + (i%3)*75;
    n.vx=n.vy=0;
  });
}

/* ── state ── */
const active = Object.fromEntries(Object.keys(KINDS).map(k=>[k,true]));
let query = "", selected = null, hovered = null, mode = "layers";
let panX = 0, panY = 0, zoom = 1, needsDraw = true;
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

function visible(n){ return active[n.kind] && n; }
function matches(n){ if(!query) return true;
  return (n.id + " " + n.text + " " + n.desc).toLowerCase().includes(query); }

/* ── simulation ── */
function tick(){
  const GRAV = 0.002, REP = 1300, LINK = 0.14, LEN = 65, VCAP = 5;
  for(let i=0;i<nodes.length;i++){
    const a = nodes[i]; if(!active[a.kind]) continue;
    a.vx -= a.x*GRAV; a.vy -= a.y*GRAV;
    for(let j=i+1;j<nodes.length;j++){
      const b = nodes[j]; if(!active[b.kind]) continue;
      let dx=a.x-b.x, dy=a.y-b.y, d2=dx*dx+dy*dy+150;
      const f = REP/d2;
      dx*=f; dy*=f; a.vx+=dx; a.vy+=dy; b.vx-=dx; b.vy-=dy;
    }
  }
  for(const l of links){
    if(!active[l.a.kind]||!active[l.b.kind]) continue;
    const dx=l.b.x-l.a.x, dy=l.b.y-l.a.y, d=Math.sqrt(dx*dx+dy*dy)||1;
    const f = LINK*(d-LEN)/d;
    l.a.vx+=dx*f; l.a.vy+=dy*f; l.b.vx-=dx*f; l.b.vy-=dy*f;
  }
  for(const n of nodes){
    if(n===dragNode) { n.vx=0; n.vy=0; continue; }
    n.vx*=0.85; n.vy*=0.85;
    const v = Math.sqrt(n.vx*n.vx+n.vy*n.vy);
    if(v>VCAP){ n.vx*=VCAP/v; n.vy*=VCAP/v; }
    n.x+=n.vx; n.y+=n.vy;
  }
}

function fitView(){
  let x0=1e9,y0=1e9,x1=-1e9,y1=-1e9,count=0;
  for(const n of nodes){ if(!active[n.kind]) continue; count++;
    x0=Math.min(x0,n.x); y0=Math.min(y0,n.y);
    x1=Math.max(x1,n.x); y1=Math.max(y1,n.y); }
  if(!count||!W||!H) return;
  zoom = Math.min(1.5, Math.max(0.15,
    0.88*Math.min(W/(x1-x0+120), H/(y1-y0+120))));
  panX = -zoom*(x0+x1)/2; panY = -zoom*(y0+y1)/2;
}

/* ── rendering ── */
const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
let W=0, H=0, DPR = devicePixelRatio||1;
const graphBox = document.getElementById("graph");
function resize(){
  const r = graphBox.getBoundingClientRect();
  W=r.width; H=r.height;
  canvas.width=Math.round(W*DPR); canvas.height=Math.round(H*DPR);
  needsDraw=true;
}
new ResizeObserver(resize).observe(graphBox);

function css(v){ return getComputedStyle(document.documentElement)
  .getPropertyValue(v).trim(); }

function shapePath(shape, r){
  ctx.beginPath();
  if(shape==="circle"||shape==="dot"||shape==="ring") ctx.arc(0,0,r,0,7);
  else if(shape==="diamond"){ ctx.moveTo(0,-r*1.25); ctx.lineTo(r*1.25,0);
    ctx.lineTo(0,r*1.25); ctx.lineTo(-r*1.25,0); ctx.closePath(); }
  else if(shape==="triangle"){ ctx.moveTo(0,-r*1.25); ctx.lineTo(r*1.15,r*0.9);
    ctx.lineTo(-r*1.15,r*0.9); ctx.closePath(); }
  else if(shape==="square") ctx.rect(-r,-r,2*r,2*r);
  else ctx.rect(-r*1.2,-r*0.8,2.4*r,1.6*r);
}

function draw(){
  ctx.setTransform(DPR,0,0,DPR,0,0);
  ctx.clearRect(0,0,W,H);
  ctx.translate(W/2+panX, H/2+panY); ctx.scale(zoom,zoom);
  const ink=css("--ink"), muted=css("--muted"), paper=css("--paper");
  if(mode==="layers"){
    ctx.globalAlpha=0.8; ctx.fillStyle=muted; ctx.textAlign="center";
    ctx.font=`600 ${13/zoom}px -apple-system, sans-serif`;
    for(let e=1;e<=24;e++) ctx.fillText("E"+e, (e-12.5)*COL, -370);
    ctx.textAlign="right";
    ctx.font=`${12/zoom}px -apple-system, sans-serif`;
    for(const [t,y] of LANE_PT) ctx.fillText(t, -12.4*COL, y+4);
    ctx.globalAlpha=1;
  }
  const neighbors = new Set();
  const focus = selected||hovered;
  if(focus){ neighbors.add(focus.id);
    links.forEach(l=>{ if(l.a===focus) neighbors.add(l.b.id);
      if(l.b===focus) neighbors.add(l.a.id); }); }

  for(const l of links){
    if(!active[l.a.kind]||!active[l.b.kind]) continue;
    const dim = focus && !(l.a===focus||l.b===focus);
    ctx.globalAlpha = dim ? 0.08 : (l.g==="prov"||l.g==="ref" ? 0.3 : 0.55);
    ctx.strokeStyle = muted;
    ctx.lineWidth = (l.g==="sup"||l.g==="dis" ? 1.8 : 0.9)/zoom;
    ctx.setLineDash(l.g==="dis" ? [5/zoom,4/zoom]
      : l.g==="meta" ? [2/zoom,3/zoom] : []);
    ctx.beginPath(); ctx.moveTo(l.a.x,l.a.y); ctx.lineTo(l.b.x,l.b.y);
    ctx.stroke();
    /* arrowhead */
    if(!dim && zoom>0.5 && l.g!=="ref"){
      const dx=l.b.x-l.a.x, dy=l.b.y-l.a.y, d=Math.sqrt(dx*dx+dy*dy)||1;
      const rr = KINDS[l.b.kind].r+4, px=l.b.x-dx/d*rr, py=l.b.y-dy/d*rr;
      const s=4/zoom;
      ctx.setLineDash([]);
      ctx.beginPath(); ctx.moveTo(px,py);
      ctx.lineTo(px-dx/d*s*2+dy/d*s, py-dy/d*s*2-dx/d*s);
      ctx.lineTo(px-dx/d*s*2-dy/d*s, py-dy/d*s*2+dx/d*s);
      ctx.closePath(); ctx.fillStyle=muted; ctx.fill();
    }
  }
  ctx.setLineDash([]);

  for(const n of nodes){
    if(!active[n.kind]) continue;
    const k = KINDS[n.kind];
    const dimF = focus && !neighbors.has(n.id);
    const dimQ = query && !matches(n);
    ctx.globalAlpha = (dimF||dimQ) ? 0.15 : 1;
    ctx.save(); ctx.translate(n.x,n.y);
    const col = css(k.c);
    const r = k.r + Math.min(4, n.deg*0.25);
    shapePath(k.shape, r);
    if(k.shape==="ring"){ ctx.lineWidth=3; ctx.strokeStyle=col;
      ctx.fillStyle=paper; ctx.fill(); ctx.stroke(); }
    else { ctx.fillStyle=col; ctx.fill();
      ctx.lineWidth=1.5; ctx.strokeStyle=paper; ctx.stroke(); }
    if(n===selected){ shapePath(k.shape, r+4/zoom);
      ctx.lineWidth=1.5/zoom; ctx.strokeStyle=ink; ctx.stroke(); }
    if(zoom>0.3 && (n.kind!=="evidence"||focus) && !(dimF||dimQ)){
      ctx.font = `${11/zoom}px -apple-system, sans-serif`;
      ctx.fillStyle = ink; ctx.textAlign="center";
      ctx.fillText(n.id, 0, r+13/zoom);
    }
    ctx.restore();
  }
  ctx.globalAlpha = 1;
}

/* ── main loop ── */
let cooling = 0;
let userMovedView = false;
function frame(){
  if(mode==="force" && cooling>0){ tick(); cooling--; needsDraw=true;
    if(!userMovedView && (cooling%20===0)) fitView(); }
  if(needsDraw){ draw(); needsDraw=false; }
  requestAnimationFrame(frame);
}
requestAnimationFrame(frame);
function reheat(n){
  if(mode!=="force"){ needsDraw=true; return; }
  if(reduced){ for(let i=0;i<200;i++) tick(); needsDraw=true; return; }
  cooling = Math.max(cooling, n); needsDraw=true;
}
function setMode(m){
  mode=m; userMovedView=false;
  if(m==="layers"){ cooling=0; layeredLayout(); }
  else if(reduced){ for(let i=0;i<600;i++) tick(); }
  else cooling=600;
  fitView(); needsDraw=true;
}

/* ── interaction ── */
let dragNode=null, panning=false, lastX=0, lastY=0, moved=false;
function toWorld(ev){
  const r=canvas.getBoundingClientRect();
  return [(ev.clientX-r.left-W/2-panX)/zoom, (ev.clientY-r.top-H/2-panY)/zoom];
}
function pick(ev){
  const [x,y]=toWorld(ev);
  let best=null, bd=1e9;
  for(const n of nodes){
    if(!active[n.kind]) continue;
    const r=KINDS[n.kind].r+6, d=(n.x-x)**2+(n.y-y)**2;
    if(d<r*r && d<bd){ best=n; bd=d; }
  }
  return best;
}
canvas.addEventListener("pointerdown", ev=>{
  canvas.setPointerCapture(ev.pointerId);
  moved=false; lastX=ev.clientX; lastY=ev.clientY;
  dragNode=pick(ev); panning=!dragNode;
  canvas.style.cursor = dragNode? "grabbing":"grab";
});
canvas.addEventListener("pointermove", ev=>{
  const tip=document.getElementById("tip");
  if(dragNode){
    const [x,y]=toWorld(ev); dragNode.x=x; dragNode.y=y; moved=true;
    reheat(120); return;
  }
  if(panning && ev.buttons){
    panX+=ev.clientX-lastX; panY+=ev.clientY-lastY;
    lastX=ev.clientX; lastY=ev.clientY; moved=true; userMovedView=true;
    needsDraw=true; return;
  }
  const n=pick(ev);
  if(n!==hovered){ hovered=n; needsDraw=true; }
  if(n){
    tip.style.display="block";
    tip.style.left=Math.min(innerWidth-360, ev.clientX+14)+"px";
    tip.style.top=(ev.clientY+14)+"px";
    tip.innerHTML=`<span class="id">${n.id}</span> · ${KINDS[n.kind].pt}`+
      (n.text?`<br><span class="t">${esc(n.text.slice(0,160))}${n.text.length>160?"…":""}</span>`:"");
  } else tip.style.display="none";
});
canvas.addEventListener("pointerup", ev=>{
  if(!moved){ const n=pick(ev); select(n); }
  dragNode=null; panning=false; canvas.style.cursor="grab";
});
canvas.addEventListener("wheel", ev=>{
  ev.preventDefault();
  const f = Math.exp(-ev.deltaY*0.0012);
  const r=canvas.getBoundingClientRect();
  const mx=ev.clientX-r.left-W/2, my=ev.clientY-r.top-H/2;
  panX = mx-(mx-panX)*f; panY = my-(my-panY)*f;
  zoom*=f; zoom=Math.min(4,Math.max(0.15,zoom)); userMovedView=true;
  needsDraw=true;
},{passive:false});

function esc(s){ const d=document.createElement("i"); d.textContent=s;
  return d.innerHTML; }

/* ── sidebar ── */
function select(n){
  selected=n; needsDraw=true;
  const side=document.getElementById("side");
  if(!n){ side.classList.remove("open"); side.innerHTML=""; return; }
  const rel=[];
  for(const l of links){
    if(l.a===n) rel.push(`→ ${EDGE_PT[l.g]} (<code>${l.p}</code>) <button class="nav" data-id="${l.b.id}">${l.b.id}</button>`);
    if(l.b===n) rel.push(`← ${EDGE_PT[l.g]} (<code>${l.p}</code>) <button class="nav" data-id="${l.a.id}">${l.a.id}</button>`);
  }
  const crate = n.entry ? `<p><a href="../packages/entry${String(n.entry).padStart(2,"0")}/ro-crate-preview.html">pacote de evidência da entrada ${n.entry}</a></p>` : "";
  side.innerHTML = `<button class="close" aria-label="Fechar">fechar ✕</button>
    <div class="kind">${KINDS[n.kind].pt}${n.entry?` · entrada ${n.entry}`:""}</div>
    <h2>${esc(n.id)}</h2>
    ${n.text?`<p>${esc(n.text)}</p>`:""}
    ${n.desc?`<p class="desc">${esc(n.desc)}</p>`:""}
    ${crate}
    <h3>Relações (${rel.length})</h3>
    <ul>${rel.map(r=>`<li>${r}</li>`).join("")}</ul>`;
  side.classList.add("open");
  side.querySelector(".close").onclick=()=>select(null);
  side.querySelectorAll("button.nav").forEach(b=>{
    b.onclick=()=>{ const m=byId[b.dataset.id]; select(m);
      panX=-m.x*zoom; panY=-m.y*zoom; needsDraw=true; };
  });
}

/* ── controls ── */
const legend=document.getElementById("legend");
for(const [k,v] of Object.entries(KINDS)){
  const lab=document.createElement("label");
  lab.innerHTML=`<input type="checkbox" checked>
    <span class="sw" style="background:var(${v.c});
    ${v.shape==="ring"?"background:transparent;border:2.5px solid var("+v.c+");":""}
    ${v.shape==="diamond"?"transform:rotate(45deg);border-radius:2px;":""}
    ${v.shape==="square"||v.shape==="rect"?"border-radius:2px;":""}
    ${v.shape==="dot"?"width:.5rem;height:.5rem;":""}"></span>${v.pt}`;
  lab.querySelector("input").addEventListener("change",ev=>{
    active[k]=ev.target.checked; reheat(200);
    if(selected&&!active[selected.kind]) select(null);
  });
  legend.appendChild(lab);
}
document.getElementById("edgeLegend").textContent =
  "arestas: sólida grossa = sustenta · tracejada = contesta · " +
  "pontilhada = corrige/atualiza/qualifica · fina = proveniência/sobre";
document.getElementById("q").addEventListener("input",ev=>{
  query=ev.target.value.trim().toLowerCase(); needsDraw=true;
});
document.querySelectorAll('#modeSwitch input').forEach(r=>{
  r.addEventListener("change",()=>setMode(r.value));
});
matchMedia("(prefers-color-scheme: dark)").addEventListener("change",
  ()=>{ needsDraw=true; });
layeredLayout();
resize();
fitView();
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
