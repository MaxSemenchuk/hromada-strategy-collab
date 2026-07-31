#!/usr/bin/env python3
"""Suggest IMC package (theme + legal form) on matching edges.

Hypotheses only — never set known=true. Does not change combined `score`.

Theme from strategy/complementary/explicit text keywords (same family as
mss_analysis.categorize / agreement_essence). Form from rule table in
docs/mss-cooperation-research.md, optionally softened by registry priors.

Usage:
  from mss_suggest import annotate_edges, suggest_package
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MSS_REGISTRY = ROOT / "data" / "cache" / "mss" / "mss_registry.xlsx"

# Stable theme ids → Ukrainian labels (UI / release)
THEME_LABELS: dict[str, str] = {
    "cnap": "ЦНАП / адмінпослуги",
    "fire": "Пожежна охорона",
    "waste": "Поводження з відходами",
    "water": "Водопостачання / водовідведення",
    "education": "Освіта",
    "health": "Охорона здоров'я",
    "social": "Соціальні послуги",
    "tourism": "Туризм / кластер",
    "roads": "Дороги / інфраструктура",
    "archbud": "Архітектурно-будівельний контроль",
    "registration": "Державна реєстрація",
    "agglomeration": "Агломерація / метрополія",
    "security": "Безпека / ЦЗ",
    "other": "Інше / не визначено",
}

FORM_LABELS: dict[str, str] = {
    "joint_project": "спільний проєкт",
    "joint_finance": "спільне утримання",
    "delegation": "делегування",
    "joint_enterprise": "спільне КП",
    "joint_body": "спільний орган",
    "agglomeration": "агломерація",
}

# theme_id → list of compiled patterns (scored on blob)
_THEME_PATTERNS: list[tuple[str, re.Pattern[str], int]] = [
    ("agglomeration", re.compile(r"агломерац|метропол", re.I), 12),
    ("cnap", re.compile(r"цнап|адмін(?:істративн)?\w*\s*послуг|центр\s*дія|е-послуг", re.I), 10),
    ("fire", re.compile(r"пожежн", re.I), 10),
    ("archbud", re.compile(r"архітектурно-будівельн|архбуд|будівельн\w*\s*паспорт", re.I), 9),
    (
        "registration",
        re.compile(r"реєстрац\w*.{0,40}(?:акт|громадян|нерухом|речов)", re.I),
        8,
    ),
    ("waste", re.compile(r"відход|смітт|тпв|полігон|сортувал", re.I), 10),
    (
        "water",
        re.compile(r"водопостачан|водовідведен|водоканал|каналіз", re.I),
        10,
    ),
    ("tourism", re.compile(r"турист|спадщин|рекреац|маршрут|дмо\b|фестивал", re.I), 9),
    ("education", re.compile(r"освіт|школ|днз|дошкільн|ліце|садоч", re.I), 8),
    (
        "health",
        re.compile(r"медичн|охорони\s*здоров|амбулатор|лікарн|фап\b", re.I),
        8,
    ),
    ("social", re.compile(r"соціальн\w*\s*(?:послуг|захист)|впо\b|ветеран", re.I), 7),
    ("roads", re.compile(r"дорог|шляхов|вулиц|мост|міст\b|транспорт", re.I), 6),
    ("security", re.compile(r"безпек|укритт|цивільн\w*\s*захист|\bцз\b", re.I), 7),
]

# Complementary / DREAM sector tag → theme_id
SECTOR_TO_THEME: dict[str, str] = {
    "Освіта": "education",
    "Охорона здоров'я": "health",
    "Вода / каналізація (ЖКГ)": "water",
    "Довкілля / екологія": "waste",
    "Транспорт / логістика": "roads",
    "Безпека / ЦЗ": "security",
    "Туризм": "tourism",
    "Культура / спадщина": "tourism",
    "Соціальні послуги": "social",
    "Е-врядування": "cnap",
    "IT / цифровізація": "cnap",
}

# Default form by theme (docs/mss-cooperation-research.md)
THEME_DEFAULT_FORM: dict[str, str] = {
    "cnap": "delegation",
    "registration": "delegation",
    "archbud": "delegation",
    "fire": "joint_finance",
    "education": "joint_finance",
    "health": "joint_finance",
    "social": "joint_finance",
    "waste": "joint_enterprise",
    "water": "joint_enterprise",
    "tourism": "joint_project",
    "roads": "joint_project",
    "security": "joint_project",
    "agglomeration": "agglomeration",
    "other": "joint_project",
}

AGGLOMERATION_CAVEAT = (
    "окремий закон про агломерації ще не активний — поки асоціація ОМС / звичайне МСС"
)

_FORM_FROM_REGISTRY_TEXT = [
    (re.compile(r"делегуван", re.I), "delegation"),
    (re.compile(r"спільного\s+фінансуван|утриман", re.I), "joint_finance"),
    (
        re.compile(r"спільн\w+\s+комунальн\w+\s+підприєм|утворен\w+\s+спільн", re.I),
        "joint_enterprise",
    ),
    (re.compile(r"спільного\s+органу|орган\w+\s+управлін", re.I), "joint_body"),
    (re.compile(r"спільн\w+\s+про[еє]кт", re.I), "joint_project"),
]

_registry_priors_cache: dict[str, str] | None = None


def theme_label(theme_id: str | None) -> str | None:
    if not theme_id:
        return None
    return THEME_LABELS.get(theme_id, theme_id)


def form_label(form_id: str | None) -> str | None:
    if not form_id:
        return None
    return FORM_LABELS.get(form_id, form_id)


def detect_theme_scores(text: str) -> Counter[str]:
    scores: Counter[str] = Counter()
    if not (text or "").strip():
        return scores
    for theme_id, pat, weight in _THEME_PATTERNS:
        if pat.search(text):
            scores[theme_id] += weight
    return scores


def theme_from_sector_tags(tags: list[str] | set[str] | None) -> Counter[str]:
    scores: Counter[str] = Counter()
    for tag in tags or []:
        tid = SECTOR_TO_THEME.get(str(tag).strip())
        if tid:
            scores[tid] += 8
    return scores


def pick_theme(scores: Counter[str]) -> tuple[str | None, int]:
    if not scores:
        return None, 0
    theme_id, score = scores.most_common(1)[0]
    return theme_id, int(score)


def classify_registry_form(title: str, form_text: str) -> str | None:
    blob = f"{title or ''} {form_text or ''}"
    for pat, form_id in _FORM_FROM_REGISTRY_TEXT:
        if pat.search(blob):
            return form_id
    return None


def load_registry_theme_form_priors(
    path: Path | None = None,
) -> dict[str, str]:
    """Most-common legal form per detected theme in MinRegion registry XLSX."""
    global _registry_priors_cache
    if _registry_priors_cache is not None and path is None:
        return _registry_priors_cache
    xlsx = path or MSS_REGISTRY
    out: dict[str, str] = {}
    if not xlsx.exists():
        if path is None:
            _registry_priors_cache = out
        return out
    try:
        import openpyxl
    except ImportError:
        return out

    wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)
    ws = wb.active
    by_theme: dict[str, Counter[str]] = {}
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0 or not row:
            continue
        title = str(row[1] or "")
        form_text = str(row[6] or "") if len(row) > 6 else ""
        form_id = classify_registry_form(title, form_text)
        if not form_id:
            continue
        theme_id, _ = pick_theme(detect_theme_scores(f"{title} {form_text}"))
        if not theme_id or theme_id == "other":
            continue
        by_theme.setdefault(theme_id, Counter())[form_id] += 1
    for theme_id, counter in by_theme.items():
        out[theme_id] = counter.most_common(1)[0][0]
    if path is None:
        _registry_priors_cache = out
    return out


def suggest_form(
    theme_id: str | None,
    *,
    track: str | None = None,
    multi_party_hint: bool = False,
    agglomeration_mentioned: bool = False,
    registry_priors: dict[str, str] | None = None,
) -> tuple[str, str]:
    """Return (form_id, rationale)."""
    if agglomeration_mentioned or theme_id == "agglomeration":
        return "agglomeration", AGGLOMERATION_CAVEAT

    if multi_party_hint and theme_id in ("tourism", "waste", "water", None, "other"):
        if theme_id == "tourism":
            return "joint_project", "багатосторонній / кластерний сигнал → спільний проєкт"
        if theme_id in ("waste", "water"):
            return (
                "joint_enterprise",
                "інфраструктурний актив + кілька сторін → спільне КП (гіпотеза)",
            )

    form_id = THEME_DEFAULT_FORM.get(theme_id or "other", "joint_project")

    # Track overrides: cold-start vision → prefer light joint project unless
    # theme clearly needs delegation/finance/enterprise.
    if track == "thematic" and form_id in ("delegation", "joint_finance"):
        if theme_id == "tourism":
            form_id = "joint_project"
    if track == "operational" and theme_id in (None, "other"):
        form_id = "joint_project"
        return form_id, "операційний сусід без чіткої теми → легка форма (ст. 11)"

    priors = registry_priors if registry_priors is not None else load_registry_theme_form_priors()
    prior = priors.get(theme_id or "")
    rationale_parts: list[str] = []
    if theme_id:
        rationale_parts.append(f"тема «{theme_label(theme_id)}»")
    if prior and prior != form_id:
        # Soft: prefer rule table, mention prior as note
        rationale_parts.append(
            f"у реєстрі для цієї теми частіше «{form_label(prior)}»"
        )
    elif prior:
        form_id = prior
        rationale_parts.append("пріор реєстру Мінрегіону")
    else:
        rationale_parts.append("правило за темою")

    if track == "thematic":
        rationale_parts.append("схожа стратегія")
    elif track == "operational":
        rationale_parts.append("зручний сусід")
    elif track == "complementary":
        rationale_parts.append("доповнення ресурсів")
    elif track in ("explicit-ask", "explicit_ask"):
        rationale_parts.append("явний запит МСС")

    return form_id, " · ".join(rationale_parts)


def suggest_package(
    *,
    text_blob: str = "",
    track: str | None = None,
    sector_tags: list[str] | None = None,
    explicit_theme: str | None = None,
    reasons: list[str] | None = None,
    multi_party_hint: bool = False,
    registry_priors: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build suggested_theme / suggested_form payload for one edge."""
    scores = detect_theme_scores(text_blob)
    scores.update(theme_from_sector_tags(sector_tags))
    if reasons:
        scores.update(detect_theme_scores(" ".join(str(r) for r in reasons)))

    # Thematic track: boost vision themes so generic utility keywords in
    # long Goals lists do not always win.
    if track == "thematic":
        for tid in ("tourism", "agglomeration"):
            if scores.get(tid):
                scores[tid] += 6

    if explicit_theme:
        et = explicit_theme.strip().lower()
        mapped, _ = pick_theme(detect_theme_scores(explicit_theme))
        if mapped:
            scores[mapped] += 15
        elif "агломерац" in et:
            scores["agglomeration"] += 15
        elif "цнап" in et or "адмін" in et:
            scores["cnap"] += 15
        elif "турист" in et:
            scores["tourism"] += 15

    theme_id, theme_score = pick_theme(scores)
    if not theme_id:
        theme_id = "other"
        theme_score = 0

    agg = theme_id == "agglomeration" or bool(
        re.search(r"агломерац|метропол", text_blob or "", re.I)
    )
    form_id, form_rationale = suggest_form(
        theme_id,
        track=track,
        multi_party_hint=multi_party_hint,
        agglomeration_mentioned=agg,
        registry_priors=registry_priors,
    )

    confidence = "low"
    if theme_score >= 15:
        confidence = "high"
    elif theme_score >= 8:
        confidence = "medium"

    out: dict[str, Any] = {
        "suggested_theme": theme_label(theme_id),
        "suggested_theme_id": theme_id,
        "suggested_form": form_label(form_id),
        "suggested_form_id": form_id,
        "suggest_confidence": confidence,
        "suggest_rationale": form_rationale,
    }
    if form_id == "agglomeration":
        out["suggest_caveat"] = AGGLOMERATION_CAVEAT
    return out


def _profile_blob(row: dict, *, for_theme: bool = True) -> str:
    """Text used for theme detection.

    Prefer Goals/Projects/MSSAgreements — Challenges/Strengths often list
    generic waste/water needs and pollute pairwise themes.
    """
    if for_theme:
        parts = [
            row.get("Goals") or "",
            row.get("Projects") or "",
            row.get("MSSAgreements") or "",
            row.get("PartnersMentioned") or "",
        ]
    else:
        parts = [
            row.get("Goals") or "",
            row.get("Projects") or "",
            row.get("Challenges") or "",
            row.get("MSSAgreements") or "",
            row.get("PartnersMentioned") or "",
            row.get("Strengths") or "",
        ]
    return "\n".join(p for p in parts if p)


def annotate_edges(
    edges: list[dict],
    *,
    hromadas_by_name: dict[str, dict] | None = None,
    registry_priors: dict[str, str] | None = None,
) -> dict[str, int]:
    """Mutate edges in place with suggested_* fields. Returns counts."""
    priors = registry_priors if registry_priors is not None else load_registry_theme_form_priors()
    by_name = hromadas_by_name or {}
    counts = {"annotated": 0, "with_theme": 0, "agglomeration": 0}
    agg_re = re.compile(r"агломерац|метропол", re.I)

    for e in edges:
        a = by_name.get(e.get("a") or "")
        b = by_name.get(e.get("b") or "")
        blob_a = _profile_blob(a) if a else ""
        blob_b = _profile_blob(b) if b else ""
        blob = f"{blob_a}\n{blob_b}".strip()

        # Prefer existing edge theme / reasons (complementary, explicit-ask)
        sector_tags: list[str] = []
        for reason in e.get("reasons") or []:
            for sector in SECTOR_TO_THEME:
                if sector.split()[0].lower() in str(reason).lower() or sector in str(reason):
                    sector_tags.append(sector)

        pkg = suggest_package(
            text_blob=blob,
            track=e.get("track"),
            sector_tags=sector_tags or None,
            explicit_theme=e.get("theme") if isinstance(e.get("theme"), str) else None,
            reasons=list(e.get("reasons") or []),
            multi_party_hint=False,
            registry_priors=priors,
        )

        # Agglomeration is a metro-scale form: require signal on BOTH sides
        # (or an explicit curated theme), otherwise one hub pollutes all pairs.
        if pkg.get("suggested_form_id") == "agglomeration":
            both = bool(blob_a and blob_b and agg_re.search(blob_a) and agg_re.search(blob_b))
            explicit_agg = bool(
                isinstance(e.get("theme"), str)
                and agg_re.search(e["theme"])
            )
            if not (both or explicit_agg):
                # Downgrade: keep other strongest non-agg theme from the blob
                scores = detect_theme_scores(blob)
                scores.update(theme_from_sector_tags(sector_tags))
                if reasons := e.get("reasons"):
                    scores.update(detect_theme_scores(" ".join(str(r) for r in reasons)))
                scores.pop("agglomeration", None)
                theme_id, theme_score = pick_theme(scores)
                if not theme_id:
                    theme_id, theme_score = "other", 0
                form_id, form_rationale = suggest_form(
                    theme_id,
                    track=e.get("track"),
                    registry_priors=priors,
                )
                confidence = "low"
                if theme_score >= 15:
                    confidence = "high"
                elif theme_score >= 8:
                    confidence = "medium"
                pkg = {
                    "suggested_theme": theme_label(theme_id),
                    "suggested_theme_id": theme_id,
                    "suggested_form": form_label(form_id),
                    "suggested_form_id": form_id,
                    "suggest_confidence": confidence,
                    "suggest_rationale": form_rationale
                    + " · агломерація лише з одного боку — не піднято до форми",
                }

        e.update(pkg)
        # Drop stale caveat if we downgraded
        if pkg.get("suggested_form_id") != "agglomeration":
            e.pop("suggest_caveat", None)
        counts["annotated"] += 1
        if pkg.get("suggested_theme_id") not in (None, "other"):
            counts["with_theme"] += 1
        if pkg.get("suggested_form_id") == "agglomeration":
            counts["agglomeration"] += 1
    return counts


def load_hromadas_by_name(path: Path | None = None) -> dict[str, dict]:
    p = path or (ROOT / "data" / "releases" / "hromadas.json")
    if not p.exists():
        return {}
    import json

    raw = json.loads(p.read_text(encoding="utf-8"))
    rows = raw if isinstance(raw, list) else raw.get("list", [])
    return {(r.get("Name") or "").strip(): r for r in rows if (r.get("Name") or "").strip()}


def main() -> None:
    """Smoke: print registry priors + a few synthetic packages."""
    priors = load_registry_theme_form_priors()
    print(f"Registry theme→form priors ({len(priors)}):")
    for tid, fid in sorted(priors.items(), key=lambda x: theme_label(x[0]) or x[0]):
        print(f"  {theme_label(tid):<40} → {form_label(fid)}")

    demos = [
        {"text": "спільний ЦНАП та адміністративні послуги", "track": "operational"},
        {"text": "туристичний маршрут і фестиваль спадщини", "track": "thematic"},
        {"text": "полігон ТПВ та сортувальна лінія", "track": "operational"},
        {"text": "формування Львівської агломерації", "track": "thematic"},
    ]
    print("\nDemo packages:")
    for d in demos:
        pkg = suggest_package(text_blob=d["text"], track=d["track"], registry_priors=priors)
        print(
            f"  [{d['track']}] {d['text'][:40]}… → "
            f"{pkg['suggested_theme']} / {pkg['suggested_form']} "
            f"({pkg['suggest_confidence']})"
        )


if __name__ == "__main__":
    main()
