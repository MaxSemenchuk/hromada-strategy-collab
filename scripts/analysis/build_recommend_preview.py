#!/usr/bin/env python3
"""Build docs/assets/recommend-for-preview.json for the matches page UI.

Precomputes top-K agent recommendations for every Goals seed × motivation.
Does not rematch; reads release edges + complementary layer.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from recommend_for import (  # noqa: E402
    MOTIVATIONS,
    index_hromadas,
    load_json,
    merge_complementary,
    recommend_for,
)

RELEASES = ROOT / "data" / "releases"
HROMADAS = RELEASES / "hromadas.json"
EDGES = RELEASES / "matching-edges.json"
COMPLEMENTARY = RELEASES / "matching-edges.complementary.json"
OUT = ROOT / "docs" / "assets" / "recommend-for-preview.json"
TOP_K = 5


def slim_card(c: dict) -> dict:
    pkg = c.get("package") or {}
    return {
        "partner_short": c["partner_short"],
        "package": {
            "label_uk": pkg.get("label_uk"),
            "theme_id": pkg.get("theme_id"),
            "form_id": pkg.get("form_id"),
        },
        "signal_chips": [
            {"id": ch.get("id"), "label_uk": ch.get("label_uk"), "strength": ch.get("strength")}
            for ch in (c.get("signal_chips") or [])[:3]
        ],
        "why_uk": c.get("why_helps_you_uk"),
        "why_en": c.get("why_helps_you_en"),
        "known": bool(c.get("known")),
    }


def main() -> None:
    if not EDGES.exists():
        raise SystemExit(f"Missing {EDGES}")
    hromadas = load_json(HROMADAS)
    edges = load_json(EDGES)
    complementary = load_json(COMPLEMENTARY) if COMPLEMENTARY.exists() else []
    merged = merge_complementary(edges, complementary)
    index = index_hromadas(hromadas)
    seeds = index["goals_seeds"]

    by_seed: dict[str, dict] = {}
    for s in seeds:
        key = s.get("katottg") or s["name"]
        entry: dict = {
            "short": s["short"],
            "katottg": s.get("katottg"),
            "oblast": s.get("oblast"),
            "by_motivation": {},
        }
        for mid in MOTIVATIONS:
            cards = recommend_for(
                s["name"],
                motivation=mid,
                k=TOP_K,
                edges=merged,
                complementary=[],  # already merged
            )
            entry["by_motivation"][mid] = [slim_card(c) for c in cards]
        by_seed[key] = entry

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "kind": "mss_agent_recommend_preview",
        "productUnit": "candidate agreement (partner · package · signals · why)",
        "caveat_uk": (
            "Рекомендації для громади-агента за мотивацією. "
            "Не продаємо combined score як «strategy match». "
            "Валідація матчера лишається global v7.1 / known pairs."
        ),
        "caveat_en": (
            "Hromada-as-agent recommendations by motivation. "
            "Do not sell combined score as a “strategy match”. "
            "Matcher validation stays global v7.1 / known pairs."
        ),
        "k": TOP_K,
        "motivations": [
            {
                "id": mid,
                "label_uk": m["label_uk"],
                "label_en": m["label_en"],
                "package_hint_uk": m.get("package_hint_uk"),
                "package_hint_en": m.get("package_hint_en"),
            }
            for mid, m in MOTIVATIONS.items()
        ],
        "seeds": [
            {
                "key": (s.get("katottg") or s["name"]),
                "name": s["name"],
                "short": s["short"],
                "katottg": s.get("katottg"),
                "oblast": s.get("oblast"),
            }
            for s in seeds
        ],
        "bySeed": by_seed,
        "seedCount": len(seeds),
        "edgeCount": len(edges),
        "complementaryCount": len(complementary),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {OUT.relative_to(ROOT)} "
        f"({len(seeds)} seeds × {len(MOTIVATIONS)} motivations × top-{TOP_K}; "
        f"{OUT.stat().st_size // 1024} KB)"
    )


if __name__ == "__main__":
    main()
