#!/usr/bin/env python3
"""
Shapley-value estimator for a real multi-party МСС coalition (e.g. register
#721 "Дністровський каньйон", 22 parties) — see internal/game-theory-framing.md
§6/§7 (hedonic coalition formation games).

Answers: if a coalition of hromadas jointly unlocks value v(S) (a grant tier,
shared infrastructure), how should that value be split "fairly" — where
fair means each member's average marginal contribution across all possible
orders of joining the coalition, not an equal split or first-come-first-served.

**Why Monte Carlo here is a different reason than in coop_game_sim.py.**
There, sampling handled *economic uncertainty* (q/r/S/F/N/c are random).
Here v(S) is deterministic given S — the problem is purely combinatorial:
exact Shapley value requires summing over all N! orderings (or 2^N-1
subsets), infeasible at N=22. We instead sample random orderings and
average the marginal contribution — the Monte Carlo *estimation error*
shrinks with more samples, there is no economic randomness being modeled.

**v(S) is an elicited placeholder, exactly like PROJECT_PARAMS in
coop_game_sim.py — not fitted to real grant/tourism-revenue data.** It uses
the real geo_score values already computed in matching-edges.json as a
"corridor synergy" proxy (Дністровський каньйон is a geographic corridor
cluster per docs/mss-cooperation-research.md:185 — real long-distance
pairs are rare, adjacency along the canyon is what drives it), scaled by
coalition size. Replace BASE_PER_MEMBER / SYNERGY_BONUS / the value
function itself once a real basis exists (actual joint-tourism-grant sizes,
actual visitor/revenue data).

Usage:
  python scripts/analysis/shapley_coalition_sim.py --register 721 --samples 6000
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import statistics
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
PARTNERSHIPS_CSV = ROOT / "data" / "cache" / "kse" / "partnerships-hromadas-network.csv"
EDGES_PATH = ROOT / "data" / "releases" / "matching-edges.json"

# --- placeholder value-function constants (thousand UAH-equivalent scale,
# same units as coop_game_sim.py — NOT fitted, see docstring) -------------
BASE_PER_MEMBER = 20.0   # value unlocked per member, before synergy bonus
SYNERGY_BONUS = 1.5      # multiplier on mean within-coalition geo_score


def load_cluster_nodes(register: str) -> list[str]:
    with PARTNERSHIPS_CSV.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r.get("register_number") == register]
    if not rows:
        raise SystemExit(f"No rows found for register_number={register!r}")
    nodes: set[str] = set()
    for r in rows:
        nodes.add(r["hromada_name.x"])
        nodes.add(r["hromada_name.y"])
    return sorted(nodes)


def build_geo_lookup() -> tuple[dict[frozenset[str], float], float, dict[str, str]]:
    edges = json.loads(EDGES_PATH.read_text(encoding="utf-8"))
    lookup: dict[frozenset[str], float] = {}
    all_names: set[str] = set()
    scores: list[float] = []
    for e in edges:
        a, b, g = e["a"], e["b"], e.get("geo_score")
        if g is None:
            continue
        lookup[frozenset((a, b))] = g
        all_names.add(a)
        all_names.add(b)
        scores.append(g)
    default_geo = statistics.mean(scores) if scores else 0.0
    return lookup, default_geo, {}


def match_short_to_full(short_names: list[str], full_names: set[str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for s in short_names:
        hit = next((n for n in full_names if n.startswith(s)), None)
        mapping[s] = hit if hit is not None else s  # fall back to short name itself
    return mapping


def make_value_fn(
    short_to_full: dict[str, str], geo_lookup: dict[frozenset[str], float], default_geo: float
):
    def geo(a: str, b: str) -> float:
        return geo_lookup.get(frozenset((short_to_full[a], short_to_full[b])), default_geo)

    def value(coalition_size: int, sum_pairwise_geo: float) -> float:
        if coalition_size < 2:
            return 0.0
        n_pairs = coalition_size * (coalition_size - 1) / 2
        mean_geo = sum_pairwise_geo / n_pairs if n_pairs else 0.0
        return BASE_PER_MEMBER * coalition_size * (1 + SYNERGY_BONUS * mean_geo)

    return geo, value


def estimate_shapley(
    nodes: list[str], geo_fn, value_fn, samples: int, rng: np.random.Generator
) -> dict[str, float]:
    n = len(nodes)
    totals = {node: 0.0 for node in nodes}
    idx = np.arange(n)
    for _ in range(samples):
        order = rng.permutation(idx)
        coalition: list[str] = []
        sum_geo = 0.0
        prev_value = 0.0
        for i in order:
            node = nodes[i]
            if coalition:
                sum_geo += sum(geo_fn(node, other) for other in coalition)
            coalition.append(node)
            new_value = value_fn(len(coalition), sum_geo)
            totals[node] += new_value - prev_value
            prev_value = new_value
    return {node: total / samples for node, total in totals.items()}


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--register", default="721", help="KSE register_number of the coalition")
    ap.add_argument("--samples", type=int, default=6000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json-out", type=Path)
    args = ap.parse_args()

    nodes = load_cluster_nodes(args.register)
    geo_lookup, default_geo, _ = build_geo_lookup()
    edges = json.loads(EDGES_PATH.read_text(encoding="utf-8"))
    full_names = {e["a"] for e in edges} | {e["b"] for e in edges}
    short_to_full = match_short_to_full(nodes, full_names)
    unmatched = [s for s, full in short_to_full.items() if full == s]

    geo_fn, value_fn = make_value_fn(short_to_full, geo_lookup, default_geo)
    rng = np.random.default_rng(args.seed)
    shapley = estimate_shapley(nodes, geo_fn, value_fn, args.samples, rng)

    full_coalition_value = value_fn(
        len(nodes),
        sum(geo_fn(a, b) for a, b in itertools.combinations(nodes, 2)),
    )

    print(f"\nCoalition register #{args.register}  |  {len(nodes)} parties  |  samples={args.samples}")
    print(
        f"Full-coalition v(N) = {full_coalition_value:.1f}  |  "
        f"default geo_score fallback (unmatched pairs) = {default_geo:.3f}"
    )
    if unmatched:
        print(f"Not in Goals-ready corpus (used corpus-mean geo_score fallback): {unmatched}")
    print(
        "ASSUMPTION: BASE_PER_MEMBER/SYNERGY_BONUS are illustrative placeholders, "
        "not fitted — see script docstring.\n"
    )

    ranked = sorted(shapley.items(), key=lambda kv: kv[1], reverse=True)
    total = sum(v for _, v in ranked)
    print(f"{'hromada':30}  {'shapley':>8}  {'% of total':>10}")
    print("-" * 52)
    for node, val in ranked:
        print(f"{node:30}  {val:8.2f}  {val / total:10.1%}")
    print("-" * 52)
    print(f"{'sum (efficiency check, should ~= v(N))':30}  {total:8.2f}")

    if args.json_out:
        out = {
            "register": args.register,
            "samples": args.samples,
            "unmatched_to_corpus": unmatched,
            "full_coalition_value": full_coalition_value,
            "shapley": dict(ranked),
        }
        args.json_out.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nWrote results to {args.json_out}")


if __name__ == "__main__":
    main()
