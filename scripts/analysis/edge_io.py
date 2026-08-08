"""Slim vs rich matching-edge I/O.

Release `matching-edges.json` keeps the full pairwise matrix for lab ranks
(test-known-pairs) but only core score fields — compact JSON. IMC package /
signals live on slices + mss-candidates.json; a full rich matrix may be
written under data/cache/matching/ (gitignored) for local tooling.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
RELEASE_EDGES = ROOT / "data" / "releases" / "matching-edges.json"
RICH_CACHE = ROOT / "data" / "cache" / "matching" / "matching-edges.rich.json"

# Always written to the public release matrix.
RELEASE_CORE_KEYS = (
    "a",
    "b",
    "a_katottg",
    "b_katottg",
    "score",
    "goals_cosine",
    "geo_score",
    "mss_network",
    "known",
    "track",
    "operational_score",
)


def slim_edge(edge: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in RELEASE_CORE_KEYS:
        if key not in edge:
            continue
        val = edge[key]
        if key == "operational_score" and val is None:
            continue
        out[key] = val
    return out


def write_json(path: Path, data: Any, *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if compact:
        text = json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"
    else:
        text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def write_release_edges(edges: Iterable[dict[str, Any]], path: Path | None = None) -> Path:
    """Write slim compact matrix for git / CC BY release."""
    out = path or RELEASE_EDGES
    write_json(out, [slim_edge(e) for e in edges], compact=True)
    return out


def write_rich_cache(edges: list[dict[str, Any]], path: Path | None = None) -> Path:
    """Full annotated matrix for local tooling (gitignored under data/cache/)."""
    out = path or RICH_CACHE
    write_json(out, edges, compact=True)
    return out


def load_matching_edges(
    path: Path | None = None,
    *,
    prefer_rich_cache: bool = False,
) -> list[dict[str, Any]]:
    if prefer_rich_cache and RICH_CACHE.exists():
        return json.loads(RICH_CACHE.read_text(encoding="utf-8"))
    p = path or RELEASE_EDGES
    return json.loads(p.read_text(encoding="utf-8"))


def ensure_packages(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate package/signals in memory when the release matrix is slim."""
    if not edges:
        return edges
    if any(e.get("package") or e.get("suggested_theme") for e in edges):
        return edges
    from mss_candidate import annotate_candidates
    from mss_suggest import annotate_edges, load_hromadas_by_name

    annotate_edges(edges, hromadas_by_name=load_hromadas_by_name())
    annotate_candidates(edges)
    return edges
