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

IMPORTANT — pseudo-replication: the 316 dyad-events are not 316 independent
formation decisions. They collapse to just 36 distinct `register_number`
contracts; the two biggest (#721 "Дністровський каньйон", #696 "Гуцул
Етнос") are near-complete cliques among 19 and 13 corpus hromadas
respectively, mechanically producing 170 and 78 simultaneous "positive" dyad
rows from ONE signing event each. A period-block bootstrap doesn't fix this
(it treats each period as one moving block, which is *also* wrong, just a
coarser version of the same problem). The bootstrap below resamples at the
contract-cluster level instead: the ~341k true-negative rows are one-row
clusters and stay fixed (huge, ~i.i.d., contribute negligible extra variance
either way); the handful of positive rows sharing a register_number move as
one block. This is the standard cluster-bootstrap fix for clustered binary
outcomes, and it is a materially different (more honest, wider) uncertainty
estimate than treating 316 as the effective N.

Affiliation-consistent weighting: a naive dyad-projection also distorts the
POINT ESTIMATE, not just its SE — a 19-party contract's 171 pairs each vote
in the likelihood as if independent, so it pulls the fit ~171x harder than a
simple 2-party contract despite being ONE decision. Each event row is
weighted by 1/C(k,2) (k = that contract's corpus-restricted party count) so
every contract casts one combined "vote" regardless of size — the standard
fix for projecting a bipartite affiliation network (hromada-joins-contract)
down to pairwise ties. True-negative rows keep weight 1.

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

# Annual cuts everywhere except 2020->2021, which is split into quarters.
# 264/316 formation events (84%) fall inside that single annual transition
# (two near-simultaneous multi-party contracts: a 19-hromada clique in
# 2021Q3, a 13-hromada clique in 2021Q2 — see docstring). Left annual, the
# adjacency snapshot for shared_partners_prior is frozen at 2020-12-31 for
# the entire year, so the Q2 clique's brand-new ties can never inform the
# Q3 clique's transitivity score even though they existed months earlier by
# then. Quarterly cuts let adjacency update between Q2 and Q3. This does
# NOT fix the pseudo-replication itself (each clique is still one contract,
# one cluster in the bootstrap) — it only lets the transitivity covariate
# see realistic within-year network growth. Other years get one or a
# handful of events each; splitting those into quarters would just multiply
# background rows for no inferential benefit.
PERIOD_CUTS = (
    [pd.Timestamp(f"{y}-12-31") for y in range(2014, 2021)]
    + [pd.Timestamp(d) for d in ("2021-03-31", "2021-06-30", "2021-09-30", "2021-12-31")]
    + [pd.Timestamp("2022-12-31")]
)


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


def build_tie_events(corpus_dyads: set[frozenset]) -> list[tuple[frozenset, pd.Timestamp, int]]:
    df = pd.read_csv(KSE_NETWORK_CSV, low_memory=False)
    df["dyad"] = df.apply(lambda r: frozenset((r["hromada_code.x"], r["hromada_code.y"])), axis=1)
    df = df.drop_duplicates(subset="dyad")
    df["start"] = pd.to_datetime(df["start"])
    df = df[df["dyad"].isin(corpus_dyads)]
    # a dyad can appear under >1 register_number (multiple agreements); keep earliest.
    earliest = df.sort_values("start").groupby("dyad", as_index=False).first()
    return list(zip(earliest["dyad"], earliest["start"], earliest["register_number"]))


def shared_partners_count(dyad: frozenset, adjacency: dict[str, set[str]]) -> int:
    ka, kb = tuple(dyad)
    return len(adjacency.get(ka, set()) & adjacency.get(kb, set()))


def fit_logit_design(Xd: np.ndarray, y: np.ndarray, x0: np.ndarray, w: np.ndarray | None = None) -> np.ndarray:
    """Weighted MLE via BFGS, not sklearn's LogisticRegression. `Xd` already
    has its leading intercept column of ones. `w` defaults to all-ones.

    With ~12 events among ~2*10^5 rows and an intercept around -9 to -11,
    sklearn's default lbfgs solver reliably reports false convergence to a
    *wrong-signed* coefficient (verified against a hand-rolled log-likelihood
    profile — see conversation log). BFGS from a sane starting point finds the
    correct interior maximum.
    """
    if w is None:
        w = np.ones(len(y))

    def negloglik(params: np.ndarray) -> float:
        z = Xd @ params
        return -(w * (y * z - np.log1p(np.exp(z)))).sum()

    def grad(params: np.ndarray) -> np.ndarray:
        z = Xd @ params
        p = 1.0 / (1.0 + np.exp(-z))
        return Xd.T @ (w * (p - y))

    res = minimize(negloglik, x0=x0, jac=grad, method="BFGS")
    if not res.success:
        res = minimize(negloglik, x0=res.x, jac=grad, method="Nelder-Mead")
    if not res.success:
        raise RuntimeError(f"logit fit did not converge: {res.message}")
    return res.x


def fit_logit(X: np.ndarray, y: np.ndarray, x0: np.ndarray, w: np.ndarray | None = None) -> np.ndarray:
    return fit_logit_design(np.column_stack([np.ones(len(X)), X]), y, x0, w)


def main() -> None:
    edges = load_edges()
    events = build_tie_events(set(edges.keys()))
    event_dates = {dyad: date for dyad, date, _ in events}
    event_register = {dyad: int(reg) for dyad, _, reg in events}

    print(f"Corpus dyads (from matching-edges.json): {len(edges)}")
    print(f"Dated known ties from KSE partnerships network (corpus-restricted): {len(events)}")
    print(f"  by year: {pd.Series([d.year for _, d, _ in events]).value_counts().sort_index().to_dict()}")
    n_contracts = len(set(event_register.values()))
    print(f"  collapse to {n_contracts} distinct register_number contracts (pseudo-replication — see docstring)")

    rows = []
    adjacency: dict[str, set[str]] = {}
    all_dyads = list(edges.keys())

    for period_idx in range(1, len(PERIOD_CUTS)):
        start_cut, end_cut = PERIOD_CUTS[period_idx - 1], PERIOD_CUTS[period_idx]
        period_label = f"{start_cut.date()}->{end_cut.date()}"

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
            is_event = d in formed_this_period
            rows.append(
                {
                    "period": period_label,
                    "goals_cosine": r["goals_cosine"],
                    "geo_score": r["geo_score"],
                    "shared_partners_prior": shared_partners_count(d, adjacency),
                    "donor_overlap": r["donor_overlap"],
                    "donor_total_exposure": r["donor_total_exposure"],
                    "y": int(is_event),
                    # non-events are each their own singleton cluster (no correlation
                    # among dyads that never tie); events cluster by contract, since a
                    # single multi-party agreement produces many simultaneous "events".
                    "cluster_id": f"contract:{event_register[d]}" if is_event else f"row:{len(rows)}",
                }
            )

    data = pd.DataFrame(rows)
    print(f"\nPooled MPLE dataset: {len(data)} (dyad, period) rows, {data['y'].sum()} formation events")
    print(data.groupby("period")["y"].agg(["size", "sum"]))

    # Affiliation-consistent weight: each contract casts one combined vote
    # regardless of how many corpus-restricted pairs it expands to.
    cluster_sizes = data.groupby("cluster_id")["cluster_id"].transform("size")
    data["weight"] = np.where(data["y"] == 1, 1.0 / cluster_sizes, 1.0)
    print(
        f"Weight range on event rows: {data.loc[data.y == 1, 'weight'].min():.4f}"
        f" .. {data.loc[data.y == 1, 'weight'].max():.4f}"
        f" (1.0 = singleton contract, small = big clique down-weighted)"
    )

    X_cols = ["goals_cosine", "geo_score", "shared_partners_prior", "donor_overlap", "donor_total_exposure"]
    X = data[X_cols].to_numpy()
    y = data["y"].to_numpy()
    w = data["weight"].to_numpy()

    params = fit_logit(X, y, x0=np.array([-9.0] + [0.0] * len(X_cols)), w=w)
    intercept, coefs = params[0], params[1:]
    print("\n=== MPLE point estimates (log-odds), BFGS ===")
    for name, coef in zip(X_cols, coefs):
        print(f"  {name:<22} {coef:+.3f}  (odds ratio {np.exp(coef):.3f})")
    print(f"  {'intercept':<22} {intercept:+.3f}")

    # Contract-cluster bootstrap: hold the huge, effectively-i.i.d. background
    # of true-negative rows fixed, and resample only the event-clusters (grouped
    # by register_number, so a 170-dyad clique from one contract moves as one
    # block, never split) with replacement. This targets the actual source of
    # uncertainty — "how would estimates change with a different set of ~36
    # comparable contracts" — instead of period-block bootstrap's coarser and
    # partially-redundant treatment of the same clustering.
    bg = data[data["y"] == 0]
    Xd_bg = np.column_stack([np.ones(len(bg)), bg[X_cols].to_numpy()])
    y_bg = bg["y"].to_numpy()
    w_bg = bg["weight"].to_numpy()

    event_rows = data[data["y"] == 1]
    clusters = [(g[X_cols].to_numpy(), g["weight"].to_numpy()) for _, g in event_rows.groupby("cluster_id")]
    n_clusters = len(clusters)
    print(f"Event rows collapse to {n_clusters} contract-clusters for the bootstrap")

    rng = np.random.RandomState(20260810)
    boot_coefs = []
    n_boot = 300
    for _ in range(n_boot):
        sampled = [clusters[i] for i in rng.randint(0, n_clusters, size=n_clusters)]
        ev_X = np.concatenate([s[0] for s in sampled], axis=0)
        ev_w = np.concatenate([s[1] for s in sampled], axis=0)
        Xd_ev = np.column_stack([np.ones(len(ev_X)), ev_X])
        Xd = np.vstack([Xd_bg, Xd_ev])
        yb = np.concatenate([y_bg, np.ones(len(ev_X))])
        wb = np.concatenate([w_bg, ev_w])
        try:
            bp = fit_logit_design(Xd, yb, x0=params, w=wb)
            boot_coefs.append(bp[1:])
        except Exception:
            continue

    boot_coefs = np.array(boot_coefs)
    print(f"\n=== Contract-cluster bootstrap ({n_clusters} clusters, {len(boot_coefs)}/{n_boot} valid fits) ===")
    for i, name in enumerate(X_cols):
        lo, hi = np.percentile(boot_coefs[:, i], [2.5, 97.5])
        print(f"  {name:<22} 95% CI [{lo:+.3f}, {hi:+.3f}]")

    out = {
        "n_dyad_period_rows": len(data),
        "n_formation_events": int(data["y"].sum()),
        "n_contracts": n_contracts,
        "point_estimates": {name: float(c) for name, c in zip(X_cols, coefs)},
        "intercept": float(intercept),
        "bootstrap_95ci": {
            name: [float(np.percentile(boot_coefs[:, i], 2.5)), float(np.percentile(boot_coefs[:, i], 97.5))]
            for i, name in enumerate(X_cols)
        },
        "n_valid_bootstrap_fits": int(len(boot_coefs)),
        "bootstrap_method": "contract-cluster (resample register_number clusters; background fixed)",
    }
    out_path = ROOT / "internal" / "tergm-pilot-results.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
