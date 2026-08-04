#!/usr/bin/env python3
"""Regression: curated known МСС pairs must exist and rank reasonably under v7.1.

Hard gates are calibrated to the ~5k-edge Goals corpus (wave C, 2026-08):
absolute top-20 from the ~70-Goals era no longer holds after corpus growth.
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
CLUSTER_TOP_N = 200  # was 20 on smaller corpora; ~top 4% of 4950

OPERATIONAL = frozenset(
    ["Слобожанська селищна територіальна громада", "Обухівська селищна територіальна громада"]
)
OPERATIONAL_TOP_N = 250  # was 50; geo/network recovery still required

# Expanded curated batch — must be present; soft rank band (IMC network + geo).
EXPANDED_TOP_N = 500


def ensure_edges() -> list[dict]:
    if not EDGES.exists():
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "analysis" / "match.py")])
    return json.loads(EDGES.read_text(encoding="utf-8"))


def main() -> None:
    edges = ensure_edges()
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
        if r is None or r > CLUSTER_TOP_N:
            failed.append((f"cluster top-{CLUSTER_TOP_N}", pair, r))

    r_op = rank_map.get(OPERATIONAL)
    if r_op is None or r_op > OPERATIONAL_TOP_N:
        failed.append((f"operational top-{OPERATIONAL_TOP_N}", OPERATIONAL, r_op))

    expanded = KNOWN_PAIRS - NIZHYN_CLUSTER - {OPERATIONAL}
    for pair in expanded:
        r = rank_map.get(pair)
        if r is None or r > EXPANDED_TOP_N:
            failed.append((f"expanded top-{EXPANDED_TOP_N}", pair, r))

    print(f"Curated known N={len(KNOWN_PAIRS)} (of {len(edges)} edges)\nRanks:")
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
        f"\nOK: core cluster top-{CLUSTER_TOP_N}; CNAP top-{OPERATIONAL_TOP_N}; "
        f"expanded top-{EXPANDED_TOP_N}; all {len(KNOWN_PAIRS)} flagged known"
    )


if __name__ == "__main__":
    main()
