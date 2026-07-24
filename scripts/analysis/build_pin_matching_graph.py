#!/usr/bin/env python3
"""Build PIN + matching overlay viz: full МСС network + Leaflet map / force graph.

Sources:
  - data/cache/kse/partnerships-hromadas-network.csv
  - data/cache/kse/geography.csv
  - data/releases/matching-edges.json
  - data/releases/hromadas.json
  - docs/geo/ukraine-oblasts.geojson  (Natural Earth admin-1, simplified)

Writes docs/mss-pin-matching-graph.html
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / "data/cache/kse/partnerships-hromadas-network.csv"
GEO = ROOT / "data/cache/kse/geography.csv"
EDGES = ROOT / "data/releases/matching-edges.json"
HROMADAS = ROOT / "data/releases/hromadas.json"
OBLASTS = ROOT / "docs/geo/ukraine-oblasts.geojson"
OUTLINE = ROOT / "docs/geo/ukraine-outline.geojson"
TEMPLATE = Path(__file__).with_name("mss_pin_matching_graph.template.html")
OUT = ROOT / "docs/mss-pin-matching-graph.html"

TOP_HYPOTHESES = 40
MIN_HYPOTHESIS_SCORE = 0.15


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


def build_payload() -> dict:
    geo = load_geo()
    pin_nodes, pin_edges = load_pin()

    hromadas = json.loads(HROMADAS.read_text(encoding="utf-8"))
    corpus = [r for r in hromadas if r.get("Goals") and r.get("Katottg")]
    name_to_code = {r["Name"]: r["Katottg"] for r in corpus}
    code_to_full = {r["Katottg"]: r["Name"] for r in corpus}
    corpus_codes = set(name_to_code.values())

    matching = json.loads(EDGES.read_text(encoding="utf-8"))
    corpus_matching = [
        e for e in matching if e["a"] in name_to_code and e["b"] in name_to_code
    ]
    known = [e for e in corpus_matching if e.get("known")]
    # Broader KSE check: mss_network>0 but not curated known (dedupe by KATOTTG).
    pin_corpus_by_codes: dict[tuple[str, str], dict] = {}
    for e in corpus_matching:
        if e.get("known") or float(e.get("mss_network") or 0) <= 0:
            continue
        ca, cb = name_to_code[e["a"]], name_to_code[e["b"]]
        if ca == cb:
            continue
        key = tuple(sorted((ca, cb)))
        prev = pin_corpus_by_codes.get(key)
        if prev is None or float(e["score"]) > float(prev["score"]):
            pin_corpus_by_codes[key] = e

    pin_corpus_keys = set(pin_corpus_by_codes)
    known_code_keys = {
        tuple(sorted((name_to_code[e["a"]], name_to_code[e["b"]]))) for e in known
    }

    hypotheses = sorted(
        (
            e
            for e in corpus_matching
            if not e.get("known")
            and float(e.get("mss_network") or 0) <= 0
            and e["score"] >= MIN_HYPOTHESIS_SCORE
        ),
        key=lambda e: -e["score"],
    )[:TOP_HYPOTHESES]

    known_edges = [
        {"a": name_to_code[e["a"]], "b": name_to_code[e["b"]], "kind": "known", "score": e["score"]}
        for e in known
    ]
    pin_corpus_edges = [
        {
            "a": key[0],
            "b": key[1],
            "kind": "pin_corpus",
            "score": e["score"],
            "goals_cosine": e.get("goals_cosine"),
        }
        for key, e in sorted(pin_corpus_by_codes.items())
        if key not in known_code_keys
    ]
    hyp_edges = []
    for e in hypotheses:
        ca, cb = name_to_code[e["a"]], name_to_code[e["b"]]
        key = tuple(sorted((ca, cb)))
        if key in pin_corpus_keys or key in known_code_keys:
            continue
        hyp_edges.append(
            {
                "a": ca,
                "b": cb,
                "kind": "hypothesis",
                "score": e["score"],
                "goals_cosine": e.get("goals_cosine"),
            }
        )

    for e in known_edges + pin_corpus_edges + hyp_edges:
        for code in (e["a"], e["b"]):
            if code not in pin_nodes:
                pin_nodes[code] = {
                    "id": code,
                    "label": short_label(code_to_full.get(code, code)),
                }

    degree: dict[str, int] = {c: 0 for c in pin_nodes}
    for e in pin_edges:
        degree[e["a"]] = degree.get(e["a"], 0) + 1
        degree[e["b"]] = degree.get(e["b"], 0) + 1

    nodes = []
    with_geo = 0
    for code, base in sorted(pin_nodes.items(), key=lambda x: x[1]["label"]):
        g = geo.get(code)
        lat = lon = oblast = None
        label = base["label"]
        if g:
            lat, lon = g["lat"], g["lon"]
            oblast = g["oblast"]
            label = g["name_short"] or label
            with_geo += 1
        nodes.append(
            {
                "id": code,
                "label": label,
                "full_name": code_to_full.get(code),
                "katottg": code,
                "oblast": oblast,
                "lat": lat,
                "lon": lon,
                "degree": degree.get(code, 0),
                "in_corpus": code in corpus_codes,
                "in_pin": any(code in (e["a"], e["b"]) for e in pin_edges),
            }
        )

    if not OBLASTS.exists():
        raise SystemExit(f"Missing {OBLASTS}")
    if not OUTLINE.exists():
        raise SystemExit(f"Missing {OUTLINE}")
    oblasts = json.loads(OBLASTS.read_text(encoding="utf-8"))
    outline = json.loads(OUTLINE.read_text(encoding="utf-8"))

    return {
        "meta": {
            "corpus_size": len(corpus),
            "pin_edges": len(pin_edges),
            "pin_nodes": len(nodes),
            "hypothesis_edges": len(hyp_edges),
            "known_edges": len(known_edges),
            "pin_corpus_edges": len(pin_corpus_edges),
            "nodes_with_geo": with_geo,
            "oblasts": len(oblasts.get("features", [])),
            "pin_source": "KSE-Loc-Data-Hub partnerships-hromadas-network.csv",
            "geo_source": "KSE-Loc-Data-Hub geography.csv (lat_center/lon_center)",
            "oblasts_source": "Natural Earth admin-1 → docs/geo/ukraine-oblasts.geojson",
            "outline_source": "docs/geo/ukraine-outline.geojson (mask outside UA)",
            "matching_source": "data/releases/matching-edges.json",
            "top_hypotheses": TOP_HYPOTHESES,
            "min_hypothesis_score": MIN_HYPOTHESIS_SCORE,
        },
        "oblasts": oblasts,
        "ukraine_outline": outline,
        "nodes": nodes,
        "edges": pin_edges + known_edges + pin_corpus_edges + hyp_edges,
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
        f"PIN {m['pin_nodes']}n/{m['pin_edges']}e · oblasts={m['oblasts']} · "
        f"known={m['known_edges']} pin∩corpus={m['pin_corpus_edges']} hyp={m['hypothesis_edges']}"
    )


if __name__ == "__main__":
    main()
