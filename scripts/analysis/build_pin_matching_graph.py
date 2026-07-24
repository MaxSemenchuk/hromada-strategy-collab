#!/usr/bin/env python3
"""Build PIN + matching overlay viz: full МСС network + Leaflet map / force graph.

Sources:
  - data/cache/kse/partnerships-hromadas-network.csv
  - data/cache/kse/geography.csv
  - data/releases/matching-edges.json
  - data/releases/hromadas.json
  - scripts/hromada-output/*.json  (optional DonorsPrograms overrides)
  - docs/geo/ukraine-oblasts.geojson  (Natural Earth admin-1, simplified)

Writes docs/mss-pin-matching-graph.html
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PIN = ROOT / "data/cache/kse/partnerships-hromadas-network.csv"
GEO = ROOT / "data/cache/kse/geography.csv"
EDGES = ROOT / "data/releases/matching-edges.json"
HROMADAS = ROOT / "data/releases/hromadas.json"
OUTPUTS = ROOT / "scripts/hromada-output"
OBLASTS = ROOT / "docs/geo/ukraine-oblasts.geojson"
OUTLINE = ROOT / "docs/geo/ukraine-outline.geojson"
TEMPLATE = Path(__file__).with_name("mss_pin_matching_graph.template.html")
OUT = ROOT / "docs/mss-pin-matching-graph.html"

TOP_HYPOTHESES = 40
MIN_HYPOTHESIS_SCORE = 0.15

# Controlled vocab — keep in sync with scripts/structure-hromada-strategy.ts
DONOR_PATTERNS: list[tuple[str, list[str]]] = [
    ("EGAP", [r"\bEGAP\b"]),
    ("DOBRE", [r"\bDOBRE\b", r"USAID\s*DOBRE"]),
    ("GIZ", [r"\bGIZ\b"]),
    ("U-LEAD", [r"U-LEAD", r"U\s*LEAD"]),
    ("DECIDE", [r"\bDECIDE\b"]),
    ("ПРООН/UNDP", [r"ПРООН", r"\bUNDP\b", r"\bUN4"]),
    ("МФ Відродження", [r"Відродження", r"Renaissance", r"\bIRF\b"]),
    ("Ре:Форм", [r"Ре:Форм", r"Re:Form", r"ReForm"]),
    ("DESPRO", [r"\bDESPRO\b"]),
]
DONOR_NAMES = [name for name, _ in DONOR_PATTERNS]


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


def clip(text: str | None, n: int = 420) -> str | None:
    if not text:
        return None
    t = re.sub(r"\s+", " ", str(text)).strip()
    if len(t) <= n:
        return t
    return t[: n - 1].rstrip() + "…"


def infer_donors(text: str | None) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    for name, pats in DONOR_PATTERNS:
        if any(re.search(p, text, re.IGNORECASE) for p in pats):
            found.append(name)
    return found


def normalize_name_key(name: str) -> str:
    return re.sub(
        r"\s+",
        " ",
        re.sub(r"\s+(міська|сільська|селищна)\s+", " ", name.lower()),
    ).strip()


def load_output_donors() -> dict[str, list[str]]:
    """Optional overrides from scripts/hromada-output/*.json donors_programs."""
    out: dict[str, list[str]] = {}
    if not OUTPUTS.exists():
        return out
    allowed = set(DONOR_NAMES)
    for path in OUTPUTS.glob("*.json"):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        donors = raw.get("donors_programs")
        if not isinstance(donors, list) or not donors:
            continue
        cleaned = [d for d in donors if d in allowed]
        if not cleaned:
            continue
        # filename is kebab Name without extension — match loosely via stem
        key = normalize_name_key(path.stem.replace("-", " "))
        out[key] = cleaned
    return out


def donors_for_row(row: dict, output_donors: dict[str, list[str]]) -> list[str]:
    name = row.get("Name") or ""
    key = normalize_name_key(name)
    # Prefer structured DonorsPrograms if ever exported; else output override; else infer
    explicit = row.get("DonorsPrograms")
    if isinstance(explicit, str) and explicit.strip():
        parts = [p.strip() for p in explicit.split(",") if p.strip()]
        return [p for p in parts if p in DONOR_NAMES]
    if isinstance(explicit, list):
        return [p for p in explicit if p in DONOR_NAMES]
    if key in output_donors:
        return list(output_donors[key])
    inferred = infer_donors(row.get("PartnersMentioned"))
    # Also scan Goals/Projects lightly for program names
    extra = infer_donors(
        " ".join(
            filter(
                None,
                [row.get("Goals"), row.get("Projects"), row.get("MSSAgreements")],
            )
        )
    )
    return sorted(set(inferred + extra), key=lambda d: DONOR_NAMES.index(d))


def build_payload() -> dict:
    geo = load_geo()
    pin_nodes, pin_edges = load_pin()
    output_donors = load_output_donors()

    hromadas = json.loads(HROMADAS.read_text(encoding="utf-8"))
    corpus = [r for r in hromadas if r.get("Goals") and r.get("Katottg")]
    name_to_code = {r["Name"]: r["Katottg"] for r in corpus}
    code_to_row = {r["Katottg"]: r for r in corpus}
    code_to_full = {r["Katottg"]: r["Name"] for r in corpus}
    corpus_codes = set(name_to_code.values())

    code_donors: dict[str, list[str]] = {}
    for r in corpus:
        code = r["Katottg"]
        code_donors[code] = donors_for_row(r, output_donors)

    matching = json.loads(EDGES.read_text(encoding="utf-8"))
    corpus_matching = [
        e for e in matching if e["a"] in name_to_code and e["b"] in name_to_code
    ]
    known = [e for e in corpus_matching if e.get("known")]
    hypotheses = sorted(
        (
            e
            for e in corpus_matching
            if not e.get("known") and e["score"] >= MIN_HYPOTHESIS_SCORE
        ),
        key=lambda e: -e["score"],
    )[:TOP_HYPOTHESES]

    pin_keys = {tuple(sorted((e["a"], e["b"]))) for e in pin_edges}

    known_edges = [
        {
            "a": name_to_code[e["a"]],
            "b": name_to_code[e["b"]],
            "kind": "known",
            "score": e["score"],
        }
        for e in known
    ]
    hyp_edges = []
    for e in hypotheses:
        ca, cb = name_to_code[e["a"]], name_to_code[e["b"]]
        if tuple(sorted((ca, cb))) in pin_keys:
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

    for e in known_edges + hyp_edges:
        for code in (e["a"], e["b"]):
            if code not in pin_nodes:
                pin_nodes[code] = {
                    "id": code,
                    "label": short_label(code_to_full.get(code, code)),
                }

    # Ensure corpus hromadas with donors appear even if off PIN / matching
    for code, donors in code_donors.items():
        if donors and code not in pin_nodes:
            pin_nodes[code] = {
                "id": code,
                "label": short_label(code_to_full.get(code, code)),
            }

    degree: dict[str, int] = {c: 0 for c in pin_nodes}
    for e in pin_edges:
        degree[e["a"]] = degree.get(e["a"], 0) + 1
        degree[e["b"]] = degree.get(e["b"], 0) + 1

    nodes: list[dict] = []
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
        row = code_to_row.get(code) or {}
        donors = code_donors.get(code) or []
        nodes.append(
            {
                "id": code,
                "type": "hromada",
                "label": label,
                "full_name": code_to_full.get(code) or row.get("Name"),
                "katottg": code,
                "oblast": oblast or row.get("Oblast"),
                "lat": lat,
                "lon": lon,
                "degree": degree.get(code, 0),
                "in_corpus": code in corpus_codes,
                "in_pin": any(code in (e["a"], e["b"]) for e in pin_edges),
                "donors": donors,
                "has_donor": bool(donors),
                "goals": clip(row.get("Goals")),
                "partners": clip(row.get("PartnersMentioned"), 360),
                "mss": clip(row.get("MSSAgreements"), 280),
                "strategy_url": row.get("StrategyUrl"),
            }
        )

    # Fund nodes + donor edges (hromada ↔ fund)
    donor_edges: list[dict] = []
    fund_members: dict[str, list[str]] = {name: [] for name in DONOR_NAMES}
    for n in nodes:
        for d in n["donors"]:
            fund_members[d].append(n["id"])
            donor_edges.append(
                {"a": n["id"], "b": f"fund:{d}", "kind": "donor", "fund": d}
            )

    fund_nodes: list[dict] = []
    for name in DONOR_NAMES:
        members = fund_members[name]
        if not members:
            continue
        lats = [by["lat"] for by in nodes if by["id"] in members and by["lat"] is not None]
        lons = [by["lon"] for by in nodes if by["id"] in members and by["lon"] is not None]
        lat = sum(lats) / len(lats) if lats else None
        lon = sum(lons) / len(lons) if lons else None
        # Slight offset so fund markers don't sit exactly on a hromada
        if lat is not None and lon is not None:
            lat += 0.35
            lon += 0.25
        fund_nodes.append(
            {
                "id": f"fund:{name}",
                "type": "fund",
                "label": name,
                "full_name": name,
                "katottg": None,
                "oblast": None,
                "lat": lat,
                "lon": lon,
                "degree": len(members),
                "in_corpus": False,
                "in_pin": False,
                "donors": [],
                "has_donor": False,
                "members": members,
                "goals": None,
                "partners": None,
                "mss": None,
                "strategy_url": None,
            }
        )

    if not OBLASTS.exists():
        raise SystemExit(f"Missing {OBLASTS}")
    if not OUTLINE.exists():
        raise SystemExit(f"Missing {OUTLINE}")
    oblasts = json.loads(OBLASTS.read_text(encoding="utf-8"))
    outline = json.loads(OUTLINE.read_text(encoding="utf-8"))

    with_donors = sum(1 for n in nodes if n["has_donor"])

    return {
        "meta": {
            "corpus_size": len(corpus),
            "pin_edges": len(pin_edges),
            "pin_nodes": len(nodes),
            "hypothesis_edges": len(hyp_edges),
            "known_edges": len(known_edges),
            "nodes_with_geo": with_geo,
            "oblasts": len(oblasts.get("features", [])),
            "fund_nodes": len(fund_nodes),
            "donor_edges": len(donor_edges),
            "hromadas_with_donors": with_donors,
            "donor_vocab": DONOR_NAMES,
            "pin_source": "KSE-Loc-Data-Hub partnerships-hromadas-network.csv",
            "geo_source": "KSE-Loc-Data-Hub geography.csv (lat_center/lon_center)",
            "oblasts_source": "Natural Earth admin-1 → docs/geo/ukraine-oblasts.geojson",
            "outline_source": "docs/geo/ukraine-outline.geojson (mask outside UA)",
            "matching_source": "data/releases/matching-edges.json",
            "donors_source": "PartnersMentioned (+ hromada-output donors_programs)",
            "top_hypotheses": TOP_HYPOTHESES,
            "min_hypothesis_score": MIN_HYPOTHESIS_SCORE,
        },
        "oblasts": oblasts,
        "ukraine_outline": outline,
        "nodes": nodes + fund_nodes,
        "edges": pin_edges + known_edges + hyp_edges + donor_edges,
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
        f"PIN {m['pin_nodes']}n/{m['pin_edges']}e · funds={m['fund_nodes']} · "
        f"donors={m['hromadas_with_donors']} · known={m['known_edges']} hyp={m['hypothesis_edges']}"
    )


if __name__ == "__main__":
    main()
