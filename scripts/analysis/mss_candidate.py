#!/usr/bin/env python3
"""Normalize matching edges into МСС candidate packages + evidence signals.

Product unit: candidate agreement (theme · form), not strategy similarity.
Does not change v7 combined `score` or set known=true.

Usage:
  from mss_candidate import annotate_candidates, write_candidates_sidecar
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RELEASES = ROOT / "data" / "releases"
CANDIDATES_OUT = RELEASES / "mss-candidates.json"
CANDIDATES_MANIFEST = RELEASES / "mss-candidates.manifest.json"

SIGNAL_LABELS: dict[str, str] = {
    "strategy_goals": "схожа стратегія",
    "geo": "зручний сусід",
    "complementary": "доповнення ресурсів",
    "explicit_ask": "явний запит МСС",
    "network": "мережа МСС",
    "structural": "ресурси / DREAM",
}

TRACK_TO_PRIMARY: dict[str, str] = {
    "thematic": "strategy_goals",
    "operational": "geo",
    "mixed": "strategy_goals",
    "complementary": "complementary",
    "explicit-ask": "explicit_ask",
    "explicit_ask": "explicit_ask",
}

STRENGTH_ORDER = {"high": 3, "medium": 2, "low": 1}


def _strength_from_score(value: float | None, *, high: float, medium: float) -> str:
    if value is None:
        return "low"
    if value >= high:
        return "high"
    if value >= medium:
        return "medium"
    return "low"


def package_from_edge(e: dict[str, Any]) -> dict[str, Any]:
    """Build package block from mss_suggest fields already on the edge."""
    theme = e.get("suggested_theme")
    theme_id = e.get("suggested_theme_id")
    form = e.get("suggested_form")
    form_id = e.get("suggested_form_id")
    theme_part = theme or "тема не визначена"
    form_part = form or "спільний проєкт"
    # Human line for hromada-facing UI (not legal-code jargon alone)
    label_uk = f"{theme_part} — {form_part}"
    pkg: dict[str, Any] = {
        "theme": theme,
        "theme_id": theme_id,
        "form": form,
        "form_id": form_id,
        "confidence": e.get("suggest_confidence") or "low",
        "rationale": e.get("suggest_rationale"),
        "label_uk": label_uk,
    }
    if e.get("suggest_caveat"):
        pkg["caveat"] = e["suggest_caveat"]
    return pkg


def build_signals(e: dict[str, Any]) -> list[dict[str, str]]:
    """Evidence tracks present on this edge (full list for JSON)."""
    signals: list[dict[str, str]] = []
    track = e.get("track") or ""

    goals = e.get("goals_cosine")
    if goals is not None or track == "thematic":
        g = float(goals) if goals is not None else 0.0
        # Thematic slice already filtered; treat track as at least medium
        strength = _strength_from_score(g, high=0.12, medium=0.05)
        if track == "thematic" and STRENGTH_ORDER[strength] < STRENGTH_ORDER["medium"]:
            strength = "medium"
        if g > 0 or track == "thematic":
            signals.append(
                {
                    "id": "strategy_goals",
                    "label_uk": SIGNAL_LABELS["strategy_goals"],
                    "strength": strength,
                }
            )

    geo = e.get("geo_score")
    if geo is not None or track == "operational":
        g = float(geo) if geo is not None else 0.0
        strength = _strength_from_score(g, high=0.85, medium=0.5)
        if track == "operational" and STRENGTH_ORDER[strength] < STRENGTH_ORDER["medium"]:
            strength = "medium"
        if g > 0 or track == "operational":
            signals.append(
                {
                    "id": "geo",
                    "label_uk": SIGNAL_LABELS["geo"],
                    "strength": strength,
                }
            )

    comp = e.get("complementary_score")
    if comp is not None or track == "complementary":
        c = float(comp) if comp is not None else 0.0
        strength = _strength_from_score(c, high=0.85, medium=0.5)
        if track == "complementary" and STRENGTH_ORDER[strength] < STRENGTH_ORDER["medium"]:
            strength = "medium"
        if c > 0 or track == "complementary":
            signals.append(
                {
                    "id": "complementary",
                    "label_uk": SIGNAL_LABELS["complementary"],
                    "strength": strength,
                }
            )

    ask = e.get("explicit_ask_score")
    if ask is not None or track in ("explicit-ask", "explicit_ask"):
        a = float(ask) if ask is not None else 0.0
        strength = _strength_from_score(a, high=0.85, medium=0.5)
        if track in ("explicit-ask", "explicit_ask") and STRENGTH_ORDER[strength] < STRENGTH_ORDER[
            "medium"
        ]:
            strength = "medium"
        if a > 0 or track in ("explicit-ask", "explicit_ask"):
            signals.append(
                {
                    "id": "explicit_ask",
                    "label_uk": SIGNAL_LABELS["explicit_ask"],
                    "strength": strength,
                }
            )

    net = e.get("mss_network")
    if net is not None and float(net) > 0:
        signals.append(
            {
                "id": "network",
                "label_uk": SIGNAL_LABELS["network"],
                "strength": "high" if float(net) >= 1.0 else "medium",
            }
        )

    fiscal = e.get("fiscal_similarity")
    dream = e.get("dream_overlap")
    op = e.get("operational_score")
    if fiscal is not None or dream is not None or op is not None:
        # Structural covariates — only surface when they add something
        best = max(
            float(fiscal) if fiscal is not None else 0.0,
            float(dream) if dream is not None else 0.0,
            float(op) if op is not None else 0.0,
        )
        if best >= 0.4 or (dream is not None and float(dream) > 0):
            signals.append(
                {
                    "id": "structural",
                    "label_uk": SIGNAL_LABELS["structural"],
                    "strength": _strength_from_score(best, high=0.75, medium=0.45),
                }
            )

    # Stable order: stronger first, then id
    signals.sort(
        key=lambda s: (-STRENGTH_ORDER.get(s["strength"], 0), s["id"]),
    )
    return signals


def discovery_primary_for(e: dict[str, Any], signals: list[dict[str, str]]) -> str:
    track = e.get("track") or ""
    if track in TRACK_TO_PRIMARY:
        primary = TRACK_TO_PRIMARY[track]
        # mixed: prefer strongest non-network signal if present
        if track == "mixed" and signals:
            for s in signals:
                if s["id"] != "network":
                    return s["id"]
        return primary
    if signals:
        for s in signals:
            if s["id"] != "network":
                return s["id"]
        return signals[0]["id"]
    return "strategy_goals"


def annotate_candidate(e: dict[str, Any]) -> dict[str, Any]:
    """Mutate one edge with kind/package/signals/discovery_primary/status."""
    pkg = package_from_edge(e)
    signals = build_signals(e)
    e["kind"] = "mss_candidate"
    e["package"] = pkg
    e["signals"] = signals
    e["discovery_primary"] = discovery_primary_for(e, signals)
    e["status"] = "registry_known" if e.get("known") else "hypothesis"
    return e


def annotate_candidates(edges: list[dict[str, Any]]) -> dict[str, int]:
    """Mutate edges in place. Returns counts."""
    counts = {"annotated": 0, "with_theme": 0, "registry_known": 0}
    for e in edges:
        annotate_candidate(e)
        counts["annotated"] += 1
        if (e.get("package") or {}).get("theme_id") not in (None, "other"):
            counts["with_theme"] += 1
        if e.get("status") == "registry_known":
            counts["registry_known"] += 1
    return counts


def _pair_key(e: dict[str, Any]) -> tuple[str, str]:
    a = (e.get("a") or "").strip()
    b = (e.get("b") or "").strip()
    return tuple(sorted((a, b)))  # type: ignore[return-value]


def _short_row(e: dict[str, Any]) -> dict[str, Any]:
    """Compact candidate for sidecar / UI."""
    pkg = e.get("package") or package_from_edge(e)
    signals = e.get("signals") or build_signals(e)
    # UI chips: top 3
    chips = [
        {"id": s["id"], "label_uk": s["label_uk"], "strength": s["strength"]}
        for s in signals[:3]
    ]
    row: dict[str, Any] = {
        "kind": "mss_candidate",
        "a": e.get("a"),
        "b": e.get("b"),
        "a_short": e.get("a_short"),
        "b_short": e.get("b_short"),
        "status": e.get("status") or ("registry_known" if e.get("known") else "hypothesis"),
        "package": pkg,
        "signals": signals,
        "signal_chips": chips,
        "discovery_primary": e.get("discovery_primary")
        or discovery_primary_for(e, signals),
        "track": e.get("track"),
        "known": bool(e.get("known")),
    }
    # Rank hints from source layer (not a combined product score)
    for key in (
        "score",
        "goals_cosine",
        "geo_score",
        "mss_network",
        "complementary_score",
        "explicit_ask_score",
        "operational_score",
        "suggest_confidence",
    ):
        if key in e and e[key] is not None:
            row[key] = e[key]
    return row


def write_candidates_sidecar(
    *,
    matching_edges: list[dict[str, Any]] | None = None,
    thematic: list[dict[str, Any]] | None = None,
    operational: list[dict[str, Any]] | None = None,
    complementary: list[dict[str, Any]] | None = None,
    explicit_ask: list[dict[str, Any]] | None = None,
    top_n_per_slice: int = 40,
    out_path: Path | None = None,
    manifest_path: Path | None = None,
) -> dict[str, Any]:
    """Thin browse file: known + top hypotheses from slices (not full pairwise)."""
    releases = RELEASES

    def _load(name: str) -> list[dict[str, Any]]:
        p = releases / name
        if not p.exists():
            return []
        return json.loads(p.read_text(encoding="utf-8"))

    edges = matching_edges if matching_edges is not None else _load("matching-edges.json")
    thematic = thematic if thematic is not None else _load("matching-edges.thematic.json")
    operational = (
        operational if operational is not None else _load("matching-edges.operational.json")
    )
    complementary = (
        complementary
        if complementary is not None
        else _load("matching-edges.complementary.json")
    )
    explicit_ask = (
        explicit_ask
        if explicit_ask is not None
        else _load("matching-edges.explicit-ask.json")
    )

    # Ensure candidate fields exist
    for collection in (edges, thematic, operational, complementary, explicit_ask):
        for e in collection:
            if "package" not in e:
                annotate_candidate(e)

    seen: set[tuple[str, str]] = set()
    known_rows: list[dict[str, Any]] = []
    for e in edges:
        if not e.get("known"):
            continue
        key = _pair_key(e)
        if key in seen or not key[0]:
            continue
        seen.add(key)
        known_rows.append(_short_row(e))

    def _take(
        collection: list[dict[str, Any]], *, source: str, limit: int
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for e in collection:
            if e.get("known"):
                continue
            key = _pair_key(e)
            if key in seen or not key[0]:
                continue
            seen.add(key)
            row = _short_row(e)
            row["source_slice"] = source
            out.append(row)
            if len(out) >= limit:
                break
        return out

    # Hypothesis browse order: explicit-ask → thematic → complementary → operational
    # (strength of "why talk" signal, not form buckets)
    hypotheses: list[dict[str, Any]] = []
    hypotheses.extend(_take(explicit_ask, source="explicit-ask", limit=top_n_per_slice))
    hypotheses.extend(_take(thematic, source="thematic", limit=top_n_per_slice))
    hypotheses.extend(_take(complementary, source="complementary", limit=top_n_per_slice))
    hypotheses.extend(_take(operational, source="operational", limit=top_n_per_slice))

    generated = datetime.now(timezone.utc).isoformat()
    payload = {
        "generatedAt": generated,
        "kind": "mss_candidates",
        "caveat": (
            "Кандидати договорів МСС (гіпотези). "
            "package.form — правова форма за правилами, не факт реєстру. "
            "known/registry_known — лише кураторська валідація. "
            "Стратегії / geo / complementary / explicit-ask — сигнали пошуку."
        ),
        "counts": {
            "registry_known": len(known_rows),
            "hypotheses": len(hypotheses),
        },
        "registry_known": known_rows,
        "hypotheses": hypotheses,
    }

    out = out_path or CANDIDATES_OUT
    man = manifest_path or CANDIDATES_MANIFEST
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "generatedAt": generated,
        "path": out.name,
        "registryKnown": len(known_rows),
        "hypotheses": len(hypotheses),
        "topNPerSlice": top_n_per_slice,
        "sliceOrder": ["explicit-ask", "thematic", "complementary", "operational"],
        "note": (
            "Thin sidecar for UI browse — not full pairwise. "
            "Forms are package fields; do not browse primarily by form_id."
        ),
        "license": "CC BY 4.0 — see DATA-LICENSE.md",
    }
    man.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return {
        "path": str(out),
        "registry_known": len(known_rows),
        "hypotheses": len(hypotheses),
    }


def main() -> None:
    edges = json.loads((RELEASES / "matching-edges.json").read_text(encoding="utf-8"))
    counts = annotate_candidates(edges)
    (RELEASES / "matching-edges.json").write_text(
        json.dumps(edges, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    result = write_candidates_sidecar(matching_edges=edges)
    print(f"annotated {counts['annotated']} edges "
          f"(theme={counts['with_theme']}, known={counts['registry_known']})")
    print(
        f"sidecar {result['path']}: "
        f"known={result['registry_known']} hypotheses={result['hypotheses']}"
    )


if __name__ == "__main__":
    main()
