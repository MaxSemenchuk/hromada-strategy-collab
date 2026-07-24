#!/usr/bin/env python3
"""PIN ∩ corpus report — all matching edges with mss_network > 0.

Separate from curated `known: true` validation (yarn test-known-pairs):
  - known = hand-picked ground truth for text→agreement regression
  - pin∩corpus = every KSE-linked pair that also has Goals on both sides

Writes data/releases/matching-edges.pin-corpus.json (ranked, deduped by KATOTTG).
Does not fail the build on ranks (soft diagnostic). Exit 1 only if edges missing
or zero PIN∩corpus pairs found when matching-edges exists.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDGES = ROOT / "data" / "releases" / "matching-edges.json"
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
OUT = ROOT / "data" / "releases" / "matching-edges.pin-corpus.json"
MANIFEST = ROOT / "data" / "releases" / "matching-edges.manifest.json"

# Soft diagnostics (printed, not enforced as hard regression).
SOFT_TOP_N = 50


def short_name(full: str) -> str:
    return full.replace("територіальна громада", "").strip().split()[0] if full else ""


def katottg_map() -> dict[str, str]:
    rows = json.loads(HROMADAS.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for r in rows:
        name = r.get("Name")
        code = r.get("Katottg")
        if name and code and (r.get("Goals") or "").strip():
            # Prefer first occurrence; duplicate Katottg names are a data quirk.
            out.setdefault(name, code)
    return out


def build_rows(edges: list[dict], name_to_code: dict[str, str]) -> list[dict]:
    ranked = sorted(edges, key=lambda e: -float(e.get("score") or 0))
    rank_map = {frozenset([e["a"], e["b"]]): i + 1 for i, e in enumerate(ranked)}

    by_codes: dict[frozenset[str], dict] = {}
    for e in edges:
        if float(e.get("mss_network") or 0) <= 0:
            continue
        ca, cb = name_to_code.get(e["a"]), name_to_code.get(e["b"])
        if not ca or not cb or ca == cb:
            continue
        key = frozenset((ca, cb))
        row = {
            "a": e["a"],
            "b": e["b"],
            "a_katottg": ca,
            "b_katottg": cb,
            "a_short": short_name(e["a"]),
            "b_short": short_name(e["b"]),
            "score": e.get("score"),
            "goals_cosine": e.get("goals_cosine"),
            "geo_score": e.get("geo_score"),
            "mss_network": e.get("mss_network"),
            "track": e.get("track"),
            "known": bool(e.get("known")),
            "rank": rank_map.get(frozenset([e["a"], e["b"]])),
        }
        prev = by_codes.get(key)
        if prev is None or (row["known"] and not prev["known"]):
            by_codes[key] = row
        elif row["known"] == prev["known"]:
            # Keep better rank / higher score on name collisions.
            if (row["rank"] or 10**9) < (prev["rank"] or 10**9):
                by_codes[key] = row

    rows = sorted(by_codes.values(), key=lambda r: (r["rank"] is None, r["rank"] or 0))
    return rows


def update_manifest(rows: list[dict]) -> None:
    if not MANIFEST.exists():
        return
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    curated = sum(1 for r in rows if r["known"])
    other = len(rows) - curated
    in_top = sum(1 for r in rows if r["rank"] is not None and r["rank"] <= SOFT_TOP_N)
    man["pinCorpusOverlap"] = {
        "path": "matching-edges.pin-corpus.json",
        "count": len(rows),
        "curatedKnown": curated,
        "otherPinCorpus": other,
        "inTopN": in_top,
        "topN": SOFT_TOP_N,
        "note": (
            "All mss_network>0 pairs with Goals on both sides. "
            "Curated known=true stays the hard regression set; this file is the broader KSE check."
        ),
    }
    MANIFEST.write_text(json.dumps(man, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    if not EDGES.exists():
        raise SystemExit(f"Missing {EDGES} — run yarn match first")

    edges = json.loads(EDGES.read_text(encoding="utf-8"))
    name_to_code = katottg_map()
    rows = build_rows(edges, name_to_code)

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": "PIN∩corpus: matching edges with mss_network>0 (KSE partnerships)",
        "pairCount": len(rows),
        "curatedKnownCount": sum(1 for r in rows if r["known"]),
        "otherPinCorpusCount": sum(1 for r in rows if not r["known"]),
        "softTopN": SOFT_TOP_N,
        "inSoftTopN": sum(1 for r in rows if r["rank"] is not None and r["rank"] <= SOFT_TOP_N),
        "warning": (
            "Not a substitute for known=true regression. "
            "Combined score already includes mss_network (15%) — ranks are partly circular."
        ),
        "pairs": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    update_manifest(rows)

    print(f"PIN ∩ corpus: {len(rows)} unique KATOTTG pairs "
          f"(curated known={payload['curatedKnownCount']}, "
          f"other={payload['otherPinCorpusCount']})")
    print(f"In top-{SOFT_TOP_N} by combined score: {payload['inSoftTopN']}/{len(rows)}")
    print()
    print(f"{'rank':>5}  {'known':5}  {'score':5}  {'goals':5}  pair")
    for r in rows:
        rk = f"#{r['rank']}" if r["rank"] else "?"
        print(
            f"{rk:>5}  {'yes' if r['known'] else 'no':5}  "
            f"{float(r['score'] or 0):5.3f}  {float(r['goals_cosine'] or 0):5.3f}  "
            f"{r['a_short']} ↔ {r['b_short']}"
        )
    print(f"\nWrote {OUT.relative_to(ROOT)}")
    if MANIFEST.exists():
        print(f"Updated {MANIFEST.relative_to(ROOT)}")

    if not rows:
        print("\nFAILED: no PIN∩corpus pairs (mss_network>0) in matching-edges", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
