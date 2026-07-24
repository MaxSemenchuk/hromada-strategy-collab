"""
Dual-track labels for matching edges (v6 scores unchanged).

  thematic   — high goals_cosine, low geo  → cold-start vision partners
  operational — high geo, not thematic     → convenient service co-sharers
  mixed      — everything else (incl. high goals+high geo, or mid scores)

Combined `score` is NOT a pure strategy match — see docs/project-history.md
(МСС registry section, 2026-07-24).
"""

from __future__ import annotations

from typing import Any

# Thresholds (document in MANIFEST / export manifest when changed)
GOALS_PERCENTILE = 90
GEO_THEMATIC_MAX = 0.35
GEO_OPERATIONAL_MIN = 0.85

TRACK_THEMATIC = "thematic"
TRACK_OPERATIONAL = "operational"
TRACK_MIXED = "mixed"


def goals_percentile_threshold(edges: list[dict], percentile: float = GOALS_PERCENTILE) -> float:
    """Inclusive percentile of goals_cosine over the edge list."""
    vals = sorted(float(e.get("goals_cosine") or 0.0) for e in edges)
    if not vals:
        return 0.0
    # nearest-rank, 1-indexed
    k = max(1, min(len(vals), int(round(percentile / 100.0 * len(vals)))))
    return vals[k - 1]


def assign_track(
    goals_cosine: float,
    geo_score: float,
    *,
    goals_floor: float,
    geo_thematic_max: float = GEO_THEMATIC_MAX,
    geo_operational_min: float = GEO_OPERATIONAL_MIN,
) -> str:
    if goals_cosine >= goals_floor and geo_score <= geo_thematic_max:
        return TRACK_THEMATIC
    if geo_score >= geo_operational_min:
        return TRACK_OPERATIONAL
    return TRACK_MIXED


def assign_tracks(edges: list[dict], *, goals_percentile: float = GOALS_PERCENTILE) -> dict[str, Any]:
    """Mutate edges in place: set `track`. Returns threshold metadata."""
    floor = goals_percentile_threshold(edges, goals_percentile)
    counts = {TRACK_THEMATIC: 0, TRACK_OPERATIONAL: 0, TRACK_MIXED: 0}
    for e in edges:
        track = assign_track(
            float(e.get("goals_cosine") or 0.0),
            float(e.get("geo_score") or 0.0),
            goals_floor=floor,
        )
        e["track"] = track
        counts[track] += 1
    return {
        "goalsPercentile": goals_percentile,
        "goalsFloor": round(floor, 3),
        "geoThematicMax": GEO_THEMATIC_MAX,
        "geoOperationalMin": GEO_OPERATIONAL_MIN,
        "counts": counts,
    }


def thematic_slice(edges: list[dict], *, limit: int | None = None) -> list[dict]:
    """Cold-start vision candidates: track=thematic, ranked by goals_cosine."""
    out = [e for e in edges if e.get("track") == TRACK_THEMATIC and not e.get("known")]
    out.sort(key=lambda e: (-float(e.get("goals_cosine") or 0), -float(e.get("score") or 0)))
    return out if limit is None else out[:limit]


def operational_slice(edges: list[dict], *, limit: int | None = None) -> list[dict]:
    """
    Convenient neighbours not already linked in the МСС network.
    track=operational, mss_network == 0, exclude known validation pairs.
    """
    out = [
        e
        for e in edges
        if e.get("track") == TRACK_OPERATIONAL
        and float(e.get("mss_network") or 0) == 0.0
        and not e.get("known")
    ]
    out.sort(key=lambda e: (-float(e.get("score") or 0), -float(e.get("geo_score") or 0)))
    return out if limit is None else out[:limit]
