#!/usr/bin/env python3
"""Build a "digital democracy barometer" from e-dem.ua's live public API.

e-dem.ua (OpenCity / EGAP — Фонд Східна Європа, Мінцифра, SDC) runs the
dominant e-participation platform for Ukrainian hromadas: e-petitions and
participatory ("громадський") budgets on hromada-specific subdomains. Unlike
KSE-Loc-Data-Hub's `edem-data.csv` (a static Sept-2022 scrape, see
docs/external-data-sources.md), this hits the platform's own
`external_api/{petitions,budgets}/statistics.json` endpoints directly, so
coverage and counts are current as of run time.

Records come back keyed by legacy KOATUU ("KOATYY"/"KOATTU"), not katottg —
mapped via KSE's admin map (`enrich_from_kse.koatuu_to_hromada`). Rows for
rayon/oblast councils and the platform's test stand are dropped (they carry a
KOATUU code but are not hromadas).

Usage:
  yarn edem-barometer
  python3 scripts/analysis/build_edem_barometer.py
"""

from __future__ import annotations

import json
import re
import ssl
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from enrich_from_kse import koatuu_to_hromada, war_status_df

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "cache" / "edem"
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
OUT = ROOT / "data" / "releases" / "edem-barometer.json"
MANIFEST = ROOT / "data" / "releases" / "edem-barometer.manifest.json"

UA = "hromada-strategy-collab/0.1 (+https://github.com/MaxSemenchuk/hromada-strategy-collab; research)"
BASE = "https://e-dem.ua/external_api"

# Non-hromada entities that legitimately carry a KOATUU code on this platform.
NON_HROMADA_RE = re.compile(
    r"районна рада|обласна рада|обласна державна адмін|ОДА$|тестова громада",
    re.I,
)


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        ctx = ssl.create_default_context()
        try:
            ctx.load_default_certs()
        except Exception:
            pass
        return ctx


def _fetch_json(path: str) -> list[dict]:
    url = f"{BASE}/{path}?oms_id="
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, context=_ssl_context(), timeout=60) as resp:
        return json.loads(resp.read())


def _num(v) -> float:
    try:
        return float(v) if v is not None else 0.0
    except (TypeError, ValueError):
        return 0.0


def _clean(v):
    return None if pd.isna(v) else v


def _koatuu(rec: dict) -> str:
    v = (rec.get("KOATYY") or rec.get("KOATTU") or "").strip()
    return v.zfill(10) if v else v


def _rank_score(values: pd.Series) -> pd.Series:
    """0 for non-positive/missing; percentile rank (0, 100] among positives."""
    positive = values[values > 0]
    pct = positive.rank(pct=True) * 100
    return pct.reindex(values.index).fillna(0.0).round(1)


def main() -> None:
    CACHE.mkdir(parents=True, exist_ok=True)
    print("Fetching e-dem.ua petitions + budgets statistics…")
    petitions_raw = _fetch_json("petitions/statistics.json")
    budgets_raw = _fetch_json("budgets/statistics.json")
    (CACHE / "petitions.json").write_text(
        json.dumps(petitions_raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    (CACHE / "budgets.json").write_text(
        json.dumps(budgets_raw, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(f"  petitions: {len(petitions_raw)} rows, budgets: {len(budgets_raw)} rows")

    crosswalk = koatuu_to_hromada()
    if not crosswalk:
        raise RuntimeError("KOATUU→hromada crosswalk empty — check KSE admin_map fetch")

    names_by_code: dict[str, str] = {}
    oblast_by_code: dict[str, str] = {}
    population_by_code: dict[str, int] = {}
    universe: list[str] = []
    if HROMADAS.exists():
        for row in json.loads(HROMADAS.read_text(encoding="utf-8")):
            code = (row.get("Katottg") or "").strip()
            if code:
                universe.append(code)
                names_by_code[code] = row.get("Name") or ""
                oblast_by_code[code] = row.get("Oblast") or ""
                pop = row.get("Population")
                if isinstance(pop, (int, float)) and pop > 0:
                    population_by_code[code] = int(pop)

    war = war_status_df()

    per: dict[str, dict] = {code: {} for code in universe}
    unmatched_petitions = 0
    unmatched_budgets = 0

    for rec in petitions_raw:
        city = rec.get("City") or ""
        if NON_HROMADA_RE.search(city):
            continue
        code = crosswalk.get(_koatuu(rec))
        if not code or code not in per:
            unmatched_petitions += 1
            continue
        row = per[code]
        row["petition_url"] = rec.get("Url")
        row["petitions_total"] = row.get("petitions_total", 0) + _num(rec.get("Petitions"))
        row["petitions_active"] = row.get("petitions_active", 0) + _num(rec.get("PetitionsActive"))
        row["petitions_pending"] = row.get("petitions_pending", 0) + _num(rec.get("PetitionsPending"))
        row["petition_online_votes"] = row.get("petition_online_votes", 0) + _num(rec.get("OnlineVotes"))

    for rec in budgets_raw:
        title = rec.get("Title") or rec.get("City") or ""
        if NON_HROMADA_RE.search(title):
            continue
        code = crosswalk.get(_koatuu(rec))
        if not code or code not in per:
            unmatched_budgets += 1
            continue
        row = per[code]
        row["budget_url"] = rec.get("Url")
        row["budget_amount_total"] = row.get("budget_amount_total", 0) + _num(rec.get("Budgets"))
        row["budget_projects"] = row.get("budget_projects", 0) + _num(rec.get("Projects"))
        row["budget_project_winners"] = row.get("budget_project_winners", 0) + _num(rec.get("ProjectVinners"))
        row["budget_online_votes"] = row.get("budget_online_votes", 0) + _num(rec.get("OnlineVotes"))
        row["budget_offline_votes"] = row.get("budget_offline_votes", 0) + _num(rec.get("OfflineVotes"))

    df = pd.DataFrame.from_dict(per, orient="index").reindex(universe)
    for col in (
        "petitions_total",
        "petitions_active",
        "petitions_pending",
        "petition_online_votes",
        "budget_amount_total",
        "budget_projects",
        "budget_project_winners",
        "budget_online_votes",
        "budget_offline_votes",
    ):
        if col not in df.columns:
            df[col] = 0.0
        df[col] = df[col].fillna(0.0)

    df["petition_activity_score"] = _rank_score(df["petitions_total"])
    df["petition_participation_score"] = _rank_score(df["petition_online_votes"])
    df["budget_activity_score"] = _rank_score(df["budget_projects"])
    df["budget_scale_score"] = _rank_score(df["budget_amount_total"])
    df["overall_score"] = (
        df[
            [
                "petition_activity_score",
                "petition_participation_score",
                "budget_activity_score",
                "budget_scale_score",
            ]
        ]
        .mean(axis=1)
        .round(1)
    )

    positive = df.loc[df["overall_score"] > 0, "overall_score"]
    tier_bounds = [0.0, 0.0, 0.0, 0.0]
    if len(positive) >= 4:
        tier_bounds = [0.0] + list(positive.quantile([1 / 3, 2 / 3, 1.0]).round(1))

    def tier(score: float) -> str:
        if score <= 0:
            return "не підключено"
        if score <= tier_bounds[1]:
            return "низький"
        if score <= tier_bounds[2]:
            return "середній"
        return "високий"

    df["tier"] = df["overall_score"].map(tier)

    # Per-capita view: absolute counts favor big cities by population alone.
    # Below MIN_POP_FOR_RANK a single petition/project swings the rate wildly,
    # so those hromadas get raw per-capita numbers but are excluded from the
    # per-capita score/tier (not ranked, not silently scored 0).
    MIN_POP_FOR_RANK = 1500
    df["population"] = pd.Series(population_by_code).reindex(universe)
    has_pop = df["population"] > 0
    pop_floor = df["population"] >= MIN_POP_FOR_RANK

    petitions_per_10k = (df["petitions_total"] / df["population"] * 10000).where(has_pop)
    budget_per_capita = (df["budget_amount_total"] / df["population"]).where(has_pop)
    df["petitions_per_10k_pop"] = petitions_per_10k.round(2)
    df["budget_uah_per_capita"] = budget_per_capita.round(2)

    df["petition_intensity_score"] = _rank_score(petitions_per_10k.where(pop_floor).fillna(0.0))
    df["budget_intensity_score"] = _rank_score(budget_per_capita.where(pop_floor).fillna(0.0))
    df["overall_score_per_capita"] = (
        df[["petition_intensity_score", "budget_intensity_score"]].mean(axis=1).round(1)
    )
    df.loc[~pop_floor, "overall_score_per_capita"] = float("nan")

    positive_pc = df.loc[df["overall_score_per_capita"] > 0, "overall_score_per_capita"]
    tier_bounds_pc = [0.0, 0.0, 0.0, 0.0]
    if len(positive_pc) >= 4:
        tier_bounds_pc = [0.0] + list(positive_pc.quantile([1 / 3, 2 / 3, 1.0]).round(1))

    def tier_pc(score: float) -> str:
        if pd.isna(score):
            return "населення замале"
        if score <= 0:
            return "не підключено"
        if score <= tier_bounds_pc[1]:
            return "низький"
        if score <= tier_bounds_pc[2]:
            return "середній"
        return "високий"

    df["tier_per_capita"] = df["overall_score_per_capita"].map(tier_pc)

    war_flags = {}
    if war is not None:
        for code in df.index:
            if code in war.index:
                w = war.loc[code]
                if isinstance(w, pd.DataFrame):
                    w = w.iloc[0]
                war_flags[code] = w.get("Status_war_sept")

    rows: list[dict] = []
    for code, r in df.iterrows():
        rows.append(
            {
                "katottg": code,
                "name": names_by_code.get(code, ""),
                "oblast": oblast_by_code.get(code, ""),
                "on_petition_platform": pd.notna(r.get("petition_url")),
                "petitions_total": int(r["petitions_total"]),
                "petitions_active": int(r.get("petitions_active", 0)),
                "petitions_pending": int(r.get("petitions_pending", 0)),
                "petition_online_votes": int(r["petition_online_votes"]),
                "petition_url": _clean(r.get("petition_url")),
                "on_budget_platform": pd.notna(r.get("budget_url")),
                "budget_projects": int(r["budget_projects"]),
                "budget_amount_total_uah": int(r["budget_amount_total"]),
                "budget_project_winners": int(r.get("budget_project_winners", 0)),
                "budget_online_votes": int(r.get("budget_online_votes", 0)),
                "budget_offline_votes": int(r.get("budget_offline_votes", 0)),
                "budget_url": _clean(r.get("budget_url")),
                "petition_activity_score": r["petition_activity_score"],
                "petition_participation_score": r["petition_participation_score"],
                "budget_activity_score": r["budget_activity_score"],
                "budget_scale_score": r["budget_scale_score"],
                "overall_score": r["overall_score"],
                "tier": r["tier"],
                "population": int(r["population"]) if pd.notna(r.get("population")) else None,
                "petitions_per_10k_pop": _clean(r.get("petitions_per_10k_pop")),
                "budget_uah_per_capita": _clean(r.get("budget_uah_per_capita")),
                "overall_score_per_capita": _clean(r.get("overall_score_per_capita")),
                "tier_per_capita": r["tier_per_capita"],
                "war_status_sept_2022": _clean(war_flags.get(code)),
            }
        )

    rows.sort(key=lambda x: -x["overall_score"])

    connected = sum(1 for r in rows if r["on_petition_platform"] or r["on_budget_platform"])
    with_petitions = sum(1 for r in rows if r["on_petition_platform"])
    with_budget = sum(1 for r in rows if r["on_budget_platform"])
    by_tier = {t: sum(1 for r in rows if r["tier"] == t) for t in ("високий", "середній", "низький", "не підключено")}
    by_tier_pc = {
        t: sum(1 for r in rows if r["tier_per_capita"] == t)
        for t in ("високий", "середній", "низький", "не підключено", "населення замале")
    }
    with_population = sum(1 for r in rows if r["population"] is not None)

    payload = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {
            "platform": "e-dem.ua (OpenCity / EGAP — Фонд Східна Європа, Мінцифра, SDC)",
            "endpoints": [
                f"{BASE}/petitions/statistics.json",
                f"{BASE}/budgets/statistics.json",
            ],
            "join_key": "KOATUU (legacy, zero-padded to 10 digits) → katottg via KSE admin map",
            "notes": [
                "Live snapshot at generation time — not a historical panel; re-run to refresh.",
                "consultations/open_city e-dem endpoints are platform-wide aggregates only, "
                "no per-hromada breakdown available — not included here.",
                "on_*_platform=false does not distinguish 'no such tool' from 'uses a "
                "non-e-dem.ua e-participation platform' — e-dem.ua is dominant but not the "
                "only provider.",
                "war_status_sept_2022 is KSE's Sept-2022 snapshot, NOT current — it will show "
                "hromadas occupied after that date (e.g. Avdiivka, fell Feb 2024) as "
                "'not occupied'. Cross-check current status manually before treating an "
                "active-looking score as ground truth for frontline/occupied hromadas.",
                "Scores are 0 for hromadas absent from the platform or with zero recorded "
                "activity; percentile ranks are computed only among hromadas with >0 on that "
                "metric, so a hromada present-but-idle scores 0 rather than an artificial "
                "mid-range rank.",
                f"Unmatched KOATUU rows (rayon/oblast councils excluded already): "
                f"{unmatched_petitions} petitions, {unmatched_budgets} budgets — see "
                "docs/edem-barometer.md for what's typically left over.",
                "overall_score (and its tiers) is ABSOLUTE — it favors big cities by "
                "population alone, not necessarily by per-resident engagement. Use "
                "overall_score_per_capita / tier_per_capita for a population-normalized view.",
            ],
        },
        "methodology": {
            "petition_activity_score": "percentile rank of petitions_total among hromadas with >0",
            "petition_participation_score": "percentile rank of petition_online_votes among >0",
            "budget_activity_score": "percentile rank of budget_projects among >0",
            "budget_scale_score": "percentile rank of budget_amount_total_uah among >0",
            "overall_score": "mean of the four component scores (0-100) — absolute, not population-adjusted",
            "tier_bounds": {
                "низький": f"0 < overall_score <= {tier_bounds[1]}",
                "середній": f"{tier_bounds[1]} < overall_score <= {tier_bounds[2]}",
                "високий": f"overall_score > {tier_bounds[2]}",
            },
            "petitions_per_10k_pop": "petitions_total / population * 10000",
            "budget_uah_per_capita": "budget_amount_total_uah / population",
            "overall_score_per_capita": (
                "mean of percentile ranks of petitions_per_10k_pop and budget_uah_per_capita, "
                f"computed only among hromadas with population >= {MIN_POP_FOR_RANK} "
                "(below that a single petition swings the rate too much to rank meaningfully); "
                "null (tier_per_capita='населення замале') for smaller/unknown-population hromadas"
            ),
            "tier_bounds_per_capita": {
                "низький": f"0 < overall_score_per_capita <= {tier_bounds_pc[1]}",
                "середній": f"{tier_bounds_pc[1]} < overall_score_per_capita <= {tier_bounds_pc[2]}",
                "високий": f"overall_score_per_capita > {tier_bounds_pc[2]}",
            },
        },
        "coverage": {
            "hromadas_total": len(rows),
            "connected_any": connected,
            "with_petitions": with_petitions,
            "with_budget": with_budget,
            "with_population": with_population,
            "min_population_for_per_capita_rank": MIN_POP_FOR_RANK,
            "by_tier": by_tier,
            "by_tier_per_capita": by_tier_pc,
        },
        "hromadas": rows,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(
        json.dumps(
            {
                "file": "edem-barometer.json",
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
        f"Wrote {OUT.relative_to(ROOT)} — {len(rows)} hromadas, "
        f"{connected} connected (petitions {with_petitions}, budget {with_budget}); "
        f"tiers: {by_tier}; per-capita tiers ({with_population} with population): {by_tier_pc}"
    )


if __name__ == "__main__":
    main()
