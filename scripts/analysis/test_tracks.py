#!/usr/bin/env python3
"""Regression: dual-track labels and slice files stay coherent."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from tracks import (  # noqa: E402
    TRACK_MIXED,
    TRACK_OPERATIONAL,
    TRACK_THEMATIC,
    assign_track,
    assign_tracks,
    operational_slice,
    thematic_slice,
)

EDGES = ROOT / "data" / "releases" / "matching-edges.json"
THEMATIC = ROOT / "data" / "releases" / "matching-edges.thematic.json"
OPERATIONAL = ROOT / "data" / "releases" / "matching-edges.operational.json"

OPERATIONAL_PAIR = frozenset(
    ["Слобожанська селищна територіальна громада", "Обухівська селищна територіальна громада"]
)


def test_unit_rules() -> None:
    assert assign_track(0.10, 0.0, goals_floor=0.08) == TRACK_THEMATIC
    assert assign_track(0.10, 0.85, goals_floor=0.08) == TRACK_OPERATIONAL  # geo wins over dual-high
    assert assign_track(0.03, 0.85, goals_floor=0.08) == TRACK_OPERATIONAL
    assert assign_track(0.03, 0.6, goals_floor=0.08) == TRACK_MIXED
    # edge case: high goals + high geo → operational (geo gate), not thematic
    assert assign_track(0.12, 1.0, goals_floor=0.08) == TRACK_OPERATIONAL


def test_release_files() -> None:
    if not EDGES.exists():
        raise SystemExit(f"Missing {EDGES}")

    # Re-run export so tracks/slices are fresh (no embeddings needed)
    subprocess.check_call([sys.executable, str(ROOT / "scripts" / "analysis" / "export_edges.py")])

    edges = json.loads(EDGES.read_text(encoding="utf-8"))
    if not edges:
        raise SystemExit("matching-edges.json is empty")

    missing = [e for e in edges if e.get("track") not in (TRACK_THEMATIC, TRACK_OPERATIONAL, TRACK_MIXED)]
    if missing:
        raise SystemExit(f"{len(missing)} edges missing/invalid track")

    meta = assign_tracks([dict(e) for e in edges])  # idempotent check on copy
    if meta["counts"]["thematic"] < 1:
        raise SystemExit("expected at least one thematic edge")
    if meta["counts"]["operational"] < 1:
        raise SystemExit("expected at least one operational edge")

    # Known CNAP pair should be operational (high geo, low goals)
    op = next(
        e for e in edges if frozenset([e["a"], e["b"]]) == OPERATIONAL_PAIR
    )
    if op["track"] != TRACK_OPERATIONAL:
        raise SystemExit(f"Slobozhanske↔Obukhivka track={op['track']!r}, expected operational")

    thematic = json.loads(THEMATIC.read_text(encoding="utf-8"))
    operational = json.loads(OPERATIONAL.read_text(encoding="utf-8"))

    if any(e.get("known") for e in thematic + operational):
        raise SystemExit("slice files must exclude known=true validation pairs")
    if any(float(e.get("mss_network") or 0) > 0 for e in operational):
        raise SystemExit("operational slice must exclude existing МСС-network links")
    if any(e.get("track") != TRACK_THEMATIC for e in thematic):
        raise SystemExit("thematic slice contains non-thematic rows")
    if any(e.get("track") != TRACK_OPERATIONAL for e in operational):
        raise SystemExit("operational slice contains non-operational rows")

    # Slice helpers agree with files (full filters, then limit)
    assert thematic == thematic_slice(edges, limit=50)
    assert operational == operational_slice(edges, limit=50)

    print(
        f"OK: tracks thematic={meta['counts']['thematic']} "
        f"operational={meta['counts']['operational']} mixed={meta['counts']['mixed']}; "
        f"slices thematic={len(thematic)} operational={len(operational)}"
    )


def main() -> None:
    test_unit_rules()
    test_release_files()


if __name__ == "__main__":
    main()
