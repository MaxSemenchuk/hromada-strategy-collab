#!/usr/bin/env python3
"""Build data/releases/goals-hierarchy.json from Goals text + curated overrides.

Curated gold (operational lines) lives in data/sources/goals-hierarchy-overrides.json.
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
OUT = ROOT / "data" / "releases" / "goals-hierarchy.json"
MANIFEST = ROOT / "data" / "releases" / "goals-hierarchy.manifest.json"


def main() -> None:
    rows = json.loads(HROMADAS.read_text(encoding="utf-8"))
    overrides: dict[str, dict] = {}
    if OVERRIDES.exists():
        raw = json.loads(OVERRIDES.read_text(encoding="utf-8"))
        for item in raw.get("hromadas") or []:
            key = item.get("name") or item.get("katottg")
            if key:
                overrides[key] = item

    out_rows: list[dict] = []
    with_ops = 0
    curated = 0
    for r in rows:
        goals = (r.get("Goals") or "").strip()
        if not goals:
            continue
        name = r.get("Name") or ""
        code = r.get("Katottg") or r.get("KATOTTG") or ""
        ov = overrides.get(name) or overrides.get(code)
        if ov and (ov.get("strategic_goals") or ov.get("operational_goals")):
            curated += 1
            strategic = ov.get("strategic_goals") or []
            operational = ov.get("operational_goals") or []
            mss_intents = ov.get("mss_intents") or []
            source = "curated-override"
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
        "method": "parse Goals text + optional curated overrides",
        "hromadaCount": len(out_rows),
        "withOperational": with_ops,
        "curatedCount": curated,
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
        f"{with_ops} with operational, {curated} curated"
    )


if __name__ == "__main__":
    main()
