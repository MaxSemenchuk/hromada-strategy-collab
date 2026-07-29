#!/usr/bin/env python3
"""Label matching edges with dual tracks and write thematic/operational slices.

Does not recompute embeddings — works on the existing matching-edges.json.
Combined `score` is left unchanged; see tracks.py / project-history.md.
Also attaches operational boost fields (fiscal / DREAM) without altering score.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from enrich_operational import enrich_edges  # noqa: E402
from tracks import assign_tracks, operational_slice, thematic_slice  # noqa: E402

EDGES = ROOT / "data" / "releases" / "matching-edges.json"
MANIFEST = ROOT / "data" / "releases" / "matching-edges.manifest.json"
THEMATIC = ROOT / "data" / "releases" / "matching-edges.thematic.json"
OPERATIONAL = ROOT / "data" / "releases" / "matching-edges.operational.json"

SLICE_LIMIT = 50


def main() -> None:
    if not EDGES.exists():
        raise SystemExit(f"Missing {EDGES} — run yarn match first")

    edges = json.loads(EDGES.read_text(encoding="utf-8"))
    meta = assign_tracks(edges)
    boost = enrich_edges(edges)

    EDGES.write_text(json.dumps(edges, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    thematic = thematic_slice(edges, limit=SLICE_LIMIT)
    operational = operational_slice(edges, limit=SLICE_LIMIT)
    THEMATIC.write_text(json.dumps(thematic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OPERATIONAL.write_text(
        json.dumps(operational, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    known = sum(1 for e in edges if e.get("known"))
    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "pairCount": len(edges),
        "knownValidationPairs": known,
        "method": "v7: 60% goals_cosine (hierarchy-aware) + 25% KSE geo + 15% KSE mss_network",
        "model": "intfloat/multilingual-e5-small",
        "license": "CC BY 4.0 — see DATA-LICENSE.md",
        "warning": (
            "Unverified hypotheses unless known=true. "
            "Combined score is not a pure strategy match — use track / slice files."
        ),
        "tracks": {
            "thematic": (
                f"goals_cosine >= p{meta['goalsPercentile']} ({meta['goalsFloor']}) "
                f"and geo_score <= {meta['geoThematicMax']} — cold-start vision partners"
            ),
            "operational": (
                f"geo_score >= {meta['geoOperationalMin']} and not thematic — "
                "convenient service co-sharers; slice ranked by operational_score "
                "(geo + fiscal_similarity + dream_overlap) when available"
            ),
            "mixed": "all other pairs",
            "counts": meta["counts"],
            "goalsFloor": meta["goalsFloor"],
            "goalsPercentile": meta["goalsPercentile"],
            "geoThematicMax": meta["geoThematicMax"],
            "geoOperationalMin": meta["geoOperationalMin"],
        },
        "operationalBoost": {
            "note": "Extra fields on edges; v7 combined-score weights unchanged from v6",
            "fields": ["fiscal_similarity", "dream_overlap", "operational_score"],
            "enriched": boost["enriched"],
            "withOperationalScore": boost["with_operational_score"],
        },
        "slices": {
            "thematic": {
                "path": "matching-edges.thematic.json",
                "limit": SLICE_LIMIT,
                "count": len(thematic),
                "rankBy": "goals_cosine",
                "excludes": ["known=true"],
            },
            "operational": {
                "path": "matching-edges.operational.json",
                "limit": SLICE_LIMIT,
                "count": len(operational),
                "rankBy": "operational_score|score",
                "excludes": ["known=true", "mss_network>0"],
                "note": "Neighbours not already linked in the KSE МСС network",
            },
            "complementary": {
                "path": "matching-edges.complementary.json",
                "note": "Separate yarn complementary-match — resource/DREAM ↔ Challenges",
            },
        },
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote tracks onto {EDGES} ({len(edges)} edges)")
    print(
        f"  thematic={meta['counts']['thematic']} "
        f"operational={meta['counts']['operational']} "
        f"mixed={meta['counts']['mixed']} "
        f"(goals p{meta['goalsPercentile']} floor={meta['goalsFloor']})"
    )
    print(
        f"  operational boost: {boost['with_operational_score']} edges with operational_score"
    )
    print(f"Wrote {THEMATIC} ({len(thematic)} rows)")
    print(f"Wrote {OPERATIONAL} ({len(operational)} rows)")
    print(f"Wrote {MANIFEST}")


if __name__ == "__main__":
    main()
