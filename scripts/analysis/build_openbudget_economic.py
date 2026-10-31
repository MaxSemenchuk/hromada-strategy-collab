"""Economic-classification (КЕКВ) execution panel for all downloaded hromadas.

Sources: data/openbudget/raw/*_ECONOMIC_* (347 hromadas) and, for the first 319 hromadas, the
PROGRAM files summed over COD_CONS_EK != '0000' (verified equal to ECONOMIC totals).
Output: data/openbudget/economic.csv.gz (budget_code, year, quarter, fund, kekv, kekv_name,
zat, plans, fakt), cumulative within the year, UAH.
"""
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[2] / "data" / "openbudget"
RAW = OUT / "raw"
num = ["zat", "plans", "fakt"]

eco = []
for f in RAW.glob("*_ECONOMIC_*.csv"):
    if f.stat().st_size < 300:
        continue
    d = pd.read_csv(f, sep=";", dtype=str, encoding="utf-8")
    eco.append(d.rename(columns={"REP_PERIOD": "period", "FUND_TYP": "fund", "COD_BUDGET": "budget_code",
                                 "COD_CONS_EK": "kekv", "COD_CONS_EK_NAME": "kekv_name", "ZAT_AMT": "zat",
                                 "PLANS_AMT": "plans", "FAKT_AMT": "fakt"})[
        ["period", "fund", "budget_code", "kekv", "kekv_name", *num]])
eco = pd.concat(eco, ignore_index=True)

prog = []
for f in RAW.glob("*_PROGRAM_*.csv"):
    if f.stat().st_size < 300:
        continue
    d = pd.read_csv(f, sep=";", dtype=str, encoding="utf-8")
    d = d[d.COD_CONS_EK != "0000"]
    prog.append(d.rename(columns={"REP_PERIOD": "period", "FUND_TYP": "fund", "COD_BUDGET": "budget_code",
                                  "COD_CONS_EK": "kekv", "COD_CONS_EK_NAME": "kekv_name", "ZAT_AMT": "zat",
                                  "PLANS_AMT": "plans", "FAKT_AMT": "fakt"})[
        ["period", "fund", "budget_code", "kekv", "kekv_name", *num]])
prog = pd.concat(prog, ignore_index=True)
for d in (eco, prog):
    for c in num:
        d[c] = pd.to_numeric(d[c], errors="coerce")
prog = prog.groupby(["period", "fund", "budget_code", "kekv"], as_index=False).agg(
    kekv_name=("kekv_name", "first"), zat=("zat", "sum"), plans=("plans", "sum"), fakt=("fakt", "sum"))

# cross-check on budgets present in both (the Nizhyn test file is not in raw/ -> use any overlap)
both = eco.merge(prog, on=["period", "fund", "budget_code", "kekv"], suffixes=("_e", "_p"))
if len(both):
    print(f"overlap {len(both)} rows; fakt match {((both.fakt_e.fillna(0) - both.fakt_p.fillna(0)).abs() < 1).mean():.1%}")
prog = prog[~prog.budget_code.isin(eco.budget_code.unique())]
allr = pd.concat([eco, prog], ignore_index=True)
allr["year"] = allr.period.str[3:].astype(int)
allr["quarter"] = allr.period.str[:2].astype(int) // 3
allr = allr.drop(columns="period")
allr.to_csv(OUT / "economic.csv.gz", index=False)
t = allr[(allr.fund == "T") & (allr.quarter == 4)].groupby(["budget_code", "year"]).fakt.sum()
print(len(allr), "rows;", allr.budget_code.nunique(), "budgets;", t.groupby("year").size().to_dict())
