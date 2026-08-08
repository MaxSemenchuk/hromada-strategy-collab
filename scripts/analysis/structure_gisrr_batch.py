#!/usr/bin/env python3
"""Structure GISRR local-strategy cache into data/releases/hromadas.json.

Reads data/cache/gisrr/{catalog,details}, maps to Katottg via Name+Oblast,
writes scripts/hromada-output/*.json and upserts strategy fields for rows that
do not yet have Goals (unless --force).

Usage:
  yarn structure-gisrr                 # upsert new only
  yarn structure-gisrr --limit 10
  yarn structure-gisrr --dry-run
  yarn structure-gisrr --force         # overwrite existing Goals
  yarn structure-gisrr --include-existing-goals   # also fill StrategyUrl on mined rows
"""

from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GISRR = ROOT / "data" / "cache" / "gisrr"
CATALOG = GISRR / "catalog.json"
DETAILS = GISRR / "details"
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
MANIFEST = ROOT / "data" / "releases" / "hromadas.manifest.json"
OUT_DIR = ROOT / "scripts" / "hromada-output"
HIERARCHY_GISRR = ROOT / "data" / "sources" / "gisrr-goals-hierarchy.json"

MSS_RE = re.compile(
    r"міжмуніцип\w*|міжтериторіальн\w*|\bМСС\b|сусідн\w+\s+громад",
    re.I,
)
SWOT_STRENGTH = {"1"}
SWOT_CHALLENGE = {"2", "4"}  # weaknesses + threats


def strip_html(v: object) -> str:
    if not isinstance(v, str):
        return ""
    t = re.sub(r"<[^>]+>", " ", v)
    t = htmllib.unescape(t)
    return re.sub(r"\s+", " ", t).strip()


def norm_name(s: str) -> str:
    s = (s or "").lower().replace("’", "'").replace("ʼ", "'")
    s = unicodedata.normalize("NFC", s)
    for junk in [
        " територіальна громада",
        " міська",
        " селищна",
        " сільська",
        " тг",
    ]:
        s = s.replace(junk, "")
    return re.sub(r"\s+", " ", s).strip()


def norm_obl(s: str) -> str:
    return (
        (s or "")
        .lower()
        .replace("обл.", "область")
        .replace(" область", "")
        .strip()
    )


def clean_line(s: str) -> str:
    s = strip_html(s)
    s = re.sub(r"\s+", " ", s).strip(" \t-•|")
    return s


def has_goals(row: dict) -> bool:
    g = row.get("Goals")
    return isinstance(g, str) and len(g.strip()) > 40


def out_name(name: str) -> str:
    return re.sub(r"[^\w\-]+", "-", name, flags=re.UNICODE).strip("-") + ".json"


def match_row(atu_name: str, oblast: str, by_stem: dict[str, list[dict]]) -> dict | None:
    st = norm_name(atu_name)
    cands = list(by_stem.get(st) or [])
    if not cands:
        for k, vs in by_stem.items():
            if len(st) >= 5 and (k.startswith(st) or st.startswith(k)):
                cands.extend(vs)
    if not cands:
        return None
    obl = norm_obl(oblast)
    obl_hits = [c for c in cands if obl and obl in norm_obl(c.get("Oblast") or "")]
    if len(obl_hits) == 1:
        return obl_hits[0]
    if len(obl_hits) > 1:
        # prefer exact stem match among oblast hits
        exact = [c for c in obl_hits if norm_name(c["Name"]) == st]
        return exact[0] if exact else obl_hits[0]
    if len(cands) == 1:
        return cands[0]
    return None


def convert_detail(detail: dict, catalog_entry: dict) -> dict | None:
    rows = detail.get("rows") or {}
    doc = rows.get("document") or {}
    goals_raw = [clean_line(g.get("name") or "") for g in rows.get("goals") or []]
    goals_raw = [g for g in goals_raw if len(g) > 8]
    if not goals_raw:
        return None

    # Preserve GISRR numbering; prefix bare lines as strategic goals
    strategic: list[dict] = []
    for i, g in enumerate(goals_raw, 1):
        text = g
        if not re.match(r"^(?:стратегічн|ціль|\d+)", text, re.I):
            text = f"Стратегічна ціль {i}. {text}"
        elif re.match(r"^\d+\.\s+", text) and not re.search(r"ціль", text, re.I):
            text = re.sub(r"^(\d+)\.\s+", rf"Стратегічна ціль \1. ", text, count=1)
        sid_m = re.search(r"ціль\s*(\d+)", text, re.I) or re.match(r"^(\d+)\.", text)
        sid = sid_m.group(1) if sid_m else str(i)
        rsg = (rows.get("goals") or [])[i - 1].get("rsg_id")
        strategic.append({"id": sid, "text": text, "rsg_id": rsg})

    id_by_rsg = {s.get("rsg_id"): s["id"] for s in strategic if s.get("rsg_id")}

    operational: list[dict] = []
    for sg in rows.get("subgoals") or []:
        text = clean_line(sg.get("name") or "")
        if len(text) < 8:
            continue
        parent = id_by_rsg.get(sg.get("rsg_id"))
        # ensure N.M style when possible
        if parent and not re.match(r"^\d+\.\d+", text):
            # keep as-is but still link parent
            pass
        operational.append({"parent": parent, "text": text})

    # SWOT
    strengths: list[str] = []
    challenges: list[str] = []
    for block in rows.get("swot") or []:
        btype = str(block.get("type") or "")
        for item in block.get("swot_list") or []:
            if not isinstance(item, dict):
                continue
            name = clean_line(item.get("swot_name") or item.get("name") or "")
            if len(name) < 12:
                continue
            itype = str(item.get("type") or btype)
            if itype in SWOT_STRENGTH:
                strengths.append(name)
            elif itype in SWOT_CHALLENGE:
                challenges.append(name)

    # Trends as extra challenges if SWOT thin
    if len(challenges) < 3:
        for t in rows.get("trends") or []:
            name = clean_line(t.get("name") or "")
            desc = clean_line(t.get("description") or "")
            bit = name if len(name) > 15 else desc[:200]
            if len(bit) > 20:
                challenges.append(bit)

    # Tasks → projects (cap)
    tasks = [
        clean_line(t.get("task_name") or "")
        for t in rows.get("tasks") or []
        if clean_line(t.get("task_name") or "")
    ]
    projects_lines = [f"- {t}" for t in tasks[:25] if len(t) > 15]

    # MSS intents from goals/subgoals/tasks
    mss_intents: list[dict] = []
    scan_lines = (
        [s["text"] for s in strategic]
        + [o["text"] for o in operational]
        + tasks
        + [strip_html(doc.get("strategic_vision") or "")]
    )
    for line in scan_lines:
        if not MSS_RE.search(line):
            continue
        quote = line.strip()
        if len(quote) > 280:
            m = MSS_RE.search(quote)
            if m:
                a = max(0, m.start() - 40)
                b = min(len(quote), m.end() + 120)
                quote = quote[a:b].strip()
        theme = None
        low = quote.lower()
        if re.search(r"відход|смітт|тпв|полігон", low):
            theme = "відходи"
        elif re.search(r"вод|річк|каналіац", low):
            theme = "вода"
        elif re.search(r"туризм|рекреац", low):
            theme = "туризм"
        elif re.search(r"дорож|транспорт", low):
            theme = "транспорт"
        mss_intents.append(
            {"quote": quote, "field": "gisrr-goals", "theme": theme}
        )
        if len(mss_intents) >= 8:
            break

    # Dedup intents
    seen_q: set[str] = set()
    uniq_intents = []
    for it in mss_intents:
        q = it["quote"]
        if q in seen_q:
            continue
        seen_q.add(q)
        uniq_intents.append(it)

    n_ops = len(operational)
    n_goals = len(strategic)
    if n_goals >= 2 and n_ops >= 5:
        source_quality = "full-strategy"
    elif n_goals >= 1:
        source_quality = "partial"
    else:
        return None

    flat_lines = [s["text"] for s in strategic] + [o["text"] for o in operational]
    goals_flat = "\n".join(flat_lines)

    vision = strip_html(doc.get("strategic_vision") or "")
    if vision and len(vision) > 80 and len(strengths) < 2:
        strengths.append(vision[:300] + ("…" if len(vision) > 300 else ""))

    period_from = str(doc.get("medium_term_period") or detail.get("stats", {}).get("period_from") or "").strip()
    period_to = str(doc.get("long_term_period") or detail.get("stats", {}).get("period_to") or "").strip()
    period = None
    if period_from and period_to:
        period = f"{period_from}–{period_to}"
    elif period_from or period_to:
        period = period_from or period_to

    acceptance = str(
        doc.get("acceptance_date")
        or (detail.get("stats") or {}).get("acceptance_date")
        or ""
    ).strip()
    year = None
    if acceptance and re.match(r"^\d{4}", acceptance):
        year = int(acceptance[:4])
    elif period_to and re.match(r"^\d{4}", period_to):
        year = int(period_to[:4])

    mss_note = ""
    if uniq_intents:
        mss_note = "Явний запит МСС у GISRR-цілях/задачах: " + uniq_intents[0]["quote"][:220]

    return {
        "goals": goals_flat,
        "strategic_goals": [{"id": s["id"], "text": s["text"]} for s in strategic],
        "operational_goals": operational,
        "mss_intents": uniq_intents,
        "projects": "\n".join(projects_lines) if projects_lines else "",
        "strengths": "\n".join(f"- {s}" for s in strengths[:12]),
        "challenges": "\n".join(f"- {c}" for c in challenges[:12]),
        "partners_mentioned": "",
        "mss_agreements": mss_note,
        "source_quality": source_quality,
        "confidence_notes": (
            f"Auto-structured from GISRR {catalog_entry.get('detail_url') or ''} "
            f"(reg {catalog_entry.get('reg_num')}). "
            f"goals={n_goals} subgoals={n_ops} tasks={len(tasks)}. "
            "Not hand-curated."
        ),
        "donors_programs": [],
        "strategy_url": catalog_entry.get("detail_url"),
        "strategy_year": year,
        "strategy_period": period,
        "rro_id": catalog_entry.get("rro_id"),
        "stats": {
            "goals": n_goals,
            "subgoals": n_ops,
            "tasks": len(tasks),
            "mss_intents": len(uniq_intents),
            "source_quality": source_quality,
        },
    }


def pick_best_doc(entries: list[dict]) -> dict:
    """Prefer richer hierarchy when multiple docs share one hromada."""
    scored = []
    for e in entries:
        st = (e.get("structured") or {}).get("stats") or {}
        score = st.get("subgoals", 0) * 10 + st.get("goals", 0) * 3 + st.get("tasks", 0)
        scored.append((score, e))
    scored.sort(key=lambda x: -x[0])
    return scored[0][1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="Overwrite rows that already have Goals")
    ap.add_argument(
        "--include-existing-goals",
        action="store_true",
        help="Also set StrategyUrl/period on already-mined rows (no Goals overwrite unless --force)",
    )
    args = ap.parse_args()

    if not CATALOG.exists():
        raise SystemExit(f"Missing {CATALOG} — run yarn fetch-gisrr-strategies first")

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    hromadas: list[dict] = json.loads(HROMADAS.read_text(encoding="utf-8"))
    by_kat = {h["Katottg"]: h for h in hromadas if h.get("Katottg")}
    by_stem: dict[str, list[dict]] = defaultdict(list)
    for h in hromadas:
        by_stem[norm_name(h["Name"])].append(h)

    # Convert all details, group by katottg
    prepared: list[dict] = []
    unmatched = []
    skipped_no_goals = 0
    for doc in catalog.get("documents") or []:
        path = DETAILS / f"{doc['rro_id']}.json"
        if not path.exists():
            continue
        detail = json.loads(path.read_text(encoding="utf-8"))
        structured = convert_detail(detail, doc)
        if not structured:
            skipped_no_goals += 1
            continue
        row = match_row(doc["atu_name"], doc["oblast"], by_stem)
        if not row:
            unmatched.append(doc)
            continue
        prepared.append(
            {
                "catalog": doc,
                "structured": structured,
                "katottg": row["Katottg"],
                "name": row["Name"],
            }
        )

    # One best doc per katottg
    by_k: dict[str, list[dict]] = defaultdict(list)
    for p in prepared:
        by_k[p["katottg"]].append(p)
    unique = [pick_best_doc(vs) for vs in by_k.values()]
    unique.sort(key=lambda p: p["name"])

    to_write = []
    skipped_existing = 0
    for p in unique:
        row = by_kat[p["katottg"]]
        if has_goals(row) and not args.force:
            skipped_existing += 1
            if args.include_existing_goals:
                to_write.append({**p, "mode": "meta-only"})
            continue
        to_write.append({**p, "mode": "full"})

    if args.limit > 0:
        to_write = to_write[: args.limit]

    print(
        f"GISRR structure: candidates={len(unique)} write={len(to_write)} "
        f"skip_existing_goals={skipped_existing} unmatched={len(unmatched)} "
        f"no_goals_docs={skipped_no_goals}"
    )
    if unmatched:
        print("  unmatched:", [(u["atu_name"], u["oblast"]) for u in unmatched])

    if args.dry_run:
        for p in to_write[:15]:
            st = p["structured"]["stats"]
            print(
                f"  [{p['mode']}] {p['name']} · {st['source_quality']} · "
                f"g={st['goals']} op={st['subgoals']} mss={st['mss_intents']}"
            )
        if len(to_write) > 15:
            print(f"  … +{len(to_write) - 15} more")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc).isoformat()
    hierarchy_rows = []
    upserted = 0
    meta_only = 0

    for p in to_write:
        row = by_kat[p["katottg"]]
        st = p["structured"]
        mode = p["mode"]

        if mode == "full":
            row["Goals"] = st["goals"]
            row["Projects"] = st["projects"] or row.get("Projects")
            row["Strengths"] = st["strengths"] or row.get("Strengths")
            row["Challenges"] = st["challenges"] or row.get("Challenges")
            row["PartnersMentioned"] = st["partners_mentioned"] or row.get("PartnersMentioned")
            row["MSSAgreements"] = st["mss_agreements"] or row.get("MSSAgreements")
            row["SourceQuality"] = st["source_quality"]
            row["ExtractedAt"] = now
            row["DonorsPrograms"] = row.get("DonorsPrograms") or []
            upserted += 1
        else:
            meta_only += 1

        if st.get("strategy_url") and not row.get("StrategyUrl"):
            row["StrategyUrl"] = st["strategy_url"]
        if st.get("strategy_year") and not row.get("StrategyYear"):
            row["StrategyYear"] = st["strategy_year"]
        if st.get("strategy_period") and not row.get("StrategyPeriod"):
            row["StrategyPeriod"] = st["strategy_period"]

        # local output always for full writes
        if mode == "full":
            local = {
                "goals": st["goals"],
                "projects": st["projects"],
                "strengths": st["strengths"],
                "challenges": st["challenges"],
                "partners_mentioned": st["partners_mentioned"],
                "mss_agreements": st["mss_agreements"],
                "source_quality": st["source_quality"],
                "confidence_notes": st["confidence_notes"],
                "donors_programs": [],
                "strategic_goals": st["strategic_goals"],
                "operational_goals": st["operational_goals"],
                "mss_intents": st["mss_intents"],
                "strategy_url": st.get("strategy_url"),
                "gisrr_rro_id": st.get("rro_id"),
            }
            (OUT_DIR / out_name(p["name"])).write_text(
                json.dumps(local, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            hierarchy_rows.append(
                {
                    "name": p["name"],
                    "katottg": p["katottg"],
                    "source": "gisrr-structure",
                    "strategic_goals": st["strategic_goals"],
                    "operational_goals": st["operational_goals"],
                    "mss_intents": st["mss_intents"],
                }
            )

    HROMADAS.write_text(
        json.dumps(hromadas, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    text_mined = sum(1 for r in hromadas if r.get("SourceQuality") is not None)
    goals_n = sum(1 for r in hromadas if has_goals(r))
    manifest = {}
    if MANIFEST.exists():
        try:
            manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            manifest = {}
    manifest.update(
        {
            "generatedAt": now,
            "source": "local:structure-gisrr",
            "totalRows": len(hromadas),
            "textMinedRows": text_mined,
            "goalsRows": goals_n,
            "portalUrlRows": sum(1 for r in hromadas if r.get("PortalUrl")),
            "schema": "see docs/hromadas-schema.md",
            "license": "CC BY 4.0 — see DATA-LICENSE.md",
            "lastUpsert": f"gisrr-batch:{upserted}",
            "gisrr": {
                "upserted": upserted,
                "meta_only": meta_only,
                "skipped_existing_goals": skipped_existing,
                "unmatched": len(unmatched),
                "hierarchy_rows": len(hierarchy_rows),
            },
        }
    )
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    HIERARCHY_GISRR.parent.mkdir(parents=True, exist_ok=True)
    HIERARCHY_GISRR.write_text(
        json.dumps(
            {
                "generatedAt": now,
                "method": "GISRR auto-structure (goals/subgoals)",
                "hromadaCount": len(hierarchy_rows),
                "hromadas": hierarchy_rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(
        f"done: upserted={upserted} meta_only={meta_only} "
        f"textMinedRows={text_mined} goalsRows={goals_n}"
    )
    print(f"wrote {HIERARCHY_GISRR.relative_to(ROOT)}")
    print("next: yarn build-goals-hierarchy && yarn extract-mss-intents && yarn match …")


if __name__ == "__main__":
    main()
