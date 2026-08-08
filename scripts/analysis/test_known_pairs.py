#!/usr/bin/env python3
"""Regression: curated known МСС pairs must exist and rank reasonably under v7.1.

Hard gates are calibrated to the ~5k-edge Goals corpus (wave C, 2026-08) and
scale with edge count after corpus growth (GISRR wave → ~43k edges). Absolute
top-20 from the ~70-Goals era no longer holds; absolute top-200/250 also
breaks when N grows ~9× while known-pair scores stay geo+network capped.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDGES = ROOT / "data" / "releases" / "matching-edges.json"
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from match import KNOWN_PAIRS  # noqa: E402

# Core narrative pairs — still the primary recovery story on the poster.
NIZHYN_CLUSTER = {
    frozenset(["Ніжинська міська територіальна громада", "Козелецька селищна територіальна громада"]),
    frozenset(["Батуринська міська територіальна громада", "Козелецька селищна територіальна громада"]),
    frozenset(["Ніжинська міська територіальна громада", "Батуринська міська територіальна громада"]),
}

# Wave-C calibration (~4950 edges): cluster ~top 4%, CNAP ~5%, expanded ~10%.
REF_EDGES = 4950
CLUSTER_TOP_BASE = 200
OPERATIONAL_TOP_BASE = 250
EXPANDED_TOP_BASE = 500

OPERATIONAL = frozenset(
    ["Слобожанська селищна територіальна громада", "Обухівська селищна територіальна громада"]
)


def scaled_top(base: int, n_edges: int) -> int:
    """Keep the wave-C percentile band as the corpus grows."""
    return max(base, int(round(base * n_edges / REF_EDGES)))


def ensure_edges() -> list[dict]:
    if not EDGES.exists():
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "analysis" / "match.py")])
    return json.loads(EDGES.read_text(encoding="utf-8"))


def main() -> None:
    edges = ensure_edges()
    n_edges = len(edges)
    cluster_top_n = scaled_top(CLUSTER_TOP_BASE, n_edges)
    operational_top_n = scaled_top(OPERATIONAL_TOP_BASE, n_edges)
    expanded_top_n = scaled_top(EXPANDED_TOP_BASE, n_edges)

    ranked = sorted(edges, key=lambda e: -e["score"])
    rank_map = {frozenset([e["a"], e["b"]]): i + 1 for i, e in enumerate(ranked)}
    known_flag = {
        frozenset([e["a"], e["b"]]): bool(e.get("known"))
        for e in edges
        if e.get("known")
    }

    failed: list[tuple[str, frozenset[str], int | None]] = []

    # All curated pairs must be in the edge list and flagged known.
    for pair in sorted(KNOWN_PAIRS, key=lambda p: sorted(p)[0]):
        r = rank_map.get(pair)
        if r is None:
            failed.append(("missing edge", pair, None))
        elif not known_flag.get(pair):
            failed.append(("known flag false — rematch/export?", pair, r))

    for pair in NIZHYN_CLUSTER:
        r = rank_map.get(pair)
        if r is None or r > cluster_top_n:
            failed.append((f"cluster top-{cluster_top_n}", pair, r))

    r_op = rank_map.get(OPERATIONAL)
    if r_op is None or r_op > operational_top_n:
        failed.append((f"operational top-{operational_top_n}", OPERATIONAL, r_op))

    expanded = KNOWN_PAIRS - NIZHYN_CLUSTER - {OPERATIONAL}
    for pair in expanded:
        r = rank_map.get(pair)
        if r is None or r > expanded_top_n:
            failed.append((f"expanded top-{expanded_top_n}", pair, r))

    print(
        f"Curated known N={len(KNOWN_PAIRS)} (of {n_edges} edges; "
        f"gates top-{cluster_top_n}/{operational_top_n}/{expanded_top_n} "
        f"scaled from {REF_EDGES})\nRanks:"
    )
    rows = []
    for pair in KNOWN_PAIRS:
        r = rank_map.get(pair, 10**9)
        rows.append((r, pair))
    for r, pair in sorted(rows):
        tag = ""
        if pair in NIZHYN_CLUSTER:
            tag = " [core tourism]"
        elif pair == OPERATIONAL:
            tag = " [core CNAP]"
        else:
            tag = " [expanded]"
        print(f"  #{r}: {' <-> '.join(sorted(pair))}{tag}")

    in_top50 = sum(1 for r, _ in rows if r <= 50)
    in_top200 = sum(1 for r, _ in rows if r <= 200)
    print(f"\nSummary: {in_top50}/{len(rows)} in top-50; {in_top200}/{len(rows)} in top-200")

    if failed:
        print(f"\nFAILED: {len(failed)} check(s)")
        for label, pair, r in failed:
            print(f"  [{label}] rank={r}: {' <-> '.join(sorted(pair))}")
        sys.exit(1)

    print(
        f"\nOK: core cluster top-{cluster_top_n}; CNAP top-{operational_top_n}; "
        f"expanded top-{expanded_top_n}; all {len(KNOWN_PAIRS)} flagged known"
    )


if __name__ == "__main__":
    main()
