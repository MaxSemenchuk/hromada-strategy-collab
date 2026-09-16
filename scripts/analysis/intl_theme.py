"""UA–EU cooperation themes — separate from domestic МСС (Law 1508) packaging.

Used on the MinRegion international-agreement register (Law 3668-IX) and
Interreg project titles. Does not fold into v7 `score` and never sets
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
