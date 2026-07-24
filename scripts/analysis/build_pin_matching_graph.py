#!/usr/bin/env python3
"""Build PIN + matching overlay viz: full МСС network + Leaflet map / force graph.

Sources:
  - data/cache/kse/partnerships-hromadas-network.csv
  - data/cache/kse/geography.csv
  - data/releases/matching-edges.json
  - data/releases/hromadas.json  (PortalUrl / StrategyUrl / Goals)
  - docs/geo/ukraine-oblasts.geojson  (Natural Earth admin-1, simplified)

Writes docs/mss-pin-matching-graph.html

Overlay policy (2026-07-24):
  Do NOT paint top-N by combined score — that collapses to geo neighbours in a
  sparse strategy corpus. Split tracks instead:

    thematic    — high goals_cosine  → «похожа стратегія» (default ON)
    operational — high geo           → «зручний сусід»   (default OFF)
    known       — curated registry validation pairs
    pin_corpus  — broader KSE PIN ∩ Goals corpus (mss_network>0, not known)
    universe    — all release hromadas with KSE lat/lon (metadata underlay)
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from tracks import operational_slice, thematic_slice  # noqa: E402

PIN = ROOT / "data/cache/kse/partnerships-hromadas-network.csv"
GEO = ROOT / "data/cache/kse/geography.csv"
EDGES = ROOT / "data/releases/matching-edges.json"
HROMADAS = ROOT / "data/releases/hromadas.json"
OBLASTS = ROOT / "docs/geo/ukraine-oblasts.geojson"
OUTLINE = ROOT / "docs/geo/ukraine-outline.geojson"
TEMPLATE = Path(__file__).with_name("mss_pin_matching_graph.template.html")
OUT = ROOT / "docs/mss-pin-matching-graph.html"

TOP_THEMATIC = 40
TOP_OPERATIONAL = 40


def load_geo() -> dict[str, dict]:
    out: dict[str, dict] = {}
    with GEO.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            code = row.get("hromada_code")
            try:
                lat = float(row["lat_center"])
                lon = float(row["lon_center"])
            except (KeyError, TypeError, ValueError):
                continue
            if not code:
                continue
            out[code] = {
                "lat": lat,
                "lon": lon,
                "oblast": row.get("oblast_name") or None,
                "name_short": row.get("hromada") or code,
            }
    return out


def load_pin() -> tuple[dict[str, dict], list[dict]]:
    nodes: dict[str, dict] = {}
    seen: set[tuple[str, str]] = set()
    edges: list[dict] = []
    with PIN.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            a, b = row["hromada_code.x"], row["hromada_code.y"]
            if not a or not b or a == b:
                continue
            nodes[a] = {"id": a, "label": row["hromada_name.x"] or a}
            nodes[b] = {"id": b, "label": row["hromada_name.y"] or b}
            key = tuple(sorted((a, b)))
            if key in seen:
                continue
            seen.add(key)
            edges.append({"a": a, "b": b, "kind": "pin"})
    return nodes, edges


def short_label(full: str) -> str:
    parts = full.replace("територіальна громада", "").strip().split()
    return " ".join(parts[:2]) if len(parts) >= 2 else full


def encode_overlay(
    rows: list[dict],
    *,
    kind: str,
    name_to_code: dict[str, str],
    pin_keys: set[tuple[str, str]],
) -> list[dict]:
    """Map matching-edge names → KATOTTG overlay edges; skip pairs already in PIN."""
    out: list[dict] = []
    for e in rows:
        ca, cb = name_to_code[e["a"]], name_to_code[e["b"]]
        if tuple(sorted((ca, cb))) in pin_keys:
            continue
        out.append(
            {
                "a": ca,
                "b": cb,
                "kind": kind,
                "score": e["score"],
                "goals_cosine": e.get("goals_cosine"),
                "geo_score": e.get("geo_score"),
                "track": e.get("track"),
            }
        )
    return out


def pin_corpus_overlay(
    corpus_matching: list[dict],
    *,
    name_to_code: dict[str, str],
    known_code_keys: set[tuple[str, str]],
) -> list[dict]:
    """Broader KSE check: mss_network>0 but not curated known (dedupe by KATOTTG)."""
    by_codes: dict[tuple[str, str], dict] = {}
    for e in corpus_matching:
        if e.get("known") or float(e.get("mss_network") or 0) <= 0:
            continue
        ca, cb = name_to_code[e["a"]], name_to_code[e["b"]]
        if ca == cb:
            continue
        key = tuple(sorted((ca, cb)))
        if key in known_code_keys:
            continue
        prev = by_codes.get(key)
        if prev is None or float(e["score"]) > float(prev["score"]):
            by_codes[key] = e
    return [
        {
            "a": key[0],
            "b": key[1],
            "kind": "pin_corpus",
            "score": e["score"],
            "goals_cosine": e.get("goals_cosine"),
            "geo_score": e.get("geo_score"),
            "track": e.get("track"),
        }
        for key, e in sorted(by_codes.items())
    ]


def build_payload() -> dict:
    geo = load_geo()
    pin_nodes, pin_edges = load_pin()

    hromadas = json.loads(HROMADAS.read_text(encoding="utf-8"))
    # Full metadata index (1,469) — portals / names / corpus flags by KATOTTG
    by_code: dict[str, dict] = {}
    for r in hromadas:
        code = r.get("Katottg")
        if not code:
            continue
        by_code[code] = {
            "full_name": r.get("Name"),
            "portal_url": r.get("PortalUrl") or None,
            "strategy_url": r.get("StrategyUrl") or None,
            "in_corpus": bool(r.get("Goals")),
            "source_quality": r.get("SourceQuality"),
            "type": r.get("Type"),
            "population": r.get("Population"),
        }

    corpus = [r for r in hromadas if r.get("Goals") and r.get("Katottg")]
    name_to_code = {r["Name"]: r["Katottg"] for r in corpus}
    code_to_full = {r["Katottg"]: r["Name"] for r in corpus}
    corpus_codes = set(name_to_code.values())

    matching = json.loads(EDGES.read_text(encoding="utf-8"))
    corpus_matching = [
        e for e in matching if e["a"] in name_to_code and e["b"] in name_to_code
    ]
    known = [e for e in corpus_matching if e.get("known")]
    thematic = thematic_slice(corpus_matching, limit=TOP_THEMATIC)
    operational = operational_slice(corpus_matching, limit=TOP_OPERATIONAL)

    pin_keys = {tuple(sorted((e["a"], e["b"]))) for e in pin_edges}
    known_code_keys = {
        tuple(sorted((name_to_code[e["a"]], name_to_code[e["b"]]))) for e in known
    }

    known_edges = [
        {
            "a": name_to_code[e["a"]],
            "b": name_to_code[e["b"]],
            "kind": "known",
            "score": e["score"],
            "goals_cosine": e.get("goals_cosine"),
            "geo_score": e.get("geo_score"),
            "track": e.get("track"),
        }
        for e in known
    ]
    pin_corpus_edges = pin_corpus_overlay(
        corpus_matching, name_to_code=name_to_code, known_code_keys=known_code_keys
    )
    thematic_edges = encode_overlay(
        thematic, kind="thematic", name_to_code=name_to_code, pin_keys=pin_keys
    )
    operational_edges = encode_overlay(
        operational, kind="operational", name_to_code=name_to_code, pin_keys=pin_keys
    )

    for e in known_edges + pin_corpus_edges + thematic_edges + operational_edges:
        for code in (e["a"], e["b"]):
            if code not in pin_nodes:
                pin_nodes[code] = {
                    "id": code,
                    "label": short_label(code_to_full.get(code, code)),
                }

    pin_member = {e["a"] for e in pin_edges} | {e["b"] for e in pin_edges}

    degree: dict[str, int] = {c: 0 for c in pin_nodes}
    for e in pin_edges:
        degree[e["a"]] = degree.get(e["a"], 0) + 1
        degree[e["b"]] = degree.get(e["b"], 0) + 1

    def enrich(code: str, label_fallback: str) -> dict:
        g = geo.get(code)
        meta = by_code.get(code) or {}
        lat = lon = oblast = None
        label = label_fallback
        if g:
            lat, lon = g["lat"], g["lon"]
            oblast = g["oblast"]
            label = g["name_short"] or label
        return {
            "id": code,
            "label": label,
            "full_name": meta.get("full_name") or code_to_full.get(code),
            "katottg": code,
            "oblast": oblast,
            "lat": lat,
            "lon": lon,
            "degree": degree.get(code, 0),
            "in_corpus": code in corpus_codes or bool(meta.get("in_corpus")),
            "in_pin": code in pin_member,
            "portal_url": meta.get("portal_url"),
            "strategy_url": meta.get("strategy_url"),
            "source_quality": meta.get("source_quality"),
            "type": meta.get("type"),
            "population": meta.get("population"),
        }

    nodes = []
    with_geo = 0
    for code, base in sorted(pin_nodes.items(), key=lambda x: x[1]["label"]):
        n = enrich(code, base["label"])
        if n["lat"] is not None:
            with_geo += 1
        nodes.append(n)

    # Universe layer: every release hromada with KSE lat/lon (≈ full mainland set)
    universe: list[dict] = []
    for code, meta in by_code.items():
        g = geo.get(code)
        if not g:
            continue
        universe.append(
            {
                "id": code,
                "label": g.get("name_short") or short_label(meta.get("full_name") or code),
                "full_name": meta.get("full_name"),
                "katottg": code,
                "oblast": g.get("oblast"),
                "lat": g["lat"],
                "lon": g["lon"],
                "in_corpus": bool(meta.get("in_corpus")),
                "in_pin": code in pin_member,
                "portal_url": meta.get("portal_url"),
                "strategy_url": meta.get("strategy_url"),
                "source_quality": meta.get("source_quality"),
                "type": meta.get("type"),
                "population": meta.get("population"),
            }
        )
    universe.sort(key=lambda n: n.get("full_name") or n["label"] or n["id"])

    if not OBLASTS.exists():
        raise SystemExit(f"Missing {OBLASTS}")
    if not OUTLINE.exists():
        raise SystemExit(f"Missing {OUTLINE}")
    oblasts = json.loads(OBLASTS.read_text(encoding="utf-8"))
    outline = json.loads(OUTLINE.read_text(encoding="utf-8"))

    portal_on_map = sum(1 for n in universe if n.get("portal_url"))

    return {
        "meta": {
            "corpus_size": len(corpus),
            "pin_edges": len(pin_edges),
            "pin_nodes": len(nodes),
            "universe_nodes": len(universe),
            "universe_with_portal": portal_on_map,
            "thematic_edges": len(thematic_edges),
            "operational_edges": len(operational_edges),
            "known_edges": len(known_edges),
            "pin_corpus_edges": len(pin_corpus_edges),
            # legacy alias: thematic only (combined-score hyp layer removed)
            "hypothesis_edges": len(thematic_edges),
            "nodes_with_geo": with_geo,
            "oblasts": len(oblasts.get("features", [])),
            "pin_source": "KSE-Loc-Data-Hub partnerships-hromadas-network.csv",
            "geo_source": "KSE-Loc-Data-Hub geography.csv (lat_center/lon_center)",
            "oblasts_source": "Natural Earth admin-1 → docs/geo/ukraine-oblasts.geojson",
            "outline_source": "docs/geo/ukraine-outline.geojson (mask outside UA)",
            "matching_source": "data/releases/matching-edges.json",
            "hromadas_source": "data/releases/hromadas.json (PortalUrl/StrategyUrl)",
            "top_thematic": TOP_THEMATIC,
            "top_operational": TOP_OPERATIONAL,
            "overlay_policy": (
                "thematic=goals_cosine track; operational=geo neighbours; "
                "pin_corpus=mss_network>0 not known; no combined-score hyp layer; "
                "universe=all release rows with KSE geo (metadata layer)"
            ),
        },
        "oblasts": oblasts,
        "ukraine_outline": outline,
        "nodes": nodes,
        "universe": universe,
        "edges": pin_edges + known_edges + pin_corpus_edges + thematic_edges + operational_edges,
    }


def main() -> None:
    for path in (PIN, GEO, TEMPLATE):
        if not path.exists():
            raise SystemExit(f"Missing {path}")
    payload = build_payload()
    html = TEMPLATE.read_text(encoding="utf-8").replace(
        "__DATA__", json.dumps(payload, ensure_ascii=False)
    )
    OUT.write_text(html, encoding="utf-8")
    m = payload["meta"]
    print(
        f"Wrote {OUT.relative_to(ROOT)} — "
        f"PIN {m['pin_nodes']}n/{m['pin_edges']}e · "
        f"universe={m['universe_nodes']} (portal={m['universe_with_portal']}) · "
        f"oblasts={m['oblasts']} · "
        f"known={m['known_edges']} pin∩corpus={m['pin_corpus_edges']} "
        f"thematic={m['thematic_edges']} operational={m['operational_edges']}"
    )


if __name__ == "__main__":
    main()
