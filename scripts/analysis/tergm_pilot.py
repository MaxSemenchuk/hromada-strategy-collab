"""TERGM pilot (experimental, not wired into `yarn match`).

Question: does treating the МСС network as *temporal* (formation dates from the
official registry) rather than a single static snapshot change what we can say
about goals_cosine / geo_score as predictors of tie formation?

Method: MPLE (maximum pseudo-likelihood) — pooled logistic regression over
discrete yearly transitions, predicting which not-yet-tied dyads form a tie in
each transition. This is the same estimator `btergm` (R) uses internally, just
implemented directly since no R/statnet is installed in this environment. Not
full MCMC-MLE `tergm` — see caveats printed at the end.

Ground-truth ties + dates come from KSE's own registry-to-katottg join
(data/cache/kse/partnerships-hromadas-network.csv — the same source
`enrich_from_kse.mss_network_score` reads). No name-matching needed: this file
is already keyed by hromada_code (katottg) with a `start` date per pair. This
supersedes an earlier v1 of this script that hand-extracted dates for only the
12 pairs in match.py's KNOWN_PAIRS by name-matching the raw registry xlsx —
that was 26x fewer events than what KSE already had joined for us.

`end` in that CSV is not a real dissolution date (every row has
active_2402==1; `end` looks like the contract's nominal term-end, not an
observed termination) — so this stays a formation-only model, no
dissolution/persistence side.

Also adds donor_overlap (dyadic: count of shared DonorsPrograms entries) and
donor_total_exposure (nodal control: combined donor-program count on both
sides, so overlap isn't confounded with "both sides are just generically
donor-active"). DonorsPrograms is extracted independently of Goals, so unlike
template_collision it isn't circular with goals_cosine — see conversation log
for why a "shared consultant" tie was considered and dropped (no structured
per-hromada consultant identity field exists yet).

Run: python3 scripts/analysis/tergm_pilot.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[2]
KSE_NETWORK_CSV = ROOT / "data" / "cache" / "kse" / "partnerships-hromadas-network.csv"

PERIOD_ENDS = list(range(2014, 2023))  # 8 transitions: 2014->15 ... 2021->22


def load_donor_programs() -> dict[str, set[str]]:
    """DonorsPrograms per hromada — extracted from strategy text independently
    of Goals, so not circular with goals_cosine (unlike template_collision,
    which is derived from the same subgoal lines as goals_cosine — see
    match.py's template_collision_fraction)."""
    raw = json.loads((ROOT / "data/releases/hromadas.json").read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("list", [])
    out: dict[str, set[str]] = {}
    for r in rows:
        katottg = r.get("Katottg") or r.get("KATOTTG")
        programs = r.get("DonorsPrograms")
        if katottg and programs:
            out[katottg] = set(programs)
    return out


def load_edges() -> dict[frozenset, dict]:
    edges = json.loads((ROOT / "data/releases/matching-edges.json").read_text(encoding="utf-8"))
    donors = load_donor_programs()
    out: dict[frozenset, dict] = {}
    for r in edges:
        ka, kb = r["a_katottg"], r["b_katottg"]
        dyad = frozenset((ka, kb))
        da, db = donors.get(ka, set()), donors.get(kb, set())
        out[dyad] = {
            "a": r["a"],
            "b": r["b"],
            "goals_cosine": r["goals_cosine"],
            "geo_score": r["geo_score"],
            "known": r.get("known", False),
            # dyadic: do they share a donor program (and how many)
            "donor_overlap": len(da & db),
            # nodal control: how donor-active is each side, regardless of overlap
            "donor_total_exposure": len(da) + len(db),
        }
    return out


def build_tie_events(corpus_dyads: set[frozenset]) -> list[tuple[frozenset, pd.Timestamp]]:
    df = pd.read_csv(KSE_NETWORK_CSV, low_memory=False)
    df["dyad"] = df.apply(lambda r: frozenset((r["hromada_code.x"], r["hromada_code.y"])), axis=1)
    df = df.drop_duplicates(subset="dyad")
    df["start"] = pd.to_datetime(df["start"])
    df = df[df["dyad"].isin(corpus_dyads)]
    # a dyad can appear under >1 register_number (multiple agreements); keep earliest.
    earliest = df.sort_values("start").groupby("dyad", as_index=False).first()
    return list(zip(earliest["dyad"], earliest["start"]))


def shared_partners_count(dyad: frozenset, adjacency: dict[str, set[str]]) -> int:
    ka, kb = tuple(dyad)
    return len(adjacency.get(ka, set()) & adjacency.get(kb, set()))


def fit_logit(X: np.ndarray, y: np.ndarray, x0: np.ndarray) -> np.ndarray:
    """MLE via BFGS, not sklearn's LogisticRegression.

    With ~12 events among ~2*10^5 rows and an intercept around -9 to -11,
    sklearn's default lbfgs solver reliably reports false convergence to a
    *wrong-signed* coefficient (verified against a hand-rolled log-likelihood
    profile — see conversation log). BFGS from a sane starting point finds the
    correct interior maximum.
    """
    Xd = np.column_stack([np.ones(len(X)), X])

    def negloglik(params: np.ndarray) -> float:
        z = Xd @ params
        return -(y * z - np.log1p(np.exp(z))).sum()

    def grad(params: np.ndarray) -> np.ndarray:
        z = Xd @ params
        p = 1.0 / (1.0 + np.exp(-z))
        return Xd.T @ (p - y)

    res = minimize(negloglik, x0=x0, jac=grad, method="BFGS")
    if not res.success:
        res = minimize(negloglik, x0=res.x, jac=grad, method="Nelder-Mead")
    if not res.success:
        raise RuntimeError(f"logit fit did not converge: {res.message}")
    return res.x


def main() -> None:
    edges = load_edges()
    events = build_tie_events(set(edges.keys()))
    event_dates = {dyad: date for dyad, date in events}

    print(f"Corpus dyads (from matching-edges.json): {len(edges)}")
    print(f"Dated known ties from KSE partnerships network (corpus-restricted): {len(events)}")
    print(f"  by year: {pd.Series([d.year for _, d in events]).value_counts().sort_index().to_dict()}")

    rows = []
    adjacency: dict[str, set[str]] = {}
    all_dyads = list(edges.keys())

    for period_idx in range(1, len(PERIOD_ENDS)):
        start_year, end_year = PERIOD_ENDS[period_idx - 1], PERIOD_ENDS[period_idx]
        start_cut = pd.Timestamp(f"{start_year}-12-31")
        end_cut = pd.Timestamp(f"{end_year}-12-31")

        tied_before = {d for d, dt in event_dates.items() if dt <= start_cut}
        formed_this_period = {
            d for d, dt in event_dates.items() if start_cut < dt <= end_cut
        }

        # adjacency snapshot as of start of this transition (for shared-partner stat)
        adjacency = {}
        for d in tied_before:
            ka, kb = tuple(d)
            adjacency.setdefault(ka, set()).add(kb)
            adjacency.setdefault(kb, set()).add(ka)

        at_risk = [d for d in all_dyads if d not in tied_before]
        for d in at_risk:
            r = edges[d]
            rows.append(
                {
                    "period": f"{start_year}->{end_year}",
                    "goals_cosine": r["goals_cosine"],
                    "geo_score": r["geo_score"],
                    "shared_partners_prior": shared_partners_count(d, adjacency),
                    "donor_overlap": r["donor_overlap"],
                    "donor_total_exposure": r["donor_total_exposure"],
                    "y": int(d in formed_this_period),
                }
            )

    data = pd.DataFrame(rows)
    print(f"\nPooled MPLE dataset: {len(data)} (dyad, period) rows, {data['y'].sum()} formation events")
    print(data.groupby("period")["y"].agg(["size", "sum"]))

    X_cols = ["goals_cosine", "geo_score", "shared_partners_prior", "donor_overlap", "donor_total_exposure"]
    X = data[X_cols].to_numpy()
    y = data["y"].to_numpy()

    params = fit_logit(X, y, x0=np.array([-9.0] + [0.0] * len(X_cols)))
    intercept, coefs = params[0], params[1:]
    print("\n=== MPLE point estimates (log-odds), BFGS ===")
    for name, coef in zip(X_cols, coefs):
        print(f"  {name:<22} {coef:+.3f}  (odds ratio {np.exp(coef):.3f})")
    print(f"  {'intercept':<22} {intercept:+.3f}")

    # Block bootstrap over the 5 time periods (btergm's own method: resample
    # whole transitions with replacement, not individual dyads).
    periods = data["period"].unique()
    rng = np.random.RandomState(20260810)
    boot_coefs = []
    n_boot = 300
    for _ in range(n_boot):
        sampled_periods = rng.choice(periods, size=len(periods), replace=True)
        chunks = [data[data["period"] == p] for p in sampled_periods]
        boot_df = pd.concat(chunks, ignore_index=True)
        if boot_df["y"].nunique() < 2:
            continue
        bx = boot_df[X_cols].to_numpy()
        by = boot_df["y"].to_numpy()
        try:
            bp = fit_logit(bx, by, x0=params)
            boot_coefs.append(bp[1:])
        except Exception:
            continue

    boot_coefs = np.array(boot_coefs)
    print(f"\n=== Block bootstrap over {len(periods)} periods ({len(boot_coefs)}/{n_boot} valid fits) ===")
    for i, name in enumerate(X_cols):
        lo, hi = np.percentile(boot_coefs[:, i], [2.5, 97.5])
        print(f"  {name:<22} 95% CI [{lo:+.3f}, {hi:+.3f}]")

    out = {
        "n_dyad_period_rows": len(data),
        "n_formation_events": int(data["y"].sum()),
        "n_periods": len(periods),
        "point_estimates": {name: float(c) for name, c in zip(X_cols, coefs)},
        "intercept": float(intercept),
        "bootstrap_95ci": {
            name: [float(np.percentile(boot_coefs[:, i], 2.5)), float(np.percentile(boot_coefs[:, i], 97.5))]
            for i, name in enumerate(X_cols)
        },
        "n_valid_bootstrap_fits": int(len(boot_coefs)),
    }
    out_path = ROOT / "internal" / "tergm-pilot-results.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
