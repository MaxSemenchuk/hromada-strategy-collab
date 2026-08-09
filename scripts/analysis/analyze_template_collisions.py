#!/usr/bin/env python3
"""One-off analysis: distribution of template_collision ratios across the
corpus, to pick a threshold before wiring the guardrail into match.py's
output. Read-only — does not touch data/releases/.

Usage:
  python3 scripts/analysis/analyze_template_collisions.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from match import (  # noqa: E402
    build_records,
    default_input,
    load_hromadas,
    template_collision,
    template_collision_fraction,
)

BUCKETS = [
    (0.90, 1.01, "≥0.90 (near-full-document dup)"),
    (0.70, 0.90, "0.70–0.90"),
    (0.50, 0.70, "0.50–0.70"),
    (0.30, 0.50, "0.30–0.50"),
    (0.10, 0.30, "0.10–0.30"),
    (0.0, 0.10, "<0.10"),
]


def main() -> None:
    hromadas = load_hromadas(default_input())
    records = build_records(hromadas)
    n = len(records)
    print(f"Analyzing {n} records ({n * (n - 1) // 2} pairs)...\n")

    results = []
    for i in range(n):
        for j in range(i + 1, n):
            frac = template_collision_fraction(records[i]["subgoals"], records[j]["subgoals"])
            results.append((frac, records[i]["name"], records[j]["name"], i, j))

    results.sort(key=lambda r: -r[0])

    print("=== Distribution (min line-overlap fraction, both directions) ===")
    for lo, hi, label in BUCKETS:
        count = sum(1 for r in results if lo <= r[0] < hi)
        print(f"{label:<30} {count}")

    print("\n=== Top 20 by overlap fraction ===")
    for frac, a, b, i, j in results[:20]:
        coll = template_collision(records[i]["subgoals"], records[j]["subgoals"])
        print(f"\n{frac:.2f}  {a[:35]} <-> {b[:35]}")
        if coll:
            print(f'   sample: "{coll[0][:70]}" / "{coll[1][:70]}"')


if __name__ == "__main__":
    main()
