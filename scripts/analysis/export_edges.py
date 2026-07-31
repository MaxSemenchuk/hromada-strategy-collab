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
from mss_candidate import annotate_candidates, write_candidates_sidecar  # noqa: E402
from mss_suggest import annotate_edges, load_hromadas_by_name  # noqa: E402
from tracks import assign_tracks, operational_slice, thematic_slice  # noqa: E402

EDGES = ROOT / "data" / "releases" / "matching-edges.json"
MANIFEST = ROOT / "data" / "releases" / "matching-edges.manifest.json"
THEMATIC = ROOT / "data" / "releases" / "matching-edges.thematic.json"
OPERATIONAL = ROOT / "data" / "releases" / "matching-edges.operational.json"
COMPLEMENTARY = ROOT / "data" / "releases" / "matching-edges.complementary.json"
EXPLICIT_ASK = ROOT / "data" / "releases" / "matching-edges.explicit-ask.json"

SLICE_LIMIT = 50


def main() -> None:
    if not EDGES.exists():
        raise SystemExit(f"Missing {EDGES} — run yarn match first")

    edges = json.loads(EDGES.read_text(encoding="utf-8"))
    meta = assign_tracks(edges)
    boost = enrich_edges(edges)
    suggest = annotate_edges(edges, hromadas_by_name=load_hromadas_by_name())
    candidates = annotate_candidates(edges)

    EDGES.write_text(json.dumps(edges, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    thematic = thematic_slice(edges, limit=SLICE_LIMIT)
    operational = operational_slice(edges, limit=SLICE_LIMIT)
    THEMATIC.write_text(json.dumps(thematic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OPERATIONAL.write_text(
        json.dumps(operational, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    complementary = (
        json.loads(COMPLEMENTARY.read_text(encoding="utf-8")) if COMPLEMENTARY.exists() else []
    )
    explicit_ask = (
        json.loads(EXPLICIT_ASK.read_text(encoding="utf-8")) if EXPLICIT_ASK.exists() else []
    )
    # Annotate slice files already on disk (complementary / explicit-ask from own yarn cmds)
    if complementary:
        annotate_candidates(complementary)
        COMPLEMENTARY.write_text(
            json.dumps(complementary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    if explicit_ask:
        annotate_candidates(explicit_ask)
        EXPLICIT_ASK.write_text(
            json.dumps(explicit_ask, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    sidecar = write_candidates_sidecar(
        matching_edges=edges,
        thematic=thematic,
        operational=operational,
        complementary=complementary,
        explicit_ask=explicit_ask,
    )

    known = sum(1 for e in edges if e.get("known"))
    manifest = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "pairCount": len(edges),
        "knownValidationPairs": known,
        "method": "v7.1: 60% goals_cosine (hierarchy-aware; 0.65 bipartite + 0.35 centroid) + 25% KSE geo + 15% KSE mss_network",
        "model": "intfloat/multilingual-e5-small",
        "license": "CC BY 4.0 — see DATA-LICENSE.md",
        "warning": (
            "Product unit is an МСС candidate agreement (package theme·form), not a strategy twin. "
            "Unverified hypotheses unless known=true / status=registry_known. "
            "Combined score ranks one discovery signal — use package + signals / slice files. "
            "suggested_theme / suggested_form / package are IMC hypotheses, not registry facts."
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
        "mssSuggest": {
            "note": (
                "Rule-based theme + legal-form package (mss_suggest.py); "
                "does not change score; never sets known=true"
            ),
            "fields": [
                "suggested_theme",
                "suggested_theme_id",
                "suggested_form",
                "suggested_form_id",
                "suggest_confidence",
                "suggest_rationale",
                "suggest_caveat",
            ],
            "annotated": suggest["annotated"],
            "withTheme": suggest["with_theme"],
            "agglomerationHints": suggest["agglomeration"],
            "docs": "docs/mss-cooperation-research.md",
        },
        "mssCandidate": {
            "note": (
                "Normalized candidate wrapper (mss_candidate.py): kind/package/signals/"
                "discovery_primary/status. Signals are discovery evidence, not IMC legal forms. "
                "Thin browse sidecar: mss-candidates.json"
            ),
            "fields": [
                "kind",
                "package",
                "signals",
                "discovery_primary",
                "status",
            ],
            "annotated": candidates["annotated"],
            "withTheme": candidates["with_theme"],
            "registryKnown": candidates["registry_known"],
            "sidecar": {
                "path": "mss-candidates.json",
                "registryKnown": sidecar["registry_known"],
                "hypotheses": sidecar["hypotheses"],
            },
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
    print(
        f"  mss suggest: {suggest['with_theme']}/{suggest['annotated']} with theme "
        f"(agglomeration hints={suggest['agglomeration']})"
    )
    print(
        f"  mss candidate: {candidates['annotated']} annotated "
        f"(known={candidates['registry_known']}); "
        f"sidecar hypotheses={sidecar['hypotheses']}"
    )
    print(f"Wrote {THEMATIC} ({len(thematic)} rows)")
    print(f"Wrote {OPERATIONAL} ({len(operational)} rows)")
    print(f"Wrote mss-candidates.json ({sidecar['hypotheses']} hypotheses)")
    print(f"Wrote {MANIFEST}")


if __name__ == "__main__":
    main()
