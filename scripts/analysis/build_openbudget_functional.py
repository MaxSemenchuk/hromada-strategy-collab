"""One functional-classification (КФКВК) table for all downloaded hromadas.

Sources: data/openbudget/raw/*_FUNCTIONAL_* and the PROGRAM files (aggregated over
COD_CONS_EK == '0000' by COD_CONS_MB_FK) for the first 319 hromadas.
WARNING: the FUNCTIONAL API output has NO execution (FAKT) column -- its header lists PLANS_AMT
twice and the 3rd amount equals the adjusted plan (verified against PROGRAM data on 2026-10-31).
So `fakt` is NaN for FUNCTIONAL-only budgets; use PROGRAM (or ECONOMIC) output for execution.
Output: data/openbudget/functional.csv.gz  (budget_code, year, quarter, fund, kfkvk, kfkvk_name,
zat, plans, fakt) -- cumulative within the year, UAH.
"""
import csv
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[2] / "data" / "openbudget"
RAW = OUT / "raw"
cols = ["period", "fund", "budget_code", "kfkvk", "kfkvk_name", "zat", "plans", "fakt"]
fcols = cols[:7]

parts = []
for f in RAW.glob("*_FUNCTIONAL_*.csv"):
    if f.stat().st_size < 300:
        continue
    d = pd.read_csv(f, sep=";", header=0, usecols=range(7), names=fcols, dtype=str, encoding="utf-8")
    parts.append(d)
fun = pd.concat(parts, ignore_index=True)
fun["fakt"] = float("nan")

prog = []
for f in RAW.glob("*_PROGRAM_*.csv"):
    if f.stat().st_size < 300:
        continue
    d = pd.read_csv(f, sep=";", dtype=str, encoding="utf-8")
    d = d[d.COD_CONS_EK == "0000"]
    d = d.rename(columns={"REP_PERIOD": "period", "FUND_TYP": "fund", "COD_BUDGET": "budget_code",
                          "COD_CONS_MB_FK": "kfkvk", "COD_CONS_MB_FK_NAME": "kfkvk_name",
                          "ZAT_AMT": "zat", "PLANS_AMT": "plans", "FAKT_AMT": "fakt"})[cols]
    prog.append(d)
prog = pd.concat(prog, ignore_index=True)
for d in (fun, prog):
    for c in ("zat", "plans", "fakt"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
keys = ["period", "fund", "budget_code", "kfkvk"]
prog = prog.groupby(keys, as_index=False).agg(kfkvk_name=("kfkvk_name", "first"), zat=("zat", "sum"),
                                              plans=("plans", "sum"), fakt=("fakt", "sum"))
both = fun.merge(prog, on=keys, suffixes=("_f", "_p"))
if len(both):
    ok = (both.plans_f - both.plans_p).abs() < 1
    print(f"cross-check on {len(both)} overlapping rows: plans match {ok.mean():.1%}")
prog = prog[~prog.budget_code.isin(fun.budget_code.unique())]
allr = pd.concat([fun, prog], ignore_index=True)
allr["year"] = allr.period.str[3:].astype(int)
allr["quarter"] = allr.period.str[:2].astype(int) // 3
allr = allr.drop(columns="period")
allr.to_csv(OUT / "functional.csv.gz", index=False)
print(len(allr), "rows;", allr.budget_code.nunique(), "budgets;", allr.groupby("year").budget_code.nunique().to_dict())
