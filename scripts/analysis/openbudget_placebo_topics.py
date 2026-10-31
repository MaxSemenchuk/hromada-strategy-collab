"""Robustness for openbudget_before_after.py.

A. Placebo / pre-trend: same diff-in-diff but on two years BEFORE the agreement (s-2 -> s-1).
   A non-zero treated-vs-control gap here means differing trends, not an agreement effect.
B. Topic-specific: spending on the agreement's own topic (education КФКВК 09xx; communal/waste
   0620+0512) around the first agreement of that topic. Only the 319 hromadas with functional
   execution data; control = other agreement hromadas WITHOUT an agreement on that topic.
Inflation: all comparisons are within the same calendar window, so the common price level cancels
in the treated-minus-control difference; absolute (nominal) changes are not deflated.
"""
import csv
import json
import re
from pathlib import Path

import numpy as np
import openpyxl
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


def panel(path, mask, valcol_filter=None, by="year"):
    d = pd.read_csv(path, dtype={"kekv": str, "kfkvk": str, "budget_code": str})
    d = d[(d.fund == "T") & (d.quarter == 4) & d.fakt.notna()]
    d["katottg"] = d.budget_code.map(codes)
    d = d[mask(d)]
    s = d.groupby(["katottg", "year"]).fakt.sum().reset_index()
    s["pop"] = s.katottg.map(pop)
    s = s[(s.fakt > 0) & (s["pop"] > 0)]
    s["lpc"] = np.log(s.fakt / s["pop"])
    return s.set_index(["katottg", "year"]).lpc


def delta(P, k, a, b):
    try:
        return P.loc[(k, b)] - P.loc[(k, a)]
    except KeyError:
        return np.nan


def did(P, T, C, a, b):
    dt = np.array([delta(P, k, a, b) for k in T], float); dt = dt[~np.isnan(dt)]
    dc = np.array([delta(P, k, a, b) for k in C], float); dc = dc[~np.isnan(dc)]
    if len(dt) < 5 or len(dc) < 5:
        return None
    bs = [rng.choice(dt, len(dt)).mean() - rng.choice(dc, len(dc)).mean() for _ in range(2000)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return len(dt), len(dc), round(dt.mean(), 3), round(dc.mean(), 3), round(dt.mean() - dc.mean(), 3), round(lo, 3), round(hi, 3)


cols = ["n_treated", "n_control", "treated_delta", "control_delta", "diff_in_diff", "ci_lo", "ci_hi"]
p = pd.read_csv(ROOT / "data/cache/kse/partnerships-hromadas-network.csv")
p["start"] = pd.to_datetime(p.start)
long = pd.concat([p[["register_number", "start", "hromada_code.x"]].set_axis(["reg", "start", "k"], axis=1),
                  p[["register_number", "start", "hromada_code.y"]].set_axis(["reg", "start", "k"], axis=1)]).drop_duplicates()
first = long.groupby("k").start.min().dt.year
ctrl = set(pd.read_csv(OUT / "control-sample.csv").katottg)

print("== A. Placebo / pre-trend (total spending, s-2 -> s-1) ==")
Pall = panel(OUT / "economic.csv.gz", lambda d: d.kekv.notna())
rowsA = []
for s in (2021, 2022):
    r = did(Pall, list(first[first == s].index), ctrl, s - 2, s - 1)
    if r:
        rowsA.append((s, f"{s-2}->{s-1}", *r))
A = pd.DataFrame(rowsA, columns=["start_year", "window", *cols]); print(A.to_string(index=False))

print("\n== B. Topic-specific (functional execution, 319 agreement hromadas) ==")
ws = openpyxl.load_workbook(ROOT / "data/cache/mss/mss_registry.xlsx", read_only=True).active
title = {str(r[0]).strip(): str(r[1] or "") for r in list(ws.iter_rows(values_only=True))[1:]}
long["title"] = long.reg.astype(str).map(title)
TOP = {"education": (r"школ|освіт|ліцей|дошкіл|садоч|навчальн|підвіз|шкільн", lambda d: d.kfkvk.str.startswith("09")),
       "communal_waste": (r"відход|сміт|ТПВ|полігон|вивезен|сортув|водопостач|водовідвед|каналізац|благоустр",
                          lambda d: d.kfkvk.isin(["0620", "0512"]))}
agr_all = set(long.k)
rowsB = []
for name, (rx, mask) in TOP.items():
    hit = long[long.title.str.contains(rx, case=False, regex=True, na=False)]
    topic_first = hit.groupby("k").start.min().dt.year
    Pt = panel(OUT / "functional.csv.gz", mask)
    have = set(Pt.index.get_level_values(0))
    for s in (2020, 2021, 2022):
        T = [k for k in topic_first[topic_first == s].index if k in have]
        C = [k for k in agr_all - set(topic_first.index) if k in have]
        r = did(Pt, T, C, s - 1, s + 1)
        if r:
            rowsB.append((name, s, *r))
B = pd.DataFrame(rowsB, columns=["topic", "start_year", *cols]); print(B.to_string(index=False))
A.to_csv(OUT / "placebo_results.csv", index=False); B.to_csv(OUT / "topic_results.csv", index=False)
