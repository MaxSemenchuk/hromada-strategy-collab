#!/usr/bin/env python3
"""Build a readable PIN + matching-overlay graph for our strategy corpus.

Sources:
  - data/cache/kse/partnerships-hromadas-network.csv  (KSE, known МСС pairs)
  - data/releases/matching-edges.json                 (hypothesis scores)
  - data/releases/hromadas.json                       (names + KATOTTG)

Writes docs/mss-pin-matching-graph.html with an in-browser force layout
(stronger repulsion than the old static spring_layout MVP).
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / "data/cache/kse/partnerships-hromadas-network.csv"
EDGES = ROOT / "data/releases/matching-edges.json"
HROMADAS = ROOT / "data/releases/hromadas.json"
OUT = ROOT / "docs/mss-pin-matching-graph.html"

# Keep the viz sparse enough to read.
TOP_HYPOTHESES = 30
MIN_HYPOTHESIS_SCORE = 0.15


def load_corpus() -> list[dict]:
    rows = json.loads(HROMADAS.read_text(encoding="utf-8"))
    return [r for r in rows if r.get("Goals") and r.get("Katottg")]


def load_pin_pairs() -> list[tuple[str, str]]:
    """Unique undirected (code_a, code_b) pairs from KSE network CSV."""
    seen: set[tuple[str, str]] = set()
    pairs: list[tuple[str, str]] = []
    with PIN.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            a, b = row["hromada_code.x"], row["hromada_code.y"]
            if not a or not b or a == b:
                continue
            key = tuple(sorted((a, b)))
            if key in seen:
                continue
            seen.add(key)
            pairs.append(key)  # type: ignore[arg-type]
    return pairs


def short_label(full: str) -> str:
    # "Галицька міська територіальна громада" → "Галицька міська"
    parts = full.replace("територіальна громада", "").strip().split()
    return " ".join(parts[:2]) if len(parts) >= 2 else full


def build_payload() -> dict:
    corpus = load_corpus()
    by_code = {r["Katottg"]: r for r in corpus}
    by_name = {r["Name"]: r for r in corpus}
    codes = set(by_code)

    pin_pairs = load_pin_pairs()
    pin_edges = []
    for a, b in pin_pairs:
        if a in codes and b in codes:
            pin_edges.append(
                {
                    "a": by_code[a]["Name"],
                    "b": by_code[b]["Name"],
                    "kind": "pin",
                }
            )

    matching = json.loads(EDGES.read_text(encoding="utf-8"))
    # Only edges whose both ends are in the goals corpus
    corpus_matching = [
        e
        for e in matching
        if e["a"] in by_name and e["b"] in by_name
    ]

    known = [e for e in corpus_matching if e.get("known")]
    hypotheses = sorted(
        (e for e in corpus_matching if not e.get("known") and e["score"] >= MIN_HYPOTHESIS_SCORE),
        key=lambda e: -e["score"],
    )[:TOP_HYPOTHESES]

    # Avoid duplicating PIN edges as hypotheses when mss_network already fires
    pin_keys = {tuple(sorted((e["a"], e["b"]))) for e in pin_edges}
    hyp_edges = []
    for e in hypotheses:
        key = tuple(sorted((e["a"], e["b"])))
        if key in pin_keys:
            continue
        hyp_edges.append(
            {
                "a": e["a"],
                "b": e["b"],
                "kind": "hypothesis",
                "score": e["score"],
                "goals_cosine": e.get("goals_cosine"),
            }
        )

    known_edges = []
    for e in known:
        known_edges.append(
            {
                "a": e["a"],
                "b": e["b"],
                "kind": "known",
                "score": e["score"],
            }
        )

    # Nodes: all corpus members that appear in any edge, plus isolates with goals
    used = set()
    for e in pin_edges + hyp_edges + known_edges:
        used.add(e["a"])
        used.add(e["b"])
    # Always include known-pair nodes even if filtered
    for e in known:
        used.add(e["a"])
        used.add(e["b"])

    # Prefer connected subgraph; drop isolates for readability
    nodes = []
    for name in sorted(used):
        row = by_name[name]
        nodes.append(
            {
                "id": name,
                "label": short_label(name),
                "katottg": row["Katottg"],
                "oblast": row.get("Oblast"),
                "in_pin": any(
                    name in (e["a"], e["b"]) for e in pin_edges + known_edges
                ),
            }
        )

    return {
        "meta": {
            "corpus_size": len(corpus),
            "pin_edges": len(pin_edges),
            "hypothesis_edges": len(hyp_edges),
            "known_edges": len(known_edges),
            "pin_source": "KSE-Loc-Data-Hub partnerships-hromadas-network.csv",
            "matching_source": "data/releases/matching-edges.json",
            "top_hypotheses": TOP_HYPOTHESES,
            "min_hypothesis_score": MIN_HYPOTHESIS_SCORE,
        },
        "nodes": nodes,
        "edges": pin_edges + known_edges + hyp_edges,
    }


HTML = """<!DOCTYPE html>
<html lang="uk">
<head>
<meta charset="utf-8"/>
<title>МСС: KSE PIN + matching overlay</title>
<style>
  :root {
    --bg: #14181d; --surface: #1b2027; --ink: #e9e6de; --ink-muted: #a9ac9f;
    --border: #2d333c; --accent: #57ab9c; --gold: #d9a548; --hyp: #7aa2ff; --rule: #333a44;
  }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink); font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
  .wrap { display: grid; grid-template-columns: 280px 1fr; min-height: 100vh; }
  @media (max-width: 900px) { .wrap { grid-template-columns: 1fr; } }
  aside { padding: 1.25rem 1.2rem; border-right: 1px solid var(--rule); background: var(--surface); }
  h1 { font-size: 1.05rem; font-weight: 600; margin: 0 0 0.6rem; line-height: 1.35; }
  .lede { font-size: 0.85rem; color: var(--ink-muted); margin: 0 0 1rem; line-height: 1.45; }
  .stat { display: flex; justify-content: space-between; font-size: 0.82rem; padding: 0.35rem 0; border-bottom: 1px solid var(--rule); }
  .stat b { font-variant-numeric: tabular-nums; }
  .legend { margin-top: 1.1rem; font-size: 0.8rem; color: var(--ink-muted); }
  .legend div { display: flex; align-items: center; gap: 0.5rem; margin: 0.35rem 0; }
  .sw { width: 22px; height: 0; border-top: 2px solid; display: inline-block; }
  .sw.pin { border-color: var(--accent); }
  .sw.known { border-color: var(--gold); border-top-width: 3px; }
  .sw.hyp { border-color: var(--hyp); border-top-style: dashed; }
  .hint { margin-top: 1rem; font-size: 0.78rem; color: var(--ink-muted); line-height: 1.4; }
  main { position: relative; }
  canvas { display: block; width: 100%; height: 100vh; cursor: grab; }
  canvas:active { cursor: grabbing; }
  #tooltip {
    display: none; position: absolute; pointer-events: none; z-index: 2;
    background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
    padding: 0.55rem 0.7rem; font-size: 0.8rem; max-width: 280px; line-height: 1.35;
  }
</style>
</head>
<body>
<div class="wrap">
  <aside>
    <h1>KSE PIN + matching overlay</h1>
    <p class="lede">Відомі МСС-ребра з KSE (реєстр) поверх нашого корпусу стратегій, плюс топ гіпотез матчера. Без багатосторонніх «плям» з сирого реєстру.</p>
    <div class="stat"><span>Корпус (з Goals)</span><b id="s-corpus">—</b></div>
    <div class="stat"><span>Вузлів на графі</span><b id="s-nodes">—</b></div>
    <div class="stat"><span>PIN (відомі)</span><b id="s-pin">—</b></div>
    <div class="stat"><span>Known validation</span><b id="s-known">—</b></div>
    <div class="stat"><span>Hypotheses</span><b id="s-hyp">—</b></div>
    <div class="legend">
      <div><span class="sw pin"></span> KSE PIN (реєстр МСС)</div>
      <div><span class="sw known"></span> known validation pairs</div>
      <div><span class="sw hyp"></span> matching hypothesis</div>
    </div>
    <p class="hint">Тягни полотно мишкою · скрол = zoom · наведи на вузол для назви. Force-layout крутиться в браузері (сильна repulsion), щоб не злипалось.</p>
  </aside>
  <main>
    <canvas id="c"></canvas>
    <div id="tooltip"></div>
  </main>
</div>
<script>
const DATA = __DATA__;

const meta = DATA.meta;
document.getElementById('s-corpus').textContent = meta.corpus_size;
document.getElementById('s-nodes').textContent = DATA.nodes.length;
document.getElementById('s-pin').textContent = meta.pin_edges;
document.getElementById('s-known').textContent = meta.known_edges;
document.getElementById('s-hyp').textContent = meta.hypothesis_edges;

const canvas = document.getElementById('c');
const ctx = canvas.getContext('2d');
const tip = document.getElementById('tooltip');

const nodes = DATA.nodes.map((n, i) => {
  const angle = (i / DATA.nodes.length) * Math.PI * 2;
  return {
    ...n,
    x: Math.cos(angle) * 220,
    y: Math.sin(angle) * 180,
    vx: 0, vy: 0,
  };
});
const byId = Object.fromEntries(nodes.map(n => [n.id, n]));
const edges = DATA.edges
  .filter(e => byId[e.a] && byId[e.b])
  .map(e => ({ ...e, source: byId[e.a], target: byId[e.b] }));

let width = 0, height = 0, dpr = 1;
let camX = 0, camY = 0, scale = 1;
let dragging = null, panning = false, lastX = 0, lastY = 0;
let hover = null;

function resize() {
  dpr = window.devicePixelRatio || 1;
  width = canvas.clientWidth;
  height = canvas.clientHeight;
  canvas.width = Math.floor(width * dpr);
  canvas.height = Math.floor(height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
resize();
window.addEventListener('resize', resize);

function worldFromEvent(ev) {
  const rect = canvas.getBoundingClientRect();
  const sx = ev.clientX - rect.left;
  const sy = ev.clientY - rect.top;
  return {
    x: (sx - width / 2 - camX) / scale,
    y: (sy - height / 2 - camY) / scale,
    sx, sy,
  };
}

function findNode(wx, wy) {
  const hit = 12 / scale;
  let best = null, bestD = hit * hit;
  for (const n of nodes) {
    const dx = n.x - wx, dy = n.y - wy;
    const d = dx * dx + dy * dy;
    if (d < bestD) { bestD = d; best = n; }
  }
  return best;
}

canvas.addEventListener('mousedown', (ev) => {
  const w = worldFromEvent(ev);
  const n = findNode(w.x, w.y);
  if (n) {
    dragging = n;
    n.fx = n.x; n.fy = n.y;
  } else {
    panning = true;
    lastX = ev.clientX; lastY = ev.clientY;
  }
});
window.addEventListener('mouseup', () => {
  if (dragging) { dragging.fx = null; dragging.fy = null; }
  dragging = null; panning = false;
});
window.addEventListener('mousemove', (ev) => {
  const w = worldFromEvent(ev);
  if (dragging) {
    dragging.fx = w.x; dragging.fy = w.y;
    dragging.x = w.x; dragging.y = w.y;
  } else if (panning) {
    camX += ev.clientX - lastX;
    camY += ev.clientY - lastY;
    lastX = ev.clientX; lastY = ev.clientY;
  }
  hover = findNode(w.x, w.y);
  if (hover) {
    tip.style.display = 'block';
    tip.style.left = (w.sx + 14) + 'px';
    tip.style.top = (w.sy + 14) + 'px';
    tip.innerHTML = `<strong>${hover.id}</strong><br/>${hover.oblast || ''}<br/><span style="color:#a9ac9f">${hover.katottg}</span>`;
  } else {
    tip.style.display = 'none';
  }
});
canvas.addEventListener('wheel', (ev) => {
  ev.preventDefault();
  const factor = ev.deltaY < 0 ? 1.08 : 0.92;
  scale = Math.min(4, Math.max(0.35, scale * factor));
}, { passive: false });

function tick() {
  const n = nodes.length;
  // Strong charge (repulsion) — main anti-clump lever
  const charge = 1800;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      let dx = nodes[j].x - nodes[i].x;
      let dy = nodes[j].y - nodes[i].y;
      let dist2 = dx * dx + dy * dy || 0.01;
      let dist = Math.sqrt(dist2);
      // soft floor so close nodes still push hard
      const f = charge / Math.max(dist2, 25);
      const fx = (dx / dist) * f;
      const fy = (dy / dist) * f;
      nodes[i].vx -= fx; nodes[i].vy -= fy;
      nodes[j].vx += fx; nodes[j].vy += fy;
    }
  }
  // Springs — PIN/known tighter than hypotheses
  for (const e of edges) {
    const a = e.source, b = e.target;
    let dx = b.x - a.x, dy = b.y - a.y;
    let dist = Math.sqrt(dx * dx + dy * dy) || 0.01;
    const rest = e.kind === 'hypothesis' ? 140 : 95;
    const k = e.kind === 'hypothesis' ? 0.012 : 0.035;
    const f = k * (dist - rest);
    const fx = (dx / dist) * f;
    const fy = (dy / dist) * f;
    a.vx += fx; a.vy += fy;
    b.vx -= fx; b.vy -= fy;
  }
  // Weak centering
  for (const node of nodes) {
    node.vx += -node.x * 0.002;
    node.vy += -node.y * 0.002;
    if (node.fx != null) { node.x = node.fx; node.y = node.fy; node.vx = 0; node.vy = 0; continue; }
    node.vx *= 0.82; node.vy *= 0.82;
    node.x += node.vx; node.y += node.vy;
  }
}

function draw() {
  tick();
  ctx.clearRect(0, 0, width, height);
  ctx.save();
  ctx.translate(width / 2 + camX, height / 2 + camY);
  ctx.scale(scale, scale);

  for (const e of edges) {
    ctx.beginPath();
    ctx.moveTo(e.source.x, e.source.y);
    ctx.lineTo(e.target.x, e.target.y);
    if (e.kind === 'pin') {
      ctx.strokeStyle = 'rgba(87,171,156,0.55)';
      ctx.lineWidth = 1.6 / scale;
      ctx.setLineDash([]);
    } else if (e.kind === 'known') {
      ctx.strokeStyle = 'rgba(217,165,72,0.9)';
      ctx.lineWidth = 2.4 / scale;
      ctx.setLineDash([]);
    } else {
      ctx.strokeStyle = 'rgba(122,162,255,0.55)';
      ctx.lineWidth = 1.2 / scale;
      ctx.setLineDash([5 / scale, 4 / scale]);
    }
    ctx.stroke();
    ctx.setLineDash([]);
  }

  for (const n of nodes) {
    const hi = hover === n;
    const r = (hi ? 7 : 4.5) / Math.sqrt(scale);
    ctx.beginPath();
    ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
    ctx.fillStyle = n.in_pin ? '#57ab9c' : '#7aa2ff';
    ctx.globalAlpha = hi ? 1 : 0.9;
    ctx.fill();
    ctx.globalAlpha = 1;
    if (hi || scale > 1.15) {
      ctx.font = `${11 / scale}px -apple-system, sans-serif`;
      ctx.fillStyle = '#e9e6de';
      ctx.textAlign = 'left';
      ctx.fillText(n.label, n.x + 8 / scale, n.y + 3 / scale);
    }
  }
  ctx.restore();
  requestAnimationFrame(draw);
}
requestAnimationFrame(draw);
</script>
</body>
</html>
"""


def main() -> None:
    if not PIN.exists():
        raise SystemExit(
            f"Missing {PIN}. Run: python3 scripts/analysis/enrich_from_kse.py "
            "(or fetch partnerships-hromadas-network.csv into data/cache/kse/)"
        )
    payload = build_payload()
    html = HTML.replace("__DATA__", json.dumps(payload, ensure_ascii=False))
    OUT.write_text(html, encoding="utf-8")
    m = payload["meta"]
    print(
        f"Wrote {OUT.relative_to(ROOT)} — "
        f"nodes={len(payload['nodes'])} pin={m['pin_edges']} "
        f"known={m['known_edges']} hyp={m['hypothesis_edges']}"
    )


if __name__ == "__main__":
    main()
