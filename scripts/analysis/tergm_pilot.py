"""TERGM pilot (experimental, not wired into `yarn match`).

Question: does treating the МСС network as *temporal* (formation dates from the
official registry) rather than a single static snapshot change what we can say
about goals_cosine / geo_score as predictors of tie formation?

Method: MPLE (maximum pseudo-likelihood) — pooled logistic regression over
discrete yearly transitions, predicting which not-yet-tied dyads form a tie in
each transition. This is the same estimator `btergm` (R) uses internally, just
implemented directly since no R/statnet is installed in this environment. Not
full MCMC-MLE `tergm` — see caveats printed at the end.

Known ties + dates were hand-extracted from data/cache/mss/mss_registry.xlsx by
name-matching against the 12 `known: true` pairs in match.py's KNOWN_PAIRS
(see conversation log for the extraction step). Hardcoded here because the
registry's free-text subject column isn't reliably machine-joinable to katottg
at scale — this pilot deliberately stays scoped to the 12 pairs we already
trust, not a full registry-wide join.

Run: python3 scripts/analysis/tergm_pilot.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

ROOT = Path(__file__).resolve().parents[2]

# (name_a, name_b, earliest registry date_added for a tie connecting them)
DATED_KNOWN_TIES = [
    ("Вашковецька сільська територіальна громада", "Сокирянська міська територіальна громада", "2017-12-06"),
    ("Рукшинська сільська територіальна громада", "Хотинська міська територіальна громада", "2017-12-29"),
    ("Слобожанська селищна територіальна громада", "Обухівська селищна територіальна громада", "2018-02-20"),
    ("Клішковецька сільська територіальна громада", "Хотинська міська територіальна громада", "2018-11-05"),
    ("Тернопільська міська територіальна громада", "Байковецька сільська територіальна громада", "2019-05-06"),
    ("Львівська міська територіальна громада", "Жовківська міська територіальна громада", "2020-01-23"),
    ("Верховинська селищна територіальна громада", "Кутська селищна територіальна громада", "2021-05-31"),
    ("Клішковецька сільська територіальна громада", "Рукшинська сільська територіальна громада", "2021-07-13"),
    ("Галицька міська територіальна громада", "Дубовецька сільська територіальна громада", "2021-07-23"),
    ("Ніжинська міська територіальна громада", "Козелецька селищна територіальна громада", "2021-10-28"),
    ("Батуринська міська територіальна громада", "Козелецька селищна територіальна громада", "2021-10-28"),
    ("Ніжинська міська територіальна громада", "Батуринська міська територіальна громада", "2021-10-28"),
]

PERIOD_ENDS = [2016, 2017, 2018, 2019, 2020, 2021]  # 5 transitions: 2016->17 ... 2020->21


def load_katottg_by_name() -> dict[str, str]:
    raw = json.loads((ROOT / "data/releases/hromadas.json").read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("list", [])
    out = {}
    for r in rows:
        name = r.get("Name")
        katottg = r.get("Katottg") or r.get("KATOTTG")
        if name and katottg:
            out[name] = katottg
    return out


def load_edges() -> dict[frozenset, dict]:
    edges = json.loads((ROOT / "data/releases/matching-edges.json").read_text(encoding="utf-8"))
    out: dict[frozenset, dict] = {}
    for r in edges:
        dyad = frozenset((r["a_katottg"], r["b_katottg"]))
        out[dyad] = {
            "a": r["a"],
            "b": r["b"],
            "goals_cosine": r["goals_cosine"],
            "geo_score": r["geo_score"],
            "known": r.get("known", False),
        }
    return out


def build_tie_events(name_to_katottg: dict[str, str]) -> list[tuple[frozenset, pd.Timestamp]]:
    events = []
    missing = []
    for a, b, date in DATED_KNOWN_TIES:
        ka, kb = name_to_katottg.get(a), name_to_katottg.get(b)
        if not ka or not kb:
            missing.append((a, b))
            continue
        events.append((frozenset((ka, kb)), pd.Timestamp(date)))
    if missing:
        print(f"WARNING: {len(missing)} dated pair(s) could not be resolved to katottg: {missing}")
    return events


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

    res = minimize(negloglik, x0=x0, method="BFGS")
    if not res.success:
        raise RuntimeError(f"logit fit did not converge: {res.message}")
    return res.x


def main() -> None:
    name_to_katottg = load_katottg_by_name()
    edges = load_edges()
    events = build_tie_events(name_to_katottg)
    event_dates = {dyad: date for dyad, date in events}

    print(f"Corpus dyads (from matching-edges.json): {len(edges)}")
    print(f"Dated known ties resolved: {len(events)} / {len(DATED_KNOWN_TIES)}")
    for dyad, date in sorted(events, key=lambda x: x[1]):
        row = edges.get(dyad)
        label = f"{row['a']} <-> {row['b']}" if row is not None else "(not in matching-edges corpus)"
        print(f"  {date.date()}  {label}")

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
                    "y": int(d in formed_this_period),
                }
            )

    data = pd.DataFrame(rows)
    print(f"\nPooled MPLE dataset: {len(data)} (dyad, period) rows, {data['y'].sum()} formation events")
    print(data.groupby("period")["y"].agg(["size", "sum"]))

    X_cols = ["goals_cosine", "geo_score", "shared_partners_prior"]
    X = data[X_cols].to_numpy()
    y = data["y"].to_numpy()

    params = fit_logit(X, y, x0=np.array([-9.0, 0.0, 0.0, 0.0]))
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
