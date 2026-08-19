#!/usr/bin/env python3
"""
Cooperation-game Monte Carlo simulator — expected value of investing in a
specific joint project (shared ЦНАП, joint water grant) for a candidate
hromada pair.

Two-layer risk model (see internal/game-theory-framing.md §5):
  q = P(negotiation succeeds, agreement signed)      -- coordination risk
  r = P(project delivers value | agreement signed)   -- execution risk

  EV_i = q * (r*S + (1-r)*F) + (1-q)*N - c

q, r, S, F, N, c are drawn from distributions per Monte Carlo sample, not
point estimates, so the output carries downside risk (P(EV<0), CVaR10)
alongside mean EV — cooperation can have positive expected value and still
be worth flagging as risky.

**All q priors and S/F/N/c payoffs below are elicited placeholders, not
fitted from data.** There is no real AIM-CC funnel data yet (pilot not
launched — see internal/aim-cc-field-experiment-prereg.md) and no real
hromada budget data in this corpus. Replace TRACK_Q_PRIOR / PROJECT_PARAMS
with real numbers as they become available (AIM-CC reply/call/signing
rates by arm for q; actual ЦНАП budgets / grant sizes for S/F/N/c). Until
then, treat output rankings as illustrating the *method*, not as
decision-grade advice on which pair to fund.

Usage:
  python scripts/analysis/coop_game_sim.py --project cnap --top-n 15
  python scripts/analysis/coop_game_sim.py --project water_grant \\
      --pair-a "Верховинська селищна територіальна громада" \\
      --pair-b "Кутська селищна територіальна громада"
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EDGES_PATH = ROOT / "data" / "releases" / "matching-edges.json"

# --- Layer 1: coordination risk (q) priors by discovery track -------------
# Placeholder means pending real AIM-CC reply/call/signing funnel data,
# set directionally per the game-theoretic framing: thematic moves both
# perceived payoff and reciprocity belief, operational moves belief only
# via geo-familiarity, mixed is closest to AIM-CC's random-control arm.
TRACK_Q_PRIOR = {
    "thematic": 0.35,
    "operational": 0.30,
    "mixed": 0.15,
}
Q_PRIOR_K = 8.0  # effective sample size behind the prior -> wide Beta, not a point estimate

# --- Layer 2: execution risk (r) and monetary payoffs, by project type ----
# Units: thousand UAH-equivalent, illustrative only (ASSUMPTION, not real
# budget data). (low, mode, high) feeds a Triangular draw; r_mean/r_k feed
# a Beta draw for execution risk given a signed agreement.
PROJECT_PARAMS: dict[str, dict[str, Any]] = {
    "cnap": {
        "label": "Спільний ЦНАП (адмінпослуги)",
        "r_mean": 0.65,
        "r_k": 10.0,  # mostly internal execution risk, no competing bidder
        "S": (50, 150, 400),   # annual savings if the merger delivers
        "F": (-100, -20, 0),   # signed but savings don't materialize (sunk integration cost)
        "N": (-15, -5, 0),     # negotiation fails, no agreement reached
        "c": (10, 25, 50),     # cost to negotiate/draft the agreement
    },
    "water_grant": {
        "label": "Спільна заявка на грант (вода)",
        "r_mean": 0.35,
        "r_k": 10.0,  # competitive donor-selection risk
        "S": (200, 800, 2000),  # grant secured
        "F": (-60, -20, 0),     # applied jointly, not awarded
        "N": (-10, -3, 0),      # negotiation fails, no joint application
        "c": (15, 30, 60),
    },
}


def beta_from_mean(mean: float, k: float, n: int, rng: np.random.Generator) -> np.ndarray:
    a = mean * k
    b = (1 - mean) * k
    return rng.beta(a, b, size=n)


def load_candidates(top_n: int, pair: tuple[str, str] | None) -> list[dict[str, Any]]:
    edges = json.loads(EDGES_PATH.read_text(encoding="utf-8"))
    edges = [e for e in edges if not e.get("known")]
    if pair:
        a, b = pair
        edges = [e for e in edges if {e["a"], e["b"]} == {a, b}]
        if not edges:
            raise SystemExit(f"No candidate edge found for pair {a!r} / {b!r}")
        return edges
    edges.sort(key=lambda e: e.get("score") or 0, reverse=True)
    return edges[:top_n]


def simulate_pair(
    edge: dict[str, Any], project: str, samples: int, rng: np.random.Generator
) -> dict[str, Any]:
    params = PROJECT_PARAMS[project]
    track = edge.get("track", "mixed")
    q_mean = TRACK_Q_PRIOR.get(track, TRACK_Q_PRIOR["mixed"])

    q = beta_from_mean(q_mean, Q_PRIOR_K, samples, rng)
    r = beta_from_mean(params["r_mean"], params["r_k"], samples, rng)
    S = rng.triangular(*params["S"], size=samples)
    F = rng.triangular(*params["F"], size=samples)
    N = rng.triangular(*params["N"], size=samples)
    c = rng.triangular(*params["c"], size=samples)

    ev = q * (r * S + (1 - r) * F) + (1 - q) * N - c
    ev_sorted = np.sort(ev)
    cvar10 = float(ev_sorted[: max(1, samples // 10)].mean())

    return {
        "a": edge["a"],
        "b": edge["b"],
        "track": track,
        "score": edge.get("score"),
        "q_mean": float(q.mean()),
        "r_mean": float(r.mean()),
        "ev_mean": float(ev.mean()),
        "ev_std": float(ev.std()),
        "p_loss": float((ev < 0).mean()),
        "cvar10": cvar10,
    }


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--project", choices=sorted(PROJECT_PARAMS), default="cnap")
    ap.add_argument(
        "--top-n", type=int, default=15, help="candidates to simulate, ranked by existing match score"
    )
    ap.add_argument("--pair-a")
    ap.add_argument("--pair-b")
    ap.add_argument("--samples", type=int, default=20_000)
    ap.add_argument(
        "--loss-aversion",
        type=float,
        default=1.0,
        help="weight on CVaR10 in the risk-adjusted score (higher = more downside-averse ranking)",
    )
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--json-out", type=Path, help="optional path to also dump results as JSON")
    args = ap.parse_args()

    pair = (args.pair_a, args.pair_b) if args.pair_a and args.pair_b else None
    rng = np.random.default_rng(args.seed)
    candidates = load_candidates(args.top_n, pair)

    results = [simulate_pair(e, args.project, args.samples, rng) for e in candidates]
    for r in results:
        r["risk_adjusted"] = r["ev_mean"] + args.loss_aversion * r["cvar10"]
    results.sort(key=lambda r: r["risk_adjusted"], reverse=True)

    params = PROJECT_PARAMS[args.project]
    print(f"\nProject: {params['label']}  ({args.project})  |  samples/pair={args.samples}")
    print(
        "ASSUMPTION: q priors and S/F/N/c payoffs are illustrative placeholders, "
        "not fitted from data — see script docstring before treating rankings as decision-grade.\n"
    )
    header = (
        f"{'pair':60}  {'track':11} {'score':>5}  {'q':>5}  {'r':>5}  "
        f"{'EV':>8}  {'P(loss)':>8}  {'CVaR10':>8}  {'risk_adj':>9}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        pair_label = f"{r['a'][:28]:28} / {r['b'][:28]:28}"
        print(
            f"{pair_label:60}  {r['track']:11} {r['score'] or 0:5.2f}  "
            f"{r['q_mean']:5.2f}  {r['r_mean']:5.2f}  {r['ev_mean']:8.1f}  "
            f"{r['p_loss']:8.1%}  {r['cvar10']:8.1f}  {r['risk_adjusted']:9.1f}"
        )

    if args.json_out:
        args.json_out.write_text(
            json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nWrote {len(results)} results to {args.json_out}")


if __name__ == "__main__":
    main()
