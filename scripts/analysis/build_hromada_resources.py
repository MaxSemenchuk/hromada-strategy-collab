#!/usr/bin/env python3
"""Build hromada-level resource / competence covariates (proxy strategy signals).

Joins KSE-Loc-Data-Hub derived CSVs on KATOTTG at analysis time (not vendored),
plus population for own-income per capita. Output is a public release artifact
for complementary matching and proxy priorities where strategy PDFs are missing.

Usage:
  yarn hromada-resources
  python3 scripts/analysis/build_hromada_resources.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from enrich_from_kse import (  # noqa: E402
    _fetch_csv,
    competence_df,
    dfrr_df,
    health_facilities_by_hromada,
    latest_budget_df,
    population_df,
    war_status_df,
)

ROOT = Path(__file__).resolve().parents[2]
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
OUT = ROOT / "data" / "releases" / "hromada-resources.json"
MANIFEST = ROOT / "data" / "releases" / "hromada-resources.manifest.json"


def _num(val) -> float | None:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _int(val) -> int | None:
    n = _num(val)
    return int(n) if n is not None else None


def _jsonable(val):
    if val is None or isinstance(val, (str, bool, int, float)):
        return val
    if hasattr(val, "item"):
        try:
            return val.item()
        except Exception:
            pass
    return str(val)


def main() -> None:
    names_by_code: dict[str, str] = {}
    release_codes: set[str] | None = None
    if HROMADAS.exists():
        release_codes = set()
        for row in json.loads(HROMADAS.read_text(encoding="utf-8")):
            code = (row.get("Katottg") or row.get("KATOTTG") or "").strip()
            name = (row.get("Name") or "").strip()
            if code:
                release_codes.add(code)
                names_by_code[code] = name

    hromada = _fetch_csv("hromada").copy()
    hromada["hromada_code"] = hromada["hromada_code"].astype(str)
    if release_codes:
        hromada = hromada[hromada["hromada_code"].isin(release_codes)]
    else:
        crimea = hromada["oblast_name"].astype(str).str.contains("Крим", case=False, na=False)
        hromada = hromada[~crimea]

    budget = latest_budget_df()
    dfrr = dfrr_df()
    competence = competence_df()
    health = health_facilities_by_hromada()
    pop = population_df()
    war = war_status_df()

    # DFRR aggregate across years
    dfrr_agg = None
    if dfrr is not None and not dfrr.empty:
        g = dfrr.groupby("hromada_code", as_index=False).agg(
            dfrr_years=("year", "nunique"),
            dfrr_budget_planned_sum=("budget_planned", "sum"),
            dfrr_budget_executed_sum=("budget_executed", "sum"),
            dfrr_last_year=("year", "max"),
        )
        dfrr_agg = g.set_index("hromada_code")

    rows: list[dict] = []
    for _, h in hromada.iterrows():
        code = str(h["hromada_code"])
        name = names_by_code.get(code) or str(h.get("hromada_name") or "")
        rec: dict = {
            "katottg": code,
            "name": name,
            "oblast": None if pd.isna(h.get("oblast_name")) else h.get("oblast_name"),
            "type": None if pd.isna(h.get("type")) else h.get("type"),
        }

        # Population
        pop_total = None
        if pop is not None and code in pop.index:
            pop_total = _num(pop.loc[code].get("total_population_2022"))
            rec["population_2022"] = pop_total

        # Budget (latest year in KSE panel)
        if budget is not None and code in budget.index:
            b = budget.loc[code]
            if isinstance(b, pd.DataFrame):
                b = b.iloc[0]
            year = _int(b.get("year"))
            income_own = _num(b.get("income_own"))
            income_total = _num(b.get("income_total"))
            rec["budget_year"] = year
            rec["income_own"] = income_own
            rec["income_total"] = income_total
            rec["own_income_prop"] = _num(b.get("own_income_prop"))
            rec["income_tourist_fee"] = _num(b.get("income_tourist_fee"))
            rec["income_eco_tax"] = _num(b.get("income_eco_tax"))
            rec["diversification_income_score"] = _num(b.get("diversification_income_score"))
            if income_own is not None and pop_total and pop_total > 0:
                rec["own_income_per_capita"] = round(income_own / pop_total, 2)
            else:
                rec["own_income_per_capita"] = None
        else:
            rec["budget_year"] = None
            rec["income_own"] = None
            rec["income_total"] = None
            rec["own_income_prop"] = None
            rec["income_tourist_fee"] = None
            rec["income_eco_tax"] = None
            rec["diversification_income_score"] = None
            rec["own_income_per_capita"] = None

        # DFRR
        if dfrr_agg is not None and code in dfrr_agg.index:
            d = dfrr_agg.loc[code]
            rec["dfrr_years"] = _int(d.get("dfrr_years"))
            rec["dfrr_budget_planned_sum"] = _num(d.get("dfrr_budget_planned_sum"))
            rec["dfrr_budget_executed_sum"] = _num(d.get("dfrr_budget_executed_sum"))
            rec["dfrr_last_year"] = _int(d.get("dfrr_last_year"))
        else:
            rec["dfrr_years"] = None
            rec["dfrr_budget_planned_sum"] = None
            rec["dfrr_budget_executed_sum"] = None
            rec["dfrr_last_year"] = None

        # Community competence (missing ≠ zero — only 376 rows in source)
        if competence is not None and code in competence.index:
            c = competence.loc[code]
            if isinstance(c, pd.DataFrame):
                c = c.iloc[0]
            rec["youth_councils"] = _int(c.get("Youth_councils"))
            rec["youth_centers"] = _int(c.get("Youth_centers"))
            rec["business_support_centers"] = _int(c.get("Business_support_centers"))
            rec["competence_known"] = True
        else:
            rec["youth_councils"] = None
            rec["youth_centers"] = None
            rec["business_support_centers"] = None
            rec["competence_known"] = False

        # Health facilities (name-joined; may miss some)
        if health is not None and code in health.index:
            hf = health.loc[code]
            if isinstance(hf, pd.DataFrame):
                hf = hf.iloc[0]
            rec["health_primary"] = _int(hf.get("Первинна"))
            rec["health_specialized"] = _int(hf.get("Спеціалізована"))
            rec["health_emergency"] = _int(hf.get("Екстрена"))
            rec["health_ambulatory"] = _int(hf.get("Амбулаторія"))
            rec["health_fap"] = _int(hf.get("ФАП"))
            rec["health_known"] = True
        else:
            rec["health_primary"] = None
            rec["health_specialized"] = None
            rec["health_emergency"] = None
            rec["health_ambulatory"] = None
            rec["health_fap"] = None
            rec["health_known"] = False

        if war is not None and code in war.index:
            w = war.loc[code]
            if isinstance(w, pd.DataFrame):
                w = w.iloc[0]
            for col, key in (
                ("Status_war_sept", "war_status_sept"),
                ("Status_war_sept_ext", "war_status_sept_ext"),
                ("war_zone_10_10_2022", "war_zone_2022_10"),
                ("deoccupation_date", "war_deoccupation_date"),
            ):
                if col in w.index:
                    val = w.get(col)
                    if pd.notna(val):
                        rec[key] = _jsonable(val)

        rows.append({k: _jsonable(v) if not isinstance(v, (dict, list)) else v for k, v in rec.items()})

    war_keys = {k for r in rows for k in r if k.startswith("war_")}

    with_budget = sum(1 for r in rows if r.get("budget_year") is not None)
    with_pcap = sum(1 for r in rows if r.get("own_income_per_capita") is not None)
    with_dfrr = sum(1 for r in rows if r.get("dfrr_years") is not None)
    with_comp = sum(1 for r in rows if r.get("competence_known"))
    with_health = sum(1 for r in rows if r.get("health_known"))

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "kse": "https://github.com/kse-ua/KSE-Loc-Data-Hub",
            "zenodo": "10.5281/zenodo.15267573",
            "license": "MIT (KSE covariates); release packaging CC BY 4.0",
            "join_key": "katottg / hromada_code",
            "notes": [
                "Budget panel is KSE 2020–2022 (latest year per hromada), not live data.gov.ua oblast dumps.",
                "own_income_per_capita = income_own / total_population_2022 when both present.",
                "competence_known / health_known: missing ≠ zero.",
                "These are structural proxies — not a substitute for Goals text.",
            ],
        },
        "coverage": {
            "hromadas": len(rows),
            "with_budget": with_budget,
            "with_own_income_per_capita": with_pcap,
            "with_dfrr": with_dfrr,
            "with_competence": with_comp,
            "with_health": with_health,
            "war_fields": sorted(war_keys),
        },
        "hromadas": rows,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(
        json.dumps(
            {
                "file": "hromada-resources.json",
                "generated_at": payload["generated_at"],
                "coverage": payload["coverage"],
                "source": payload["source"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {OUT.relative_to(ROOT)} — {len(rows)} hromadas "
        f"(budget {with_budget}, pcap {with_pcap}, dfrr {with_dfrr}, "
        f"competence {with_comp}, health {with_health})"
    )


if __name__ == "__main__":
    main()
