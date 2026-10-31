"""Before/after spending around the first ММС agreement vs a control sample (diff-in-diff, descriptive).

Treated: hromadas whose FIRST registry agreement (KSE partnerships snapshot) started in year s in
{2020, 2021, 2022}. Window: year s-1 (pre) vs s+1 (post); year s is skipped (agreement mid-year).
Control: data/openbudget/control-sample.csv (random, by-oblast stratified), same window.
Outcome: change in log(per-capita total execution) and change in capital-spending share (КЕКВ 3xxx).
CIs: bootstrap over hromadas. NOT causal: the war (2022), selection into agreements, small N.
"""
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "openbudget"
rng = np.random.default_rng(42)

codes = {}
for r in csv.DictReader(open(OUT / "hromada-budget-codes.csv")):
    for col in ("codes_10digit_2023plus", "codes_11digit_to2022"):
        for c in filter(None, r[col].split(";")):
            codes[c] = r["katottg"]
pop = {x["Katottg"]: x["Population"] for x in json.load(open(ROOT / "data/releases/hromadas.json"))}

e = pd.read_csv(OUT / "economic.csv.gz", dtype={"kekv": str, "budget_code": str})
e = e[(e.fund == "T") & (e.quarter == 4)]
e["katottg"] = e.budget_code.map(codes)
e["capital"] = e.kekv.str.startswith("3")
g = e.groupby(["katottg", "year"]).apply(
    lambda d: pd.Series({"total": d.fakt.sum(), "capital": d.fakt[d.capital].sum()}), include_groups=False).reset_index()
g["pop"] = g.katottg.map(pop)
g = g[(g.total > 0) & (g["pop"] > 0)]
g["lpc"] = np.log(g.total / g["pop"])
g["capshare"] = g.capital / g.total
P = g.set_index(["katottg", "year"])

p = pd.read_csv(ROOT / "data/cache/kse/partnerships-hromadas-network.csv")
p["sy"] = pd.to_datetime(p.start).dt.year
first = pd.concat([p[["hromada_code.x", "sy"]].set_axis(["k", "sy"], axis=1),
                   p[["hromada_code.y", "sy"]].set_axis(["k", "sy"], axis=1)]).groupby("k").sy.min()
ctrl = set(pd.read_csv(OUT / "control-sample.csv").katottg)


def delta(k, a, b, col):
    try:
        return P.loc[(k, b), col] - P.loc[(k, a), col]
    except KeyError:
        return np.nan


def boot(x, n=2000):
    x = np.asarray(x, float)
    x = x[~np.isnan(x)]
    return np.percentile([rng.choice(x, len(x)).mean() for _ in range(n)], [2.5, 97.5]) if len(x) > 2 else (np.nan, np.nan)


rows = []
for s in (2020, 2021, 2022):
    T = [k for k in first[first == s].index]
    for col, name in (("lpc", "dlog per-capita spending"), ("capshare", "d capital share")):
        dt = np.array([delta(k, s - 1, s + 1, col) for k in T], float)
        dc = np.array([delta(k, s - 1, s + 1, col) for k in ctrl], float)
        dt, dc = dt[~np.isnan(dt)], dc[~np.isnan(dc)]
        if len(dt) < 3 or len(dc) < 3:
            continue
        did = dt.mean() - dc.mean()
        bs = [rng.choice(dt, len(dt)).mean() - rng.choice(dc, len(dc)).mean() for _ in range(2000)]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        rows.append((s, name, len(dt), len(dc), round(dt.mean(), 3), round(dc.mean(), 3), round(did, 3), round(lo, 3), round(hi, 3)))
res = pd.DataFrame(rows, columns=["start_year", "outcome", "n_treated", "n_control", "treated_delta",
                                  "control_delta", "diff_in_diff", "ci_lo", "ci_hi"])
print(res.to_string(index=False))
res.to_csv(OUT / "before_after_results.csv", index=False)
