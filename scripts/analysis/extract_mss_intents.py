#!/usr/bin/env python3
"""Extract explicit МСС intents from strategy fields → mss-intents + explicit-ask edges.

Scans Goals / Projects / Challenges / MSSAgreements / PartnersMentioned.
Does not set known=true. Hypotheses only (even when the quote is clear).

Usage:
  yarn extract-mss-intents
  python3 scripts/analysis/extract_mss_intents.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from goals_hierarchy import find_mss_intents_in_text, load_hierarchy_index  # noqa: E402
from mss_candidate import annotate_candidates  # noqa: E402
from mss_suggest import annotate_edges  # noqa: E402

HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
OUT_INTENTS = ROOT / "data" / "releases" / "mss-intents.json"
OUT_MANIFEST = ROOT / "data" / "releases" / "mss-intents.manifest.json"
OUT_EDGES = ROOT / "data" / "releases" / "matching-edges.explicit-ask.json"
PREVIEW = ROOT / "docs" / "assets" / "explicit-ask-preview.json"

FIELDS = (
    ("MSSAgreements", "mss_agreements"),
    ("Goals", "goals"),
    ("Projects", "projects"),
    ("Challenges", "challenges"),
    ("PartnersMentioned", "partners"),
)

# Named neighbour hints inside quotes (short forms)
NEIGHBOUR_HINT = re.compile(
    r"([А-ЯІЇЄҐ][а-яіїєґ'’\-]{2,}(?:ська|зька|цька)?)\s+"
    r"(?:міськ|селищн|сільськ|територіальн)",
    re.I,
)


def short_name(name: str) -> str:
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
    rows = json.loads(HROMADAS.read_text(encoding="utf-8"))
    hierarchy = load_hierarchy_index()
    by_short: dict[str, dict] = {}
    for r in rows:
        name = (r.get("Name") or "").strip()
        if name:
            by_short[short_name(name).lower()] = r

    intents_out: list[dict] = []
    for r in rows:
        name = (r.get("Name") or "").strip()
        code = (r.get("Katottg") or "").strip()
        if not name:
            continue
        found: list[dict] = []
        for field_key, field_label in FIELDS:
            text = (r.get(field_key) or "").strip()
            if not text:
                continue
            found.extend(find_mss_intents_in_text(text, field=field_label))

        hier = hierarchy.get(name) or hierarchy.get(code)
        if hier:
            for mi in hier.get("mss_intents") or []:
                if isinstance(mi, dict) and mi.get("quote"):
                    found.append(
                        {
                            "quote": mi["quote"][:400],
                            "field": mi.get("field") or "curated",
                            "theme": mi.get("theme"),
                        }
                    )
                elif isinstance(mi, str):
                    found.append({"quote": mi[:400], "field": "curated", "theme": None})

        # de-dupe by quote prefix
        seen: set[str] = set()
        uniq: list[dict] = []
        for item in found:
            key = item["quote"][:80].lower()
            if key in seen:
                continue
            seen.add(key)
            uniq.append(item)
        if not uniq:
            continue

        named: list[str] = []
        for item in uniq:
            for m in NEIGHBOUR_HINT.finditer(item["quote"]):
                hint = m.group(1)
                # try resolve against corpus shorts
                for short, row in by_short.items():
                    if hint.lower() in short and row.get("Name") != name:
                        named.append(row["Name"])
        named = sorted(set(named))

        intents_out.append(
            {
                "name": name,
                "short": short_name(name),
                "katottg": code or None,
                "oblast": r.get("Oblast"),
                "intent_count": len(uniq),
                "intents": uniq[:8],
                "named_neighbours": named,
            }
        )

    # Explicit-ask edges: same oblast pairs where at least one has an intent,
    # or named neighbour resolved; plus curated named pairs.
    edge_map: dict[frozenset[str], dict] = {}
    intent_by_name = {x["name"]: x for x in intents_out}

    def add_edge(a: str, b: str, reason: str, theme: str | None) -> None:
        if a == b:
            return
        key = frozenset((a, b))
        sa, sb = short_name(a), short_name(b)
        prev = edge_map.get(key)
        score = 0.95 if "named" in reason else 0.75
        row = {
            "a": a,
            "b": b,
            "a_short": sa,
            "b_short": sb,
            "track": "explicit-ask",
            "explicit_ask_score": score,
            "theme": theme,
            "reasons": [reason],
            "known": False,
        }
        if prev is None or score > prev["explicit_ask_score"]:
            edge_map[key] = row

    for item in intents_out:
        for nb in item.get("named_neighbours") or []:
            quote = item["intents"][0]["quote"] if item["intents"] else ""
            add_edge(
                item["name"],
                nb,
                f"named neighbour in intent: «{quote[:120]}»",
                item["intents"][0].get("theme") if item["intents"] else None,
            )

    # Same-oblast co-intents (both declare МСС language) — soft cluster signal
    by_oblast: dict[str, list[dict]] = {}
    for item in intents_out:
        ob = (item.get("oblast") or "").strip()
        if ob:
            by_oblast.setdefault(ob, []).append(item)
    for _ob, group in by_oblast.items():
        if len(group) < 2:
            continue
        for i, a in enumerate(group):
            for b in group[i + 1 :]:
                theme = None
                themes_a = {x.get("theme") for x in a["intents"] if x.get("theme")}
                themes_b = {x.get("theme") for x in b["intents"] if x.get("theme")}
                shared = themes_a & themes_b
                if shared:
                    theme = sorted(shared)[0]
                reason = (
                    f"обидві згадують МСС/кооперацію"
                    + (f" (тема: {theme})" if theme else "")
                )
                add_edge(a["name"], b["name"], reason, theme)

    edges = sorted(
        edge_map.values(),
        key=lambda e: (-e["explicit_ask_score"], e["a_short"], e["b_short"]),
    )
    suggest = annotate_edges(edges)
    candidates = annotate_candidates(edges)

    generated = datetime.now(timezone.utc).isoformat()
    OUT_INTENTS.write_text(
        json.dumps(
            {
                "generatedAt": generated,
                "hromadaCount": len(intents_out),
                "warning": "Quotes are extraction hypotheses — verify in source PDF before outreach.",
                "hromadas": intents_out,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    OUT_MANIFEST.write_text(
        json.dumps(
            {
                "generatedAt": generated,
                "hromadaCount": len(intents_out),
                "explicitAskEdges": len(edges),
                "mssSuggest": {
                    "annotated": suggest["annotated"],
                    "withTheme": suggest["with_theme"],
                },
                "mssCandidate": {
                    "annotated": candidates["annotated"],
                    "withTheme": candidates["with_theme"],
                },
                "method": (
                    "regex МСС/кооперація on strategy fields + curated hierarchy intents "
                    "+ suggested_theme/form (mss_suggest) + mss_candidate package/signals"
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    OUT_EDGES.write_text(json.dumps(edges, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    PREVIEW.write_text(
        json.dumps(
            {
                "generatedAt": generated,
                "caveat": "Explicit МСС language in strategy text — not registry-confirmed.",
                "intentHromadas": len(intents_out),
                "edgeCount": len(edges),
                "top": [
                    {
                        "a_short": e["a_short"],
                        "b_short": e["b_short"],
                        "explicit_ask_score": e["explicit_ask_score"],
                        "theme": e.get("theme"),
                        "suggested_theme": e.get("suggested_theme"),
                        "suggested_form": e.get("suggested_form"),
                        "reasons": e["reasons"][:2],
                    }
                    for e in edges[:30]
                ],
                "samples": [
                    {
                        "short": h["short"],
                        "quote": h["intents"][0]["quote"][:180],
                        "theme": h["intents"][0].get("theme"),
                    }
                    for h in intents_out[:15]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {OUT_INTENTS.relative_to(ROOT)} ({len(intents_out)} hromadas), "
        f"{OUT_EDGES.relative_to(ROOT)} ({len(edges)} edges)"
    )


if __name__ == "__main__":
    main()
