#!/usr/bin/env python3
"""Build data/releases/goals-hierarchy.json from Goals text + curated overrides.

Curated gold (operational lines) lives in data/sources/goals-hierarchy-overrides.json.
GISRR auto-structure: data/sources/gisrr-goals-hierarchy.json (after yarn structure-gisrr).
Flat Goals remain canonical on hromadas.json for backward compatibility.

Usage:
  yarn build-goals-hierarchy
  python3 scripts/analysis/build_goals_hierarchy.py
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from goals_hierarchy import parse_goals_text

ROOT = Path(__file__).resolve().parents[2]
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
OVERRIDES = ROOT / "data" / "sources" / "goals-hierarchy-overrides.json"
GISRR_HIERARCHY = ROOT / "data" / "sources" / "gisrr-goals-hierarchy.json"
OUT = ROOT / "data" / "releases" / "goals-hierarchy.json"
MANIFEST = ROOT / "data" / "releases" / "goals-hierarchy.manifest.json"


def _index_hierarchy_file(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("hromadas") or raw
    if not isinstance(items, list):
        return {}
    out: dict[str, dict] = {}
    for item in items:
        if not (item.get("strategic_goals") or item.get("operational_goals")):
            continue
        for key in (item.get("name"), item.get("katottg")):
            if key:
                out[str(key)] = item
    return out


def main() -> None:
    rows = json.loads(HROMADAS.read_text(encoding="utf-8"))
    overrides = _index_hierarchy_file(OVERRIDES)
    gisrr = _index_hierarchy_file(GISRR_HIERARCHY)

    out_rows: list[dict] = []
    with_ops = 0
    curated = 0
    from_gisrr = 0
    for r in rows:
        goals = (r.get("Goals") or "").strip()
        if not goals:
            continue
        name = r.get("Name") or ""
        code = r.get("Katottg") or r.get("KATOTTG") or ""
        ov = overrides.get(name) or overrides.get(code)
        gv = gisrr.get(name) or gisrr.get(code)
        if ov and (ov.get("strategic_goals") or ov.get("operational_goals")):
            curated += 1
            strategic = ov.get("strategic_goals") or []
            operational = ov.get("operational_goals") or []
            mss_intents = ov.get("mss_intents") or []
            source = "curated-override"
        elif gv and (gv.get("strategic_goals") or gv.get("operational_goals")):
            from_gisrr += 1
            strategic = gv.get("strategic_goals") or []
            operational = gv.get("operational_goals") or []
            mss_intents = gv.get("mss_intents") or []
            source = "gisrr-structure"
        else:
            parsed = parse_goals_text(goals)
            strategic = parsed["strategic_goals"]
            operational = parsed["operational_goals"]
            mss_intents = []
            source = "parsed-from-goals"
        if operational:
            with_ops += 1
        out_rows.append(
            {
                "name": name,
                "katottg": code or None,
                "source": source,
                "strategic_goals": strategic,
                "operational_goals": operational,
                "mss_intents": mss_intents,
            }
        )

    generated = datetime.now(timezone.utc).isoformat()
    payload = {
        "generatedAt": generated,
        "method": "parse Goals text + curated overrides + GISRR structure",
        "hromadaCount": len(out_rows),
        "withOperational": with_ops,
        "curatedCount": curated,
        "gisrrCount": from_gisrr,
        "hromadas": out_rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(
        json.dumps(
            {
                "generatedAt": generated,
                "hromadaCount": len(out_rows),
                "withOperational": with_ops,
                "curatedCount": curated,
                "gisrrCount": from_gisrr,
                "warning": (
                    "Sidecar for matching v7. Flat Goals on hromadas.json remain "
                    "canonical for export/NocoDB until hierarchy is written back."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {OUT.relative_to(ROOT)} — {len(out_rows)} hromadas, "
        f"{with_ops} with operational, {curated} curated, {from_gisrr} gisrr"
    )


if __name__ == "__main__":
    main()
