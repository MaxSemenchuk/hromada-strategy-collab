"""UA–EU cooperation themes — separate from domestic МСС (Law 1508) packaging.

Used on the MinRegion international-agreement register (Law 3668-IX) and
Interreg. Keep.eu official `themes[]` map into the same ids; English titles
are a fallback / supplement. Does not fold into v7 `score` and never sets
`known: true`. Extra ids (`economy`, `governance`, `borders`) exist only
on this layer so PIN theme filters stay untouched.
"""

from __future__ import annotations

import re
from collections import Counter

from mss_suggest import THEME_LABELS, THEME_LABELS_EN, detect_theme_scores

INTL_THEME_LABELS: dict[str, str] = {
    **THEME_LABELS,
    "economy": "Економіка / торгівля",
    "governance": "Врядування / інституції",
    "borders": "Кордон / митниця",
}

INTL_THEME_LABELS_EN: dict[str, str] = {
    **THEME_LABELS_EN,
    "economy": "Economy / trade",
    "governance": "Governance / institutions",
    "borders": "Border / customs",
}

# Bilingual extras on top of mss_suggest's UA registry patterns.
_INTL_EXTRA: list[tuple[str, re.Pattern[str], int]] = [
    (
        "economy",
        re.compile(
            r"економ|торгів|торгов|промислов|інвест|бізнес|"
            r"\beconom|\btrade\b|\bbusiness\b|\bsme\b|invest",
            re.I,
        ),
        8,
    ),
    (
        "governance",
        re.compile(
            r"самовряд|врядуван|інституційн|публічн\w*\s+управлін|"
            r"good\s+governance|public\s+admin|local\s+government",
            re.I,
        ),
        8,
    ),
    (
        "borders",
        re.compile(
            r"кордон|прикордон|митн|\bbcp\b|border\s+crossing|"
            r"border\s+coop|customs",
            re.I,
        ),
        10,
    ),
    (
        "health",
        re.compile(r"\bhealth\b|\bhospital\b|\bmedical\b|healthcare|palliative", re.I),
        8,
    ),
    (
        "water",
        re.compile(r"\bwater\b|wastewater|sewage|sewerage|\bflood\b|wetland", re.I),
        8,
    ),
    (
        "waste",
        re.compile(r"\bwaste\b|circular\s+econom|environment|\beco[\s\-]", re.I),
        7,
    ),
    (
        "energy",
        re.compile(r"\benergy\b|renewable|blackout|energy.?efficien", re.I),
        8,
    ),
    (
        "education",
        re.compile(r"\beducation\b|\bschool\b|\byouth\b|\bstem\b", re.I),
        8,
    ),
    (
        "culture",
        re.compile(r"\bculture\b|\bsport\b|\bheritage\b", re.I),
        7,
    ),
    (
        "tourism",
        re.compile(r"\btourism\b|tourist|recreat", re.I),
        8,
    ),
    (
        "security",
        re.compile(
            r"civil\s+protect|disaster|\bsafety\b|crisis|resilience|"
            r"emergency|надзвичай",
            re.I,
        ),
        8,
    ),
    (
        "fire",
        re.compile(r"\bfire\b|пожеж", re.I),
        9,
    ),
    (
        "roads",
        re.compile(r"\broad\b|transport|mobility|інфраструктур", re.I),
        6,
    ),
    (
        "social",
        re.compile(r"\bsocial\b|\bidp\b|veteran|гуманітар", re.I),
        7,
    ),
    (
        "cnap",
        re.compile(r"e-?government|e-?service|digitalis|цифровізац", re.I),
        7,
    ),
]


# keep.eu browse-API `themes[].title` → our ids. Unlisted titles (evaluation,
# rural development, generic innovation) stay unmapped; title heuristics fill
# the gap. Some keep.eu labels are compound → more than one id.
KEEP_THEME_TO_INTL: dict[str, tuple[str, ...]] = {
    "water management": ("water",),
    "health and social services": ("health", "social"),
    "traditional energy": ("energy",),
    "green technologies": ("energy",),
    "coastal management and maritime issues": ("water",),
    "urban development": ("archbud",),
    "multimodal transport": ("roads",),
    "demographic change and immigration": ("social",),
    "construction and renovation": ("archbud",),
    "scientific cooperation": ("education",),
    "managing natural and man-made threats, risk management": ("security",),
    "ict and digital society": ("cnap",),
    "sustainable management of natural resources": ("waste",),
    "labour market and employment": ("social",),
    "institutional cooperation and cooperation networks": ("governance",),
    "governance, partnership": ("governance",),
    "transport and mobility": ("roads",),
    "cultural heritage and arts": ("culture",),
    "regional planning and development": ("archbud",),
    "clustering and economic cooperation": ("economy",),
    "new products and services": ("economy",),
    "tourism": ("tourism",),
    "education and training": ("education",),
    "safety": ("security",),
    "logistics and freight transport": ("roads",),
    "renewable energy": ("energy",),
    "social inclusion and equal opportunities": ("social",),
    "waterways, lakes and rivers": ("water",),
    "sme and entrepreneurship": ("economy",),
    "energy efficiency": ("energy",),
    "improving transport connections": ("roads",),
    "soil and air quality": ("waste",),
    "waste and pollution": ("waste",),
    "agriculture and fisheries and forestry": ("economy",),
    "infrastructure": ("roads",),
    "cooperation between emergency services": ("security", "fire"),
    "climate change and biodiversity": ("waste",),
    "community integration and common identity": ("culture",),
}


def _uniq_ids(*groups: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for tid in group:
            if tid and tid not in seen:
                seen.add(tid)
                out.append(tid)
    return out


def map_keep_eu_themes(themes: list | None) -> list[str]:
    """Map keep.eu `{id, title}` (or title strings) onto intl theme ids."""
    ids: list[str] = []
    seen: set[str] = set()
    for item in themes or []:
        if isinstance(item, dict):
            title = (item.get("title") or item.get("name") or "").strip().lower()
        else:
            title = str(item or "").strip().lower()
        for tid in KEEP_THEME_TO_INTL.get(title, ()):
            if tid not in seen:
                seen.add(tid)
                ids.append(tid)
    return ids


def _text_or_none(value: object, limit: int = 240) -> str | None:
    if isinstance(value, dict):
        value = value.get("content") or value.get("title") or value.get("name")
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return text[:limit]


def keep_eu_project_themes(
    proj: dict | None = None,
    *,
    name_en: str = "",
    acronym: str = "",
) -> dict:
    """Official keep.eu theme fields + mapped ids; title heuristics fill gaps.

    `theme_source`: keep.eu | title | keep.eu+title | none.
    """
    proj = proj or {}
    raw: list[dict] = []
    for item in proj.get("themes") or []:
        if isinstance(item, dict) and (item.get("title") or item.get("name")):
            raw.append(
                {
                    "id": item.get("id"),
                    "title": item.get("title") or item.get("name"),
                }
            )
        elif isinstance(item, str) and item.strip():
            raw.append({"id": None, "title": item.strip()})
    official = map_keep_eu_themes(raw)
    heuristic = classify_intl_themes(name_en, acronym)
    extra = [tid for tid in heuristic if tid not in official]
    merged = _uniq_ids(official, extra)
    if official and extra:
        source = "keep.eu+title"
    elif official:
        source = "keep.eu"
    elif heuristic:
        source = "title"
    else:
        source = "none"
    return {
        "keep_themes": raw[:8],
        "theme_ids": merged[:8],
        "theme_source": source,
        "policy_objective": _text_or_none(proj.get("priority_policy_objective"), 160),
        "specific_objective": _text_or_none(proj.get("priority_specific_objective"), 240),
        "interreg_specific_objective": _text_or_none(
            proj.get("interreg_specific_objective"), 160
        ),
        "intervention": _text_or_none(proj.get("intervention_type"), 240),
    }


def classify_intl_themes(*parts: str) -> list[str]:
    """All matching theme ids, strongest first. Empty → []."""
    blob = " ".join(p for p in parts if p)
    if not blob.strip():
        return []
    scores: Counter[str] = detect_theme_scores(blob)
    for theme_id, pat, weight in _INTL_EXTRA:
        if pat.search(blob):
            scores[theme_id] += weight
    return [tid for tid, _ in scores.most_common() if tid]


def intl_theme_label(theme_id: str | None) -> str | None:
    if not theme_id:
        return None
    return INTL_THEME_LABELS.get(theme_id, theme_id)


def intl_theme_label_en(theme_id: str | None) -> str | None:
    if not theme_id:
        return None
    return INTL_THEME_LABELS_EN.get(theme_id, theme_id)


_PLACE_NOISE = re.compile(
    r"\b("
    r"гмін[аиуео]?|місто|міста|комун[аиуе]|повіт[уа]?|воєводств\w*|"
    r"район\w*|село|селищ\w*|громад[аиу]|territorial|gmina|commune|"
    r"municipality|city|town|county|voivodeship|landkreis|kreis"
    r")\b",
    re.I,
)


def partner_name_key(name: str | None) -> str:
    """Aggressive key for UA/Latin partner-name overlap (not a join id)."""
    s = _PLACE_NOISE.sub(" ", (name or "").lower())
    return re.sub(r"[^a-zа-яіїєґ]", "", s)


def names_overlap(a: str | None, b: str | None, min_len: int = 5) -> bool:
    ka, kb = partner_name_key(a), partner_name_key(b)
    if len(ka) < min_len or len(kb) < min_len:
        return False
    return ka == kb or ka in kb or kb in ka
