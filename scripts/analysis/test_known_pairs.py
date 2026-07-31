#!/usr/bin/env python3
"""Regression: known МСС validation pairs must rank well under v6 scoring."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDGES = ROOT / "data" / "releases" / "matching-edges.json"

# Core validation trio — historically top 2–5 on small corpora; with true cosine
# (v7.1), length/hub blend, and ~70 Goals rows, expect top 20 by combined score.
NIZHYN_CLUSTER = {
    frozenset(["Ніжинська міська територіальна громада", "Козелецька селищна територіальна громада"]),
    frozenset(["Батуринська міська територіальна громада", "Козелецька селищна територіальна громада"]),
    frozenset(["Ніжинська міська територіальна громада", "Батуринська міська територіальна громада"]),
}
CLUSTER_TOP_N = 20

# Operational CNAP pair — goals-only historically buried (~#132); with geo should improve.
OPERATIONAL = frozenset(
    ["Слобожанська селищна територіальна громада", "Обухівська селищна територіальна громада"]
)
OPERATIONAL_TOP_N = 50


def ensure_edges() -> list[dict]:
    if not EDGES.exists():
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "analysis" / "match.py")])
    return json.loads(EDGES.read_text(encoding="utf-8"))


def main() -> None:
    edges = ensure_edges()
    ranked = sorted(edges, key=lambda e: -e["score"])
    rank_map = {frozenset([e["a"], e["b"]]): i + 1 for i, e in enumerate(ranked)}

    failed = []
    for pair in NIZHYN_CLUSTER:
        r = rank_map.get(pair)
        if r is None or r > CLUSTER_TOP_N:
            failed.append((f"cluster top-{CLUSTER_TOP_N}", pair, r))

    r_op = rank_map.get(OPERATIONAL)
    if r_op is None or r_op > OPERATIONAL_TOP_N:
        failed.append((f"operational top-{OPERATIONAL_TOP_N}", OPERATIONAL, r_op))

    print("Ranks:")
    for pair in NIZHYN_CLUSTER | {OPERATIONAL}:
        print(f"  #{rank_map.get(pair, '?')}: {' <-> '.join(sorted(pair))}")

    if failed:
        print(f"\nFAILED: {len(failed)} check(s)")
        for label, pair, r in failed:
            print(f"  [{label}] rank={r}: {' <-> '.join(sorted(pair))}")
        sys.exit(1)

    print(f"\nOK: Nizhyn cluster in top {CLUSTER_TOP_N}; operational pair in top {OPERATIONAL_TOP_N}")


if __name__ == "__main__":
    main()
