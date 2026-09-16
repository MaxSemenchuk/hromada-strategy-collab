#!/usr/bin/env python3
"""Named objects / neighbours / GISRR leftovers from strategy text.

Writes:
  data/releases/strategy-entities.json
  data/releases/matching-edges.shared-asset.json

Does not set known=true. Does not change v7 combined score.

Usage:
  yarn extract-strategy-entities
  python3 scripts/analysis/extract_strategy_entities.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

from goals_hierarchy import find_mss_intents_in_text  # noqa: E402
from mss_candidate import annotate_candidates  # noqa: E402
from mss_suggest import annotate_edges  # noqa: E402
from strategy_text import (  # noqa: E402
    ASSET_HINT_RE,
    COOP_CTX_RE,
    build_name_index,
    find_assets,
    find_deficits,
    find_named_neighbours,
    find_offers,
    short_name,
)
from structure_gisrr_batch import (  # noqa: E402
    CATALOG,
    DETAILS,
    SWOT_CHALLENGE,
    SWOT_STRENGTH,
    clean_line,
    match_row,
    norm_name,
    strip_html,
)

HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
OUT = ROOT / "data" / "releases" / "strategy-entities.json"
OUT_MANIFEST = ROOT / "data" / "releases" / "strategy-entities.manifest.json"
OUT_EDGES = ROOT / "data" / "releases" / "matching-edges.shared-asset.json"
PREVIEW = ROOT / "docs" / "assets" / "shared-asset-preview.json"

FIELDS = (
    ("Goals", "goals"),
    ("Projects", "projects"),
    ("Challenges", "challenges"),
    ("Strengths", "strengths"),
    ("MSSAgreements", "mss_agreements"),
    ("PartnersMentioned", "partners"),
)

SWOT_OPP = {"3"}


def _blob(row: dict) -> str:
    return "\n".join((row.get(k) or "") for k, _ in FIELDS)


def load_gisrr_extras(rows: list[dict]) -> dict[str, dict]:
    """SWOT opportunities + leftover tasks keyed by Katottg. Cache-only."""
    extras: dict[str, dict] = {}
    if not CATALOG.exists() or not DETAILS.exists():
        return extras
    by_stem: dict[str, list[dict]] = defaultdict(list)
    for h in rows:
        if h.get("Name"):
            by_stem[norm_name(h["Name"])].append(h)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    for doc in catalog.get("documents") or []:
        path = DETAILS / f"{doc['rro_id']}.json"
        if not path.exists():
            continue
        row = match_row(doc.get("atu_name") or "", doc.get("oblast") or "", by_stem)
        if not row:
            continue
        code = row.get("Katottg") or ""
        if not code:
            continue
        detail = json.loads(path.read_text(encoding="utf-8"))
        gisrr_rows = detail.get("rows") or {}
        intents: list[dict] = []
        assets: list[dict] = []
        neighbours_text: list[str] = []
        tasks = [
            clean_line(t.get("task_name") or "")
            for t in gisrr_rows.get("tasks") or []
            if clean_line(t.get("task_name") or "")
        ]
        # Head (already often in Projects) + tail that our 25-cap drops.
        for task in tasks:
            if len(task) < 16:
                continue
            if find_mss_intents_in_text(task, field="gisrr-task"):
                intents.extend(find_mss_intents_in_text(task, field="gisrr-task"))
            elif ASSET_HINT_RE.search(task) or COOP_CTX_RE.search(task):
                assets.extend(find_assets(task, field="gisrr-task"))
                neighbours_text.append(task)
        for block in gisrr_rows.get("swot") or []:
            btype = str(block.get("type") or "")
            for item in block.get("swot_list") or []:
                if not isinstance(item, dict):
                    continue
                name = clean_line(item.get("swot_name") or item.get("name") or "")
                if len(name) < 16:
                    continue
                itype = str(item.get("type") or btype)
                if itype in SWOT_STRENGTH or itype in SWOT_CHALLENGE:
                    continue
                if itype in SWOT_OPP:
                    found = find_mss_intents_in_text(name, field="gisrr-swot-opportunity")
                    if found:
                        intents.extend(found)
                    elif COOP_CTX_RE.search(name):
                        intents.append(
                            {
                                "quote": name[:400],
                                "field": "gisrr-swot-opportunity",
                                "theme": None,
                            }
                        )
                    neighbours_text.append(name)
                    assets.extend(find_assets(name, field="gisrr-swot-opportunity"))
        vision = strip_html((gisrr_rows.get("document") or {}).get("strategic_vision") or "")
        if vision and COOP_CTX_RE.search(vision):
            found = find_mss_intents_in_text(vision, field="gisrr-vision")
            intents.extend(found[:1])

        seen_q: set[str] = set()
        uniq_intents: list[dict] = []
        for it in intents:
            key = (it.get("quote") or "")[:80].lower()
            if not key or key in seen_q:
                continue
            seen_q.add(key)
            uniq_intents.append(it)
        bucket = extras.setdefault(
            code,
            {"intents": [], "assets": [], "neighbour_blobs": []},
        )
        bucket["intents"].extend(uniq_intents)
        bucket["assets"].extend(assets)
        bucket["neighbour_blobs"].extend(neighbours_text)
    return extras


def pair_shared_assets(records: list[dict]) -> list[dict]:
    """Hypothesis edges: two hromadas name the same proper object."""
    by_key: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for rec in records:
        for asset in rec.get("assets") or []:
            if asset.get("common"):
                blob = " ".join(asset.get("quote") or "" for _ in [0])
                if not COOP_CTX_RE.search(blob) and "розчищ" not in (asset.get("quote") or "").lower():
                    continue
            by_key[(asset["kind"], asset["key"])].append(
                {
                    "rec": rec,
                    "asset": asset,
                }
            )

    edge_map: dict[frozenset[str], dict] = {}
    for (kind, key), members in by_key.items():
        uniq: dict[str, dict] = {}
        for m in members:
            name = m["rec"]["name"]
            uniq.setdefault(name, m)
        members = list(uniq.values())
        if len(members) < 2:
            continue
        for i, a in enumerate(members):
            for b in members[i + 1 :]:
                ra, rb = a["rec"], b["rec"]
                same_ob = bool(ra.get("oblast") and ra["oblast"] == rb["oblast"])
                if a["asset"].get("common") and not same_ob:
                    continue
                score = 0.8 if a["asset"].get("common") else 0.95
                if same_ob:
                    score = min(1.0, score + 0.05)
                display = a["asset"].get("name") or key
                reason = (
                    f"спільний обʼєкт «{display}» ({kind}) у стратегіях "
                    f"{ra['short']} і {rb['short']}"
                )
                pair = frozenset((ra["name"], rb["name"]))
                prev = edge_map.get(pair)
                row = {
                    "a": ra["name"],
                    "b": rb["name"],
                    "a_short": ra["short"],
                    "b_short": rb["short"],
                    "a_katottg": ra.get("katottg"),
                    "b_katottg": rb.get("katottg"),
                    "track": "shared_asset",
                    "shared_asset_score": round(score, 3),
                    "theme": a["asset"].get("theme"),
                    "asset_kind": kind,
                    "asset_key": key,
                    "asset_name": display,
                    "reasons": [reason],
                    "same_oblast": same_ob,
                    "known": False,
                }
                if prev is None or score > prev["shared_asset_score"]:
                    edge_map[pair] = row
    edges = sorted(
        edge_map.values(),
        key=lambda e: (
            -e["shared_asset_score"],
            -int(e["same_oblast"]),
            e["a_short"],
            e["b_short"],
        ),
    )
    return edges[:250]


def main() -> None:
    rows = json.loads(HROMADAS.read_text(encoding="utf-8"))
    index = build_name_index(rows)
    gisrr = load_gisrr_extras(rows)

    records: list[dict] = []
    for r in rows:
        name = (r.get("Name") or "").strip()
        if not name:
            continue
        code = (r.get("Katottg") or "").strip()
        oblast = r.get("Oblast") or ""
        assets: list[dict] = []
        deficits: list[dict] = []
        offers: list[dict] = []
        neighbour_blobs: list[str] = []
        extra_intents: list[dict] = []
        for field_key, field_label in FIELDS:
            text = (r.get(field_key) or "").strip()
            if not text:
                continue
            assets.extend(find_assets(text, field=field_label))
            if field_key == "Challenges":
                deficits.extend(find_deficits(text, field=field_label))
            if field_key in ("Strengths", "Projects"):
                offers.extend(find_offers(text, field=field_label))
            neighbour_blobs.append(text)

        extra = gisrr.get(code) or {}
        assets.extend(extra.get("assets") or [])
        extra_intents.extend(extra.get("intents") or [])
        neighbour_blobs.extend(extra.get("neighbour_blobs") or [])

        seen_asset: set[tuple[str, str]] = set()
        uniq_assets: list[dict] = []
        for a in assets:
            sig = (a.get("kind"), a.get("key"))
            if sig in seen_asset:
                continue
            seen_asset.add(sig)
            uniq_assets.append(a)

        named: list[dict] = []
        seen_nb: set[str] = set()
        for blob in neighbour_blobs:
            for nb in find_named_neighbours(
                blob,
                speaker_name=name,
                speaker_oblast=oblast,
                index=index,
            ):
                if nb["name"] in seen_nb:
                    continue
                seen_nb.add(nb["name"])
                named.append(nb)

        if not (uniq_assets or deficits or offers or named or extra_intents):
            continue
        records.append(
            {
                "name": name,
                "short": short_name(name),
                "katottg": code or None,
                "oblast": oblast or None,
                "assets": uniq_assets[:12],
                "deficits": deficits[:8],
                "offers": offers[:8],
                "named_neighbours": named[:8],
                "gisrr_extra_intents": extra_intents[:8],
            }
        )

    edges = pair_shared_assets(records)
    suggest = annotate_edges(edges)
    candidates = annotate_candidates(edges)

    generated = datetime.now(timezone.utc).isoformat()
    OUT.write_text(
        json.dumps(
            {
                "generatedAt": generated,
                "hromadaCount": len(records),
                "warning": (
                    "Named objects / neighbours / deficits from strategy text and GISRR "
                    "cache. Hypotheses — verify in source PDF. Not v7 score, not known=true."
                ),
                "hromadas": records,
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
                "hromadaCount": len(records),
                "withAssets": sum(1 for h in records if h["assets"]),
                "withDeficits": sum(1 for h in records if h["deficits"]),
                "withNamedNeighbours": sum(1 for h in records if h["named_neighbours"]),
                "withGisrrExtraIntents": sum(1 for h in records if h["gisrr_extra_intents"]),
                "sharedAssetEdges": len(edges),
                "mssSuggest": {
                    "annotated": suggest["annotated"],
                    "withTheme": suggest["with_theme"],
                },
                "mssCandidate": {
                    "annotated": candidates["annotated"],
                    "withTheme": candidates["with_theme"],
                },
                "method": (
                    "strategy_text named objects + neighbour NER + GISRR SWOT type 3 / "
                    "task tail; shared-asset pairs by (kind, key); not v7 score"
                ),
                "warning": "МСС candidate hypotheses — not known=true.",
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
                "caveat": "Shared named object in strategy text — not a registered IMC agreement.",
                "hromadaCount": len(records),
                "edgeCount": len(edges),
                "top": [
                    {
                        "a_short": e["a_short"],
                        "b_short": e["b_short"],
                        "shared_asset_score": e["shared_asset_score"],
                        "asset_name": e.get("asset_name"),
                        "asset_kind": e.get("asset_kind"),
                        "suggested_theme": e.get("suggested_theme"),
                        "suggested_form": e.get("suggested_form"),
                        "reasons": e["reasons"][:2],
                    }
                    for e in edges[:30]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        f"Wrote {OUT.relative_to(ROOT)} ({len(records)} hromadas), "
        f"{OUT_EDGES.relative_to(ROOT)} ({len(edges)} edges); "
        f"named_neighbours={sum(1 for h in records if h['named_neighbours'])} "
        f"gisrr_intents={sum(1 for h in records if h['gisrr_extra_intents'])}"
    )


if __name__ == "__main__":
    main()
