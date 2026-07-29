#!/usr/bin/env python3
"""Build docs/assets/resources-preview.json from release resource + DREAM layers.

Compact join for the stakeholder site (GitHub Pages serves docs/ only).

Usage:
  yarn build-resources-preview
  python3 scripts/analysis/build_resources_preview.py
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESOURCES = ROOT / "data" / "releases" / "hromada-resources.json"
DREAM = ROOT / "data" / "releases" / "dream-priorities.json"
OUT = ROOT / "docs" / "assets" / "resources-preview.json"


def short_name(name: str | None) -> str:
    if not name:
        return ""
    for suffix in (
        " міська територіальна громада",
        " селищна територіальна громада",
        " сільська територіальна громада",
        " територіальна громада",
    ):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def main() -> None:
    res = json.loads(RESOURCES.read_text(encoding="utf-8"))
    dream = json.loads(DREAM.read_text(encoding="utf-8"))

    by_code: dict[str, dict] = {}
    for row in res.get("hromadas") or []:
        code = (row.get("katottg") or "").strip()
        if not code:
            continue
        by_code[code] = {
            "katottg": code,
            "name": row.get("name") or "",
            "short": short_name(row.get("name")),
            "oblast": row.get("oblast"),
            "own_income_per_capita": row.get("own_income_per_capita"),
            "own_income_prop": row.get("own_income_prop"),
            "budget_year": row.get("budget_year"),
            "dfrr_years": row.get("dfrr_years"),
            "dfrr_budget_executed_sum": row.get("dfrr_budget_executed_sum"),
            "competence_known": bool(row.get("competence_known")),
            "youth_councils": row.get("youth_councils"),
            "youth_centers": row.get("youth_centers"),
            "business_support_centers": row.get("business_support_centers"),
            "health_known": bool(row.get("health_known")),
            "health_primary": row.get("health_primary"),
            "health_specialized": row.get("health_specialized"),
            "war_status_sept": row.get("war_status_sept"),
            "dream_projects": 0,
            "top_sectors": [],
            "sample_title": None,
        }

    sector_totals: Counter[str] = Counter()
    for row in dream.get("hromadas") or []:
        code = (row.get("katottg") or "").strip()
        if not code:
            continue
        bucket = by_code.get(code)
        if bucket is None:
            bucket = {
                "katottg": code,
                "name": row.get("name") or "",
                "short": short_name(row.get("name")),
                "oblast": None,
                "own_income_per_capita": None,
                "own_income_prop": None,
                "budget_year": None,
                "dfrr_years": None,
                "dfrr_budget_executed_sum": None,
                "competence_known": False,
                "youth_councils": None,
                "youth_centers": None,
                "business_support_centers": None,
                "health_known": False,
                "health_primary": None,
                "health_specialized": None,
                "war_status_sept": None,
                "dream_projects": 0,
                "top_sectors": [],
                "sample_title": None,
            }
            by_code[code] = bucket
        elif not bucket.get("name") and row.get("name"):
            bucket["name"] = row["name"]
            bucket["short"] = short_name(row["name"])

        bucket["dream_projects"] = int(row.get("project_count") or 0)
        bucket["top_sectors"] = list(row.get("top_sectors") or [])[:4]
        titles = row.get("sample_titles") or []
        bucket["sample_title"] = titles[0] if titles else None
        for s, n in (row.get("sector_counts") or {}).items():
            sector_totals[s] += int(n)

    rows = sorted(
        by_code.values(),
        key=lambda r: (-int(r.get("dream_projects") or 0), -(r.get("own_income_per_capita") or 0), r.get("short") or ""),
    )

    with_dream = sum(1 for r in rows if (r.get("dream_projects") or 0) > 0)
    with_pcap = sum(1 for r in rows if r.get("own_income_per_capita") is not None)
    with_comp = sum(1 for r in rows if r.get("competence_known"))
    with_health = sum(1 for r in rows if r.get("health_known"))

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "KSE resource proxies × DREAM revealed project priorities (KATOTTG join)",
        "caveat": "Structural / revealed proxies — not a substitute for Goals text. Competence/health missing ≠ zero. DREAM sectors from WB-ECO + title keywords.",
        "coverage": {
            "rows": len(rows),
            "resources": (res.get("coverage") or {}),
            "dream": (dream.get("coverage") or {}),
            "with_dream_projects": with_dream,
            "with_own_income_per_capita": with_pcap,
            "with_competence": with_comp,
            "with_health": with_health,
        },
        "sector_totals": [
            {"sector": s, "count": n} for s, n in sector_totals.most_common(12)
        ],
        "top_dream": [
            {
                "short": r["short"] or r["name"],
                "oblast": r.get("oblast"),
                "dream_projects": r["dream_projects"],
                "top_sectors": r["top_sectors"],
                "sample_title": r.get("sample_title"),
            }
            for r in rows
            if (r.get("dream_projects") or 0) > 0
        ][:40],
        "hromadas": rows,
    }

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {OUT.relative_to(ROOT)} — {len(rows)} rows "
        f"(dream {with_dream}, pcap {with_pcap}, ~{OUT.stat().st_size // 1024} KB)"
    )


if __name__ == "__main__":
    main()
