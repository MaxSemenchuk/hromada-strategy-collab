#!/usr/bin/env python3
"""Complementary matching: resource / DREAM priority of A ↔ challenge of B.

v3: kitchen-sink sector hits are capped; named deficits (worn water pipe,
missing landfill, …) outweigh generic «освіта / культура». Separate from
v7 goals-cosine. Does not set known=true. Hypotheses only.

Signals:
  - DREAM top_sectors(A) hit keyword patterns in Challenges(B) (and reverse)
  - Strengths(A) sector tags hit Challenges(B) (and reverse)
  - Named deficit of B matched by Strengths/Projects offer of A
  - Resource proxies (health / competence / fiscal) when the other side's
    Challenges mention the matching need

Usage:
  yarn complementary-match
  python3 scripts/analysis/complementary_match.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from mss_candidate import annotate_candidates  # noqa: E402
from mss_suggest import SECTOR_TO_THEME, annotate_edges, theme_label  # noqa: E402
from strategy_text import (  # noqa: E402
    KITCHEN_SINK_CAP,
    KITCHEN_SINK_SECTORS,
    OFFER_LABELS,
    deficit_kinds,
    offer_kinds,
    sector_hit_weight,
)
HROMADAS = ROOT / "data" / "releases" / "hromadas.json"
RESOURCES = ROOT / "data" / "releases" / "hromada-resources.json"
DREAM = ROOT / "data" / "releases" / "dream-priorities.json"
TWINNING = ROOT / "data" / "releases" / "twinning-partners.json"
OUT = ROOT / "data" / "releases" / "matching-edges.complementary.json"
MANIFEST = ROOT / "data" / "releases" / "matching-edges.complementary.manifest.json"
PREVIEW = ROOT / "docs" / "assets" / "complementary-preview.json"

# Sector → Ukrainian challenge/strength keyword stems (case-insensitive)
SECTOR_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "Освіта": [re.compile(p, re.I) for p in (r"освіт", r"школ", r"ліце", r"садоч", r"учнів", r"кадр")],
    "Охорона здоров'я": [re.compile(p, re.I) for p in (r"мед", r"лікарн", r"здоров", r"амбулатор", r"ФАП", r"лікув")],
    "Вода / каналізація (ЖКГ)": [
        re.compile(p, re.I) for p in (r"вод[оа]", r"каналіз", r"водопостач", r"водовідвед", r"ЖКГ", r"тепломер")
    ],
    "Довкілля / екологія": [re.compile(p, re.I) for p in (r"еколог", r"смітт", r"відход", r"ТПВ", r"полігон", r"забрудн")],
    "Транспорт / логістика": [re.compile(p, re.I) for p in (r"транспорт", r"дорог", r"логістик", r"перевезен", r"міст ")],
    "Енергетика (ВДЕ)": [re.compile(p, re.I) for p in (r"енерг", r"котельн", r"тепло", r"ВДЕ", r"соняч", r"електропостач")],
    "Безпека / ЦЗ": [re.compile(p, re.I) for p in (r"безпек", r"укритт", r"ЦЗ", r"цивільн", r"пожеж", r"обстріл")],
    "Туризм": [re.compile(p, re.I) for p in (r"турист", r"спадщин", r"рекреац", r"готель")],
    "Культура / спадщина": [re.compile(p, re.I) for p in (r"культур", r"музей", r"спадщин", r"театр", r"бібліот")],
    "Підприємництво / МСБ": [re.compile(p, re.I) for p in (r"бізнес", r"підприєм", r"МСБ", r"інвест", r"робоч")],
    "Соціальні послуги": [re.compile(p, re.I) for p in (r"соціал", r"ВПО", r"ветеран", r"вразлив")],
    "Відновлення / реконструкція": [re.compile(p, re.I) for p in (r"відновл", r"реконструк", r"зруйнов", r"відбудов", r"руйнув")],
    "Е-врядування": [re.compile(p, re.I) for p in (r"ЦНАП", r"адмінпослуг", r"е-послуг", r"Центр\s*Дія", r"е-урядуван")],
    "IT / цифровізація": [
        re.compile(p, re.I)
        for p in (r"цифров", r"інформатизац", r"\bIT\b", r"інтернет", r"смарт", r"е-послуг", r"портал")
    ],
    "Сільське господарство / АПК": [re.compile(p, re.I) for p in (r"аграр", r"с/г", r"сільськ", r"АПК", r"фермер")],
}

RESOURCE_NEED_PATTERNS: list[tuple[str, re.Pattern[str], str]] = [
    ("health", re.compile(r"мед|лікарн|здоров|амбулатор", re.I), "health_capacity"),
    ("competence", re.compile(r"молодь|бізнес|кадр|підприєм", re.I), "competence"),
    ("fiscal", re.compile(r"бюджет|фінанс|доход|інвест", re.I), "fiscal_capacity"),
    ("water", re.compile(r"вод[оа]|каналіз|ЖКГ", re.I), "dfrr_or_infra"),
    (
        "international",
        re.compile(r"міжнарод|донор|грант|євроінтеграц|партнер\w*\s+(закордон|іноземн)", re.I),
        "international_ties",
    ),
]


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


def sectors_in_text(text: str) -> set[str]:
    if not text:
        return set()
    hits: set[str] = set()
    for sector, patterns in SECTOR_PATTERNS.items():
        if any(p.search(text) for p in patterns):
            hits.add(sector)
    return hits


def load_profiles() -> dict[str, dict]:
    """Index by katottg."""
    profiles: dict[str, dict] = {}

    for row in json.loads(HROMADAS.read_text(encoding="utf-8")):
        code = (row.get("Katottg") or row.get("KATOTTG") or "").strip()
        name = (row.get("Name") or "").strip()
        if not code or not name:
            continue
        challenges = (row.get("Challenges") or "").strip()
        strengths = (row.get("Strengths") or "").strip()
        projects = (row.get("Projects") or "").strip()
        profiles[code] = {
            "katottg": code,
            "name": name,
            "short": short_name(name),
            "oblast": row.get("Oblast"),
            "challenges": challenges,
            "strengths": strengths,
            "projects": projects,
            "challenge_sectors": sectors_in_text(challenges),
            "strength_sectors": sectors_in_text(strengths),
            "deficit_kinds": deficit_kinds(challenges),
            "offer_kinds": offer_kinds(strengths, projects),
            "dream_sectors": [],
            "own_income_per_capita": None,
            "health_primary": None,
            "health_known": False,
            "competence_known": False,
            "youth_centers": None,
            "business_support_centers": None,
            "dfrr_years": None,
            # A hromada with donor-program or EU-twinning experience is
            # itself a resource — "we've done this before, we can help you
            # navigate it too" — not evidence of a tie to any specific
            # candidate partner. See twinning merge below.
            "international_ties": bool(row.get("DonorsPrograms")),
        }

    if RESOURCES.exists():
        for row in json.loads(RESOURCES.read_text(encoding="utf-8")).get("hromadas") or []:
            code = (row.get("katottg") or "").strip()
            if code not in profiles:
                continue
            p = profiles[code]
            p["own_income_per_capita"] = row.get("own_income_per_capita")
            p["health_primary"] = row.get("health_primary")
            p["health_known"] = bool(row.get("health_known"))
            p["competence_known"] = bool(row.get("competence_known"))
            p["youth_centers"] = row.get("youth_centers")
            p["business_support_centers"] = row.get("business_support_centers")
            p["dfrr_years"] = row.get("dfrr_years")

    if DREAM.exists():
        for row in json.loads(DREAM.read_text(encoding="utf-8")).get("hromadas") or []:
            code = (row.get("katottg") or "").strip()
            if not code:
                continue
            if code not in profiles:
                profiles[code] = {
                    "katottg": code,
                    "name": row.get("name") or code,
                    "short": short_name(row.get("name") or code),
                    "oblast": None,
                    "challenges": "",
                    "strengths": "",
                    "projects": "",
                    "challenge_sectors": set(),
                    "strength_sectors": set(),
                    "deficit_kinds": set(),
                    "offer_kinds": set(),
                    "dream_sectors": list(row.get("top_sectors") or []),
                    "own_income_per_capita": None,
                    "health_primary": None,
                    "health_known": False,
                    "competence_known": False,
                    "youth_centers": None,
                    "business_support_centers": None,
                    "dfrr_years": None,
                    "international_ties": False,
                }
            else:
                profiles[code]["dream_sectors"] = list(row.get("top_sectors") or [])

    if TWINNING.exists():
        for row in json.loads(TWINNING.read_text(encoding="utf-8")).get("hromadas") or []:
            code = (row.get("katottg") or "").strip()
            if code not in profiles:
                continue
            # registry confidence only (SKEW, decentralization_ua) — not
            # the lower-confidence Cities4Cities/strategy hypothesis rows.
            if any(p.get("confidence") == "registry" for p in row.get("partners") or []):
                profiles[code]["international_ties"] = True

    return profiles


def resource_offers(p: dict) -> set[str]:
    offers: set[str] = set()
    if p.get("health_known") and (p.get("health_primary") or 0) >= 3:
        offers.add("health_capacity")
    if p.get("competence_known") and (
        (p.get("youth_centers") or 0) >= 1 or (p.get("business_support_centers") or 0) >= 1
    ):
        offers.add("competence")
    if (p.get("own_income_per_capita") or 0) >= 4000:
        offers.add("fiscal_capacity")
    if (p.get("dfrr_years") or 0) >= 2:
        offers.add("dfrr_or_infra")
    if p.get("international_ties"):
        offers.add("international_ties")
    return offers


def resource_needs(challenges: str) -> set[str]:
    needs: set[str] = set()
    if not challenges:
        return needs
    for _key, pattern, need in RESOURCE_NEED_PATTERNS:
        if pattern.search(challenges):
            needs.add(need)
    return needs


def pair_reasons_weighted(a: dict, b: dict) -> tuple[list[str], float]:
    """Directed + symmetric complementary reasons with anti-saturation weights.

    v3: specific sectors (water/waste/energy/…) keep DREAM 1.0 / Strengths 0.85.
    Kitchen-sink sectors (освіта/культура/МСБ/…) are cheap and capped at 0.5
    total so a pair cannot saturate on template SWOT. Named deficit↔offer
    (worn water pipe, missing landfill, …) is 1.6. Resource proxy 0.55.
    Score = 1 - exp(-0.40 * weight_sum), then ×1.2 if same oblast (capped at 1).
    Require weight_sum ≥ 1.2.
    """
    reasons: list[str] = []
    kitchen_reasons: list[str] = []
    specific_w = 0.0
    kitchen_w = 0.0

    a_dream = set(a.get("dream_sectors") or [])
    a_str = set(a.get("strength_sectors") or [])
    b_dream = set(b.get("dream_sectors") or [])
    b_str = set(b.get("strength_sectors") or [])
    b_need = set(b.get("challenge_sectors") or [])
    a_need = set(a.get("challenge_sectors") or [])

    def add_sector(src: str, sector: str, offer_short: str, need_short: str) -> None:
        nonlocal specific_w, kitchen_w
        w = sector_hit_weight(sector, source=src)
        line = f"{src} «{sector}» у {offer_short} ↔ виклик у {need_short}"
        if sector in KITCHEN_SINK_SECTORS:
            kitchen_w += w
            kitchen_reasons.append(line)
        else:
            specific_w += w
            reasons.append(line)

    for s in sorted((a_dream | a_str) & b_need):
        src = "DREAM" if s in a_dream else "Strengths"
        add_sector(src, s, a["short"], b["short"])
    for s in sorted((b_dream | b_str) & a_need):
        src = "DREAM" if s in b_dream else "Strengths"
        add_sector(src, s, b["short"], a["short"])

    kitchen_w = min(kitchen_w, KITCHEN_SINK_CAP)
    if kitchen_reasons:
        extra = len(kitchen_reasons) - 1
        suffix = f" (+{extra} шаблонних секторів)" if extra > 0 else ""
        reasons.append(kitchen_reasons[0] + suffix)

    a_off = set(a.get("offer_kinds") or [])
    b_off = set(b.get("offer_kinds") or [])
    a_def = set(a.get("deficit_kinds") or [])
    b_def = set(b.get("deficit_kinds") or [])
    for kind in sorted(a_off & b_def):
        reasons.append(
            f"конкретний ресурс «{OFFER_LABELS.get(kind, kind)}» у {a['short']} "
            f"↔ дефіцит у {b['short']}"
        )
        specific_w += 1.6
    for kind in sorted(b_off & a_def):
        reasons.append(
            f"конкретний ресурс «{OFFER_LABELS.get(kind, kind)}» у {b['short']} "
            f"↔ дефіцит у {a['short']}"
        )
        specific_w += 1.6

    a_res = resource_offers(a)
    b_res = resource_offers(b)
    b_needs = resource_needs(b.get("challenges") or "")
    a_needs = resource_needs(a.get("challenges") or "")

    labels = {
        "health_capacity": "медмережа",
        "competence": "competence (молодь/бізнес)",
        "fiscal_capacity": "фіскальна ємність",
        "dfrr_or_infra": "досвід ДФРР/інфри",
        "international_ties": "міжнародні зв'язки / досвід з донорами",
    }
    for need in sorted(a_res & b_needs):
        reasons.append(f"ресурс «{labels.get(need, need)}» у {a['short']} ↔ потреба в {b['short']}")
        specific_w += 0.55
    for need in sorted(b_res & a_needs):
        reasons.append(f"ресурс «{labels.get(need, need)}» у {b['short']} ↔ потреба в {a['short']}")
        specific_w += 0.55

    weight_sum = specific_w + kitchen_w
    seen: set[str] = set()
    out: list[str] = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            out.append(r)
    out.sort(key=lambda r: (0 if "↔ дефіцит" in r else 1))
    return out, weight_sum


def same_oblast(a: dict, b: dict) -> bool:
    oa, ob = (a.get("oblast") or "").strip(), (b.get("oblast") or "").strip()
    return bool(oa and ob and oa == ob)


def complementary_score(weight_sum: float, same_ob: bool) -> float:
    import math

    if weight_sum < 1.2:
        return 0.0
    base = 1.0 - math.exp(-0.40 * weight_sum)
    if same_ob:
        base = min(1.0, base * 1.2)
    return round(base, 3)


def main() -> None:
    profiles = load_profiles()
    # Require real Challenges text (not dream-only synthetic profiles)
    with_challenges = [
        p
        for p in profiles.values()
        if (p.get("challenges") or "").strip() and p.get("challenge_sectors")
    ]
    with_offer = [
        p
        for p in profiles.values()
        if p.get("dream_sectors") or p.get("strength_sectors") or p.get("offer_kinds") or resource_offers(p)
    ]
    print(f"Profiles: {len(profiles)}; with challenges={len(with_challenges)}; with offers={len(with_offer)}")

    # Candidate pairs: each challenged hromada × offer hromadas (cap)
    edge_map: dict[frozenset[str], dict] = {}
    for need_p in with_challenges:
        scored: list[tuple[float, dict, list[str]]] = []
        for offer_p in with_offer:
            if offer_p["katottg"] == need_p["katottg"]:
                continue
            reasons, wsum = pair_reasons_weighted(offer_p, need_p)
            if not reasons:
                continue
            same = same_oblast(offer_p, need_p)
            score = complementary_score(wsum, same)
            if score <= 0:
                continue
            named_n = sum(1 for r in reasons if "↔ дефіцит" in r)
            scored.append((score, named_n, wsum, offer_p, reasons))
        scored.sort(key=lambda x: (-x[0], -x[1], -x[2]))
        # Prefer same-oblast in the shortlist: take up to 8 same-ob + fill to 12
        same_first = [x for x in scored if same_oblast(x[3], need_p)]
        cross = [x for x in scored if not same_oblast(x[3], need_p)]
        shortlist = same_first[:8] + cross[: max(0, 12 - len(same_first[:8]))]
        for score, named_n, _wsum, offer_p, reasons in shortlist:
            key = frozenset((need_p["katottg"], offer_p["katottg"]))
            prev = edge_map.get(key)
            if prev is None or score > prev["complementary_score"]:
                edge_map[key] = {
                    "a": need_p["name"],
                    "b": offer_p["name"],
                    "a_short": need_p["short"],
                    "b_short": offer_p["short"],
                    "a_katottg": need_p["katottg"],
                    "b_katottg": offer_p["katottg"],
                    "track": "complementary",
                    "complementary_score": score,
                    "reason_count": len(reasons),
                    "reasons": reasons[:6],
                    "same_oblast": same_oblast(need_p, offer_p),
                    "named_deficit": named_n > 0,
                    "known": False,
                }

    edges = sorted(
        edge_map.values(),
        key=lambda e: (
            -e["complementary_score"],
            -int(bool(e.get("named_deficit"))),
            -int(e["same_oblast"]),
            -e["reason_count"],
            e["a_short"],
            e["b_short"],
        ),
    )
    # Keep a publishable top slice
    edges = edges[:400]

    # Seed theme from complementary sector hits before rule-based package
    for e in edges:
        tags: list[str] = []
        for reason in e.get("reasons") or []:
            for sector in SECTOR_TO_THEME:
                if sector in reason or f"«{sector}»" in reason:
                    tags.append(sector)
                # reasons use short Ukrainian sector names sometimes
                head = sector.split()[0]
                if head and head in reason:
                    tags.append(sector)
        if tags:
            tid = SECTOR_TO_THEME.get(tags[0])
            if tid:
                e["theme"] = theme_label(tid)

    suggest = annotate_edges(edges)
    candidates = annotate_candidates(edges)

    generated = datetime.now(timezone.utc).isoformat()
    OUT.write_text(json.dumps(edges, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    MANIFEST.write_text(
        json.dumps(
            {
                "generatedAt": generated,
                "pairCount": len(edges),
                "namedDeficitPairs": sum(1 for e in edges if e.get("named_deficit")),
                "mssSuggest": {
                    "annotated": suggest["annotated"],
                    "withTheme": suggest["with_theme"],
                },
                "mssCandidate": {
                    "annotated": candidates["annotated"],
                    "withTheme": candidates["with_theme"],
                },
                "method": (
                    "complementary v3: named deficit↔offer + capped kitchen-sink sectors; "
                    "weighted DREAM/Strengths/resource → Challenges; "
                    "prefer named-deficit then same-oblast shortlist; "
                    "+ suggested_theme/form (mss_suggest) + mss_candidate package/signals"
                ),
                "warning": (
                    "МСС candidate hypotheses (complementary signal) — not v7 strategy matching, "
                    "not known=true. Keyword hit ≠ verified МСС plan."
                ),
                "inputs": [
                    "hromadas.json (Challenges/Strengths)",
                    "dream-priorities.json",
                    "hromada-resources.json",
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    preview = {
        "generatedAt": generated,
        "caveat": "Complementary hypotheses — resource/DREAM of one side ↔ challenge of the other. Not goals-cosine.",
        "pairCount": len(edges),
        "top": [
            {
                "a_short": e["a_short"],
                "b_short": e["b_short"],
                "complementary_score": e["complementary_score"],
                "same_oblast": e["same_oblast"],
                "named_deficit": bool(e.get("named_deficit")),
                "suggested_theme": e.get("suggested_theme"),
                "suggested_form": e.get("suggested_form"),
                "reasons": e["reasons"][:3],
            }
            for e in edges[:40]
        ],
    }
    PREVIEW.write_text(json.dumps(preview, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {OUT.relative_to(ROOT)} ({len(edges)} edges)")
    print(f"Wrote {PREVIEW.relative_to(ROOT)}")
    print(
        f"mss suggest: {suggest['with_theme']}/{suggest['annotated']} with theme"
    )
    print("Top 5:")
    for e in edges[:5]:
        print(
            f"  {e['complementary_score']:.3f} {e['a_short']} ↔ {e['b_short']}: "
            f"{e.get('suggested_theme')}/{e.get('suggested_form')} — {e['reasons'][0]}"
        )


if __name__ == "__main__":
    main()
