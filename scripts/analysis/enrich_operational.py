#!/usr/bin/env python3
"""Enrich v6 matching edges with operational boost fields (score unchanged).

Adds:
  fiscal_similarity   — closeness of own_income_per_capita (0–1), or null
  dream_overlap       — shared DREAM top-sector overlap |∩|/|∪| (0–1), or null
  operational_score   — only when geo_score is high enough for operational use:
                        0.55×geo + 0.25×fiscal + 0.20×dream (missing parts reweighted)

Does NOT modify combined v6 `score` (keeps known-pair regression intact).
Operational slice ranking prefers `operational_score` when present.

Usage:
  yarn enrich-operational
  (also called from export_edges.py)
"""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDGES = ROOT / "data" / "releases" / "matching-edges.json"
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
RESOURCES = ROOT / "data" / "releases" / "hromada-resources.json"
DREAM = ROOT / "data" / "releases" / "dream-priorities.json"

# Align with tracks.GEO_OPERATIONAL_MIN — only boost convenient neighbours
GEO_OPERATIONAL_MIN = 0.85


def fiscal_similarity(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    if a <= 0 or b <= 0:
        return None
    # ratio closeness on log scale: identical → 1, 10× apart → ~0
    ratio = max(a, b) / min(a, b)
    return float(max(0.0, 1.0 - math.log10(ratio)))


def dream_overlap(sectors_a: list[str] | None, sectors_b: list[str] | None) -> float | None:
    """|A∩B| / |A∪B| — set overlap (Jaccard). Null if either side has no sectors."""
    a = set(sectors_a or [])
    b = set(sectors_b or [])
    if not a or not b:
        return None
    union = a | b
    if not union:
        return None
    return len(a & b) / len(union)


def operational_score(geo: float, fiscal: float | None, dream: float | None) -> float | None:
    if geo < GEO_OPERATIONAL_MIN:
        return None
    parts: list[tuple[float, float]] = [(0.55, geo)]
    if fiscal is not None:
        parts.append((0.25, fiscal))
    if dream is not None:
        parts.append((0.20, dream))
    wsum = sum(w for w, _ in parts)
    if wsum <= 0:
        return None
    return round(sum(w * v for w, v in parts) / wsum, 3)


def load_by_name() -> dict[str, dict]:
    """name → {katottg, pcap, dream_sectors}."""
    by_name: dict[str, dict] = {}
    code_to_name: dict[str, str] = {}

    for row in json.loads(HROMADAS.read_text(encoding="utf-8")):
        name = (row.get("Name") or "").strip()
        code = (row.get("Katottg") or row.get("KATOTTG") or "").strip()
        if not name:
            continue
        by_name[name] = {"katottg": code or None, "pcap": None, "dream_sectors": []}
        if code:
            code_to_name[code] = name

    if RESOURCES.exists():
        for row in json.loads(RESOURCES.read_text(encoding="utf-8")).get("hromadas") or []:
            code = (row.get("katottg") or "").strip()
            name = code_to_name.get(code) or (row.get("name") or "").strip()
            if name in by_name:
                by_name[name]["pcap"] = row.get("own_income_per_capita")
            elif name:
                by_name[name] = {
                    "katottg": code or None,
                    "pcap": row.get("own_income_per_capita"),
                    "dream_sectors": [],
                }

    if DREAM.exists():
        for row in json.loads(DREAM.read_text(encoding="utf-8")).get("hromadas") or []:
            code = (row.get("katottg") or "").strip()
            name = code_to_name.get(code) or (row.get("name") or "").strip()
            sectors = list(row.get("top_sectors") or [])
            if name in by_name:
                by_name[name]["dream_sectors"] = sectors
            elif name:
                by_name[name] = {"katottg": code or None, "pcap": None, "dream_sectors": sectors}

    return by_name


def enrich_edges(edges: list[dict], by_name: dict[str, dict] | None = None) -> dict:
    by_name = by_name or load_by_name()
    enriched = 0
    with_ops = 0
    for e in edges:
        a = by_name.get(e.get("a") or "", {})
        b = by_name.get(e.get("b") or "", {})
        fiscal = fiscal_similarity(a.get("pcap"), b.get("pcap"))
        dream = dream_overlap(a.get("dream_sectors"), b.get("dream_sectors"))
        geo = float(e.get("geo_score") or 0.0)
        ops = operational_score(geo, fiscal, dream)

        e["fiscal_similarity"] = round(fiscal, 3) if fiscal is not None else None
        e["dream_overlap"] = round(dream, 3) if dream is not None else None
        e["operational_score"] = ops
        if fiscal is not None or dream is not None:
            enriched += 1
        if ops is not None:
            with_ops += 1

    return {"enriched": enriched, "with_operational_score": with_ops, "total": len(edges)}


def main() -> None:
    if not EDGES.exists():
        raise SystemExit(f"Missing {EDGES} — run yarn match first")
    edges = json.loads(EDGES.read_text(encoding="utf-8"))
    stats = enrich_edges(edges)
    EDGES.write_text(json.dumps(edges, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Enriched {EDGES.relative_to(ROOT)}: "
        f"{stats['enriched']}/{stats['total']} with fiscal/dream fields, "
        f"{stats['with_operational_score']} with operational_score "
        f"(geo>={GEO_OPERATIONAL_MIN})"
    )


if __name__ == "__main__":
    main()
