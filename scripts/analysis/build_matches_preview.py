#!/usr/bin/env python3
"""Build docs/assets/matches-preview.json from release edges + pin∩corpus report."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EDGES = ROOT / "data" / "releases" / "matching-edges.json"
MANIFEST = ROOT / "data" / "releases" / "matching-edges.manifest.json"
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
PIN_CORPUS = ROOT / "data" / "releases" / "matching-edges.pin-corpus.json"
OUT = ROOT / "docs" / "assets" / "matches-preview.json"
TOP_N = 20


def short_name(full: str) -> str:
    parts = full.replace("територіальна громада", "").strip().split()
    return parts[0] if parts else full


def slim(e: dict) -> dict:
    out = {
        "a": e["a"],
        "b": e["b"],
        "score": e.get("score"),
        "goals_cosine": e.get("goals_cosine"),
        "geo_score": e.get("geo_score"),
        "mss_network": e.get("mss_network"),
        "known": bool(e.get("known")),
        "track": e.get("track"),
        "a_short": short_name(e["a"]),
        "b_short": short_name(e["b"]),
        **({"rank": e["rank"]} if e.get("rank") is not None else {}),
    }
    for key in (
        "suggested_theme",
        "suggested_form",
        "suggest_confidence",
        "suggest_rationale",
        "suggest_caveat",
        "kind",
        "discovery_primary",
        "status",
    ):
        if e.get(key):
            out[key] = e[key]
    if e.get("package"):
        out["package"] = e["package"]
    if e.get("signals"):
        out["signals"] = e["signals"]
        out["signal_chips"] = e["signals"][:3]
    return out


def main() -> None:
    if not EDGES.exists():
        raise SystemExit(f"Missing {EDGES}")
    edges = json.loads(EDGES.read_text(encoding="utf-8"))
    man = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    hromadas = json.loads(HROMADAS.read_text(encoding="utf-8"))
    goals = sum(1 for r in hromadas if (r.get("Goals") or "").strip())
    text_mined = sum(
        1
        for r in hromadas
        if r.get("SourceQuality") in ("full-strategy", "partial", "proxy-info")
    )

    # Release matrix is slim (scores only); annotate the small preview subset.
    sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
    from edge_io import ensure_packages  # noqa: E402

    known_raw = [e for e in edges if e.get("known")]
    known_raw.sort(key=lambda e: -float(e.get("score") or 0))
    top_raw = [
        e
        for e in sorted(edges, key=lambda x: -float(x.get("score") or 0))
        if not e.get("known")
    ][:TOP_N]
    ensure_packages(known_raw + top_raw)

    known = [slim(e) for e in known_raw]
    top = [slim(e) for e in top_raw]

    pin_corpus = []
    if PIN_CORPUS.exists():
        pc = json.loads(PIN_CORPUS.read_text(encoding="utf-8"))
        pin_corpus = [slim(p) for p in pc.get("pairs", [])]

    candidates_path = ROOT / "data" / "releases" / "mss-candidates.json"
    candidates_meta = None
    if candidates_path.exists():
        cand = json.loads(candidates_path.read_text(encoding="utf-8"))
        candidates_meta = {
            "registryKnown": len(cand.get("registry_known") or []),
            "hypotheses": len(cand.get("hypotheses") or []),
            "caveat": cand.get("caveat"),
        }

    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "method": man.get("method") or "v7: 60% goals_cosine + 25% KSE geo + 15% KSE mss_network",
        "productUnit": "mss_candidate",
        "pairCount": len(edges),
        "corpusGoals": goals,
        "textMinedRows": text_mined,
        "tracks": man.get("tracks"),
        "mssCandidate": man.get("mssCandidate"),
        "candidatesSidecar": candidates_meta,
        "known": known,
        "pinCorpus": pin_corpus,
        "top": top,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"Wrote {OUT.relative_to(ROOT)} — known={len(known)} "
        f"pin∩corpus={len(pin_corpus)} top={len(top)}"
    )


if __name__ == "__main__":
    main()
